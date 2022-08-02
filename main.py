import requests
from utils import accept_terms_and_conditions
from search import get_search_page_by_hearing_date

# Agree to the terms and conditions
session = accept_terms_and_conditions()

results, last_page = get_search_page_by_hearing_date(session, "07/01/2022", 9999)

print(results)
