from datetime import date
from sqlalchemy import ForeignKey, String, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class CaseCharge(Base):
    __tablename__ = "case_charges"
    __table_args__ = (
        # Ensures we don't map the exact same charge record to a case twice
        UniqueConstraint(
            "case_id", "charge_id", "filling_date", name="uq_case_charge_occurrence"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("court_cases.id", ondelete="CASCADE"), nullable=False
    )
    charge_id: Mapped[int] = mapped_column(
        ForeignKey("charges.id", ondelete="RESTRICT"), nullable=False
    )

    filling_date: Mapped[date] = mapped_column(Date, nullable=False)
    case_type_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    class_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_original: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    is_amended: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Relationships
    court_case: Mapped["CourtCase"] = relationship(
        "CourtCase", back_populates="charges"
    )
    charge: Mapped["Charge"] = relationship("Charge", back_populates="case_links")

    def __repr__(self) -> str:
        return f"<CaseCharge(case_id={self.case_id}, charge_id={self.charge_id})>"
