import logging
from airflow import DAG
from airflow.sdk import task
from datetime import datetime, timedelta
from airflow.models.param import Param
import pandas as pd

from src.main import scrape_day_court_cases
from src.services.case import normalize_cases_dataframe, save_cases_dataframe_to_db
from src.utils import accept_terms_and_conditions

logger = logging.getLogger(__name__)

default_args = {
    "owner": "anas",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@task
def generate_dates(start_date_str: str, end_date_str: str) -> list:
    """Generates a list of date strings between start and end dates."""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    return date_list


# @task(pool="court_website_pool") # Pool to be created and configured
@task(max_active_tis_per_dag=10)
def scrape_data(date_str: str):
    """Scrapes a single day of court cases.

    Each dynamic-mapped task instance creates its own RateLimitedCachedSession by
    calling accept_terms_and_conditions(). This ensures rate limiting and caching are
    active in every worker — passing only cookies via XCom would silently drop the
    LimiterMixin from the session.
    """
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    logger.info(f"Scraping {current_date}")

    session = accept_terms_and_conditions()

    path = scrape_day_court_cases(current_date, session)

    # Return the path if found, or None if empty
    return str(path) if path else None


@task
def filter_valid_paths(paths: list) -> list:
    """Filters out None values so we don't map over empty paths."""
    return [p for p in paths if p is not None]


@task
def ingest_data(path: str):
    """Ingests a single JSON file into the DB."""
    logger.info(f"Ingesting: {path}")
    try:
        df = pd.read_json(path, lines=True)
        if not df.empty:
            df = normalize_cases_dataframe(df)
            save_cases_dataframe_to_db(df)
        else:
            logger.warning(f"File {path} is empty.")
    except ValueError as e:
        logger.error(f"Error processing {path}: {e}")



with DAG(
    "court_case_scraper_workflow",
    default_args=default_args,
    description="Scrape court cases with customizable date ranges",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    params={
        "start_date": Param("2024-05-01", type="string"),
        "end_date": Param("2024-05-02", type="string"),
    },
) as dag:
    date_array = generate_dates(
        start_date_str="{{ params.start_date }}", end_date_str="{{ params.end_date }}"
    )

    scraped_files = scrape_data.override(task_id="dynamic_scrape").expand(
        date_str=date_array
    )

    valid_files = filter_valid_paths(scraped_files)

    ingest_data.expand(path=valid_files)
