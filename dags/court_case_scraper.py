from airflow import DAG
from airflow.sdk import task
from datetime import datetime, timedelta
from airflow.sdk import Param
import pandas as pd
import sys
from pathlib import Path

# Add the src directory to the Python path
# This is still needed unless we package the code properly
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from main import scrape_day_court_cases
from services.case import normalize_cases_dataframe, save_cases_dataframe_to_db
from utils import accept_terms_and_conditions, date_range

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
    
    # Iterate through the date range
    # Note: date_range generator in utils might need adjustment if it doesn't include end_date
    # For now assuming it works as intended or we adjust here.
    # The original code used: while date <= end_date: ... date += timedelta(days=1)
    
    current_date = start_date
    while current_date <= end_date:
        print(f"Scraping {current_date}")
        path = scrape_day_court_cases(current_date, session)
        if path:
            # Ensure path is string for XCom
            json_paths.append(str(path))
        current_date += timedelta(days=1)
        
    return json_paths

@task
def ingest_data(json_paths: list):
    if not json_paths:
        print("No data to ingest.")
        return

    for path in json_paths:
        print(f"Ingesting file: {path}")
        try:
            df = pd.read_json(path, lines=True)
            if not df.empty:
                df = normalize_cases_dataframe(df)
                save_cases_dataframe_to_db(df)
            else:
                print(f"File {path} is empty.")
        except ValueError as e:
            print(f"Error reading {path}: {e}")

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
    
    # Get params from DAG run context
    # Note: In TaskFlow, we can pass params directly if we access them from context or use Jinja templates
    # But for simplicity in this refactor, we'll pass them as arguments to the task
    
    # We need to retrieve the params. 
    # One way is to use a python_callable that gets context, but with decorators it's slightly different.
    # We can use '{{ params.start_date }}' if we want to rely on templates, 
    # but here we are calling the python function directly.
    
    # Let's use a wrapper task or just pass the values if we can.
    # Actually, standard way with TaskFlow is to just call the task.
    # The arguments will be resolved at runtime if we use templates, 
    # OR we can just access kwargs in the function if we accept **kwargs.
    
    # Let's try passing the templates.
    scraped_files = scrape_data(
        start_date_str='{{ params.start_date }}', 
        end_date_str='{{ params.end_date }}'
    )
    
    ingest_data(scraped_files)
