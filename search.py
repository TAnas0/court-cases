def get_search_page_by_hearing_date(session, date, last_index):
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
        "searchBy": "HD",
        "endingIndex": last_index,
    }
    res = session.post(url, headers=headers, json=data)
    if res.status_code == 200:
        res = res.json()["context"]["entity"]["payload"]
        return res["searchResults"], res.get("hasMoreRecords", None) != "Y", res.get("lastResponseIndex", None)
    else:
        raise Exception()

def search_by_hearing_date(session, date):
    all_results = []
    page = 1
    last_page = False
    last_index = 0
    while not last_page:
        results, last_page, last_index = get_search_page_by_hearing_date(session, date, last_index)
        all_results += results
        page += 1

    return all_results    