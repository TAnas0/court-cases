import duckdb
import pandas as pd

def run_eda(parquet_path):
    con = duckdb.connect()
    
    print("\n" + "="*30)
    print("      GENERAL STATS")
    print("="*30)
    total_cases = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()[0]
    print(f"Total Cases: {total_cases:,}")
    
    print("\n--- Top 10 Localities ---")
    locality_df = con.execute(f"""
        SELECT locality_name, COUNT(*) as count 
        FROM '{parquet_path}' 
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """).df()
    print(locality_df.to_string(index=False))
    
    print("\n" + "="*30)
    print("      DISTRIBUTION")
    print("="*30)
    print("--- Outcomes (Disposition) ---")
    outcome_df = con.execute(f"""
        SELECT 
            disposition_text, 
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / {total_cases}, 2) as percentage
        FROM '{parquet_path}'
        GROUP BY 1 ORDER BY 2 DESC
    """).df()
    print(outcome_df.to_string(index=False))

    print("\n--- Participant Roles (Unnested) ---")
    roles_df = con.execute(f"""
        SELECT 
            p.participantCode as role,
            count(*) as count
        FROM (SELECT unnest(participants) as p FROM '{parquet_path}')
        GROUP BY 1 ORDER BY 2 DESC
    """).df()
    print(roles_df.to_string(index=False))

    print("\n" + "="*30)
    print("      DEMOGRAPHICS")
    print("="*30)
    print("--- Dismissal Rate by Race (Top 10 by Vol) ---")
    race_df = con.execute(f"""
        SELECT 
            race,
            COUNT(*) as total_cases,
            ROUND(AVG(CASE WHEN disposition_text = 'D' THEN 1 ELSE 0 END) * 100.0, 2) as dismissal_rate
        FROM '{parquet_path}'
        WHERE race IS NOT NULL
        GROUP BY 1
        HAVING total_cases > 100
        ORDER BY total_cases DESC LIMIT 10
    """).df()
    print(race_df.to_string(index=False))

    print("\n" + "="*30)
    print("      FINANCIALS")
    print("="*30)
    print("--- Fine distribution (> $0) ---")
    fines_df = con.execute(f"""
        SELECT 
            MIN(fine_amount) as min_fine, 
            MAX(fine_amount) as max_fine, 
            AVG(fine_amount) as avg_fine,
            MEDIAN(fine_amount) as median_fine
        FROM '{parquet_path}' 
        WHERE fine_amount > 0
    """).df()
    print(fines_df.to_string(index=False))

    print("\n" + "="*30)
    print("      EFFICIENCY")
    print("="*30)
    print("--- Busiest Weekdays (Avg Cases) ---")
    weekday_df = con.execute(f"""
        SELECT 
            dayname(hearing_timestamp) as weekday, 
            dayofweek(hearing_timestamp) as dow,
            ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT hearing_timestamp::DATE), 0) as avg_cases
        FROM '{parquet_path}'
        WHERE hearing_timestamp IS NOT NULL
        GROUP BY 1, 2
        ORDER BY dow
    """).df()
    print(weekday_df[['weekday', 'avg_cases']].to_string(index=False))

    print("\n--- Avg Days to Hearing (Top 10 Charges) ---")
    efficiency_df = con.execute(f"""
        SELECT 
            chargeDesc,
            COUNT(*) as count,
            ROUND(AVG(date_diff('day', offense_date, hearing_timestamp::DATE)), 1) as avg_days
        FROM '{parquet_path}'
        WHERE offense_date IS NOT NULL
        GROUP BY 1
        HAVING count > 100
        ORDER BY count DESC LIMIT 10
    """).df()
    print(efficiency_df.to_string(index=False))

    print("\n" + "="*30)
    print("      LEGAL REPRESENTATION")
    print("="*30)
    lawyer_df = con.execute(f"""
        SELECT 
            CASE WHEN attorney_type IS NOT NULL THEN 'Attorney' ELSE 'No Attorney' END as representation,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / {total_cases}, 2) as percentage
        FROM '{parquet_path}'
        GROUP BY ALL
    """).df()
    print(lawyer_df.to_string(index=False))

    print("\n" + "="*30)
    print("      CHARGE PROFILES (TOP 5)")
    print("="*30)
    charge_profile_df = con.execute(f"""
        WITH top_charges AS (
            SELECT chargeDesc FROM '{parquet_path}'
            GROUP BY 1 ORDER BY count(*) DESC LIMIT 5
        )
        SELECT 
            chargeDesc,
            disposition_text,
            count(*) as count
        FROM '{parquet_path}'
        WHERE chargeDesc IN (SELECT chargeDesc FROM top_charges)
        GROUP BY 1, 2
        ORDER BY 1, 3 DESC
    """).df()
    # Using pivot for better readability of charge profiles
    pivot_df = charge_profile_df.pivot(index='chargeDesc', columns='disposition_text', values='count').fillna(0).astype(int)
    print(pivot_df.to_string())

if __name__ == "__main__":
    run_eda("output/silver/2024/05/cases.parquet")
