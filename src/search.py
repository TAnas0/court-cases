import logging
import requests

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _log_retry(retry_state):
    logger.warning(
        f"Retrying request (attempt {retry_state.attempt_number}): "
        f"{retry_state.outcome.exception()}"
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    before_sleep=_log_retry,
)
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
        raise

    if res.status_code == 200:
        try:
            payload = res.json()["context"]["entity"].get("payload")
            if payload:
                return payload.get("searchResults"), payload.get("hasMoreRecords") != "Y", payload.get("lastResponseIndex")
            else:
                logger.info(f"Empty payload for date {date}, last_index {last_index}")
                return None, None, None
        except KeyError as e:
            logger.error("Failed to parse search response: context.entity.payload missing")
            raise
    else:
        raise Exception(f"Search request failed with status {res.status_code}: {res.text}")

def search_by_hearing_date(session, date):
    count = 0
    all_results = []
    page = 1
    last_page = False
    last_index = 0
    logger.debug(f"Starting search for date {date}")
    while not last_page:
        count += 1
        if count and count % 50 == 0:
            logger.debug(f"Searching court cases after last index: {last_index}")
        results, last_page, last_index = get_search_page_by_hearing_date(session, date, last_index)
        if results:
            all_results += results
        logger.debug(f"Page {page}: Found {len(results) if results else 0} results. Total so far: {len(all_results)}")
        page += 1
    logger.debug(f"Getting all search results for date {date} required {count} network requests")
    return all_results