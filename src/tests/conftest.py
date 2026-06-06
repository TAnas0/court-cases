import os

# Set dummy DATABASE_URL for tests to prevent KeyError/failures during import/collection
os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost:5432/dummy_db")
os.environ.setdefault("DUCKDB_PATH", "output/gold/court_analytics.duckdb")
