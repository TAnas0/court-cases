
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .base import Base
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped


class Case(Base):
    __tablename__ = 'cases'
    __table_args__ = (
        UniqueConstraint('case_number', 'code_section', 'is_appeal', 'commenced_by', name='uq_case_key'),
    )

    id = Column(Integer, primary_key=True)
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
    court_id = Column(Integer, ForeignKey("courts.id"))
    court: Mapped["Court"] = relationship("Court", back_populates="cases")

    def __repr__(self):
        return f"<Case(case_number='{self.case_number}', type='{self.case_type}')>"
