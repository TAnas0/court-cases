from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from .base import Base


class Hearing(Base):
    """
    Hearing entity stores individual hearing details for each case.
    """
    __tablename__ = 'hearings'

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    schedule_date = Column(DateTime, nullable=False)
    hearing_type = Column(String(5), nullable=True)
    result = Column(String(5), nullable=True)
    court_room = Column(String(10), nullable=True)
    continuance_code = Column(String(10), nullable=True)
    plea = Column(String(5), nullable=True)
