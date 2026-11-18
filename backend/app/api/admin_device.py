from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.deps import require_role
from backend.app.schemas.auth import SessionUser
from backend.app.models.models import Attempt, AuditLog

router = APIRouter(prefix="/admin", tags=["Admin Controls"])


class ReleaseDeviceLockRequest(BaseModel):
    employee_code: str
    reason: str


@router.post("/release-device-lock")
def release_device_lock(
    req: ReleaseDeviceLockRequest,
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    code = req.employee_code.strip().upper()
    attempt = db.query(Attempt).filter_by(employee_code=code, status="IN_PROGRESS").first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active in-progress assessment found for employee code {code}."
        )

    # Reset device token hash so next login generates a fresh device token
    attempt.device_token_hash = "RELEASED_BY_ADMIN"
    
    db.add(AuditLog(
        actor=current_user.employee_code,
        action="RELEASE_DEVICE_LOCK",
        entity="attempt",
        detail={"employee_code": code, "attempt_id": attempt.id, "reason": req.reason}
    ))
    db.commit()

    return {
        "status": "success",
        "message": f"Device lock for {code} has been released. The candidate can now log in from their new device."
    }
