import os
import time
from datetime import date
import logging
import pandas as pd

from utils import (
    accept_terms_and_conditions,
    format_case_details,
    date_range,
    get_csv_path,
    get_sample_court_case,
)
from search import search_by_hearing_date
from details import get_case_details


logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
)
logging.getLogger('requests_cache').setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Agree to the terms and conditions
session = accept_terms_and_conditions()

sample_court_case = get_sample_court_case(session)

start_date = date(2021, 1, 1)
end_date = date(2021, 2, 1)

def scrape_day_court_cases(session, date):
    csv_path = get_csv_path(date)
    start_time = time.time()
    results = search_by_hearing_date(session, date.strftime("%m/%d/%Y"))
    logger.info(f"Found a total of {len(results)} search results for date {date}")
    logger.info(f"Getting search results of date {date} took {(time.time() - start_time)/60} minutes")

    start_time = time.time()
    details = []
    for case in results:
        try:
            case_details = get_case_details(
                session,
                case["qualifiedFips"],
                case["courtLevel"],
                case["divisionType"],
                case["caseNumber"],
            )
            case_formatted = format_case_details(case | case_details)  # Merging search results with details response
            details.append(case_formatted)
            if (details and len(details) % 100 == 0) or case == results[-1]:
                df = pd.DataFrame(details)
                df.to_csv(
                    f"{csv_path}",
                    index=False,
                    header=False,
                    mode="a",
                    columns=sample_court_case.keys(),
                )
                details = []

        except Exception as e:
            logger.exception(e)
            raise e
    logger.info(f"Getting details of {len(results)} court cases took {(time.time() - start_time)/60} minutes")
    

def prepare_csv_file_location(date): # TODO rename
    """
    Ensure directory of the CSV for the date exists
    Ensure the CSV exists with the right header

    Args:
        date (_type_): _description_
    """
    csv_path = get_csv_path(date)
    csv_directory = csv_path[:-6]
    if not os.path.exists(csv_directory):
        os.makedirs(csv_directory, exist_ok=True)
    try:
        previous_results = pd.read_csv(csv_path)
        # TODO handle cache of a day
    except FileNotFoundError:
        logger.info(f"No scraped data found for date {date}. Creating CSV file with header...")
        with open(csv_path, "w") as f:
            sample_court_case = get_sample_court_case(session)
            f.write(f"{','.join(list(sample_court_case.keys()))}\n")
            return

logger.info(f"Scraping start from {start_date} to {end_date}")

if __name__ == "__main__":
    for d in date_range(start_date, end_date): # ! Last day not included
        prepare_csv_file_location(d)
        scrape_day_court_cases(session, d)
