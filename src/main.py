import pandas as pd
from utils import accept_terms_and_conditions
from search import get_search_page_by_hearing_date, search_by_hearing_date
from utils import get_court_name_by_fips


# Agree to the terms and conditions
session = accept_terms_and_conditions()

date = "07/01/2022"
date = "08/06/2022"
date = "01/02/2020"
results, last_page, last_index = get_search_page_by_hearing_date(session, date, 0)

results = search_by_hearing_date(session, date)
print(results)
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

# TODO Separate hearing datetime, into hearing date and hearing time

df.to_csv(f"output/{date.replace('/', '-')}.csv", index=False)


print()