import os

# Set dummy DATABASE_URL for tests to prevent KeyError/failures during import/collection
os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost:5432/dummy_db")
os.environ.setdefault("DUCKDB_PATH", "output/gold/court_analytics.duckdb")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.models.base import Base

@pytest.fixture(scope="session")
def engine():
    """Create a localized, in-memory SQLite DB engine for unit testing."""
    # Using SQLite with a shared cache acts as an isolated operational playground
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """Provides a transactional database session rolled back after every test."""
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()