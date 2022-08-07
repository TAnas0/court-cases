import time
from datetime import date
import pandas as pd

from utils import accept_terms_and_conditions, format_case_details, date_range
from search import search_by_hearing_date
from details import get_case_details


# Agree to the terms and conditions
session = accept_terms_and_conditions()

# date = "07/01/2022"
# date = "08/06/2022"
# date = "01/02/2020"

start_date = date(2020, 8, 6)
end_date = date(2020, 8, 9)

for d in date_range(start_date, end_date): # ! Last day not included
    results = search_by_hearing_date(session, d.strftime("%m/%d/%Y"))

    details = []
    start_time = time.time()
    print(f"Getting case details for date {d}")
    for case in results:
        try:
            case_details = get_case_details(session, case["qualifiedFips"], case["courtLevel"], case["divisionType"], case["caseNumber"])
            case_formatted = format_case_details(case | case_details)  # Merging search results with details response
            details.append(case_formatted)
        except Exception as e:
            print(e)
    print(f"Getting details took {time.time() - start_time} seconds")

    df = pd.DataFrame(details)
    df.to_csv(
        f"output/{d.strftime('%m/%d/%Y').replace('/', '-')}-details.csv",
        index=False,
        columns=details[0].keys()
    )

print()