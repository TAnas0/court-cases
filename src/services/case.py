import logging
import pandas as pd
from src.utils import try_json_loads, to_snake_case
from src.models.court_case import CourtCase
from src.database.main import get_court_by_qualified_fips

logger = logging.getLogger(__name__)


def normalize_cases_dataframe(df):
    """
    Preprocesses a dataframe of raw court cases.
    # Normalizes a dataframe of court cases that were read directly from raw scraped court cases data.
    Extracts CourtCase, Hearings, Charges, Participants, Dispositions, etc. as Pandas dataframe ready to be saved to the DB.
    """

    df = df.map(try_json_loads)  # Convert JSON-like strings into JSON
    df = pd.json_normalize(df.to_dict(orient="records"), sep="_")

    # Rename columns to snake case
    df.columns = [to_snake_case(col) for col in df.columns]

    # Normalize date/datetimes columns
    df = df.rename(
        columns={
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
        }
    )
    df = df.drop(columns=["case_charge_offense_date"])

    df["appeal_date"] = pd.to_datetime(df["appeal_date"], format="%m/%d/%Y").dt.date
    df["filed_date"] = pd.to_datetime(df["filed_date"], format="%m/%d/%Y").dt.date
    df["offense_date"] = pd.to_datetime(df["offense_date"], format="%m/%d/%Y").dt.date
    df["arrest_date"] = pd.to_datetime(df["arrest_date"], format="%m/%d/%Y").dt.date
    df["disposition_date"] = pd.to_datetime(
        df["disposition_date"], format="%m/%d/%Y"
    ).dt.date
    df["fines_paid_date"] = pd.to_datetime(df["fines_paid_date"]).dt.date
    df["hearing_date"] = pd.to_datetime(df["hearing_date"], format="%m/%d/%Y, %I:%M %p")
    # TODO appeal_withdrawn_date

    df["costs_paid_date"] = pd.to_datetime(df["costs_paid_date"], unit="ms")
    df["dmv_license_restrictions_start_date"] = pd.to_datetime(
        df["dmv_license_restrictions_start_date"], format="%m/%d/%Y"
    )

    # Normalize nullable boolean values
    df["is_active"] = df["is_active"].map({"Y": True, "N": False})
    df["is_criminal"] = df["is_criminal"].map({"Y": True, "N": False})
    df["is_traffic_fatality"] = df["is_traffic_fatality"].map({"Y": True, "N": False})
    df["is_dmv_alcohol_safety_action_code"] = df[
        "is_dmv_alcohol_safety_action_code"
    ].map({"Y": True, "N": False})
    # TODO normalize column is_appeal

    # normalize_case_participants_df(df[["case_tracking_id", "formatted_case_number", "case_participant"]])

    df = df.where(
        pd.notnull(df), None
    )  # Replace NaN, NaT, and other nullable Pandas value to None
    return df

def save_cases_to_parquet(df, target_path):
    # TODO docstring
    # TODO explore options to to_parquet
    df.to_parquet(target_path, index=False)
    # TODO log more info
    logger.info(f"Saved normalized data to {target_path}")
