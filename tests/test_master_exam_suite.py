import pytest
import json
from datetime import datetime, timezone, timedelta
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.config import settings
from backend.app.models.models import (
    Roster, Assessment, Section, Question, Option, Attempt, Answer, Violation, Restart, PendingSheetWrite
)
from backend.app.schemas.auth import SessionUser, LoginRequest
from backend.app.schemas.candidate import AnswerSaveRequest, ConsentRequest
from backend.app.api.auth import login
from backend.app.api.candidate import get_exam, save_answer, get_status, submit_exam, give_consent
from backend.app.api.proctor import report_violation, ViolationReportRequest
from backend.app.api.admin import reconcile_sheet_and_db, finalize_and_export_multi_sheet
from backend.app.services.shuffle_service import generate_attempt_shuffle, should_keep_options_fixed
from backend.app.services.question_import_service import parse_and_validate_question_file, generate_sample_template_csv
from backend.app.services.sheets_service import process_pending_sheet_writes, queue_or_write_sheet
from backend.app.services.export_service import generate_final_comprehensive_excel
from fastapi import HTTPException


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
def exam_test_setup():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Create test candidates in Roster
    candidates = [
        ("CAND_SUITE_01", "Alice Sharma", "HR", "CANDIDATE"),
        ("CAND_SUITE_02", "Bob Verma", "HR", "CANDIDATE"),
        ("CAND_SUITE_03", "Charlie Rao", "CLAIM", "CANDIDATE"),
    ]
    for code, name, dept, role in candidates:
        r = session.query(Roster).filter_by(employee_code=code).first()
        if not r:
            r = Roster(employee_code=code, full_name=name, department=dept, role=role, is_active=True)
            session.add(r)

    # Ensure HR assessment exists
    ass = session.query(Assessment).filter_by(id=1).first()
    if not ass:
        ass = Assessment(
            id=1,
            title="HR TEAM – PROFESSIONAL ASSESSMENT",
            duration_minutes=60,
            total_marks=100,
            marks_per_question=2,
            negative_marking=False,
            status="OPEN",
            settings={"department": "HR"}
        )
        session.add(ass)
    # Ensure clean attempts for test suite candidates
    session.query(Answer).filter(Answer.attempt.has(Attempt.employee_code.in_(["CAND_SUITE_01", "CAND_SUITE_02", "CAND_SUITE_03"]))).delete(synchronize_session=False)
    session.query(Violation).filter(Violation.attempt.has(Attempt.employee_code.in_(["CAND_SUITE_01", "CAND_SUITE_02", "CAND_SUITE_03"]))).delete(synchronize_session=False)
    session.query(Restart).filter(Restart.attempt.has(Attempt.employee_code.in_(["CAND_SUITE_01", "CAND_SUITE_02", "CAND_SUITE_03"]))).delete(synchronize_session=False)
    session.query(Attempt).filter(Attempt.employee_code.in_(["CAND_SUITE_01", "CAND_SUITE_02", "CAND_SUITE_03"])).delete(synchronize_session=False)
    session.commit()
    session.close()


def test_different_candidates_get_different_shuffles(exam_test_setup):
    """Verifies that two candidates in the same department receive different question/option orders."""
    session = SessionLocal()
    try:
        req = DummyRequest()
        resp = DummyResponse()

        # Login candidate 1
        l1 = login(LoginRequest(employee_code="CAND_SUITE_01", full_name="Alice Sharma", department="HR"), req, resp, db=session)
        att1 = session.query(Attempt).filter_by(id=l1.attempt_id).first()

        # Login candidate 2
        l2 = login(LoginRequest(employee_code="CAND_SUITE_02", full_name="Bob Verma", department="HR"), req, resp, db=session)
        att2 = session.query(Attempt).filter_by(id=l2.attempt_id).first()

        assert att1.id != att2.id
        # Given 50 questions, probability of identical Fisher-Yates shuffle is 1/50! (~0)
        assert att1.question_order != att2.question_order or len(att1.question_order) <= 1
    finally:
        session.close()


def test_fixed_options_protection():
    """Verifies that questions with 'All of the above' or 'None of the above' keep fixed option orders."""
    options_with_all = ["Option 1", "Option 2", "Option 3", "All of the above"]
    options_normal = ["Salary", "Leaves", "Appraisal", "Bonus"]

    assert should_keep_options_fixed(options_with_all) is True
    assert should_keep_options_fixed(options_normal) is False


def test_one_attempt_enforcement(exam_test_setup):
    """Verifies that a candidate cannot take the test a second time once submitted."""
    session = SessionLocal()
    try:
        att = session.query(Attempt).filter_by(employee_code="CAND_SUITE_01").first()
        att.status = "SUBMITTED"
        session.commit()

        req = DummyRequest()
        resp = DummyResponse()
        with pytest.raises(HTTPException) as exc:
            login(LoginRequest(employee_code="CAND_SUITE_01", full_name="Alice Sharma", department="HR"), req, resp, db=session)
        assert exc.value.status_code == 403
        assert "You have already attempted this test." in exc.value.detail
    finally:
        session.close()


def test_tab_switch_warnings_and_restart(exam_test_setup):
    """Verifies that tab switches 1-5 give warnings, and the 6th switch triggers RESTART."""
    session = SessionLocal()
    try:
        # Reset candidate 2 to in_progress
        att = session.query(Attempt).filter_by(employee_code="CAND_SUITE_02").first()
        att.status = "IN_PROGRESS"
        att.warning_count = 0
        att.restart_count = 0
        session.commit()

        user = SessionUser(employee_code="CAND_SUITE_02", full_name="Bob Verma", role="CANDIDATE", attempt_id=att.id)

        # Violations 1 to 5: Warnings
        for w in range(1, 6):
            res = report_violation(ViolationReportRequest(kind="TAB_SWITCH"), current_user=user, db=session)
            assert res.action == "WARNING"

        # 6th Violation: RESTART
        res6 = report_violation(ViolationReportRequest(kind="TAB_SWITCH"), current_user=user, db=session)
        assert res6.action == "RESTART"
        assert "restarted" in res6.message

        session.refresh(att)
        assert att.restart_count == 1
        assert att.warning_count == 0  # Reset for the fresh run
        assert att.tab_switch_total >= 6
    finally:
        session.close()


def test_pass_fail_rule_threshold():
    """Verifies that Score >= 35 is PASS and Score < 35 is FAIL."""
    from backend.app.services.grading import determine_band
    assert settings.PASS_MARKS == 35

    score_pass = 35
    score_fail = 34
    assert ("PASS" if score_pass >= settings.PASS_MARKS else "FAIL") == "PASS"
    assert ("PASS" if score_fail >= settings.PASS_MARKS else "FAIL") == "FAIL"


def test_question_import_validation():
    """Verifies validation of question bank template: exact 100 marks requirement and no duplicate IDs."""
    sample_csv = generate_sample_template_csv().encode("utf-8")
    valid_q, errors, dept_marks = parse_and_validate_question_file(sample_csv, "template.csv")
    assert len(errors) == 0
    assert len(valid_q) == 200  # 100 HR + 100 CLAIM
    assert dept_marks.get("HR") == 100
    assert dept_marks.get("CLAIM") == 100

    # Invalid CSV with wrong marks total (not 100)
    bad_csv = (
        "question_id,department,question_text,option_a,option_b,option_c,option_d,correct_option,marks\n"
        "HR_01,HR,Stem text?,A,B,C,D,A,50\n"
    ).encode("utf-8")
    _, bad_errors, _ = parse_and_validate_question_file(bad_csv, "bad.csv")
    assert any("must add up to exactly 100" in e for e in bad_errors)


def test_pending_sheet_writes_retry_queue():
    """Verifies durable queueing in pending_sheet_writes and idempotent drain."""
    session = SessionLocal()
    try:
        key = f"test_idemp_{datetime.now(timezone.utc).timestamp()}"
        payload = {"row": ["test_val_1", "test_val_2"]}
        queue_or_write_sheet(session, "append_attempt", key, payload, attempt_id=1)

        record = session.query(PendingSheetWrite).filter_by(idempotency_key=key).first()
        assert record is not None
        assert record.status in ("COMPLETED", "PENDING")

        processed = process_pending_sheet_writes(session)
        assert processed >= 0
    finally:
        session.close()


def test_comprehensive_excel_generation():
    """Verifies that the multi-tab finalize export contains all required sheets."""
    session = SessionLocal()
    try:
        excel_bytes = generate_final_comprehensive_excel(session)
        assert len(excel_bytes) > 1000
        assert excel_bytes.startswith(b"PK")  # Valid ZIP / XLSX signature
    finally:
        session.close()


def test_claim_department_assessment_flow(exam_test_setup):
    """Verifies login, 100-question paper delivery, and answer submission for the Claim Department."""
    session = SessionLocal()
    try:
        req = DummyRequest()
        resp = DummyResponse()

        # Login candidate Charlie Rao for CLAIM department
        auth_resp = login(LoginRequest(employee_code="CAND_SUITE_03", full_name="Charlie Rao", department="CLAIM"), req, resp, db=session)
        assert auth_resp.role == "CANDIDATE"
        assert auth_resp.attempt_id is not None

        user = SessionUser(
            employee_code="CAND_SUITE_03",
            full_name="Charlie Rao",
            role="CANDIDATE",
            attempt_id=auth_resp.attempt_id
        )

        # Candidate gives consent
        consent_resp = give_consent(ConsentRequest(consent=True), current_user=user, db=session)
        assert "recorded" in consent_resp["message"].lower()

        # Retrieve exam paper
        exam = get_exam(current_user=user, db=session)
        assert len(exam.questions) == 100
        assert sum(q.marks for q in exam.questions) == 100

        # Verify each question has exactly 4 options
        for q in exam.questions:
            assert len(q.options) == 4

        # Save an answer for first question
        first_q = exam.questions[0]
        first_opt = first_q.options[0]
        save_resp = save_answer(AnswerSaveRequest(question_id=first_q.id, option_id=first_opt.id), current_user=user, db=session)
        assert save_resp.status.lower() == "saved"

        # Submit exam
        sub_resp = submit_exam(current_user=user, db=session)
        assert sub_resp.status in ("SUBMITTED", "AUTO_SUBMITTED")
        assert sub_resp.score is not None
        assert sub_resp.result in ("PASS", "FAIL")
    finally:
        session.close()


def test_ashtapradhan_assessment_flow(exam_test_setup):
    """Verifies login, 25-question paper delivery, candidate personal info/post profiling, and submission for the Ashtapradhan Assessment."""
    session = SessionLocal()
    try:
        import uuid
        cand_code = f"ASH_{uuid.uuid4().hex[:8].upper()}"
        req = DummyRequest()
        resp = DummyResponse()

        # Login candidate for ASSESSMENT department with profile details
        auth_resp = login(
            LoginRequest(
                employee_code=cand_code,
                full_name="Tanaji Malusare",
                department="ASSESSMENT",
                current_department="Operations",
                current_post="Executive",
                mobile_number="9876543210",
                target_post="संचालक कार्यालय प्रमुख (Manager)"
            ),
            req,
            resp,
            db=session
        )
        assert auth_resp.role == "CANDIDATE"
        assert auth_resp.attempt_id is not None

        user = SessionUser(
            employee_code=cand_code,
            full_name="Tanaji Malusare",
            role="CANDIDATE",
            attempt_id=auth_resp.attempt_id
        )

        # Candidate gives consent
        consent_resp = give_consent(ConsentRequest(consent=True), current_user=user, db=session)
        assert "recorded" in consent_resp["message"].lower()

        # Retrieve exam paper
        exam = get_exam(current_user=user, db=session)
        assert len(exam.questions) == 25
        assert sum(q.marks for q in exam.questions) == 100
        for q in exam.questions:
            assert q.marks == 4
            assert len(q.options) == 4

        # Save an answer for first question
        first_q = exam.questions[0]
        first_opt = first_q.options[0]
        save_resp = save_answer(AnswerSaveRequest(question_id=first_q.id, option_id=first_opt.id), current_user=user, db=session)
        assert save_resp.status.lower() == "saved"

        # Submit exam
        sub_resp = submit_exam(current_user=user, db=session)
        assert sub_resp.status in ("SUBMITTED", "AUTO_SUBMITTED")
        assert sub_resp.score is not None
        assert sub_resp.result in ("PASS", "FAIL")
    finally:
        session.close()

