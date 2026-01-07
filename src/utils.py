from datetime import timedelta
import logging
import requests_cache
from inflection import underscore

import json
import ast
from pathlib import Path

from src.constants.main import courts
from src.details import get_case_details
from src.search import get_search_page_by_hearing_date


logger = logging.getLogger(__name__)

def accept_terms_and_conditions():
    # TODO: Relocate session initialization to a dedicated service
    session = requests_cache.CachedSession(
        'demo_cache1',
        expire_after=timedelta(days=30),
        allowable_codes=[200, 400], # Note: API may return 200 OK even for application-level failures
        allowable_methods=["POST"],
        stale_if_error=False,
    )
    session.get(
        url="https://eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
        },
        verify=False,
        timeout=30,
    )

    return session

def get_court_name_by_fips(fipsCode4):
    return list(filter(lambda d: d["fipsCode4"] == fipsCode4, courts))[0]["courtName"]

def get_court_by_fips(fipsCode4):
    return list(filter(lambda d: d["fipsCode4"] == fipsCode4, courts))[0]


def date_range(start_date, end_date):
    # https://stackoverflow.com/a/1060330/4017403
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_json_path(d):
    return f"output/{d.strftime('%Y')}/{d.strftime('%m')}/{d.strftime('%d')}.json"

def get_court_case_url(case):
    return f"https://eapps.courts.state.va.us/ocis/details;fromOcis=true;fullcaseNumber={case['qualifiedFips']}{case['divisionType']}{case['caseNumber']}"

def get_sample_court_case(session):
    """
    Gets a sample court case object
    Used to determine columns of the CSVs/Pandas
    """
    search = get_search_page_by_hearing_date(session, "01/01/2021", 0)
    search_results = search[0]
    case = search_results[0]
    # Fetch details for a specific known case for validation
    case_details = get_case_details(session, "770C", "C", "R", "2100000100")
    return case_details | case


def normalize_nullable_values(value, nullable_values, null_value):
    """
    Normalize nullable values.
    If `value` is in `nullable_values`, return `null_value`. Else return `value`.
    """
    if value not in nullable_values:
        return value
    else:
        return null_value


def to_snake_case(s):
    return underscore(s.strip()  # Remove leading/trailing spaces
            .replace(" ", "_")  # Replace spaces with underscores
            .replace("-", "_")  # Replace dashes with underscores
            .replace("/", "_"))  # Replace slashes with underscores


def try_json_loads(val):
    if not isinstance(val, str):
        return val
    val = val.strip()
    if not val or not val.startswith(("{", "[", "\"", "'")):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        return ast.literal_eval(val)  # Fallback for single-quoted dicts
    except (ValueError, SyntaxError):
        return val
