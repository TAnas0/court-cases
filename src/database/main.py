import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    DeclarativeBase = None
from sqlalchemy.dialects.postgresql import insert
from src.models import CourtCase, Charge, Court

# Configuration for PostgreSQL database
DATABASE_URL = os.environ["DATABASE_URL"]  # Fail explicitly if not set

# Create the SQLAlchemy engine
# Disable SQL echo in production by checking SQL_ECHO environment variable
engine = create_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO", "false").lower() == "true")

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models to inherit (for compatibility / general usage)
if DeclarativeBase is not None:
    class Base(DeclarativeBase):
        pass
else:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()



def get_db():
    """Dependency that creates and closes a session automatically for each request or function call."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_court_by_qualified_fips(session, qualified_fips):
    """
    """
    court = session.query(Court).filter_by(fips_code_4=qualified_fips).first()
    return court

def upsert_cases(session, cases_instances):
    
    cases_data_list = [instance.__dict__ for instance in cases_instances]

    # Remove SQLAlchemy internal attributes (e.g., _sa_instance_state)
    for case_data in cases_data_list:
        case_data.pop('_sa_instance_state', None)
        
    statement = insert(Case).values(cases_data_list)
    
    # Specify conflict handling on composite unique constraint
    statement = statement.on_conflict_do_update(
        index_elements=['case_number', 'code_section', 'is_appeal', 'commenced_by'],
        set_={col.name: getattr(statement.excluded, col.name) for col in CourtCase.__table__.columns} # Update all columns
    )

    # Execute the statement to insert or update
    session.execute(statement)
    session.commit()

def get_case_by_id(session, id):
    case = session.query(Case).filter_by(id=id).first()
    return case

def get_cases_by_ids(session, ids):
    """Retrieve cases by a list of IDs."""
    cases = session.query(Case).filter(Case.id.in_(ids)).all()
    return cases

def get_case_by_formatted_number(session, formatted_case_number):
    case = session.query(Case).filter_by(formatted_case_number=formatted_case_number).first()
    return case

def get_cases_by_formatted_numbers(session, formatted_case_numbers):
    """Retrieve cases by a list of formatted numbers."""
    cases = session.query(Case).filter(Case.formatted_case_number.in_(formatted_case_numbers)).all()
    return cases

def get_charge_by_id(session, id):
    charge = session.query(Charge).filter_by(id=id).first()
    return charge

def get_charges_by_ids(session, ids):
    """Retrieve charges by a list of IDs."""
    charges = session.query(Charge).filter(Charge.id.in_(ids)).all()
    return charges

def get_charge_by_code_section(session, code_section):
    charge = session.query(Charge).filter_by(code_section=code_section).first()
    return charge

def get_charges_by_code_sections(session, code_sections):
    """Retrieve charges by a list of code sections."""
    charges = session.query(Charge).filter(Charge.code_section.in_(code_sections)).all()
    return charges