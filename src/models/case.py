
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Integer, DateTime, Table
from sqlalchemy.orm import relationship
from .base import Base
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from typing import List


# Association table for the many-to-many relationship
# case_charge_association = Table(
#     'case_charge_association',
#     Base.metadata,
#     Column('case_id', Integer, ForeignKey('cases.id'), primary_key=True),
#     Column('charge_id', Integer, ForeignKey('charges.id'), primary_key=True),
# )

class Case(Base):
    # TODO add a Charge attribute (and model)
    # TODO track history of a case, e.g. transfer to a new court
    __tablename__ = 'cases'
    __table_args__ = (
        UniqueConstraint('case_number', 'code_section', 'is_appeal', 'commenced_by', name='uq_case_key'),
    )

    id = mapped_column(Integer, primary_key=True)
    case_number = Column(String, nullable=False)
    formatted_case_number = Column(String, nullable=False)
    charge_amended = Column(Boolean, default=False)
    code_section = Column(String)
    case_type = Column(String)
    offense_date = Column(Date)
    arrest_date = Column(Date)
    is_criminal = Column(Boolean, default=False)
    category = Column(String)
    sub_category = Column(String)
    is_appeal = Column(Boolean, default=False)
    appeal_date = Column(Date)
    is_active = Column(Boolean, default=False)
    commenced_by = Column(String)
    
    # Relationships
    court_id = mapped_column(ForeignKey("courts.id"))
    court: Mapped["Court"] = relationship(back_populates="cases")


    # case_charges: Mapped[List["CaseCharge"]] = relationship(back_populates="case")
    # case_charges = relationship("CaseCharge", back_populates="case")

    # participants = relationship("Participant", back_populates="case")
    # hearings = relationship("Hearing", back_populates="case")
    # financial_information = relationship("FinancialInformation", back_populates="case")

    def __repr__(self):
        return f"<Case(case_number='{self.case_number}', name='{self.name}')>"

    # TODO calculated attribute to point to the case web page: for virginia, https://eapps.courts.state.va.us/ocis/details;fromOcis=true;fullcaseNumber=680JA0400120500

class Hearing(Base):
    """
    Hearing entity stores individual hearing details for each case.
    """
    __tablename__ = 'hearings'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    schedule_date = Column(DateTime, nullable=False) # ? Can it support date only, ordoes it require time too?
    hearing_type = Column(String(5), nullable=True)
    result = Column(String(5), nullable=True)
    court_room = Column(String(10), nullable=True)
    continuance_code = Column(String(10), nullable=True)
    plea = Column(String(5), nullable=True)
    sequence_number = Column(Integer, nullable=False)
    
    # case = relationship("Case", back_populates="hearings")
