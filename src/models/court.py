from .base import Base
from .court_case import CourtCase
from typing import List, TYPE_CHECKING
from sqlalchemy import UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .court_case import CourtCase


class Court(Base):
    __tablename__ = "courts"
    __table_args__ = (
        UniqueConstraint(
            "qualified_fips",
            "court_level",
            "division_type",
            name="uq_court_jurisdiction_boundary",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    qualified_fips: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    court_level: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "District", "Circuit"
    division_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "Criminal", "Civil"
    court_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    cases: Mapped[List["CourtCase"]] = relationship(
        "CourtCase", back_populates="court", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Court(id={self.id}, fips='{self.qualified_fips}', level='{self.court_level}')>"
