import duckdb
import glob
import os
import argparse


def load_data(db_path, data_dir):
    """
    Loads JSONL files from the data directory into a DuckDB database.
    """
    # Connect to DuckDB
    con = duckdb.connect(db_path)

    # Find all JSONL files
    jsonl_files = glob.glob(os.path.join(data_dir, "**/*.json"), recursive=True)

    if not jsonl_files:
        print(f"No JSONL files found in {data_dir}")
        return

    print(f"Found {len(jsonl_files)} JSONL files.")

    # Create table (or replace)
    # We can use DuckDB's read_json_auto to infer schema and load data
    # To load multiple files, we can pass the list or a glob pattern

    # Construct a glob pattern that matches the files we found, or just pass the list if supported
    # DuckDB supports list of files in read_json_auto since recent versions, but let's use the glob pattern if possible
    # or loop and append.

    # Simplest way: Create table from the first file, then append others?
    # Or just use read_json_auto with the glob pattern for the whole directory if structure is consistent.

    # Let's try to load all at once using the glob pattern for the directory
    # Assuming data_dir is like 'output/' and files are in subdirs.

    search_pattern = os.path.join(data_dir, "**/*.json")

    print(f"Loading data from {search_pattern}...")

    try:
        # Create a table 'court_cases'
        con.execute(f"""
            CREATE OR REPLACE TABLE court_cases AS 
            SELECT * FROM read_json_auto('{search_pattern}', filename=true)
        """)

        count = con.execute("SELECT COUNT(*) FROM court_cases").fetchone()[0]
        print(f"Successfully loaded {count} records into 'court_cases' table.")

    except Exception as e:
        print(f"Error loading data: {e}")
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load JSONL data into DuckDB.")
    parser.add_argument(
        "--db-path", default="court_cases.duckdb", help="Path to DuckDB database file."
    )
    parser.add_argument(
        "--data-dir", default="output", help="Directory containing JSONL files."
    )

    args = parser.parse_args()

    load_data(args.db_path, args.data_dir)
