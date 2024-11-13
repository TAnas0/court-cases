import os
import sys
import json
from src.database.main import SessionLocal
from src.models import Court
import pandas as pd


def seed_courts():
    COURTS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'courts.json')
    COURTS_URLS_PATH = os.path.join(os.path.dirname(__file__), 'courts_urls.csv')

    courts_df = pd.read_json(COURTS_JSON_PATH)

    courts_urls_df = pd.read_csv(COURTS_URLS_PATH)
    courts_df = pd.merge(courts_df, courts_urls_df, on='fipsCode4', how='outer')
    courts_df = courts_df.where(courts_df.notnull(), None)

    db = SessionLocal()

    try:
        for court_data in courts_df.itertuples():
            court = Court(
                name=court_data.courtName,
                court_type=court_data.courtTypeCode,
                fips_code=court_data.fipsCode,
                fips_code_4=court_data.fipsCode4,
                url=court_data.url,
            )
            db.add(court)

        db.commit()
        print("Courts seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error inserting data: {e}")

    finally:
        db.close()



if __name__ == "__main__":
    seed_courts()
