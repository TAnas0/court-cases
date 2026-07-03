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
            "case_charge_offense_date": "offense_date",
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
    # df = df.drop(columns=["case_charge_offense_date"])

    DATE_FORMATS = {
        "hearing_date": "%m/%d/%Y, %I:%M %p",
        "filed_date": "%m/%d/%Y",
        "disposition_date": "%m/%d/%Y",
        "appeal_date": "%m/%d/%Y",
        "offense_date": "%m/%d/%Y",
        "arrest_date": "%m/%d/%Y",
        "fines_paid_date": "%m/%d/%Y",
        "costs_paid_date": "%m/%d/%Y",
        "dmv_license_restrictions_start_date": "%m/%d/%Y",
    }

    def _safe_to_datetime(series: pd.Series, fmt: str) -> pd.Series:
        """Parse a date Series defensively.

        pandas 2.x errors='coerce' does not intercept ValueError from
        _assemble_from_unit_mappings, which is triggered when column values are
        dicts (e.g. nested OCIS API objects that were not fully flattened by
        json_normalize). Coercing non-string values to None first ensures pandas
        always takes the string-parse path where errors='coerce' works correctly.
        """
        safe = series.apply(lambda x: x if isinstance(x, str) else None)
        return pd.to_datetime(safe, format=fmt, errors="coerce")

    for col, fmt in DATE_FORMATS.items():
        if col in df.columns:
            df[col] = _safe_to_datetime(df[col], fmt)

    # TODO: appeal_withdrawn_date — not yet in DATE_FORMATS; add when format confirmed.


    # Normalize nullable boolean values
    BOOL_MAP = {"Y": True, "N": False}
    BOOL_COLS = [
        "is_active",
        "is_criminal",
        "is_traffic_fatality",
        "is_dmv_alcohol_safety_action_code",
    ]
    # df["is_active"] = df["is_active"].map(BOOL_MAP)
    # df["is_criminal"] = df["is_criminal"].map(BOOL_MAP)
    # df["is_traffic_fatality"] = df["is_traffic_fatality"].map(BOOL_MAP)
    # df["is_dmv_alcohol_safety_action_code"] = df[
    #     "is_dmv_alcohol_safety_action_code"
    # ].map(BOOL_MAP)
    # TODO normalize column is_appeal

    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].map(BOOL_MAP)

    # normalize_case_participants_df(df[["case_tracking_id", "formatted_case_number", "case_participant"]])

    # df = df.where(
    #     pd.notnull(df), None
    # )  # Replace NaN, NaT, and other nullable Pandas value to None
    return df

def save_cases_to_parquet(df, target_path):
    # TODO docstring
    # TODO explore options to to_parquet
    df.to_parquet(target_path, index=False)
    # TODO log more info
    logger.info(f"Saved normalized data to {target_path}")
