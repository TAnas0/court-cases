import pandas as pd

from utils import accept_terms_and_conditions, format_case_details
from search import get_search_page_by_hearing_date, search_by_hearing_date
from utils import get_court_name_by_fips
from details import get_case_details


# Agree to the terms and conditions
session = accept_terms_and_conditions()

date = "07/01/2022"
date = "08/06/2022"
date = "01/02/2020"
results, last_page, last_index = get_search_page_by_hearing_date(session, date, 0)

results = search_by_hearing_date(session, date)

details = []
for case in results:
    case_details = get_case_details(session, case["qualifiedFips"], case["courtLevel"], case["divisionType"], case["caseNumber"])
    case_formatted = format_case_details(case | case_details)  # Merging search results with details response
    details.append(case_formatted)

df = pd.DataFrame(results)
df["courtName"] = df["qualifiedFips"].apply(get_court_name_by_fips)

cols = [
    "caseNumber",
    "formattedCaseNumber",
    ""
    # "Filed Date",
    # locality
    "name",


    "chargeDesc",
    "codeSection",
    "caseType",

    "offenseDate",

    "complainantName",
    "chargeAmended",

]

last_cols = [
    "qualifiedFips",

]

# Reorder columns of the DataFrame
cols = cols + df.columns.tolist() + last_cols
cols = sorted(set(cols), key=cols.index)
df = df[cols]

df.to_csv(f"output/{date.replace('/', '-')}.csv", index=False)


df = pd.DataFrame(details)
df.to_csv(
    f"output/{date.replace('/', '-')}-details.csv",
    index=False,
    columns=details[0].keys()
)

print()