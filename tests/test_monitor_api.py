import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Assessment, Attempt, Violation, Snapshot, Answer
from backend.app.schemas.auth import SessionUser, LoginRequest
from backend.app.api.auth import login
from backend.app.api.monitor import (
    get_monitored_candidates, get_candidate_timeline, review_violation,
    send_proctor_message, ReviewViolationRequest, SendProctorMessageRequest
)


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
def monitor_setup():
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

    monitor_user = SessionUser(
        employee_code="HR_MONITOR_01",
        full_name="Chief Exam Proctor",
        role="MONITOR"
    )

    candidate_user = SessionUser(
        employee_code="EMP001",
        full_name="Aarav Sharma",
        role="CANDIDATE",
        attempt_id=1
    )

    session.close()
    return monitor_user, candidate_user


def test_monitor_candidates_security_and_exclusion_of_answers(monitor_setup):
    monitor_user, candidate_user = monitor_setup
    session = SessionLocal()
    try:
        # Monitor calling get_monitored_candidates succeeds
        tiles = get_monitored_candidates(current_user=monitor_user, db=session)
        assert isinstance(tiles, list)

        # SECURITY SCAN: Verify answer key and scores NEVER appear in monitor candidate tiles
        for t in tiles:
            tile_dict = t.model_dump()
            assert "score" not in tile_dict
            assert "percentage" not in tile_dict
            assert "answers" not in tile_dict
            assert "is_correct" not in tile_dict
            assert t.total_questions == 50
            assert t.status_ring in ("green", "amber", "red", "grey")
    finally:
        session.close()


def test_candidate_cannot_access_monitor_routes(monitor_setup):
    monitor_user, candidate_user = monitor_setup
    session = SessionLocal()
    try:
        from backend.app.api.deps import require_role
        role_checker = require_role("MONITOR", "ADMIN")

        # Candidate user attempting to access monitor endpoint is refused with 403
        with pytest.raises(HTTPException) as exc_info:
            role_checker(current_user=candidate_user)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
    finally:
        session.close()


def test_monitor_review_violation(monitor_setup):
    monitor_user, candidate_user = monitor_setup
    session = SessionLocal()
    try:
        # Create a test violation
        att = session.query(Attempt).first()
        if not att:
            pytest.skip("No attempt in DB")

        viol = Violation(
            attempt_id=att.id,
            at=datetime.now(timezone.utc),
            kind="TAB_SWITCH",
            counted=True,
            warning_number=1,
            review_status="PENDING"
        )
        session.add(viol)
        session.commit()

        # Monitor marks as DISMISSED
        res = review_violation(
            violation_id=viol.id,
            req=ReviewViolationRequest(review_status="DISMISSED"),
            current_user=monitor_user,
            db=session
        )

        assert res["review_status"] == "DISMISSED"
        assert res["reviewed_by"] == "HR_MONITOR_01"

        # Verify in DB
        session.refresh(viol)
        assert viol.review_status == "DISMISSED"
    finally:
        session.close()


def test_monitor_send_message(monitor_setup):
    monitor_user, candidate_user = monitor_setup
    session = SessionLocal()
    try:
        res = send_proctor_message(
            req=SendProctorMessageRequest(attempt_id=None, message="Test announcement"),
            current_user=monitor_user,
            db=session
        )
        assert res["status"] == "sent"
        assert res["message"] == "Test announcement"
    finally:
        session.close()
