from backend.app.core.config import settings
from backend.app.services.shuffle_service import generate_attempt_shuffle
from backend.app.services.sheets_service import queue_or_write_sheet
from backend.app.models.models import Restart, Question, Option, Answer
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.deps import require_role
from backend.app.schemas.auth import SessionUser
from backend.app.schemas.proctor import (
    ViolationReportRequest, ViolationReportResponse,
    HeartbeatRequest, HeartbeatResponse
)
from backend.app.models.models import Attempt, Violation, Snapshot, Event
from backend.app.core.signaling import signaling_manager

router = APIRouter(prefix="/candidate", tags=["Proctoring Engine"])

# Uncounted violation kinds (informational / logged only)
UNCOUNTED_KINDS = {"NETWORK_OFFLINE", "HEARTBEAT_RECONNECTED", "WINDOW_BLUR_BRIEF"}

# In-memory heartbeat tracker: {attempt_id: last_heartbeat_timestamp}
_last_heartbeats: Dict[int, float] = {}

# In-memory snapshot rate-limiting tracker: {attempt_id: last_snapshot_timestamp}
_last_snapshot_times: Dict[int, float] = {}

MAX_SNAPSHOTS_PER_ATTEMPT = 60
MIN_SNAPSHOT_INTERVAL_SECONDS = 10.0


@router.post("/violation", response_model=ViolationReportResponse)
def report_violation(
    req: ViolationReportRequest,
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot record violation: assessment is already {attempt.status}."
        )

    now = datetime.now(timezone.utc)
    kind_upper = req.kind.upper()
    is_counted = kind_upper not in UNCOUNTED_KINDS

    attempt.violation_count += 1
    warn_num = None
    tier = "UNCOUNTED"
    action = "WARNING"

    # Increment specific violation totals
    if kind_upper in ("TAB_SWITCH", "FULLSCREEN_EXIT", "WINDOW_BLUR"):
        attempt.tab_switch_total += 1
    elif kind_upper in ("NO_FACE", "FACE_MISSING", "MULTIPLE_FACES", "FACE_MISMATCH", "LOOKING_AWAY", "CAMERA_OFF"):
        attempt.face_violation_total += 1

    if is_counted:
        if attempt.warning_count < 5:
            attempt.warning_count += 1
            warn_num = attempt.warning_count
            action = "WARNING"
            if warn_num == 1:
                tier = "WARNING_1"
            elif warn_num == 2:
                tier = "WARNING_2"
            elif warn_num == 3:
                tier = "WARNING_3"
            elif warn_num == 4:
                tier = "FINAL_WARNING"
            else:
                tier = "POST_FINAL_NOTED"
        else:
            # 6th counted violation: Trigger RESTART
            action = "RESTART"
            tier = "RESTART"
            warn_num = 6
            attempt.restart_count += 1
            attempt.warning_count = 0  # reset current run counter

            # 1. Reset timer to fresh 60 minutes
            attempt.started_at = now
            attempt.deadline_at = now + timedelta(minutes=settings.EXAM_DURATION_MINUTES)

            # 2. Preserve candidate saved answers (Never delete candidate work)
            # Answers are safely retained in DB mapped to question_id to prevent candidate data loss

            # 3. Reshuffle questions and options to a brand new order
            questions = db.query(Question).filter_by(assessment_id=attempt.assessment_id).all()
            options_by_q = {q.id: db.query(Option).filter_by(question_id=q.id).all() for q in questions}
            new_q_ids, new_opt_order = generate_attempt_shuffle(questions, options_by_q)
            attempt.question_order = new_q_ids
            attempt.option_order = new_opt_order

            # 4. Record Restart
            restart_record = Restart(
                attempt_id=attempt.id,
                candidate_id=attempt.employee_code,
                reason=f"Exceeded 5 violations: {kind_upper}",
                restart_number=attempt.restart_count,
                at=now
            )
            db.add(restart_record)

            # 5. Queue Sheet writes
            queue_or_write_sheet(
                db=db,
                operation="append_restart",
                idempotency_key=f"restart_{attempt.id}_{attempt.restart_count}",
                payload={"row": [now.isoformat(), attempt.id, attempt.employee_code, restart_record.reason, attempt.restart_count]},
                attempt_id=attempt.id
            )

    # Create violation row
    violation = Violation(
        attempt_id=attempt.id,
        at=now,
        kind=kind_upper,
        detail=req.detail or {},
        counted=is_counted,
        warning_number=warn_num,
        action=action,
        review_status="PENDING"
    )
    db.add(violation)
    db.flush()

    # Process and rate-limit snapshot storage (max 1 per 10s, max 60 total)
    if req.snapshot:
        now_ts = time.time()
        last_snap_ts = _last_snapshot_times.get(attempt.id, 0.0)

        # Check budget limits
        if (now_ts - last_snap_ts >= MIN_SNAPSHOT_INTERVAL_SECONDS):
            total_snapshots = db.query(Snapshot).filter_by(attempt_id=attempt.id).count()
            if total_snapshots < MAX_SNAPSHOTS_PER_ATTEMPT:
                try:
                    # Strip data URL prefix if present
                    raw_b64 = req.snapshot
                    if "," in raw_b64:
                        raw_b64 = raw_b64.split(",", 1)[1]
                    
                    jpeg_bytes = base64.b64decode(raw_b64)

                    # Validate JPEG magic bytes (\xff\xd8\xff) and max size (100KB)
                    if len(jpeg_bytes) <= 100 * 1024 and jpeg_bytes.startswith(b"\xff\xd8\xff"):
                        snapshot_entry = Snapshot(
                            violation_id=violation.id,
                            attempt_id=attempt.id,
                            jpeg=jpeg_bytes,
                            taken_at=now
                        )
                        db.add(snapshot_entry)
                        _last_snapshot_times[attempt.id] = now_ts
                except Exception:
                    # Ignore corrupted client snapshot without failing violation record
                    pass

    db.commit()

    # Sync violation to Google Sheet
    queue_or_write_sheet(
        db=db,
        operation="append_violation",
        idempotency_key=f"violation_{attempt.id}_{violation.id}",
        payload={"row": [now.isoformat(), attempt.id, attempt.employee_code, violation.kind, warn_num or "", action]},
        attempt_id=attempt.id
    )

    # Real-time alert push to active monitors
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(signaling_manager.broadcast_to_monitors({
            "type": "violation_alert",
            "violation_id": violation.id,
            "attempt_id": attempt.id,
            "employee_code": attempt.employee_code,
            "full_name": attempt.entered_name,
            "kind": violation.kind,
            "warning_count": attempt.warning_count,
            "warning_tier": tier,
            "at": now.isoformat(),
            "has_snapshot": bool(req.snapshot)
        }))
    except (RuntimeError, Exception):
        pass

    message = ""
    if action == "RESTART":
        message = "You have exceeded the maximum allowed violations (5). Your test has been restarted with a fresh timer. Your saved answers remain safely preserved."
    elif tier in ("WARNING_1", "WARNING_2", "WARNING_3"):
        remaining = 3 - warn_num
        message = f"Warning {warn_num}/3: Security incident detected ({req.kind}). You have {remaining} warning(s) remaining."
    elif tier == "FINAL_WARNING":
        message = "You have used all 3 warnings. This is your final warning. Your activity is being monitored and reviewed. You may continue the test."
    elif tier == "POST_FINAL_NOTED":
        message = f"Activity noted: {req.kind} logged for proctor review."
    else:
        message = f"Event logged: {req.kind}"

    return ViolationReportResponse(
        violation_id=violation.id,
        warning_count=attempt.warning_count,
        warning_tier=tier,
        counted=is_counted,
        message=message,
        server_time=now,
        action=action,
        restart_count=attempt.restart_count
    )


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    req: HeartbeatRequest,
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    now = datetime.now(timezone.utc)
    _last_heartbeats[attempt.id] = time.time()

    deadline = attempt.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    remaining = max(0, int((deadline - now).total_seconds())) if attempt.status == "IN_PROGRESS" else 0

    return HeartbeatResponse(
        status="ok",
        warning_count=attempt.warning_count,
        remaining_seconds=remaining,
        server_time=now
    )


@router.get("/violations")
def list_violations(
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    violations = db.query(Violation).filter_by(attempt_id=current_user.attempt_id).order_by(Violation.at.desc()).all()
    return [
        {
            "id": v.id,
            "at": v.at,
            "kind": v.kind,
            "counted": v.counted,
            "warning_number": v.warning_number,
            "review_status": v.review_status,
            "detail": v.detail
        }
        for v in violations
    ]
