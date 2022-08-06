import pandas as pd

from utils import accept_terms_and_conditions, format_case_details
from search import search_by_hearing_date
from details import get_case_details


# Agree to the terms and conditions
session = accept_terms_and_conditions()

date = "07/01/2022"
date = "08/06/2022"
date = "01/02/2020"

results = search_by_hearing_date(session, date)

details = []
for case in results:
    case_details = get_case_details(session, case["qualifiedFips"], case["courtLevel"], case["divisionType"], case["caseNumber"])
    case_formatted = format_case_details(case | case_details)  # Merging search results with details response
    details.append(case_formatted)

df = pd.DataFrame(details)
df.to_csv(
    f"output/{date.replace('/', '-')}-details.csv",
    index=False,
    columns=details[0].keys()
)

print()