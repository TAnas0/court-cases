import pytest
from src.models import CourtCase


def test_case_creation():
    case = CourtCase(
        case_number="CR2024-001",
        # formatted_case_number="CR-2024-001",
        # code_section="18.2-95",
        # case_type="M",
        # is_criminal=True,
        # is_active=True,
    )
    assert case.case_number == "CR2024-001"
    # assert case.is_criminal is True


def test_case_repr():
    case = CourtCase(
        case_number="CR001",
        # case_type="F"
    )
    repr_str = repr(case)
    assert "CR001" in repr_str
