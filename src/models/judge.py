from sqlalchemy import Column, String, Integer, ForeignKey
from .base import Base


class Judge(Base):
    __tablename__ = "judges"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    court_id = Column(Integer, ForeignKey("courts.id"))

    def __repr__(self):
        return f"<Judge(name='{self.name}')>"
