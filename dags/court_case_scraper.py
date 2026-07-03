import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.sdk import task, Param

from src.details import get_case_details
from src.search import search_by_hearing_date
from src.services.case import normalize_cases_dataframe, save_cases_to_parquet
from src.utils import accept_terms_and_conditions, get_json_path

logger = logging.getLogger(__name__)

# Tune between 200–500 based on observed case density per day.
# Lower = more workers, faster wall-clock time. Higher = fewer workers, less overhead.
BATCH_SIZE = 300

TMP_DIR = Path("output/tmp")

default_args = {
    "owner": "anas",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ── Task: Generate date list ──────────────────────────────────────────

@task
def generate_dates(start_date_str: str, end_date_str: str) -> list[str]:
    """Return a list of YYYY-MM-DD strings from start_date up to and including end_date."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    date_list = []
    current = start
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return date_list


# ── Task A: Search + batch (one instance per date) ───────────────────

@task(
    map_index_template="""
    [{{ map_index }}] {{ task.op_kwargs['date_str'] | to_datetime | strftime('%a, %-d %b, %Y') }}
    """
)
def search_and_batch(date_str: str, batch_size: int = BATCH_SIZE) -> list[str]:
    """Accept T&C, fetch all case stubs for the date, split into batch specs.

    Saves each chunk of stubs to temporary storage and returns a list of file paths.
    This avoids massive XCom serialization and database bloat.
    """
    session = accept_terms_and_conditions()
    formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    logger.info("Searching for hearing in date %s...", formatted)
    stubs = search_by_hearing_date(session, formatted)
    logger.info("Hearing in date=%s found=%d stubs", date_str, len(stubs))

    if not stubs:
        return []

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, start_idx in enumerate(range(0, len(stubs), batch_size)):
        chunk = stubs[start_idx : start_idx + batch_size]
        chunk_path = TMP_DIR / f"stubs_{date_str}_batch_{i}.json"
        with open(chunk_path, "w") as f:
            json.dump(chunk, f)
        paths.append(str(chunk_path))

    return paths


# ── Shim: Flatten list-of-lists before second expand() ───────────────

@task
def flatten_batches(batched_per_date: list[list[str]]) -> list[str]:
    """Merge the per-date batch file path lists into one flat list for expand().

    Input:  [[path_date0_b0, path_date0_b1], [path_date1_b0], ...]
    Output: [path_date0_b0, path_date0_b1, path_date1_b0, ...]
    """
    flat = []
    for paths in batched_per_date:
        flat.extend(paths)
    logger.info("total_batches_across_all_dates=%d", len(flat))
    return flat


# ── Task B: Fetch details (one instance per batch) ───────────────────

@task(max_active_tis_per_dag=10)
def fetch_details(file_path: str) -> str:
    """Fetch full case details for every stub in the assigned batch file.

    Reads stubs from the temporary JSON file, processes them, and writes
    results to a temporary JSONL file isolated to this batch. Deletes the
    temporary stub file after processing.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        logger.error("Stub file not found: %s", file_path)
        return ""

    # Parse date_str and batch_idx from filename
    # Pattern: stubs_{date_str}_batch_{batch_idx}.json
    stem = path_obj.stem
    parts = stem.split("_")
    date_str = parts[1]
    batch_idx = int(parts[3])

    with open(path_obj) as f:
        cases = json.load(f)

    session = accept_terms_and_conditions()

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = TMP_DIR / f"{date_str}_batch_{batch_idx}.jsonl"

    enriched = []
    failures = 0

    for stub in cases:
        try:
            details = get_case_details(
                session,
                stub["qualifiedFips"],
                stub["courtLevel"],
                stub["divisionType"],
                stub["caseNumber"],
            )
            enriched.append(stub | details)
        except Exception as exc:
            failures += 1
            logger.error("case=%s error=%s", stub.get("caseNumber"), exc)

    # Delete the temporary stubs file to keep storage clean
    path_obj.unlink(missing_ok=True)

    if enriched:
        pd.DataFrame(enriched).to_json(
            tmp_path, orient="records", lines=True, mode="w"
        )

    logger.info(
        "date=%s batch=%d written=%d failures=%d tmp=%s",
        date_str, batch_idx, len(enriched), failures, tmp_path,
    )

    if failures:
        logger.warning("batch_failures=%d/%d", failures, len(cases))

    return str(tmp_path) if enriched else ""


# ── Task: Consolidate temp files → per-date JSONL ────────────────────

@task
def consolidate_all(tmp_paths: list[str]) -> list[str]:
    """Merge all temp batch files into their final per-date JSONL files.

    Groups temp paths by date (extracted from filename), concatenates their
    content line-by-line into the canonical output path from get_json_path(),
    then deletes the temp files.

    Returns a list of finalised output paths (one per date that had results).
    """
    # Filter out empty-string returns from wholly-failed batches
    valid = [p for p in tmp_paths if p]

    by_date: dict[str, list[str]] = defaultdict(list)
    for p in valid:
        # Filename pattern: {date_str}_batch_{batch_idx}.jsonl
        stem = Path(p).stem                        # e.g. "2024-05-01_batch_2"
        date_str = stem.rsplit("_batch_", 1)[0]    # e.g. "2024-05-01"
        by_date[date_str].append(p)

    output_paths = []
    for date_str, paths in by_date.items():
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        final_path = Path(get_json_path(date))
        final_path.parent.mkdir(parents=True, exist_ok=True)

        with final_path.open("w") as outfile:
            for tmp in sorted(paths):  # sorted = deterministic batch order
                with open(tmp) as infile:
                    outfile.write(infile.read())

        for tmp in paths:
            Path(tmp).unlink(missing_ok=True)

        logger.info("date=%s batches_merged=%d final=%s", date_str, len(paths), final_path)
        output_paths.append(str(final_path))

    return output_paths


# ── Task: Ingest finalised JSONL → Postgres ───────────────────────────

@task
def ingest_data(path: str) -> None:
    """Ingest a single finalised JSONL file into Postgres via services/case.py.

    Uses stdlib json.loads instead of pd.read_json to avoid the ujson
    'cannot assemble with duplicate keys' error. The OCIS API response can
    produce records where the same key appears at different nesting levels;
    ujson hard-rejects these while stdlib json keeps the last value silently.
    """
    logger.info("ingesting path=%s", path)
    try:
        records = []
        with open(path) as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.warning("skipping malformed line path=%s line=%d error=%s", path, lineno, exc)

        if not records:
            logger.warning("empty file skipped path=%s", path)
            return

        df = pd.DataFrame(records)
        df = normalize_cases_dataframe(df)

        # Derive the Silver output path from the source JSONL path.
        # e.g. output/2024/05/01.jsonl → output/silver/2024/05/01.parquet
        silver_path = Path(path.replace("output/", "output/silver/", 1)).with_suffix(".parquet")
        silver_path.parent.mkdir(parents=True, exist_ok=True)
        save_cases_to_parquet(df, str(silver_path))
        logger.info("saved silver path=%s rows=%d", silver_path, len(df))


    except Exception as exc:
        logger.error("ingest_error path=%s error=%s", path, exc)
        raise


# ── DAG wiring ────────────────────────────────────────────────────────

with DAG(
    "court_case_scraper_workflow",
    default_args=default_args,
    description="Scrape court cases: search → batch → details → consolidate",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    params={
        "start_date": Param("2024-05-01", type="string"),
        "end_date": Param("2024-05-02", type="string"),
    },
) as dag:
    #
    # Step 1 — generate the date list
    #
    date_array = generate_dates(
        start_date_str="{{ params.start_date }}",
        end_date_str="{{ params.end_date }}",
    )

    #
    # Step 2 — Task A: one search_and_batch instance per date.
    # Returns list[list[dict]]: outer list = dates, inner list = batch_specs for that date.
    #
    batched_per_date = search_and_batch.expand(date_str=date_array)

    #
    # Step 3 — Flatten shim: collapse list[list[str]] → list[str].
    # This is what makes the second expand() work without cross-product mapping.
    #
    all_batch_paths = flatten_batches(batched_per_date=batched_per_date)

    #
    # Step 4 — Task B: one fetch_details instance per batch file path.
    # Each worker writes its own temp file and returns its path.
    #
    tmp_paths = fetch_details.expand(file_path=all_batch_paths)

    #
    # Step 5 — Consolidate: merge temp files into per-date JSONL, delete temps.
    # Returns list of final paths (one per date).
    #
    final_paths = consolidate_all(tmp_paths=tmp_paths)

    #
    # Step 6 — Ingest each finalised JSONL into Postgres.
    #
    ingest_data.expand(path=final_paths)
