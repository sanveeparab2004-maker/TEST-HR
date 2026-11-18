import io
import json
import asyncio
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Assessment, Attempt, Violation, Snapshot, Answer, Option, Question
from backend.app.schemas.auth import SessionUser
from backend.app.api.admin import (
    get_admin_dashboard, get_all_results, get_candidate_details,
    get_question_bank, purge_retention, export_excel, export_candidate_pdf,
    export_backup
)
from backend.app.api.admin_device import release_device_lock, ReleaseDeviceLockRequest
from backend.app.api.deps import require_role


@pytest.fixture(scope="module")
def admin_setup():
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

    admin_user = SessionUser(
        employee_code="HR_ADMIN_01",
        full_name="Principal HR Administrator",
        role="ADMIN"
    )

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
    return admin_user, monitor_user, candidate_user


async def read_streaming_response(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)


def test_admin_dashboard_metrics(admin_setup):
    admin_user, monitor_user, candidate_user = admin_setup
    session = SessionLocal()
    try:
        data = get_admin_dashboard(current_user=admin_user, db=session)
        assert "total_candidates" in data
        assert "submitted_count" in data
        assert "in_progress_count" in data
        assert "not_started_count" in data
        assert "band_distribution" in data
        assert "section_averages" in data

        # Check band keys
        for b in ["Excellent", "Good", "Needs Improvement", "Requires Training"]:
            assert b in data["band_distribution"]
    finally:
        session.close()


def test_candidate_and_monitor_forbidden_on_admin_routes(admin_setup):
    admin_user, monitor_user, candidate_user = admin_setup
    admin_checker = require_role("ADMIN")

    # Monitor user is denied with 403
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(current_user=monitor_user)
    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail

    # Candidate user is denied with 403
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(current_user=candidate_user)
    assert exc_info.value.status_code == 403


def test_admin_candidate_results_and_integrity(admin_setup):
    admin_user, _, _ = admin_setup
    session = SessionLocal()
    try:
        results = get_all_results(
            current_user=admin_user, db=session
        )
        assert isinstance(results, list)
        for r in results:
            assert "employee_code" in r
            assert "full_name" in r
            assert "band" in r
            assert "integrity_status" in r
            assert r["integrity_status"] in ("Clean", "Minor", "Review Needed")
    finally:
        session.close()


def test_admin_question_bank_shows_correct_answers(admin_setup):
    admin_user, _, _ = admin_setup
    session = SessionLocal()
    try:
        bank = get_question_bank(current_user=admin_user, db=session)
        assert len(bank) == 50
        # Each question should have options with is_correct visible to Admin
        for q in bank:
            assert len(q["options"]) == 4
            correct_opts = [o for o in q["options"] if o["is_correct"]]
            assert len(correct_opts) == 1
    finally:
        session.close()


def test_admin_device_lock_release(admin_setup):
    admin_user, _, candidate_user = admin_setup
    session = SessionLocal()
    try:
        attempt = session.query(Attempt).filter_by(employee_code=candidate_user.employee_code).first()
        if not attempt:
            pytest.skip("No attempt found")

        # Set fake device token hash
        attempt.device_token_hash = "some_old_token_hash"
        session.commit()

        # Admin releases lock
        req = ReleaseDeviceLockRequest(
            employee_code=candidate_user.employee_code,
            reason="Candidate laptop battery died, switched to spare office laptop"
        )
        res = release_device_lock(req=req, current_user=admin_user, db=session)
        assert res["status"] == "success"

        session.refresh(attempt)
        assert attempt.device_token_hash == "RELEASED_BY_ADMIN"
    finally:
        session.close()


def test_admin_export_excel(admin_setup):
    admin_user, _, _ = admin_setup
    session = SessionLocal()
    try:
        response = export_excel(current_user=admin_user, db=session)
        assert "application/vnd.openxmlformats" in response.media_type
        content = response.body
        assert content[:2] == b"PK"
    finally:
        session.close()


def test_admin_export_pdf(admin_setup):
    admin_user, _, candidate_user = admin_setup
    session = SessionLocal()
    try:
        attempt = session.query(Attempt).first()
        if not attempt:
            pytest.skip("No attempt found")

        response = export_candidate_pdf(attempt_id=attempt.id, current_user=admin_user, db=session)
        assert response.media_type == "application/pdf"
        content = response.body
        assert content.startswith(b"%PDF")
    finally:
        session.close()


def test_admin_export_backup_dump(admin_setup):
    admin_user, _, _ = admin_setup
    session = SessionLocal()
    try:
        response = export_backup(current_user=admin_user, db=session)
        assert response.media_type == "application/json"
        content = response.body
        parsed = json.loads(content.decode("utf-8"))
        assert "export_timestamp" in parsed
        assert "total_attempts" in parsed
        assert "attempts" in parsed
    finally:
        session.close()


def test_admin_purge_retention(admin_setup):
    admin_user, _, _ = admin_setup
    session = SessionLocal()
    try:
        res = purge_retention(days=90, current_user=admin_user, db=session)
        assert res["status"] == "success"
        assert res["retention_days"] == 90
        assert "deleted_snapshots" in res
        assert "deleted_violations" in res
    finally:
        session.close()
