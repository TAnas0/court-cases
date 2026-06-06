import os
import json
import pytest
from src.pipeline.bronze import build_bronze_layer


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create a minimal JSONL file for testing."""
    data = [
        {"caseNumber": "CR001", "hearingDate": "01/15/2024, 09:00 AM", "name": "Test"},
        {"caseNumber": "CR002", "hearingDate": "01/16/2024, 10:00 AM", "name": "Test2"},
    ]
    jsonl_file = tmp_path / "2024" / "01" / "15.json"
    jsonl_file.parent.mkdir(parents=True)
    with open(jsonl_file, "w") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")
    return str(tmp_path / "**/*.json")


def test_bronze_creates_parquet(sample_jsonl, tmp_path):
    output = str(tmp_path / "bronze" / "cases.parquet")
    build_bronze_layer(sample_jsonl, output)
    assert os.path.exists(output)


def test_bronze_preserves_all_records(sample_jsonl, tmp_path):
    import duckdb
    output = str(tmp_path / "bronze" / "cases.parquet")
    build_bronze_layer(sample_jsonl, output)
    count = duckdb.execute(f"SELECT count(*) FROM '{output}'").fetchone()[0]
    assert count == 2


def test_bronze_handles_no_files(tmp_path):
    """Should not crash when no input files exist."""
    output = str(tmp_path / "bronze" / "cases.parquet")
    build_bronze_layer(str(tmp_path / "nonexistent/*.json"), output)
    assert not os.path.exists(output)
