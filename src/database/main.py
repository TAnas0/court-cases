from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from src.models import Case, Charge

# Configuration for PostgreSQL database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airflow:airflow@localhost:5432/virginia_court_cases")  # TODO use separate database/user than airflow

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=True)  # echo=True logs SQL statements; set to False in production

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models to inherit
Base = declarative_base()

def get_db():
    """Dependency that creates and closes a session automatically for each request or function call."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


session = SessionLocal()

def get_court_by_qualified_fips(qualified_fips):
    """
    """
    court = session.query(Court).filter_by(fips_code_4=qualified_fips).first()
    return court

def get_case_by_id(id):
    case = session.query(Case).filter_by(id=id).first()
    return case

def get_cases_by_ids(ids):
    """Retrieve cases by a list of IDs."""
    cases = session.query(Case).filter(Case.id.in_(ids)).all()
    return cases

def get_case_by_formatted_number(formatted_case_number):
    case = session.query(Case).filter_by(formatted_case_number=formatted_case_number).first()
    return case

def get_cases_by_formatted_numbers(formatted_case_numbers):
    """Retrieve cases by a list of formatted numbers."""
    cases = session.query(Case).filter(Case.formatted_case_number.in_(formatted_case_numbers)).all()
    return cases

def get_charge_by_id(id):
    charge = session.query(Charge).filter_by(id=id).first()
    return charge

def get_charges_by_ids(ids):
    """Retrieve charges by a list of IDs."""
    charges = session.query(Charge).filter(Charge.id.in_(ids)).all()
    return charges

def get_charge_by_code_section(code_section):
    charge = session.query(Charge).filter_by(code_section=code_section).first()
    return charge

def get_charges_by_code_sections(code_sections):
    """Retrieve charges by a list of code sections."""
    charges = session.query(Charge).filter(Charge.code_section.in_(code_sections)).all()
    return charges