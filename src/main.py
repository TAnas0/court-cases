import time
from datetime import date
import logging
import pandas as pd

from utils import (
    accept_terms_and_conditions,
    date_range,
    get_json_path,
    get_sample_court_case,
)
from search import search_by_hearing_date
from details import get_case_details


def setup_logging():
    logging.basicConfig(
        filename='app.log',
        level=logging.DEBUG,
    )
    logging.getLogger('requests_cache').setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from pathlib import Path

def scrape_day_court_cases(date, session=None):
    if session is None:
        session = accept_terms_and_conditions()
        
    json_path = get_json_path(date)
    # Ensure directory exists
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    results = search_by_hearing_date(session, date.strftime("%m/%d/%Y"))
    logger.info(f"Found a total of {len(results)} search results for date {date}")
    logger.info(f"Getting search results of date {date} took {(time.time() - start_time)/60} minutes")

    if not results:
        logger.info(f"No results found for date {date}")
        return json_path

    details = []
    failure_count = 0
    for index, case in enumerate(results):
        try:
            case_details = get_case_details(
                session,
                case["qualifiedFips"],
                case["courtLevel"],
                case["divisionType"],
                case["caseNumber"],
            )
            case_formatted = case | case_details  # Merging search results with details response
            details.append(case_formatted)
            if (details and len(details) % 100 == 0) or case == results[-1]:
                df = pd.DataFrame(details)
                df.to_json(
                    json_path,
                    orient="records",
                    lines=True,
                    mode="a",
                )
                print(f"Saved {index} court cases details for {date}")
                details = []

        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to process case {case.get('caseNumber')}: {e}")
            # Continue to next case instead of crashing
            continue
            
    if failure_count > 0:
        logger.warning(f"Encountered {failure_count} failures while processing {len(results)} cases for date {date}")
    logger.info(f"Getting details of {len(results)} court cases took {(time.time() - start_time)/60} minutes")
    return json_path
    

def main():
    setup_logging()
    start_date = date(2021, 1, 1)
    end_date = date(2021, 2, 1)

    logger.info(f"Scraping start from {start_date} to {end_date}")
    
    session = accept_terms_and_conditions()
    # sample_court_case = get_sample_court_case(session)

    for d in date_range(start_date, end_date): # ! Last day not included
        scrape_day_court_cases(d, session)

if __name__ == "__main__":
    main()
