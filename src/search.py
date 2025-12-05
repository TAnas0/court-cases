import logging


logger = logging.getLogger(__name__)

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
        # "selectedCourts": ["003G"],
        "selectedCourts": [],
        "searchString": [
            date
        ],
        "searchBy": "HD",
        "endingIndex": last_index,
    }
    logger.debug(f"Fetching search page for date {date}, last_index {last_index}")
    try:
        res = session.post(url, headers=headers, json=data, timeout=30)
    except Exception as e:
        logger.error(f"Request failed for date {date}, last_index {last_index}: {e}")
        raise e
        
    logger.debug(f"Received response status: {res.status_code}")
    if res.status_code == 200:
        try:
            res = res.json()["context"]["entity"].get("payload", None)
            if res:
                return res.get("searchResults", None), res.get("hasMoreRecords", None) != "Y", res.get("lastResponseIndex", None)
            else:
                logger.info(f"Error response getting search page for date {date} and last_index {last_index}")
                return None, None, None
        except KeyError as e:
            logger.error("Unexpected Error in search request. Returned status code was 200, but processing failed")
            logger.exception(e)
            raise e
    else:
        logger.debug(res)
        logger.debug(res.status_code)
        logger.debug(res.json())
        raise Exception("Details response status code is not 200. Please inspect the above.")

def search_by_hearing_date(session, date):
    count = 0
    all_results = []
    page = 1
    last_page = False
    last_index = 0
    while not last_page:
        count += 1
        if count and count % 50 == 0:
            logger.debug(f"Searching court cases after last index: {last_index}")
        results, last_page, last_index = get_search_page_by_hearing_date(session, date, last_index)
        if results:
            all_results += results
        page += 1
    logger.debug(f"Getting all search results for date {date} required {count} network requests")
    return all_results    