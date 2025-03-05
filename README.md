# Court cases scraper

This is a scraper for court cases of Virginia's [Online Case Information System 2.0](https://eapps.courts.state.va.us/ocis/search).
The data extraction is orchestrated using Apache Airflow using Docker and Docker Compose.


## Getting started

First, setup some requirements for Airflow: `bash setup_airflow.sh`. This makes sure the folders `dag`, `logs`, `plugins`,  and `config`. It also creates an environment variable `AIRFLOW_UID` set to the UID of the current user.

You can launch Airflow using the following commands:
```bash
docker compose build
docker compose up -d
```

After a while, you can access the Airflow instance at http://localhost:8080 and login using the credentials `airflow/airflow`.


## Scraping court cases Airflow DAG

You can configure the time interval to be scraped using the DAG's `start_date` and `end_date` parameters.
The court cases data will be saved as-is in CSV file under the `output` folder.

## Database

### Schema

The database schema is managed using [Alembic](https://github.com/sqlalchemy/alembic).

We suppose a database named `virginia_court_cases` exists and will store the details of the scraped court cases.

Apply the Alembic schema using `alembic -c src/database/alembic.ini upgrade head`.
This will create needed tables such as `courts`, `cases`, `charges` and `case_charges`.

### Seeders

You can seed the `virginia_court_cases` database with data such as the Virginia courts which are defined in `src/database/seeders/courts.json` and `src/database/seeders/courts_urls.csv`:

```bash
export PYTHONPATH="$(pwd):$PYTHONPATH"
python src/database/seeders/courts.py
```

