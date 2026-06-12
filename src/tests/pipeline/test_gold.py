import os
import pytest
import duckdb
from src.pipeline.gold import build_gold_layer


@pytest.fixture
def sample_silver_parquet(tmp_path):
    """Create a minimal Silver Parquet file for testing Gold aggregations."""
    silver_parquet_path = str(tmp_path / "silver_cases.parquet")
    con = duckdb.connect()

    # We construct a table matching the Silver schema structure needed by Gold queries
    con.execute("""
        CREATE TABLE silver_test (
            locality_name VARCHAR,
            caseNumber VARCHAR,
            chargeDesc VARCHAR,
            offense_date DATE,
            hearing_timestamp TIMESTAMP,
            financialInformation STRUCT(
                fines STRUCT(
                    amount STRUCT(
                        decimal DOUBLE
                    )
                )
            ),
            disposition STRUCT(
                dispositionInfo STRUCT(
                    dispositionText VARCHAR
                )
            )
        )
    """)

    # Insert 2 test records
    con.execute("""
        INSERT INTO silver_test VALUES 
        (
            'Albemarle', 'CR001', 'Grand Larceny', '2024-01-10', '2024-01-15 09:00:00',
            {'fines': {'amount': {'decimal': 150.0}}},
            {'dispositionInfo': {'dispositionText': 'Guilty'}}
        ),
        (
            'Albemarle', 'CR002', 'Speeding', '2024-01-11', '2024-01-16 10:00:00',
            {'fines': {'amount': {'decimal': 50.0}}},
            {'dispositionInfo': {'dispositionText': 'Guilty'}}
        )
    """)

    con.execute(f"COPY silver_test TO '{silver_parquet_path}' (FORMAT PARQUET)")
    con.close()
    return silver_parquet_path


def test_gold_creates_db_and_tables(sample_silver_parquet, tmp_path):
    gold_db = str(tmp_path / "gold" / "court_analytics.duckdb")
    build_gold_layer(sample_silver_parquet, gold_db)

    assert os.path.exists(gold_db)

    con = duckdb.connect(gold_db)

    # Verify that all expected analytical tables exist
    tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
    assert "monthly_locality_summary" in tables
    assert "charge_outcome_profile" in tables
    assert "locality_efficiency" in tables
    assert "day_of_week_summary" in tables
    assert "disposition_summary" in tables
    assert "hearings_per_case_distribution" in tables

    # Verify monthly locality summary content
    summary = con.execute(
        "SELECT locality_name, case_count, avg_fine FROM monthly_locality_summary"
    ).fetchone()
    assert summary[0] == "Albemarle"
    assert summary[1] == 2
    assert summary[2] == 100.0  # (150 + 50) / 2

    # Verify efficiency calculation
    efficiency = con.execute(
        "SELECT avg_days_to_hearing FROM locality_efficiency WHERE locality_name = 'Albemarle'"
    ).fetchone()[0]
    # CR001: 2024-01-15 - 2024-01-10 = 5 days
    # CR002: 2024-01-16 - 2024-01-11 = 5 days
    # Average should be 5.0
    assert efficiency == 5.0

    con.close()
