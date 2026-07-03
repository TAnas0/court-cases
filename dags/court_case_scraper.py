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

@task
def search_and_batch(date_str: str, batch_size: int = BATCH_SIZE) -> list[dict]:
    """Accept T&C, fetch all case stubs for the date, split into batch specs.

    Returns a list of batch_spec dicts — one per chunk — each carrying the
    date and its assigned slice of stubs. This list is collected by Airflow
    across all dates; flatten_batches then merges them before the second expand().

    Example return for 750 stubs at batch_size=300:
        [
            {"date_str": "2024-05-01", "batch_idx": 0, "cases": [stub_0 .. stub_299]},
            {"date_str": "2024-05-01", "batch_idx": 1, "cases": [stub_300 .. stub_599]},
            {"date_str": "2024-05-01", "batch_idx": 2, "cases": [stub_600 .. stub_749]},
        ]
    """
    session = accept_terms_and_conditions()
    formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    logger.info("Searching for hearing in date %s...", formatted)
    stubs = search_by_hearing_date(session, formatted)
    logger.info("Hearing in date=%s found=%d stubs", date_str, len(stubs))

    if not stubs:
        return []

    return [
        {"date_str": date_str, "batch_idx": i, "cases": stubs[i : i + batch_size]}
        for i in range(0, len(stubs), batch_size)
    ]


# ── Shim: Flatten list-of-lists before second expand() ───────────────

@task
def flatten_batches(batched_per_date: list[list[dict]]) -> list[dict]:
    """Merge the per-date batch spec lists into one flat list for expand().

    Airflow collects the XCom outputs of search_and_batch (one list per date)
    as a list-of-lists. expand() on that would create one worker per *date* —
    not per *batch*. This shim flattens it so expand() creates one worker per batch.

    Input:  [[spec_date0_b0, spec_date0_b1], [spec_date1_b0], ...]
    Output: [spec_date0_b0, spec_date0_b1, spec_date1_b0, ...]
    """
    flat = []
    for date_specs in batched_per_date:
        flat.extend(date_specs)
    logger.info("total_batches_across_all_dates=%d", len(flat))
    return flat


# ── Task B: Fetch details (one instance per batch) ───────────────────

@task(max_active_tis_per_dag=10)
def fetch_details(batch_spec: dict) -> str:
    """Fetch full case details for every stub in the assigned batch.

    Writes results to a temporary JSONL file isolated to this batch.
    Returns the temp file path so consolidate_all can locate it.
    Returns an empty string if the entire batch fails.

    Temp path pattern: output/tmp/{date_str}_batch_{batch_idx}.jsonl
    """
    date_str: str = batch_spec["date_str"]
    batch_idx: int = batch_spec["batch_idx"]
    cases: list[dict] = batch_spec["cases"]

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
        save_cases_to_parquet(df)

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
    # Step 3 — Flatten shim: collapse list[list[dict]] → list[dict].
    # This is what makes the second expand() work without cross-product mapping.
    #
    all_batch_specs = flatten_batches(batched_per_date=batched_per_date)

    #
    # Step 4 — Task B: one fetch_details instance per batch_spec.
    # Each worker writes its own temp file and returns its path.
    #
    tmp_paths = fetch_details.expand(batch_spec=all_batch_specs)

    #
    # Step 5 — Consolidate: merge temp files into per-date JSONL, delete temps.
    # Returns list of final paths (one per date).
    #
    final_paths = consolidate_all(tmp_paths=tmp_paths)

    #
    # Step 6 — Ingest each finalised JSONL into Postgres.
    #
    ingest_data.expand(path=final_paths)
