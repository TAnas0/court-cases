from src.models import Court
from src.models.base import Base
from src.database.main import get_db


db = get_db()

def get_all_courts():
    # Get all Courts from database
    with next(get_db()) as db:
        return db.query(Court).all()
