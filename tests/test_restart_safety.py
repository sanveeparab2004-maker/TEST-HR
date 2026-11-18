import pytest
from datetime import datetime, timezone, timedelta
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Assessment, Attempt, Answer, Violation, Question, Option
from backend.app.schemas.auth import SessionUser
from backend.app.schemas.auth import SessionUser, LoginRequest
from backend.app.schemas.candidate import AnswerSaveRequest, ConsentRequest
from backend.app.api.auth import login
from backend.app.api.candidate import get_exam, save_answer, get_status, give_consent
from backend.app.api.proctor import report_violation, ViolationReportRequest


class DummyClient:
    host = "127.0.0.1"


class DummyRequest:
    client = DummyClient()
    cookies = {}


class DummyResponse:
    def __init__(self):
        self.cookies = {}

    def set_cookie(self, key, value, **kwargs):
        self.cookies[key] = value

    def delete_cookie(self, key, **kwargs):
        self.cookies.pop(key, None)


@pytest.fixture(scope="module")
def restart_test_setup():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    emp_code = "EMP_RESTART_01"
    session.query(Answer).filter(Answer.attempt.has(employee_code=emp_code)).delete(synchronize_session=False)
    session.query(Attempt).filter_by(employee_code=emp_code).delete()
    session.commit()

    roster_entry = session.query(Roster).filter_by(employee_code=emp_code).first()
    if not roster_entry:
        roster_entry = Roster(
            employee_code=emp_code,
            full_name="Kavita Krishnan",
            department="HR Talent Acquisition",
            role="CANDIDATE",
            is_active=True
        )
        session.add(roster_entry)
        session.commit()

    assessment = session.query(Assessment).first()
    assessment_id = assessment.id if assessment else 1

    # Candidate logs in
    req = DummyRequest()
    resp = DummyResponse()
    login_res = login(
        LoginRequest(employee_code=emp_code, full_name="Kavita Krishnan"),
        req, resp, db=session
    )

    candidate_user = SessionUser(
        employee_code=emp_code,
        full_name="Kavita Krishnan",
        role="CANDIDATE",
        attempt_id=login_res.attempt_id
    )
    session.close()
    return candidate_user, assessment_id


def test_restart_safety_state_persistence(restart_test_setup):
    """
    Validates Free-Tier Constraint #6: RESTART-SAFE BY DESIGN.
    All exam state lives in DB (attempt, deadline, answers, warning_count, violations).
    A server crash/restart must not lose candidate answers, must not reset warnings,
    and must NEVER extend or reset the 60-minute deadline.
    """
    candidate_user, assessment_id = restart_test_setup

    # === STEP 1: BEFORE RESTART ===
    # Candidate gives consent and starts exam
    db1 = SessionLocal()
    try:
        give_consent(ConsentRequest(consent=True), current_user=candidate_user, db=db1)
        exam_data = get_exam(current_user=candidate_user, db=db1)
        attempt_id = candidate_user.attempt_id
        original_deadline = exam_data.deadline_at
        initial_q_order = [q.id for q in exam_data.questions]
        first_q = exam_data.questions[0]
        selected_option = first_q.options[1].id

        # Candidate submits an answer
        save_answer(
            AnswerSaveRequest(question_id=first_q.id, option_id=selected_option, flagged=True),
            current_user=candidate_user,
            db=db1
        )

        # Candidate incurs 2 counted violations
        report_violation(
            ViolationReportRequest(kind="TAB_SWITCH", details={"tab": "google.com"}),
            current_user=candidate_user,
            db=db1
        )
        report_violation(
            ViolationReportRequest(kind="WINDOW_BLUR", details={"duration_ms": 3200}),
            current_user=candidate_user,
            db=db1
        )

        # Verify state in DB before restart
        att_before = db1.query(Attempt).filter_by(id=attempt_id).first()
        assert att_before.warning_count == 2
        assert att_before.status == "IN_PROGRESS"
    finally:
        # Simulate abrupt server restart: connection closed, memory destroyed
        db1.close()

    # === STEP 2: SIMULATED RESTART OCCURS (Brand new server instance / process boots up) ===
    db2 = SessionLocal()
    try:
        # Re-fetch candidate status as if client reconnected after server came back online
        status_after = get_status(current_user=candidate_user, db=db2)
        assert status_after.status == "IN_PROGRESS"
        assert status_after.warning_count == 2
        assert status_after.consent_at is not None
        assert status_after.deadline_at == original_deadline

        # Re-fetch candidate exam payload
        exam_after = get_exam(current_user=candidate_user, db=db2)
        restarted_q_order = [q.id for q in exam_after.questions]

        # 1. Shuffled question sequence is identical (deterministic from stored DB array)
        assert initial_q_order == restarted_q_order

        # 2. Deadline is strictly preserved from database and NOT extended by the restart
        assert exam_after.deadline_at == original_deadline

        # 3. Previously saved answers survive restart intact
        saved_answer_record = db2.query(Answer).filter_by(attempt_id=attempt_id, question_id=first_q.id).first()
        assert saved_answer_record is not None
        assert saved_answer_record.option_id == selected_option
        assert saved_answer_record.flagged is True

        # 4. Warnings counter continues from exactly where it left off
        # A 3rd violation should trigger warning 3
        v3 = report_violation(
            ViolationReportRequest(kind="COPY_PASTE", details={"text": "blocked"}),
            current_user=candidate_user,
            db=db2
        )
        assert v3.warning_count == 3
        assert v3.warning_tier == "WARNING_3"
    finally:
        db2.close()
