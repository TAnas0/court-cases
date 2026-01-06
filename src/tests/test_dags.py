import sys
import os
import pytest
from airflow.models import DagBag

# Ensure local modules can be imported if needed by DAGs

def test_dag_import_errors():
    """Verify that there are no errors when importing DAGs."""
    dag_folder = os.path.join(os.path.dirname(__file__), "../../dags")
    dag_bag = DagBag(dag_folder=dag_folder, include_examples=False)
    
    assert len(dag_bag.import_errors) == 0, f"DAG import errors: {dag_bag.import_errors}"

def test_dag_exists():
    """Verify that the expected DAG exists."""
    dag_folder = os.path.join(os.path.dirname(__file__), "../../dags")
    dag_bag = DagBag(dag_folder=dag_folder, include_examples=False)
    
    assert "court_case_scraper_workflow" in dag_bag.dags
    assert dag_bag.dags["court_case_scraper_workflow"] is not None
