import duckdb
import os
import logging

logger = logging.getLogger(__name__)

def build_gold_layer(silver_path: str, gold_db_path: str):
    """
    Builds the Gold Layer (Analytical Consumers) from Silver Parquet.
    Creates structured tables in a persistent DuckDB database.
    """
    logger.info(f"Building Gold Layer from {silver_path} to {gold_db_path}")
    
    os.makedirs(os.path.dirname(gold_db_path), exist_ok=True)
    
    con = duckdb.connect(gold_db_path)
    
    try:
        # Create a view on Silver data
        con.execute(f"CREATE OR REPLACE VIEW silver_cases AS SELECT * FROM '{silver_path}'")
        
        # 1. Monthly Volume by Locality
        con.execute("""
            CREATE OR REPLACE TABLE monthly_locality_summary AS
            SELECT 
                locality_name,
                date_trunc('month', hearing_timestamp) as month,
                count(*) as case_count,
                avg(financialInformation.fines.amount.decimal) as avg_fine,
                count(distinct caseNumber) as distinct_cases
            FROM silver_cases
            GROUP BY 1, 2
        """)
        
        # 2. Charge Outcomes
        con.execute("""
            CREATE OR REPLACE TABLE charge_outcome_profile AS
            SELECT 
                chargeDesc,
                disposition.dispositionInfo.dispositionText as disposition_text,
                count(*) as case_count
            FROM silver_cases
            GROUP BY 1, 2
        """)
        
        # 3. Efficiency (Time from Offense to Hearing)
        con.execute("""
            CREATE OR REPLACE TABLE locality_efficiency AS
            SELECT 
                locality_name,
                avg(date_diff('day', offense_date, hearing_timestamp::DATE)) as avg_days_to_hearing
            FROM silver_cases
            WHERE offense_date IS NOT NULL
            GROUP BY 1
        """)
        
        # 4. Day of the Week Analysis
        con.execute("""
            CREATE OR REPLACE TABLE day_of_week_summary AS
            SELECT 
                dayname(hearing_timestamp) as day_name,
                dayofweek(hearing_timestamp) as day_index,
                count(*) as hearing_count
            FROM silver_cases
            WHERE hearing_timestamp IS NOT NULL
            GROUP BY 1, 2
            ORDER BY 2
        """)

        # 5. Disposition Summary (High Level)
        con.execute("""
            CREATE OR REPLACE TABLE disposition_summary AS
            SELECT 
                disposition.dispositionInfo.dispositionText as disposition_text,
                count(*) as count
            FROM silver_cases
            WHERE disposition_text IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)

        # 6. Hearings per Case Distribution
        con.execute("""
            CREATE OR REPLACE TABLE hearings_per_case_distribution AS
            WITH per_case_counts AS (
                SELECT caseNumber, count(*) as num_hearings
                FROM silver_cases
                GROUP BY 1
            )
            SELECT 
                num_hearings,
                count(*) as cases_with_this_count
            FROM per_case_counts
            GROUP BY 1
            ORDER BY 1
        """)
        
        logger.info("Gold Layer tables created successfully.")
        
    except Exception as e:
        logger.error(f"Failed to build Gold Layer: {e}")
        raise
    finally:
        con.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SILVER_FILE = "output/silver/cases.parquet"
    GOLD_DB = "output/gold/court_analytics.duckdb"
    
    if os.path.exists(SILVER_FILE):
        build_gold_layer(SILVER_FILE, GOLD_DB)
    else:
        logger.warning(f"Silver file {SILVER_FILE} not found.")
