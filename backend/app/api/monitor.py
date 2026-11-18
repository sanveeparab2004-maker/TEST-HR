import base64
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.database import get_db, SessionLocal
from backend.app.core.security import decode_access_token
from backend.app.core.signaling import signaling_manager
from backend.app.api.deps import require_role
from backend.app.schemas.auth import SessionUser
from backend.app.models.models import Attempt, Roster, Violation, Snapshot, Answer, Assessment, AuditLog

router = APIRouter(tags=["Monitor Proctoring Station"])


class MonitorCandidateTile(BaseModel):
    attempt_id: int
    employee_code: str
    full_name: str
    status: str
    started_at: datetime
    deadline_at: datetime
    remaining_seconds: int
    answered_count: int
    total_questions: int
    warning_count: int
    violation_count: int
    status_ring: str  # green, amber, red, grey
    is_online: bool
    last_violation_at: Optional[datetime] = None


class ReviewViolationRequest(BaseModel):
    review_status: str = Field(..., description="'CONFIRMED' or 'DISMISSED'")


class SendProctorMessageRequest(BaseModel):
    attempt_id: Optional[int] = Field(None, description="Target attempt id, or None for all active candidates")
    message: str = Field(..., min_length=1, max_length=500)


@router.get("/api/monitor/candidates", response_model=List[MonitorCandidateTile])
def get_monitored_candidates(
    current_user: SessionUser = Depends(require_role("MONITOR", "ADMIN")),
    db: Session = Depends(get_db)
):
    """Returns candidate list for live monitoring wall. Notice: Scores and answers are strictly omitted."""
    assessment = db.query(Assessment).filter_by(status="OPEN").first()
    if not assessment:
        assessment = db.query(Assessment).order_by(Assessment.id.desc()).first()
    if not assessment:
        return []

    attempts = db.query(Attempt).filter_by(assessment_id=assessment.id).all()
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(minutes=3)

    tiles = []
    for att in attempts:
        deadline = att.deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        remaining = max(0, int((deadline - now).total_seconds())) if att.status == "IN_PROGRESS" else 0

        # Answered count (only count non-null options)
        ans_count = db.query(Answer).filter(Answer.attempt_id == att.id, Answer.option_id.isnot(None)).count()

        # Last violation
        last_viol = db.query(Violation).filter_by(attempt_id=att.id).order_by(Violation.at.desc()).first()

        # Online check
        is_online = att.id in signaling_manager.candidates

        # Compute status ring color
        if att.status != "IN_PROGRESS":
            ring = "grey"
        elif att.warning_count >= 4 or not is_online:
            ring = "red"
        elif last_viol and last_viol.at.replace(tzinfo=timezone.utc) >= recent_cutoff:
            ring = "amber"
        else:
            ring = "green"

        tiles.append(MonitorCandidateTile(
            attempt_id=att.id,
            employee_code=att.employee_code,
            full_name=att.entered_name,
            status=att.status,
            started_at=att.started_at,
            deadline_at=att.deadline_at,
            remaining_seconds=remaining,
            answered_count=ans_count,
            total_questions=50,
            warning_count=att.warning_count,
            violation_count=att.violation_count,
            status_ring=ring,
            is_online=is_online,
            last_violation_at=last_viol.at if last_viol else None
        ))

    return tiles


@router.get("/api/monitor/candidate/{attempt_id}/timeline")
def get_candidate_timeline(
    attempt_id: int,
    current_user: SessionUser = Depends(require_role("MONITOR", "ADMIN")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    violations = db.query(Violation).filter_by(attempt_id=attempt_id).order_by(Violation.at.desc()).all()

    timeline = []
    for v in violations:
        snap = db.query(Snapshot).filter_by(violation_id=v.id).first()
        snap_b64 = None
        if snap and snap.jpeg:
            snap_b64 = "data:image/jpeg;base64," + base64.b64encode(snap.jpeg).decode("ascii")

        timeline.append({
            "id": v.id,
            "at": v.at,
            "kind": v.kind,
            "counted": v.counted,
            "warning_number": v.warning_number,
            "review_status": v.review_status,
            "reviewed_by": v.reviewed_by,
            "reviewed_at": v.reviewed_at,
            "detail": v.detail,
            "snapshot": snap_b64
        })

    return {
        "attempt_id": attempt.id,
        "employee_code": attempt.employee_code,
        "full_name": attempt.entered_name,
        "warning_count": attempt.warning_count,
        "violation_count": attempt.violation_count,
        "timeline": timeline
    }


@router.post("/api/monitor/violation/{violation_id}/review")
def review_violation(
    violation_id: int,
    req: ReviewViolationRequest,
    current_user: SessionUser = Depends(require_role("MONITOR", "ADMIN")),
    db: Session = Depends(get_db)
):
    if req.review_status not in ("CONFIRMED", "DISMISSED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be CONFIRMED or DISMISSED")

    violation = db.query(Violation).filter_by(id=violation_id).first()
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation record not found")

    now = datetime.now(timezone.utc)
    violation.review_status = req.review_status
    violation.reviewed_by = current_user.employee_code
    violation.reviewed_at = now

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="REVIEW_VIOLATION",
        entity="violation",
        detail={
            "violation_id": violation.id,
            "new_status": req.review_status,
            "attempt_id": violation.attempt_id
        }
    ))
    db.commit()

    return {
        "status": "success",
        "violation_id": violation.id,
        "review_status": violation.review_status,
        "reviewed_by": violation.reviewed_by,
        "reviewed_at": violation.reviewed_at
    }


@router.post("/api/monitor/message")
def send_proctor_message(
    req: SendProctorMessageRequest,
    current_user: SessionUser = Depends(require_role("MONITOR", "ADMIN")),
    db: Session = Depends(get_db)
):
    msg_payload = {
        "type": "proctor_message",
        "sender": current_user.full_name or current_user.employee_code,
        "message": req.message,
        "at": datetime.now(timezone.utc).isoformat()
    }

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        if req.attempt_id:
            loop.create_task(signaling_manager.send_to_candidate(req.attempt_id, msg_payload))
        else:
            for att_id in list(signaling_manager.candidates.keys()):
                loop.create_task(signaling_manager.send_to_candidate(att_id, msg_payload))
    except (RuntimeError, Exception):
        pass

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="SEND_PROCTOR_MESSAGE",
        entity="message",
        detail={"target_attempt_id": req.attempt_id, "message": req.message}
    ))
    db.commit()

    return {"status": "sent", "message": req.message}


# WebSocket Signalling & Fallback Snapshot Endpoint
@router.websocket("/ws/signaling")
async def websocket_signaling(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    if not token:
        # Check cookies
        token = websocket.cookies.get("access_token")

    if not token:
        await websocket.close(code=1008)
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    emp_code = payload.get("sub")
    role = payload.get("role")
    attempt_id = payload.get("attempt_id")

    if role in ("MONITOR", "ADMIN"):
        await signaling_manager.connect_monitor(websocket, emp_code)
    elif role == "CANDIDATE" and attempt_id:
        await signaling_manager.connect_candidate(websocket, attempt_id, emp_code)
    else:
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await signaling_manager.relay_webrtc(websocket, msg)
            except Exception:
                pass
    except WebSocketDisconnect:
        signaling_manager.disconnect(websocket)
    except Exception:
        signaling_manager.disconnect(websocket)
