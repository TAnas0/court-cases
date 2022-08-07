def get_search_page_by_hearing_date(session, date, last_index):
    print(f"Searching court cases after last index: {last_index}")
    url = "https://eapps.courts.state.va.us/ocis-rest/api/public/search"
    headers = {
        "Accept": "application/json, text/plain, */*",
    }
    data = {
        "courtLevels": [],
        "divisions": [
            "Criminal/Traffic"
        ],
        # "selectedCourts": ["003G"],
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
    count = 0
    print(f"Searchin date {date}")
    all_results = []
    page = 1
    last_page = False
    last_index = 0
    while not last_page:
        count += 1
        results, last_page, last_index = get_search_page_by_hearing_date(session, date, last_index)
        all_results += results
        page += 1
    print(f"Search requests count {count}")
    print(f"Found a total of {len(results)} court cases for date {date}")
    return all_results    