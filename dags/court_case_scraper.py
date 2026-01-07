from airflow import DAG
from airflow.sdk import task
from datetime import datetime, timedelta
from airflow.sdk import Param
import pandas as pd
from src.main import scrape_day_court_cases
from src.services.case import normalize_cases_dataframe, save_cases_dataframe_to_db
from src.utils import accept_terms_and_conditions, date_range

default_args = {
    'owner': 'anas',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

@task
def scrape_data(start_date_str: str, end_date_str: str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    session = accept_terms_and_conditions()
    json_paths = []
    
    current_date = start_date
    while current_date <= end_date:
        print(f"Scraping {current_date}")
        path = scrape_day_court_cases(current_date, session)
        if path:
            json_paths.append(str(path))
        current_date += timedelta(days=1)
        
    return json_paths

@task
def ingest_data(json_paths: list):
    if not json_paths:
        print("No paths provided for ingestion.")
        return

    for path in json_paths:
        print(f"Ingesting: {path}")
        try:
            df = pd.read_json(path, lines=True)
            if not df.empty:
                df = normalize_cases_dataframe(df)
                save_cases_dataframe_to_db(df)
            else:
                print(f"Warning: File {path} is empty.")
        except ValueError as e:
            print(f"Error processing {path}: {e}")

with DAG(
    'court_case_scraper_workflow',
    default_args=default_args,
    description='Scrape court cases with customizable date ranges',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    params={
        "start_date": Param("2024-05-01", type="string"),
        "end_date": Param("2024-05-02", type="string"),
    },
) as dag:
    
    scraped_files = scrape_data(
        start_date_str='{{ params.start_date }}', 
        end_date_str='{{ params.end_date }}'
    )
    
    ingest_data(scraped_files)
