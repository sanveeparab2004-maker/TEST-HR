import os
import pytest

# Ensure all tests run strictly against an isolated test database, never touching the real assess_local.db
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"

from backend.app.core.database import Base, engine, SessionLocal
from backend.app.models.models import Assessment, Roster
from backend.app.core.security import get_pin_hash
from scripts.import_questions import parse_assessment_docx, load_into_db

@pytest.fixture(scope="session", autouse=True)
def setup_and_cleanup_test_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Load questions from docx if available
        docx_path = os.path.join(os.path.dirname(__file__), "..", "data", "HR_Team_Professional_Assessment.docx")
        if os.path.exists(docx_path):
            try:
                parsed = parse_assessment_docx(docx_path)
                load_into_db(parsed)
            except Exception as e:
                print("Failed to load questions in test setup:", e)

        claim_docx = os.path.join(os.path.dirname(__file__), "..", "data", "Claim_Department_Question_Paper.docx")
        if os.path.exists(claim_docx):
            try:
                from scripts.import_claim_questions import parse_claim_docx, load_claim_into_db
                claim_q = parse_claim_docx(claim_docx)
                load_claim_into_db(claim_q)
            except Exception as e:
                print("Failed to load claim questions in test setup:", e)

        ashtapradhan_csv = os.path.join(os.path.dirname(__file__), "..", "data", "ashtapradhan_questions.csv")
        if os.path.exists(ashtapradhan_csv):
            try:
                from scripts.import_ashtapradhan_questions import load_ashtapradhan_questions, seed_ashtapradhan_into_db
                ash_q = load_ashtapradhan_questions(ashtapradhan_csv)
                seed_ashtapradhan_into_db(ash_q)
            except Exception as e:
                print("Failed to load ashtapradhan questions in test setup:", e)

        # Seed default assessment if missing
        a = session.query(Assessment).filter_by(id=1).first()
        if not a:
            a = Assessment(
                id=1,
                title="HR TEAM – PROFESSIONAL ASSESSMENT",
                duration_minutes=60,
                total_marks=100,
                marks_per_question=2,
                negative_marking=False,
                status="OPEN",
                settings={"department": "HR"}
            )
            session.add(a)

        # Seed default candidates and admins for test assertions
        users = [
            ("C-2606026", "Durvesh Parab", "HR Department", "CANDIDATE", None),
            ("E-2606026", "Durvesh Parab", "Admin Operations", "ADMIN", get_pin_hash("123456")),
            ("HR_ADMIN_01", "HR Admin", "Admin", "ADMIN", get_pin_hash("987123")),
            ("HR_MONITOR_01", "HR Monitor", "Monitor", "MONITOR", get_pin_hash("654321")),
        ]
        for code, name, dept, role, pin_hash in users:
            r = session.query(Roster).filter_by(employee_code=code).first()
            if not r:
                session.add(Roster(
                    employee_code=code,
                    full_name=name,
                    department=dept,
                    role=role,
                    pin_hash=pin_hash,
                    is_active=True
                ))
        session.commit()
    finally:
        session.close()

    yield

    # Clean up test database file after test suite runs
    if os.path.exists("test_suite.db"):
        try:
            os.remove("test_suite.db")
        except Exception:
            pass
