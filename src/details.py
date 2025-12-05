# Get a case's details
import logging


logger = logging.getLogger(__name__)

def get_case_details(session, fips, court_level, division_type, case_number):
    logger.debug(f"Getting details for {fips}/{court_level}/{division_type}/{case_number}")
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
        raise e
    if res.status_code == 200:
        result = res.json()
        if result["context"]["entity"]["status"] == "SUCCESS":
            return result["context"]["entity"]["payload"]
        else:
            logger.debug(res)
            logger.debug(res.status_code)
            logger.debug(res.json())
            raise Exception("Details response indicated as FAILURE. PLease inspect the above.")
    else:
        logger.debug(res)
        logger.debug(res.status_code)
        logger.debug(res.json())
        raise Exception("Details response status code is not 200. Please inspect the above.")
