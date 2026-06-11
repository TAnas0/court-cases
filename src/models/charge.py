from datetime import date
from sqlalchemy import Column, Date, String, Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from .base import Base
from .case_charge import CaseCharge


from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Charge(Base):
    __tablename__ = "charges"
    __table_args__ = (
        UniqueConstraint("code_section", name="uq_charge_code_section"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code_section: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    case_links: Mapped[List["CaseCharge"]] = relationship("CaseCharge", back_populates="charge")

    def __repr__(self) -> str:
        return f"<Charge(id={self.id}, code='{self.code_section}')>"
