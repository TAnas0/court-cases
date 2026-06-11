from datetime import date
from sqlalchemy.orm import Session
from src.models.court import Court
from src.models.court_case import CourtCase
from src.models.charge import Charge
from src.models.case_charge import CaseCharge

def test_court_case_charge_lifecycle(db_session: Session):
    # 1. Arrange: Create our mock jurisdiction core bounds
    mock_court = Court(
        qualified_fips="VA059",
        court_level="Circuit",
        division_type="Criminal",
        court_name="Fairfax County Circuit Court"
    )
    db_session.add(mock_court)
    db_session.flush()  # Populates mock_court.id safely

    # 2. Arrange: Create a case linked to that court
    mock_case = CourtCase(
        court_id=mock_court.id,
        case_number="CR-2026-00451A",
        style_of_case="Commonwealth v. Jane Doe",
        original_filing_date=date(2026, 3, 15),
        current_judge="Hon. Randy Bellows"
    )
    db_session.add(mock_case)
    db_session.flush()

    # 3. Arrange: Create a global master charge mapping
    statute_charge = Charge(
        code_section="18.2-248",
        description="Manufacture/Sale/Distribution of Controlled Substance"
    )
    db_session.add(statute_charge)
    db_session.flush()

    # 4. Act: Build the transactional relationship link
    case_occurrence = CaseCharge(
        case_id=mock_case.id,
        charge_id=statute_charge.id,
        filling_date=date(2026, 3, 16),
        case_type_code="Felony",
        class_code="U"
    )
    db_session.add(case_occurrence)
    db_session.commit()

    # 5. Assert: Pull a fresh look from the DB and evaluate integrity hooks
    retrieved_case = db_session.query(CourtCase).filter_by(case_number="CR-2026-00451A").one()
    
    assert len(retrieved_case.charges) == 1
    assert retrieved_case.charges[0].charge.code_section == "18.2-248"
    assert retrieved_case.court.qualified_fips == "VA059"
    assert retrieved_case.case_delay_days >= 0  # Testing our model's smart properties

    # 6. Test Cascade Delete: Dropping a case should automatically clear its links
    db_session.delete(retrieved_case)
    db_session.commit()

    remaining_links = db_session.query(CaseCharge).filter_by(case_id=mock_case.id).all()
    assert len(remaining_links) == 0

    # Ensure the global Master Charge catalog itself was safely preserved (Not deleted)
    assert db_session.query(Charge).filter_by(code_section="18.2-248").count() == 1