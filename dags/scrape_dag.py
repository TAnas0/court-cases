from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.models import Variable  # For user-defined variables
from airflow.models.param import Param, ParamsDict
import pandas as pd

import sys
from pathlib import Path
# Add the src directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from main import scrape_day_court_cases
from services.case import normalize_cases_dataframe, save_cases_dataframe_to_db


default_args = {
    'owner': 'anas',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Scraper function for a date range
def scrape_court_cases(start_date, end_date):
    # Scraping code as defined earlier
    date = start_date

    while date <= end_date:
        print(date)
        scrape_day_court_cases(date)
        date += timedelta(days=1)
    pass

# Functions for each option
def scrape_date_range(start_date, end_date, **kwargs):
    # params: ParamsDict = kwargs["params"]
    # start_date = datetime.strptime(params["start_date"], "%Y-%m-%d")
    # end_date = datetime.strptime(params["end_date"], "%Y-%m-%d")
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    scrape_court_cases(start_date, end_date)

def scrape_specific_month(**kwargs):
    params: ParamsDict = kwargs["params"]
    year = params["year"]
    month = params["month"]
    start_date = datetime(year, month, 1)
    end_date = (start_date + timedelta(days=30)).replace(day=1) - timedelta(days=1)
    scrape_court_cases(start_date, end_date)

def scrape_entire_year(year, **kwargs):
    params: ParamsDict = kwargs["params"]
    year = params["year"]
    for month in range(1, 13): # TODO Loop based on dates
        start_date = datetime(year, month, 1)
        end_date = (start_date + timedelta(days=30)).replace(day=1) - timedelta(days=1)
        scrape_court_cases(start_date, end_date)


def load_and_insert_db(**context):
    path = context['ti'].xcom_pull(key='jsonl_path')

    df = pd.read_json(path, lines=True)
    df = normalize_cases_dataframe(df)
    save_cases_dataframe_to_db(df)
    # Load JSONL file into DF
    # Normalize DF
    # Load into models
    # Save into DB

    return

# Defining the DAG
with DAG(
    'court_case_scraper',
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

    print(dag.params)
    print(dag.params["start_date"])
    # Task for custom date range
    scrape_custom_range = PythonOperator(
        task_id='scrape_custom_range',
        python_callable=scrape_date_range,
        op_kwargs={
            'start_date': dag.params["start_date"],
            'end_date': dag.params["end_date"],
        }
        # op_kwargs={
        #     'start_date': Variable.get("start_date", default_var="2024-01-01"),
        #     'end_date': Variable.get("end_date", default_var="2024-01-07"),
        # }
    )
    
    
    ingest = PythonOperator(
        task_id="ingest_to_db",
        python_callable=load_and_insert_db
    )

    scrape_custom_range >> ingest





# Separate scraping of a whole year into 12 months
def generate_monthly_tasks(year):
    tasks = []
    for month in range(1, 13):
        start_date = datetime(year, month, 1)
        end_date = (start_date + timedelta(days=31)).replace(day=1)  # First day of the next month
        tasks.append({
            "task_id": f"scrape_{start_date.strftime('%Y_%m')}",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            # "start_date": start_date,
            # "end_date": end_date,
        })
    return tasks

with DAG(
    "yearly_scrape_split_to_months",
    default_args=default_args,
    schedule=None,  # Trigger manually
) as dag:

    year = 2023  # Example: change as needed or make it dynamic

    # Generate monthly tasks
    monthly_tasks = generate_monthly_tasks(year)

    # Create a task for each month
    for task_info in monthly_tasks:
        scrape_task = PythonOperator(
            task_id=task_info["task_id"],
            python_callable=scrape_date_range,
            op_kwargs={
                "start_date": task_info["start_date"],
                "end_date": task_info["end_date"],
            },
        )