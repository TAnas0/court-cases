
from sqlalchemy import Column, String, Integer
from .base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from typing import List
from sqlalchemy.orm import mapped_column


class Court(Base):
    __tablename__ = 'courts'

    id = mapped_column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    court_type = Column(String)
    fips_code = Column(String)
    fips_code_4 = Column(String)  # 4-letter FIPS code. Includes the court type
    location = Column(String)
    url = Column(String)

    cases: Mapped[List["Case"]] = relationship(back_populates="court")
    # cases = relationship("Case", back_populates="court")
    
    def __repr__(self):
        return f"<Court(name='{self.name}', court_type='{self.court_type}')>"
