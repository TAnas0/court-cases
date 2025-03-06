import pandas as pd
from .court import get_all_courts

def normalize_cases_dataframe(df):
    """
    Normalizes a dataframe of court cases that were read directly from raw scraped court cases data.
    Extracts Case, Hearings, Charges, Participants, Dispositions, etc. as Pandas dataframe ready to be saved to the DB.
    """

    df = pd.json_normalize(df.to_dict(orient="records"), sep="_", max_level=1)

    # Normalize dispotion information
    disposition_info_df = pd.json_normalize(df['disposition_dispositionInfo'])
    df = pd.concat([df, disposition_info_df], axis=1)

    # Rename columns to snake case
    df = df.rename(columns={
        "qualifiedFips": "qualified_fips",
        "caseNumber": "case_number",
        "chargeAmended": "charge_amended",
        "offenseDate": "offense_date",
        "hearingDate": "hearing_date",
        "formattedCaseNumber": "formatted_case_number",
        "complainantName": "complainant_name",
        "codeSection": "code_section",
        "chargeDesc": "charge_desc",
        "caseType": "case_type",
        "hearingType": "hearing_type",
        "hearingResult": "hearing_result",
        "caseTrackingID": "case_tracking_id",
        "caseParticipant": "case_participants",
        "caseHearing": "case_hearings",
        "serviceInfo": "service_info",
        "pleadingAndOrder": "pleadings_and_orders",
        "subDivisionType": "sub_division_type",
        "serviceInfo": "service_info",
        "courtLevel": "court_level",
        "divisionType": "division_type",

        "caseCourt_fipsCode": "court_fips_code",
        "caseCourt_courtCategoryCode": "court_category_code",
        "caseCharge_offenseTrackingNumber": "offense_tracking_number",
        "caseCharge_originalCharge": "original_charge",
        "caseCharge_amendedCharge": "ammended_charge",
        # Rename flattened columns
        "sentencingInformation_sentence": "sentence",
        "sentencingInformation_sentenceSuspended": "sentence_suspended",
        "sentencingInformation_jailPenitentiaryTimeServedCode": "sentence_jail_penitentiary_time_served_code",
        "sentencingInformation_concurrConsecCode": "sentence_concurr_consec_code",
        "caseActiveIndicator_value": "is_active",
        "appealCase": "is_appeal",
        "locality_localityName": "locality_name",
        "locality_localityCode": "locality_code",
        "caseCategory_caseCategoryCode": "category_code",
        "caseCategory_caseSubCategoryCode": "sub_category_code",
        "caseCategory_criminalCaseIndicator": "is_criminal",
        "appealCase_appealDate": "appeal_date",
        "caseCharge_chargeFilingDate": "charge_filing_date",
        # "caseCharge_offenseDate": "offense_date", # ! Duplicated
        "caseCharge_arrestDate": "arrest_date",
        "dmvInformation_trafficFatality": "is_traffic_fatality",
        "dmvInformation_alcoholSafetyActionCode": "is_dmv_alcohol_safety_action_code",
        "dmvInformation_driverLicense": "dmv_driver_license_loss_restrictions",
        "disposition_concludedByCode": "disposition_concluded_by",
        "disposition_probationInfo": "disposition_probation",
        "dispositionDate": "disposition_date",
        "dispositionText": "disposition_text",
        "caseOtherInfo_commencedByCode": "commenced_by",
        "caseCharge_summonsNumber": "summons_number",
    })

    # Removing duplicate, and processed top-level, columns
    df = df.drop(columns=[
        "caseCharge_offenseDate",
        "sentencingInformation",
        "disposition_dispositionInfo"
    ])

    # Normalize date/datetimes columns
    df["appeal_date"] = pd.to_datetime(df["appeal_date"], format="%m/%d/%Y").dt.date
    df["charge_filing_date"] = pd.to_datetime(df["charge_filing_date"], format="%m/%d/%Y").dt.date
    df["offense_date"] = pd.to_datetime(df["offense_date"], format="%m/%d/%Y").dt.date
    df["arrest_date"] = pd.to_datetime(df["arrest_date"], format="%m/%d/%Y").dt.date
    df["disposition_date"] = pd.to_datetime(df["disposition_date"], format="%m/%d/%Y").dt.date
    df["hearing_date"] = pd.to_datetime(df["hearing_date"], format="%m/%d/%Y, %I:%M %p")

    # Normalize nullable boolean values
    df["is_active"] = df["is_active"].map({"Y": True, "N": False})
    df["is_criminal"] = df["is_criminal"].map({"Y": True, "N": False})
    df["is_traffic_fatality"] = df["is_traffic_fatality"].map({"Y": True, "N": False})
    df["is_dmv_alcohol_safety_action_code"] = df["is_dmv_alcohol_safety_action_code"].map({"Y": True, "N": False})

    # Convert nullable values of dmv_driver_license_loss_restrictions to None
    df["dmv_driver_license_loss_restrictions"] = df["dmv_driver_license_loss_restrictions"].apply(
        lambda x: None if x in [
            {},
            {"licenseLoss": {}},
            {"licenseLoss": {"days": 0, "months": 0, "years": 0}, "licenseRestrictions": {}},
        ] else x
    )

