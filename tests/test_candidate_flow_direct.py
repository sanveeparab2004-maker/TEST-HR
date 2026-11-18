import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.config import settings
from backend.app.models.models import Roster, Assessment, Attempt, Question, Option, Answer, AuditLog
from backend.app.core.security import get_pin_hash, hash_device_token
from backend.app.schemas.auth import LookupRequest, LoginRequest, SessionUser
from backend.app.schemas.candidate import AnswerSaveRequest, ConsentRequest
from backend.app.api.auth import lookup_employee, login
from backend.app.api.candidate import get_status, give_consent, get_exam, save_answer, submit_exam
from backend.app.api.admin_device import release_device_lock, ReleaseDeviceLockRequest


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
def setup_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Ensure Assessment exists
    assessment = session.query(Assessment).first()
    if not assessment:
        assessment = Assessment(
            title="HR TEAM – PROFESSIONAL ASSESSMENT",
            duration_minutes=60,
            total_marks=100,
            marks_per_question=2,
            negative_marking=False,
            status="OPEN",
            settings={"show_score_on_submission": False}
        )
        session.add(assessment)
        session.commit()

    # Ensure Monitor, Admin, and Candidate in roster
    monitor = session.query(Roster).filter_by(employee_code="HR_MONITOR_01").first()
    if not monitor:
        session.add(Roster(
            employee_code="HR_MONITOR_01",
            full_name="Chief Exam Proctor",
            role="MONITOR",
            pin_hash=get_pin_hash("654321")
        ))

    admin = session.query(Roster).filter_by(employee_code="HR_ADMIN_01").first()
    if not admin:
        session.add(Roster(
            employee_code="HR_ADMIN_01",
            full_name="HR Operations Lead",
            role="ADMIN",
            pin_hash=get_pin_hash("987123")
        ))

    cand = session.query(Roster).filter_by(employee_code="EMP001").first()
    if not cand:
        session.add(Roster(
            employee_code="EMP001",
            full_name="Aarav Sharma",
            department="Talent Acquisition",
            role="CANDIDATE"
        ))

    cand2 = session.query(Roster).filter_by(employee_code="EMP002").first()
    if not cand2:
        session.add(Roster(
            employee_code="EMP002",
            full_name="Diya Patel",
            department="HR Operations",
            role="CANDIDATE"
        ))

    session.commit()
    session.close()


def test_auth_lookup(setup_db):
    session = SessionLocal()
    try:
        # Monitor requires PIN
        res = lookup_employee(LookupRequest(employee_code="HR_MONITOR_01"), db=session)
        assert res.requires_pin is True

        # Admin requires PIN
        res = lookup_employee(LookupRequest(employee_code="HR_ADMIN_01"), db=session)
        assert res.requires_pin is True

        # Candidate does NOT require PIN
        res = lookup_employee(LookupRequest(employee_code="EMP001"), db=session)
        assert res.requires_pin is False

        # Unknown code returns False
        res = lookup_employee(LookupRequest(employee_code="UNKNOWN_999"), db=session)
        assert res.requires_pin is False
    finally:
        session.close()


def test_auth_generic_error_on_mismatch(setup_db):
    session = SessionLocal()
    req = DummyRequest()
    resp = DummyResponse()
    try:
        # Wrong name -> generic error
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(employee_code="EMP001", full_name="Wrong Name"), req, resp, db=session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Details not found. Contact HR."

        # Non-existent code -> generic error
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(employee_code="NONEXISTENT", full_name="Aarav Sharma"), req, resp, db=session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Details not found. Contact HR."

        # Monitor wrong PIN -> generic error
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(employee_code="HR_MONITOR_01", full_name="Chief Exam Proctor", pin="000000"), req, resp, db=session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Details not found. Contact HR."
    finally:
        session.close()


def test_candidate_single_device_flow_and_admin_release(setup_db):
    session = SessionLocal()
    req = DummyRequest()
    resp = DummyResponse()
    try:
        # Clean previous attempt for EMP001
        session.query(Answer).filter(Answer.attempt.has(employee_code="EMP001")).delete(synchronize_session=False)
        session.query(Attempt).filter_by(employee_code="EMP001").delete()
        session.commit()

        # 1. First login on Laptop 1
        res1 = login(LoginRequest(
            employee_code="EMP001",
            full_name="Aarav Sharma",
            device_info={"browser": "Chrome", "os": "Windows"}
        ), req, resp, db=session)

        assert res1.role == "CANDIDATE"
        device_token1 = res1.device_token
        assert device_token1 is not None

        # 2. Second login on Laptop 2 (different device token) -> REJECTED
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(
                employee_code="EMP001",
                full_name="Aarav Sharma",
                device_token="different_laptop_token_123"
            ), req, resp, db=session)
        assert exc_info.value.status_code == 403
        assert "already active on another device" in exc_info.value.detail

        # 3. Same device (Laptop 1) resumes with matching device_token -> SUCCEEDS
        res_resume = login(LoginRequest(
            employee_code="EMP001",
            full_name="Aarav Sharma",
            device_token=device_token1
        ), req, resp, db=session)
        assert res_resume.device_token == device_token1

        # 4. Admin releases device lock for EMP001
        admin_user = SessionUser(employee_code="HR_ADMIN_01", full_name="HR Operations Lead", role="ADMIN")
        release_res = release_device_lock(
            ReleaseDeviceLockRequest(employee_code="EMP001", reason="Candidate laptop screen cracked"),
            current_user=admin_user,
            db=session
        )
        assert release_res["status"] == "success"

        # 5. Candidate can now successfully log in from new Laptop 2
        res_new_device = login(LoginRequest(
            employee_code="EMP001",
            full_name="Aarav Sharma",
            device_info={"browser": "Edge", "os": "Windows"}
        ), req, resp, db=session)
        assert res_new_device.device_token != device_token1
    finally:
        session.close()


def test_candidate_exam_security_and_autosave(setup_db):
    session = SessionLocal()
    req = DummyRequest()
    resp = DummyResponse()
    try:
        # Clean previous attempt for EMP002
        session.query(Answer).filter(Answer.attempt.has(employee_code="EMP002")).delete(synchronize_session=False)
        session.query(Attempt).filter_by(employee_code="EMP002").delete()
        session.commit()

        login_res = login(LoginRequest(
            employee_code="EMP002",
            full_name="Diya Patel"
        ), req, resp, db=session)

        user = SessionUser(
            employee_code="EMP002",
            full_name="Diya Patel",
            role="CANDIDATE",
            attempt_id=login_res.attempt_id
        )

        # 1. Candidate Consent
        consent_res = give_consent(ConsentRequest(consent=True), current_user=user, db=session)
        assert "consent_at" in consent_res

        # 2. Candidate Exam Fetch
        exam_data = get_exam(current_user=user, db=session)
        assert exam_data.assessment_title == "HR TEAM – PROFESSIONAL ASSESSMENT"
        assert exam_data.duration_minutes == 60
        assert 3500 <= exam_data.remaining_seconds <= 3600
        assert len(exam_data.questions) == 50

        # SECURITY CHECK: verify is_correct is NEVER leaked in any question or option!
        for q in exam_data.questions:
            q_dict = q.model_dump()
            assert "is_correct" not in q_dict
            for opt in q.options:
                opt_dict = opt.model_dump()
                assert "is_correct" not in opt_dict
                assert opt.label in ("A", "B", "C", "D")

        # 3. Autosave an answer
        first_q = exam_data.questions[0]
        chosen_opt = first_q.options[0]

        save_res = save_answer(AnswerSaveRequest(
            question_id=first_q.id,
            option_id=chosen_opt.id,
            flagged=True
        ), current_user=user, db=session)

        assert save_res.status == "saved"
        assert save_res.flagged is True

        # 4. Fetch exam again: verify saved answer and flag are reflected
        exam_data_2 = get_exam(current_user=user, db=session)
        assert exam_data_2.answers[first_q.id] == chosen_opt.id
        assert exam_data_2.flagged[first_q.id] is True

        # 5. Submit exam
        submit_res = submit_exam(current_user=user, db=session)
        assert submit_res.status == "SUBMITTED"

        # 6. Verify subsequent answer saves are BLOCKED
        with pytest.raises(HTTPException) as exc_info:
            save_answer(AnswerSaveRequest(
                question_id=first_q.id,
                option_id=chosen_opt.id
            ), current_user=user, db=session)
        assert exc_info.value.status_code == 403

        # 7. Verify subsequent submits are BLOCKED
        with pytest.raises(HTTPException) as exc_info:
            submit_exam(current_user=user, db=session)
        assert exc_info.value.status_code == 400
    finally:
        session.close()


def test_auto_submit_on_expired_deadline(setup_db):
    session = SessionLocal()
    req = DummyRequest()
    resp = DummyResponse()
    try:
        cand = session.query(Roster).filter_by(employee_code="EMP003").first()
        if not cand:
            session.add(Roster(employee_code="EMP003", full_name="Rohan Verma", role="CANDIDATE"))
            session.commit()

        session.query(Answer).filter(Answer.attempt.has(employee_code="EMP003")).delete(synchronize_session=False)
        session.query(Attempt).filter_by(employee_code="EMP003").delete()
        session.commit()

        login_res = login(LoginRequest(
            employee_code="EMP003",
            full_name="Rohan Verma"
        ), req, resp, db=session)

        user = SessionUser(
            employee_code="EMP003",
            full_name="Rohan Verma",
            role="CANDIDATE",
            attempt_id=login_res.attempt_id
        )

        # Artificially expire deadline in DB
        att = session.query(Attempt).filter_by(id=login_res.attempt_id).first()
        att.deadline_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        session.commit()

        # Calling get_status triggers auto-submit
        status_res = get_status(current_user=user, db=session)
        assert status_res.status == "AUTO_SUBMITTED"
        assert status_res.remaining_seconds == 0

        # Calling get_exam is now blocked
        with pytest.raises(HTTPException) as exc_info:
            get_exam(current_user=user, db=session)
        assert exc_info.value.status_code == 403
    finally:
        session.close()
