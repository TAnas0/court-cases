def get_search_page_by_hearing_date(session, date, page):
    url = "https://eapps.courts.state.va.us/ocis-rest/api/public/search"
    headers = {
        "Accept": "application/json, text/plain, */*",
    }
    data = {
        "courtLevels": [],
        "divisions": [
            "Criminal/Traffic"
        ],
        "selectedCourts": [],
        "searchString": [
            date
        ],
        "searchBy": "HD"
    }
    res = session.post(url, headers=headers, json=data)
    if res.status_code == 200:
        res = res.json()["context"]["entity"]["payload"]
        return res["searchResults"], res["hasMoreRecords"] == "N"
    else:
        raise Exception()

def search_by_hearing_date(session, date):
    all_results = []
    page = 1
    last_page = False
    while not last_page:
        results, last_page = get_search_page_by_hearing_date(session, date, page)
        all_results += results
        page += 1

    return all_results    