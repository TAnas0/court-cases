
from .base import Base
from datetime import date, datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import UniqueConstraint, String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .court import Court
    from .hearing import Hearing
    from .case_charge import CaseCharge

class CourtCase(Base):
    __tablename__ = "court_cases"
    __table_args__ = (
        UniqueConstraint("court_id", "case_number", name="uq_court_case_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id", ondelete="CASCADE"), nullable=False)
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    style_of_case: Mapped[str] = mapped_column(String(500), nullable=False) # e.g., State v. Smith
    original_filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_judge: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    court: Mapped["Court"] = relationship("Court", back_populates="cases")
    hearings: Mapped[List["Hearing"]] = relationship(
        "Hearing", 
        back_populates="court_case", 
        cascade="all, delete-orphan",
        order_by="Hearing.hearing_date.asc()"
    )
    charges: Mapped[List["CaseCharge"]] = relationship("CaseCharge", back_populates="court_case", cascade="all, delete-orphan")

    # --- Smart Properties & Metrics ---
    @property
    def case_delay_days(self) -> int:
        """Calculates duration in days from original filing date to current day."""
        return (date.today() - self.original_filing_date).days

    @property
    def hearing_velocity_days(self) -> Optional[float]:
        """Calculates average frequency (in days) between scheduled hearings."""
        if len(self.hearings) < 2:
            return None
        
        intervals = [
            (self.hearings[i].hearing_date - self.hearings[i-1].hearing_date).days
            for i in range(1, len(self.hearings))
        ]
        return sum(intervals) / len(intervals)

    @property
    def latest_hearing(self) -> Optional["Hearing"]:
        """Returns the chronologically latest hearing record."""
        return self.hearings[-1] if self.hearings else None

    def __repr__(self) -> str:
        return f"<CourtCase(id={self.id}, case_number='{self.case_number}')>"