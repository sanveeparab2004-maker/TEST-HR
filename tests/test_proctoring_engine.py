import base64
import time
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Assessment, Attempt, Violation, Snapshot, Event
from backend.app.schemas.auth import SessionUser, LoginRequest
from backend.app.schemas.proctor import ViolationReportRequest, HeartbeatRequest
from backend.app.api.auth import login
from backend.app.api.proctor import report_violation, heartbeat, list_violations


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


@pytest.fixture
def candidate_user():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    assessment = session.query(Assessment).first()
    if not assessment:
        assessment = Assessment(
            title="HR TEAM – PROFESSIONAL ASSESSMENT",
            duration_minutes=60,
            total_marks=100,
            marks_per_question=2,
            negative_marking=False,
            status="OPEN"
        )
        session.add(assessment)
        session.commit()

    cand = session.query(Roster).filter_by(employee_code="EMP_PROCTOR_01").first()
    if not cand:
        session.add(Roster(
            employee_code="EMP_PROCTOR_01",
            full_name="Proctor Test Candidate",
            department="QA",
            role="CANDIDATE"
        ))
        session.commit()

    # Reset existing attempts
    session.query(Snapshot).filter(Snapshot.attempt_id.in_(
        session.query(Attempt.id).filter_by(employee_code="EMP_PROCTOR_01")
    )).delete(synchronize_session=False)
    session.query(Violation).filter(Violation.attempt.has(employee_code="EMP_PROCTOR_01")).delete(synchronize_session=False)
    session.query(Attempt).filter_by(employee_code="EMP_PROCTOR_01").delete()
    session.commit()

    req = DummyRequest()
    resp = DummyResponse()
    login_res = login(LoginRequest(
        employee_code="EMP_PROCTOR_01",
        full_name="Proctor Test Candidate"
    ), req, resp, db=session)

    user = SessionUser(
        employee_code="EMP_PROCTOR_01",
        full_name="Proctor Test Candidate",
        role="CANDIDATE",
        attempt_id=login_res.attempt_id
    )
    session.close()
    return user


def test_warning_state_machine_progression(candidate_user):
    session = SessionLocal()
    try:
        # Violation 1 -> WARNING_1
        v1 = report_violation(ViolationReportRequest(kind="TAB_SWITCH"), current_user=candidate_user, db=session)
        assert v1.warning_count == 1
        assert v1.warning_tier == "WARNING_1"
        assert v1.counted is True
        assert "Warning 1/3" in v1.message

        # Violation 2 -> WARNING_2
        v2 = report_violation(ViolationReportRequest(kind="WINDOW_BLUR"), current_user=candidate_user, db=session)
        assert v2.warning_count == 2
        assert v2.warning_tier == "WARNING_2"
        assert v2.counted is True
        assert "Warning 2/3" in v2.message

        # Violation 3 -> WARNING_3
        v3 = report_violation(ViolationReportRequest(kind="FULLSCREEN_EXIT"), current_user=candidate_user, db=session)
        assert v3.warning_count == 3
        assert v3.warning_tier == "WARNING_3"
        assert v3.counted is True
        assert "Warning 3/3" in v3.message

        # Violation 4 -> FINAL_WARNING
        v4 = report_violation(ViolationReportRequest(kind="NO_FACE"), current_user=candidate_user, db=session)
        assert v4.warning_count == 4
        assert v4.warning_tier == "FINAL_WARNING"
        assert v4.counted is True
        assert "This is your final warning" in v4.message

        # Violation 5 -> POST_FINAL_NOTED (Non-terminating: test continues, candidate is NOT kicked out!)
        v5 = report_violation(ViolationReportRequest(kind="LOOKING_AWAY"), current_user=candidate_user, db=session)
        assert v5.warning_count == 5
        assert v5.warning_tier == "POST_FINAL_NOTED"
        assert v5.counted is True
        assert "Activity noted" in v5.message

        # Verify Attempt in DB has not been terminated
        att = session.query(Attempt).filter_by(id=candidate_user.attempt_id).first()
        assert att.status == "IN_PROGRESS"
        assert att.warning_count == 5
        assert att.violation_count == 5
    finally:
        session.close()


def test_uncounted_violation_kinds(candidate_user):
    session = SessionLocal()
    try:
        # Initial warning count check
        att = session.query(Attempt).filter_by(id=candidate_user.attempt_id).first()
        init_warn_count = att.warning_count

        # NETWORK_OFFLINE should be logged but NOT counted
        res = report_violation(ViolationReportRequest(kind="NETWORK_OFFLINE"), current_user=candidate_user, db=session)
        assert res.counted is False
        assert res.warning_tier == "UNCOUNTED"

        # Warning count should remain unchanged
        session.refresh(att)
        assert att.warning_count == init_warn_count
    finally:
        session.close()


def test_snapshot_storage_and_rate_limiting(candidate_user):
    session = SessionLocal()
    try:
        # Create a valid 320px JPEG header simulation (\xff\xd8\xff...)
        valid_jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb" + b"\x00" * 200
        valid_b64 = "data:image/jpeg;base64," + base64.b64encode(valid_jpeg_bytes).decode("ascii")

        # Snapshot 1: Should be saved successfully
        res1 = report_violation(ViolationReportRequest(
            kind="COPY_PASTE",
            snapshot=valid_b64
        ), current_user=candidate_user, db=session)

        snap1 = session.query(Snapshot).filter_by(violation_id=res1.violation_id).first()
        assert snap1 is not None
        assert snap1.jpeg.startswith(b"\xff\xd8\xff")

        # Snapshot 2: Immediate report within 10 seconds -> should be rate-limited (violation recorded, snapshot skipped)
        res2 = report_violation(ViolationReportRequest(
            kind="DEV_TOOLS_KEY",
            snapshot=valid_b64
        ), current_user=candidate_user, db=session)

        snap2 = session.query(Snapshot).filter_by(violation_id=res2.violation_id).first()
        assert snap2 is None  # Rate-limited
    finally:
        session.close()


def test_heartbeat_tracking(candidate_user):
    session = SessionLocal()
    try:
        hb_res = heartbeat(HeartbeatRequest(
            timestamp=time.time(),
            fullscreen_active=True,
            camera_active=True
        ), current_user=candidate_user, db=session)

        assert hb_res.status == "ok"
        assert hb_res.remaining_seconds > 0
    finally:
        session.close()


def test_violations_query(candidate_user):
    session = SessionLocal()
    try:
        # Report a violation first
        report_violation(ViolationReportRequest(kind="TAB_SWITCH"), current_user=candidate_user, db=session)
        violation_list = list_violations(current_user=candidate_user, db=session)
        assert len(violation_list) > 0
        assert all(v["review_status"] == "PENDING" for v in violation_list)
    finally:
        session.close()
