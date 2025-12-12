from src.models import Case, Hearing, Court, Judge, Participant, Charge
from src.utils import get_court_by_fips
import pytest
import json
# from src.services.case import convert_json_case_to_model, normalize_cases_dataframe
from src.services.case import normalize_cases_dataframe, save_cases_dataframe_to_db
import pandas as pd


# FILE_PATH = "./src/tests/models/01.json"
FILE_PATH = "./src/tests/models/output_file.json"
with open(FILE_PATH, 'r') as file:
    CASES = json.load(file)

# TODO use dtypes to specify types of some columns, improve efficiency and performance, and avoid automatic type guessing
# df = pd.read_json(FILE_PATH, convert_dates=False)

# FILE_PATH = "/home/bob/github/tanas0/portfolio/court-cases/output/2024/05/02.csv.json"
# df = pd.read_json(FILE_PATH, orient="records", lines=True)
# df = normalize_cases_dataframe(df)
# save_cases_dataframe_to_db(df)
# print()

def test_case_hearing_loading():
    """
    Load a fully defined case into the case model
    Requires loading into other models such as courts, hearings, attorney, etc.
    """
    case = CASES[0]
    # for case in CASES:
    #     convert_json_case_to_model(case)

    return
    print(case)

    participants = case["caseParticipant"]
    hearings = case["caseHearing"]

    case_court = case["caseCourt"]
    # court_data = get_court_by_fips(case_court.get("fipsCode"))
    court_data = get_court_by_fips(case.get("qualifiedFips"))
    court = Court(
        name=court_data.get("courtName"),
        court_type=court_data.get("courtTypeCode"),
        location="",
        fips_code=court_data,
    )

    # case_charge = case.get()
    charge = Charge(
        code_section=case.get("codeSection"),
        description=case.get("chargeDesc"),
        severity="",
        category="",
    )
    c = Case(
        case_number="",
        formatted_case_number="",
        name="",
        offense_date="",
        charge_amended="",
        code_section=case.get("codeSection"),
        charge_desc="",
        case_type="",

        court=court,
        charges=[charge],

        # participants="",
        # hearings="",
        # financial_information="",
    )

    print(court)

    for hearing in hearings:
        c.charges.append(Hearing(
            # schedule_date="",
            hearing_type=hearing.get("hearingType"),
            hearing_result=hearing.get("hearingResult"),
            court_room=hearing.get("courtRoom"),
            # continuance_code="",
            # plea="",
            # sequence_number="",
        ))
    return

    assert c.court == court