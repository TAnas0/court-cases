# Get a case's details
import logging
import requests

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def get_case_details(session, fips, court_level, division_type, case_number):
    logger.debug(
        f"Getting details for {fips}/{court_level}/{division_type}/{case_number}"
    )
    url = "https://eapps.courts.state.va.us/ocis-rest/api/public/getCaseDetails"
    data = {
        "qualifiedFips": fips,
        "courtLevel": court_level,
        "divisionType": division_type,
        "caseNumber": case_number,
    }
    try:
        res = session.post(url, json=data, timeout=30)
    except Exception as e:
        logger.error(f"Details request failed for {case_number}: {e}")
        raise
    if res.status_code == 200:
        result = res.json()
        if result["context"]["entity"]["status"] == "SUCCESS":
            return result["context"]["entity"]["payload"]
        else:
            logger.error(
                f"Details response FAILURE for {case_number}: status={res.status_code} "
                f"body={res.text[:500]}"
            )
            raise Exception(
                f"Details response indicated as FAILURE for {case_number}. Inspect logs above."
            )
    else:
        raise Exception(
            f"Details request failed with status {res.status_code}: {res.text}"
        )
