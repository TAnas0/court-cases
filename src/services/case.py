import pandas as pd
from src.utils import try_json_loads, to_snake_case
from src.models.case import Case
from src.database.main import get_court_by_qualified_fips, upsert_cases

def normalize_cases_dataframe(df):
    """
    Preprocesses a dataframe of raw court cases.
    # Normalizes a dataframe of court cases that were read directly from raw scraped court cases data.
    Extracts Case, Hearings, Charges, Participants, Dispositions, etc. as Pandas dataframe ready to be saved to the DB.
    """

    df = df.applymap(try_json_loads)  # Convert JSON-like strings into JSON
    df = pd.json_normalize(df.to_dict(orient="records"), sep="_")

    # Rename columns to snake case
    df.columns = [to_snake_case(col) for col in df.columns]

    # Normalize date/datetimes columns
    df = df.rename(columns={
        "date": "hearing_date",
        "case_charge_charge_filing_date": "filed_date",
        "appeal_case": "is_appeal",
        "appeal_case_appeal_date": "appeal_date",
        "appeal_case_appeal_withdrawn_date": "appeal_withdrawn_date",
        "case_charge_arrest_date": "arrest_date",
        
        "locality_locality_name": "locality_name",
        "locality_locality_code": "locality_code",
        "case_category_case_category_code": "case_category_code",
        "case_category_case_sub_category_code": "case_sub_category_code",
        # "case_charge_offense_date": "offense_date",
        "disposition_disposition_info_disposition_date": "disposition_date",
        "financial_information_fines_paid_date_date": "fines_paid_date",
        "financial_information_costs_paid_date_date": "costs_paid_date",
        "dmv_information_driver_license_license_restrictions_start_date": "dmv_license_restrictions_start_date",
        
        "case_active_indicator_value": "is_active",
        "case_category_criminal_case_indicator": "is_criminal",
        "dmv_information_traffic_fatality": "is_traffic_fatality",
        "dmv_information_alcohol_safety_action_code": "is_dmv_alcohol_safety_action_code",
        
        "case_other_info_commenced_by_code": "commenced_by",

    })
    df = df.drop(columns=[
        "case_charge_offense_date"
    ])

    df["appeal_date"] = pd.to_datetime(df["appeal_date"], format="%m/%d/%Y").dt.date
    df["filed_date"] = pd.to_datetime(df["filed_date"], format="%m/%d/%Y").dt.date
    df["offense_date"] = pd.to_datetime(df["offense_date"], format="%m/%d/%Y").dt.date
    df["arrest_date"] = pd.to_datetime(df["arrest_date"], format="%m/%d/%Y").dt.date
    df["disposition_date"] = pd.to_datetime(df["disposition_date"], format="%m/%d/%Y").dt.date
    df["fines_paid_date"] = pd.to_datetime(df["fines_paid_date"]).dt.date
    df["hearing_date"] = pd.to_datetime(df["hearing_date"], format="%m/%d/%Y, %I:%M %p")
    # TODO appeal_withdrawn_date

    df["costs_paid_date"] = pd.to_datetime(df["costs_paid_date"], unit="ms")
    df["dmv_license_restrictions_start_date"] = pd.to_datetime(df["dmv_license_restrictions_start_date"], format="%m/%d/%Y")


    # Normalize nullable boolean values
    df["is_active"] = df["is_active"].map({"Y": True, "N": False})
    df["is_criminal"] = df["is_criminal"].map({"Y": True, "N": False})
    df["is_traffic_fatality"] = df["is_traffic_fatality"].map({"Y": True, "N": False})
    df["is_dmv_alcohol_safety_action_code"] = df["is_dmv_alcohol_safety_action_code"].map({"Y": True, "N": False})
    # TODO normalize column is_appeal

    # normalize_case_participants_df(df[["case_tracking_id", "formatted_case_number", "case_participant"]])

    df = df.where(pd.notnull(df), None)  # Replace NaN, NaT, and other nullable Pandas value to None
    return df

def normalize_case_participants_df(df):
    """
    """
    # make sure it references the case/hearing in question
    # Process case participants
    return

def normalize_case_participants_df_2(df):
    participants_df = pd.json_normalize(df.explode('case_participants')['case_participants'])
    participants_df['case_number'] = df.explode('case_participants')['case_number'].values
    participants_df = participants_df.rename(columns={
        "participantCode": "code",
        # "attorneyDetails": "",
        "participantStatus": "status",
        # "sequenceNumber.identificationID": "",
        "contactInformation.primaryAddress.locationCityName": "city",
        "contactInformation.primaryAddress.locationState": "state",
        "contactInformation.primaryAddress.locationCountry": "country",
        "contactInformation.primaryAddress.locationPostalCode": "postal_code",

        "contactInformation.secondaryAddress.locationCityName": "city_secondary",
        "contactInformation.secondaryAddress.locationState": "state_secondary",
        "contactInformation.secondaryAddress.locationCountry": "country_secondary",
        "contactInformation.secondaryAddress.locationPostalCode": "postal_code_secondary",
        
        "contactInformation.personName.personGivenName": "given_name",
        "contactInformation.personName.personMiddleName": "middle_name",
        "contactInformation.personName.personSurName": "surname",
        "contactInformation.personName.fullName": "full_name",
        
        "personalDetails.race": "race",
        "personalDetails.gender": "gender",
        "personalDetails.maskedBirthDate": "birth_date_masked",
        
        "contactInformation.personName.personNameSuffixText": "name_suffix_text",
        "contactInformation.businessName.businessName": "business_name",
        "contactInformation.additionalName": "additional_name",
        
        "attorneyDetails": "attorney_details"
    })
    # TODO extract attorney details: column attorneyDetails
    df = df.drop(columns=["case_participants"]) # Remove case_particpants from court dataframe
    participants_df = participants_df.drop(columns=["sequenceNumber.identificationID"])

    # TODO process attorney_details
    # Can there be multiple attorneys? If multiple, is there an order (primary attorney)?

    # TODO keep reference for each participant to the court case, or hearing

    # TODO Handle columns with lists of arbitrary lengths, and referencing a foreign key
    # case_participant
    # case_hearings
    # pleading_and_order
    # service_info

    return


def process_case_charges(df):
    return


def process_case_participants(df):
    return


def process_case_hearings(df):
    return


def save_cases_dataframe_to_db(df):
    from src.database.main import get_session
    
    with get_session() as db_session:
        df_cases = df[
            [
                "qualified_fips",
                "case_number",
                "formatted_case_number",
                "charge_amended",
                "code_section",
                "case_type",
                "offense_date",
                "arrest_date",
                "is_criminal",
                "case_category_code",
                "case_sub_category_code",
                "is_appeal",
                "appeal_date",
                "is_active",
                "commenced_by",
                "case_tracking_id",
            ]
        ]
        
        # Deduplicate based on composite unique constraint, while keeping the last
        df_cases = df_cases.drop_duplicates(subset=['case_number', 'code_section', 'is_appeal', 'commenced_by'], keep='last')
        
        cases_models = []

        for index, row in df_cases.iterrows():
            try:
                case_data = row.to_dict()
                
                court_id = get_court_by_qualified_fips(db_session, case_data["qualified_fips"]).id
                case = Case(
                    case_number=case_data["case_number"],
                    formatted_case_number=case_data["formatted_case_number"],
                    charge_amended=case_data["charge_amended"],
                    code_section=case_data["code_section"],
                    case_type=case_data["case_type"],
                    offense_date=case_data["offense_date"],
                    arrest_date=case_data["arrest_date"],
                    is_criminal=case_data["is_criminal"],
                    category=case_data["case_category_code"],
                    sub_category=case_data["case_sub_category_code"],
                    #is_appeal=case_data["is_appeal"],
                    appeal_date=case_data["appeal_date"],
                    is_active=case_data["is_active"],
                    commenced_by=case_data["commenced_by"],
                    court_id=court_id,
                )
                cases_models.append(case)

            except Exception as e:
                print(f"Error saving row {index}: {e}")

        try:
            upsert_cases(db_session, cases_models)
        except Exception as commit_exception:
            db_session.rollback()
            print(f"DB commit failed: {commit_exception}")
            raise
    return
