import logging
import json
import numpy as np
import pandas as pd
from src.utils import try_json_loads, to_snake_case
from src.models.court_case import CourtCase
from src.database.main import get_court_by_qualified_fips

logger = logging.getLogger(__name__)

# Maintainable pattern for enforcing a "Golden Schema" during transition from raw JSON to structured DataFrame
GOLDEN_SCHEMA = {
    "qualified_fips": "string",
    "court_level": "string",
    "division_type": "string",
    "case_number": "string",
    "hearing_date": "datetime64[ns]",
    "filed_date": "datetime64[ns]",
    "is_appeal": "boolean",
    "appeal_date": "datetime64[ns]",
    "appeal_withdrawn_date": "datetime64[ns]",
    "arrest_date": "datetime64[ns]",
    "locality_name": "string",
    "locality_code": "Int64",
    "case_category_code": "string",
    "case_sub_category_code": "string",
    "offense_date": "datetime64[ns]",
    "disposition_date": "datetime64[ns]",
    "fines_paid_date": "datetime64[ns]",
    "costs_paid_date": "datetime64[ns]",
    "dmv_license_restrictions_start_date": "datetime64[ns]",
    "is_active": "boolean",
    "is_criminal": "boolean",
    "is_traffic_fatality": "boolean",
    "is_dmv_alcohol_safety_action_code": "boolean",
    "commenced_by": "string",
}

def normalize_cases_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses a dataframe of raw court cases.
    Extracts CourtCase, Hearings, Charges, Participants, Dispositions, etc. as Pandas dataframe ready to be saved to the DB.
    """
    # Immutability: perform all transformations on a copy of the input DataFrame
    df = df.copy()

    # Performance Optimization: Only apply try_json_loads on object columns containing JSON-like strings
    for col in df.columns:
        if df[col].dtype == "object":
            # Check if there are string values starting with JSON indicators
            is_json_str = df[col].dropna().apply(
                lambda x: isinstance(x, str) and x.strip().startswith(("{", "[", '"', "'"))
            )
            if is_json_str.any():
                df[col] = df[col].apply(try_json_loads)

    # Flatten raw nested structures
    df = pd.json_normalize(df.to_dict(orient="records"), sep="_")

    # Rename columns to snake case
    df.columns = [to_snake_case(col) for col in df.columns]

    # Map raw field names to structured field names
    rename_map = {
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

    # Deterministic Collision Resolution: Programmatic suffixing of duplicate column names
    new_cols = []
    seen = {}
    for col in df.columns:
        mapped_col = rename_map.get(col, col)
        if mapped_col in seen:
            seen[mapped_col] += 1
            new_cols.append(f"{mapped_col}_dup_{seen[mapped_col]}")
        else:
            seen[mapped_col] = 0
            new_cols.append(mapped_col)
    df.columns = new_cols

    # Enforce the Golden Schema
    for col, dtype in GOLDEN_SCHEMA.items():
        if col not in df.columns:
            # Add missing Golden Schema column initialized with nulls
            df[col] = pd.Series([pd.NA] * len(df), dtype=dtype)
        else:
            # Cast column to correct Golden Schema type
            if dtype == "boolean":
                BOOL_MAP = {"Y": True, "N": False, True: True, False: False, "true": True, "false": False}
                df[col] = df[col].map(BOOL_MAP).astype("boolean")
            elif dtype.startswith("datetime64"):
                # Handle dates using a safe helper
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
                    "appeal_withdrawn_date": "%m/%d/%Y",
                }
                fmt = DATE_FORMATS.get(col, "%m/%d/%Y")
                safe_str = df[col].apply(lambda x: x if isinstance(x, str) else None)
                df[col] = pd.to_datetime(safe_str, format=fmt, errors="coerce")
            else:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as exc:
                    logger.warning("Coercion to golden type failed for column=%s dtype=%s error=%s", col, dtype, exc)

    # Eliminate Parquet/Arrow serialization errors (nested/empty struct handling)
    for col in df.columns:
        if df[col].dtype == "object":
            # Check if column has nested lists or dicts
            has_complex = df[col].apply(lambda x: isinstance(x, (dict, list))).any()
            if has_complex:
                # Serialize complex objects to JSON strings to maintain integrity and prevent Arrow serialization crashes
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            
            # Check if column is entirely null
            if df[col].isnull().all():
                # Cast entirely empty object columns to string dtype for clean serialization
                df[col] = df[col].astype("string")

    # Clean up null values: Replace pd.NA and np.nan with None in object/string columns,
    # ensuring numeric columns retain their proper types before final conversion.
    for col in df.columns:
        if df[col].dtype in ("object", "string", "O"):
            df[col] = df[col].replace({pd.NA: None, np.nan: None})

    return df

def save_cases_to_parquet(df, target_path):
    """Save the normalized DataFrame to a Parquet file."""
    df.to_parquet(target_path, index=False)
    logger.info(f"Saved normalized data to {target_path}")
