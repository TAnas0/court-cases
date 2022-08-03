import pandas as pd
from utils import accept_terms_and_conditions
from search import get_search_page_by_hearing_date, search_by_hearing_date

# Agree to the terms and conditions
session = accept_terms_and_conditions()

date = "07/01/2022"
results, last_page, last_index = get_search_page_by_hearing_date(session, date, 0)

results = search_by_hearing_date(session, date)
print(results)
df = pd.DataFrame(results)
df.to_csv(f"{date.replace('/', '-')}.csv")
print()