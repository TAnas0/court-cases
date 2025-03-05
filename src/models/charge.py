from datetime import date
from sqlalchemy import Column, Date, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from .base import Base
from .case import Case
from sqlalchemy.orm import mapped_column


class Charge(Base):
    __tablename__ = 'charges'

    id = mapped_column(Integer, primary_key=True)
    code_section = Column(String, unique=True, nullable=False, index=True)  # Code section of the charge (unique)
    description = Column(String, nullable=False)  # Description of the charge
    # case_charges = relationship("CaseCharge", back_populates="charge")

class CaseCharge(Base):
    """
    Links a Case to Charge
    """
    __tablename__ = 'case_charges'

    id = mapped_column(Integer, primary_key=True)
    case_type_code = Column(String, nullable=True)
    class_code = Column(String, nullable=True)
    filling_date = Column(Date, nullable=False)  # *original* charge filing date
    is_original = Column(Boolean, default=False)
    is_amended = Column(Boolean, default=False)
    # amended_by =  # TODO self-referential 1-to-many relationship to point to amendment charges

    # Relationships
    case_id = Column(Integer, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    case = relationship('Case', backref=backref('case_charges', cascade='all, delete-orphan'))
    charge_id = Column(Integer, ForeignKey('charges.id'), nullable=False)
    charge = relationship('Charge')
    # charge = relationship('Charge', backref=backref('case_charges', cascade='all, delete-orphan'))
