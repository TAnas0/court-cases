from collections import OrderedDict
# from datetime import timedelta
import requests_cache
from constants.main import courts


def accept_terms_and_conditions():
    # TODO Get session creation out of here!
    session = requests_cache.CachedSession(
        'demo_cache1',
        allowable_codes=[200, 400], # ! The API can return 200 responses on failures
        allowable_methods=["POST"],  # Excludes GET request to accept terms and conditions
        # urls_expire_after={
        #     "eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted": requests_cache.DO_NOT_CACHE,
        #     "*": timedelta(days=1),
        #     # "*": requests_cache.DO_NOT_CACHE,
        #     # "eapps.courts.state.va.us/ocis-rest/api/public/getCaseDetails": 0,
        # }
        stale_if_error=False,
    )
    session.get(
        url="https://eapps.courts.state.va.us/ocis-rest/api/public/termsAndCondAccepted",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
        },
    )

    return session

def get_court_name_by_fips(fipsCode4):
    return list(filter(lambda d: d["fipsCode4"] == fipsCode4, courts))[0]["courtName"]

def format_case_details(case_details):
    """Turn a Case details into the final format

    Args:
        case_details (_type_): as returned from the API?

    Returns:
        dict: _description_
    """
    if case_details["formattedCaseNumber"] == "GT20000008-00":
        print()
    participants = case_details["caseParticipant"]
    defendant = None
    complainant = None
    data = OrderedDict()
    try:
        for p in participants:
            if p["participantCode"] == "DEF":
                defendant = p
                addr = defendant["contactInformation"].get("primaryAddress", None)
                def_address = ""
                if addr is not None:
                    def_address = f"{addr.get('locationCityName', '')} {addr.get('locationState', '')}, {addr.get('locationPostalCode', '')}"

        data["Case Number"] = case_details["formattedCaseNumber"]
        data["Filed Date"] = case_details["caseCharge"]["chargeFilingDate"] # !
        data["Locality"] = case_details["locality"]["localityName"]
        data["Name"] = case_details["name"]
        data["Status"] = None # !
        data["Defense Attorney"] = None # !
        data["Address"] = def_address # TODO deconstruct into city/state/postalcode
        data["AKA1"] = None
        data["AKA2"] = None
        data["Gender"] = defendant["personalDetails"]["gender"] # TODO transform
        data["Race"] = defendant["personalDetails"].get("race", None) # TODO transformr
        data["DOB"] = defendant["personalDetails"].get("maskedBirthDate", "") + "/****"
        if data["DOB"] == "/****":
            data["DOB"] == None
        data["Charge"] = case_details["chargeDesc"]
        data["Code Section"] = case_details["codeSection"]
        data["Case Type"] = case_details["caseType"] # ! To transform: Felony/Misdemeanor/Infraction/Capias/Show Cause
        data["Class"] = None
        data["Offense Date"] = case_details["offenseDate"]
        data["Arrest Date"] = None
        data["Complainant"] = None
        data["Amended Charge"] = None
        data["Amended Code"] = None
        data["Amended Case Type"] = None
        data["Date"] = None
        data["Time"] = None
        data["Result"] = None
        data["Hearing Type"] = None
        data["Courtroom"] = None
        data["Plea"] = None
        data["Continuance Code"] = None
        data["Final Disposition"] = None
        data["Sentence Time"] = None
        data["Sentence Suspended Time"] = None
        data["Probation Type"] = None
        data["Probation Time"] = None
        data["Probation Starts"] = None
        data["Operator License Suspension Time"] = None
        data["Restriction Effective Date"] = None
        data["Operator License Restriction Codes"] = None
        data["Fine"] = None
        data["Costs"] = None
        data["Fine/Costs Due"] = None
        data["Fine/Costs Paid"] = None
        data["Fine/Costs Paid Date"] = None
        data["VASAP"] = None
        data["searchDate"] = None
        data["Court"] = get_court_name_by_fips(case_details["qualifiedFips"])
    except Exception as e:
        print(e)

    return data