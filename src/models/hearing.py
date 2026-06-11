from datetime import date
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import UniqueConstraint, String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .court_case import CourtCase

class Hearing(Base):
    __tablename__ = "hearings"
    __table_args__ = (
        UniqueConstraint("court_case_id", "hearing_date", name="uq_hearing_timeline_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    court_case_id: Mapped[int] = mapped_column(ForeignKey("court_cases.id", ondelete="CASCADE"), nullable=False)
    hearing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    case_status: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Comprehensive nested JSONB engine architecture matching Pydantic structural models
    case_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    court_case: Mapped["CourtCase"] = relationship("CourtCase", back_populates="hearings")

    def __repr__(self) -> str:
        return f"<Hearing(id={self.id}, case_id={self.court_case_id}, date='{self.hearing_date}')>"