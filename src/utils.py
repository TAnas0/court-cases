from collections import OrderedDict
from datetime import timedelta
import logging
import requests_cache
from constants.main import courts


logger = logging.getLogger(__name__)

def accept_terms_and_conditions():
    # TODO Get session creation out of here!
    session = requests_cache.CachedSession(
        'demo_cache1',
        expire_after=timedelta(days=30),
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
    participants = case_details["caseParticipant"]
    defendant = None
    complainant = None
    defendant_attorney = None
    data = OrderedDict()
    try:
        hearings = case_details.get("caseHearing")
        last_hearing = hearings[0]
        search_date = case_details.get("hearingDate", "").split(",")[0]
        current_hearing = filter(lambda h: h.get("courtActivityScheduleDay", {}).get("scheduleDate") == search_date, hearings)
        current_hearing = list(current_hearing)[0]
        defendant = {}
        defendant_attorney = None
        complainant = {}
        sentencing_information = case_details.get("sentencingInformation", {})
        # sentence_time = # Parse years, months, days
        for p in participants:
            if p["participantCode"] == "DEF":
                defendant = p
                defendant_attorney = defendant.get("attorneyDetails", "")
                if defendant_attorney:
                    defendant_attorney = defendant_attorney[0].get("attorneyName", {}).get("fullName")
                addr = defendant["contactInformation"].get("primaryAddress", None)
                def_address = ""
                if addr is not None:
                    def_address = f"{addr.get('locationCityName', '')} {addr.get('locationState', '')}, {addr.get('locationPostalCode', '')}"
            if p["participantCode"] == "CMP":
                complainant = p
        data["Case Number"] = case_details["formattedCaseNumber"]
        data["Filed Date"] = case_details["caseCharge"]["chargeFilingDate"] # !
        data["Locality"] = case_details["locality"].get("localityName", case_details.get("localityCode", None))
        data["Name"] = case_details["name"]
        data["Defendant Status"] = defendant.get("participantStatus")
        data["Defense Attorney"] = defendant_attorney
        data["Address"] = def_address # TODO deconstruct into city/state/postalcode
        defendant_additional_names = defendant.get("contactInformation", {}).get("additionalName", None)
        if defendant_additional_names:
            data["AKA1"] = defendant_additional_names[0].get("additionalName")
            if len(defendant_additional_names) > 1:
                data["AKA2"] = defendant_additional_names[1].get("additionalName")
        data["Gender"] = defendant.get("personalDetails").get("gender", None) # TODO transform
        data["Race"] = defendant.get("personalDetails").get("race", None) # TODO transformr
        data["DOB"] = defendant.get("personalDetails").get("maskedBirthDate", "")
        if data["DOB"]:
            data["DOB"] += "/****"
        data["Charge"] = case_details["chargeDesc"]
        data["Code Section"] = case_details["codeSection"]
        data["Case Type"] = case_details["caseType"] # ! To transform: Felony/Misdemeanor/Infraction/Capias/Show Cause
        data["Class"] = case_details.get("caseCharge", {}).get("originalCharge", {}).get("classCode")
        data["Offense Date"] = case_details["offenseDate"]
        data["Arrest Date"] = case_details.get("caseCharge", {}).get("arrestDate")
        data["Offense Date"] = case_details.get("caseCharge", {}).get("offenseDate")
        data["Complainant"] = complainant.get("contactInformation", {}).get("fullName")
        data["Amended Charge"] = case_details.get("caseCharge", {}).get("amendedCharge", {}).get("chargeDescriptionText")
        data["Amended Code"] = case_details.get("caseCharge", {}).get("amendedCharge", {}).get("codeSection")
        data["Amended Case Type"] = case_details.get("caseCharge", {}).get("amendedCharge", {}).get("caseTypeCode")
        data["Date"] = current_hearing.get("courtActivityScheduleDay", {}).get("scheduleDate")
        data["Time"] = current_hearing.get("courtActivityScheduleDay", {}).get("scheduleDayStartTime", {}).get("time")
        data["Result"] = current_hearing.get("hearingResult")
        data["Hearing Type"] = current_hearing.get("hearingType")
        data["Courtroom"] = last_hearing.get("courtRoom")
        data["Plea"] = current_hearing.get("plea")
        data["Continuance Code"] = current_hearing.get("continuanceCode")
        data["Final Disposition"] = case_details.get("disposition", {}).get("dispositionInfo", {}).get("dispositionText")
        data["Disposition Date"] = case_details.get("disposition", {}).get("dispositionInfo", {}).get("dispositionDate")
        data["Sentence Time"] = sentencing_information.get("sentence", {}).get("years") # ! To be parsed right
        data["Sentence Suspended Time"] = sentencing_information.get("sentenceSuspended", {}).get("years")
        data["Probation Type"] = case_details.get("disposition", {}).get("probationInfo", {}).get("probationType")
        data["Probation Starts"] = case_details.get("disposition", {}).get("probationInfo", {}).get("probationStart")
        data["Probation Time"] = case_details.get("disposition", {}).get("probationInfo", {}).get("duration")
        data["Operator License Suspension Time"] = case_details.get("dmvInformation", {}).get("driverLicense", {}).get("licenseLoss", {}) # ! format date
        data["Restriction Effective Date"] = case_details.get("dmvInformation", {}).get("driverLicense", {}).get("licenseRestrictions", {}).get("startDate")
        data["Operator License Restriction Codes"] = case_details.get("dmvInformation", {}).get("driverLicense", {}).get("licenseLoss", {}).get("licenseSurrenderCode")
        data["Fine"] = case_details.get("financialInformation", {}).get("fines", {}).get("amount", {}).get("decimal")
        data["Costs"] = case_details.get("financialInformation", {}).get("costs", {}).get("amount", {}).get("decimal")
        data["Fine/Costs Due"] = case_details.get("financialInformation", {}).get("fines", {}).get("amount", {}).get("decimal") # ! separate fines and costs
        data["Fine/Costs Paid"] = case_details.get("financialInformation", {}).get("fines", {}).get("paidIndicator") # ! separate costs and fines
        data["Fine Paid Date"] = case_details.get("financialInformation", {}).get("fines", {}).get("paidDate", {}).get("date")
        data["Costs Paid Date"] = case_details.get("financialInformation", {}).get("costs", {}).get("paidDate", {}).get("date") # ! same as the above? duplicated?
        data["VASAP"] = case_details.get("dmvInformation", {}).get("alcoholSafetyActionCode") == "Y"
        data["searchDate"] = search_date
        data["Traffic Fatality"] = case_details.get("dmvInformation", {}).get("trafficFatality")
        data["Court"] = get_court_name_by_fips(case_details["qualifiedFips"])

        data["Alcohol Safety Action Code"] = case_details.get("dmvInformation", {}).get("alcoholSafetyActionCode")
        # data["pleadings"] = case_details["pleadingAndOrder"] # To Be saved separately
    except Exception as e:
        logger.error(f"Error during formatting of case {case_details['formattedCaseNumber']}")
        logger.exception(e)

    return data

def date_range(start_date, end_date):
    # https://stackoverflow.com/a/1060330/4017403
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_csv_path(d):
    return f"output/{d.strftime('%Y')}/{d.strftime('%m')}/{d.strftime('%d')}.csv"
