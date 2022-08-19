import os
import time
from datetime import date
import logging
import pandas as pd

from utils import (
    accept_terms_and_conditions,
    format_case_details,
    date_range,
    merge_dictionaries,
    get_csv_path,
    get_sample_court_case,
)
from search import search_by_hearing_date
from details import get_case_details


logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    # filemode='w',
    # format='%(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('requests_cache').setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Agree to the terms and conditions
session = accept_terms_and_conditions()

sample_court_case = get_sample_court_case(session)
# date = "07/01/2022"
# date = "08/06/2022"
# date = "01/02/2020"

start_date = date(2020, 1, 7)
end_date = date(2020, 2, 1)

logger.info(f"Scraping start from {start_date} to {end_date}")
for d in date_range(start_date, end_date): # ! Last day not included
    csv_path = get_csv_path(d)
    logger.info(f"Scraping court cases for date {d}")
    start_time = time.time()
    results = search_by_hearing_date(session, d.strftime("%m/%d/%Y"))
    logger.info(f"Found a total of {len(results)} search results for date {d}")
    logger.info(f"Getting search results of date {d} took {(time.time() - start_time)/60} minutes")

    details = []
    start_time = time.time()
    logger.info(f"Getting case details for date {d}")

    csv_directory = csv_path[:-6]
    if not os.path.exists(csv_directory):
        os.makedirs(csv_directory, exist_ok=True)
    try:
        previous_results = pd.read_csv(csv_path)
    except FileNotFoundError:
        logger.info(f"No scraped data found for date {d}. Creating CSV file with header...")
        with open(csv_path, "w") as f:
            f.write(f"{','.join(list(sample_court_case.keys()))}\n")
    for case in results:
        try:
            # Handle terms not accepted errors
            case_details = get_case_details(session, case["qualifiedFips"], case["courtLevel"], case["divisionType"], case["caseNumber"])
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
            # TODO Append to the day's CSV
            # raise KeyError
        except Exception as e:
            logger.exception(e)
    logger.info(f"Getting details of {len(results)} court cases took {(time.time() - start_time)/60} minutes")

    # if details:
    #     outdir = f"output/{d.strftime('%Y')}/{d.strftime('%m')}"
    #     if not os.path.exists(outdir):
    #         os.makedirs(outdir, exist_ok=True)

    #     path = f"output/{d.strftime('%Y')}/{d.strftime('%m')}/{d.strftime('%d')}.csv"
    #     df = pd.DataFrame(details)
    #     df.to_csv(
    #         f"{path}",
    #         index=False,
    #         columns=details[0].keys(),
    #     )

print()
