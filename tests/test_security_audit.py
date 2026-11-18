import os
import glob
import json
import pytest
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Assessment, Attempt, Question, Option
from datetime import datetime, timezone, timedelta
from backend.app.schemas.auth import SessionUser
from backend.app.schemas.candidate import ConsentRequest
from backend.app.api.candidate import get_exam, get_status, give_consent
from backend.app.api.monitor import get_monitored_candidates, get_candidate_timeline


def test_candidate_api_zero_answer_leakage():
    """Verify that Candidate endpoints NEVER return is_correct or answer indicators."""
    session = SessionLocal()
    created_temp = False
    att = None
    try:
        att = session.query(Attempt).filter_by(status="IN_PROGRESS").first()
        if not att:
            att = session.query(Attempt).first()
        if not att:
            asmt = session.query(Assessment).first()
            questions = session.query(Question).filter_by(assessment_id=asmt.id).order_by(Question.id).all()
            att = Attempt(
                assessment_id=asmt.id,
                employee_code="C-2606026",
                entered_name="Durvesh Parab",
                device_token_hash="audit_test_hash",
                status="IN_PROGRESS",
                started_at=datetime.now(timezone.utc),
                deadline_at=datetime.now(timezone.utc) + timedelta(minutes=60),
                question_order=[q.id for q in questions],
                option_order={}
            )
            session.add(att)
            session.commit()
            created_temp = True

        candidate_user = SessionUser(
            employee_code=att.employee_code,
            full_name=att.entered_name,
            role="CANDIDATE",
            attempt_id=att.id
        )
        exam_data = get_exam(current_user=candidate_user, db=session)
        assert len(exam_data.questions) == 50

        # Thoroughly inspect every question and option in candidate response
        for q in exam_data.questions:
            q_dict = q.model_dump()
            assert "is_correct" not in q_dict
            assert "correct_option_id" not in q_dict
            assert "key" not in q_dict
            for opt in q.options:
                opt_dict = opt.model_dump()
                assert "is_correct" not in opt_dict
                assert "correct" not in opt_dict
    finally:
        if created_temp and att:
            session.delete(att)
            session.commit()
        session.close()


def test_monitor_api_zero_score_or_answer_leakage():
    """Verify that Monitor endpoints NEVER return scores, percentages, or answer keys during exam."""
    session = SessionLocal()
    try:
        monitor_user = SessionUser(
            employee_code="HR_MONITOR_01",
            full_name="Chief Exam Proctor",
            role="MONITOR"
        )
        tiles = get_monitored_candidates(current_user=monitor_user, db=session)
        assert isinstance(tiles, list)

        for tile in tiles:
            tile_dump = tile.model_dump()
            # Must not show score, marks, or answers
            assert "score" not in tile_dump
            assert "marks" not in tile_dump
            assert "percentage" not in tile_dump
            assert "is_correct" not in tile_dump
            assert "answers" not in tile_dump

        # Check candidate timeline
        attempt = session.query(Attempt).first()
        if attempt:
            timeline = get_candidate_timeline(attempt_id=attempt.id, current_user=monitor_user, db=session)
            timeline_dump = timeline if isinstance(timeline, dict) else timeline.model_dump()
            assert "score" not in timeline_dump
            assert "percentage" not in timeline_dump
            assert "answers" not in timeline_dump
    finally:
        session.close()


def test_frontend_bundle_zero_answer_leakage():
    """
    Scans compiled frontend JavaScript assets in frontend/dist/assets/
    to guarantee that the answer key checksum string and answer mapping
    are NOT bundled into client-side code.
    """
    js_files = glob.glob("frontend/dist/assets/*.js")
    assert len(js_files) > 0, "Frontend bundle not found. Run npm run build first."

    # Answer key checksum sequence from master prompt
    forbidden_pattern_1 = "1A 2C 3B 4B 5C 6D 7C 8D 9B 10B 11B 12B 13A 14A 15B 16C 17C 18D 19A 20D"
    forbidden_pattern_2 = "21A 22C 23C 24A 25A 26A 27D 28A 29A 30A 31A 32A 33C 34A 35B 36A 37D 38B 39B 40C"

    for js_path in js_files:
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert forbidden_pattern_1 not in content, f"Leaked answer pattern 1 in {js_path}"
        assert forbidden_pattern_2 not in content, f"Leaked answer pattern 2 in {js_path}"
        assert "ANSWER_KEY_CHECKSUM" not in content, f"Leaked checksum constant in {js_path}"
