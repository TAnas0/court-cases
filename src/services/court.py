from src.models import Court
from src.database.main import SessionLocal


def get_all_courts():
    """Get all Courts from database."""
    session = SessionLocal()
    try:
        return session.query(Court).all()
    finally:
        session.close()
