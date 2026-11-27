import json
from backend.app.services.shuffle_service import generate_attempt_shuffle
from backend.app.services.sheets_service import queue_or_write_sheet
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (
    verify_pin, hash_device_token, generate_device_token, create_access_token
)
from backend.app.models.models import Roster, Assessment, Attempt, Option, Question, AuditLog, Event
from backend.app.schemas.auth import LookupRequest, LookupResponse, LoginRequest, LoginResponse
from backend.app.api.deps import check_rate_limit, record_failed_attempt, reset_failed_attempts

router = APIRouter(prefix="/auth", tags=["Authentication"])

GENERIC_AUTH_ERROR = "Details not found. Contact HR."


@router.post("/lookup", response_model=LookupResponse)
def lookup_employee(req: LookupRequest, db: Session = Depends(get_db)):
    """Check if the provided employee code requires a PIN (MONITOR or ADMIN)."""
    code = req.employee_code.strip().upper()
    entry = db.query(Roster).filter_by(employee_code=code, is_active=True).first()
    if entry and entry.role in ("MONITOR", "ADMIN"):
        return LookupResponse(requires_pin=True)
    return LookupResponse(requires_pin=False)


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    rate_key = f"{ip}:{req.employee_code.strip().upper()}"

    if not check_rate_limit(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait a few minutes before retrying."
        )

    code = req.employee_code.strip().upper()
    entered_name = req.full_name.strip()
    target_dept = (req.department or "HR").strip().upper()

    # Look up candidate in roster
    entry = db.query(Roster).filter_by(employee_code=code, is_active=True).first()
    if not entry:
        record_failed_attempt(rate_key)
        if target_dept in ("ASSESSMENT", "ASHTAPRADHAN"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Employee Code {code} is not registered in the official exam roster. Contact HR."
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)

    # Department validation: If candidate selected Ashtapradhan Assessment, enforce authorized roster
    if target_dept in ("ASSESSMENT", "ASHTAPRADHAN"):
        if entry.role not in ("ADMIN", "MONITOR"):
            cand_dept = (entry.department or "").upper()
            if "ASSESSMENT" not in cand_dept and "ASHTAPRADHAN" not in cand_dept:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{entry.full_name} ({code}) is not enrolled for the अष्टप्रधान – संचालक कार्यालय Assessment. Only authorized candidates on the official list can take this exam."
                )

    # Name validation with flexible whitespace & token matching
    def clean_name(s: str) -> str:
        return " ".join(s.strip().lower().split())

    entered_clean = clean_name(entered_name)
    roster_clean = clean_name(entry.full_name)

    names_match = False
    if entered_clean == roster_clean:
        names_match = True
    else:
        e_tokens = set(entered_clean.split())
        r_tokens = set(roster_clean.split())
        # Match if candidate entered first + last name (e.g. 'Nitin Shinde' matching 'Nitin Appaso Shinde')
        if len(e_tokens) >= 2 and len(r_tokens) >= 2 and (e_tokens.issubset(r_tokens) or r_tokens.issubset(e_tokens)):
            names_match = True

    if not names_match:
        record_failed_attempt(rate_key)
        if target_dept in ("ASSESSMENT", "ASHTAPRADHAN"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Name entered does not match the official roster record for {code}. Please enter your registered name ({entry.full_name})."
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)

    # Role validation and PIN check for MONITOR/ADMIN
    if entry.role in ("MONITOR", "ADMIN"):
        if not req.pin or not verify_pin(req.pin.strip(), entry.pin_hash or ""):
            record_failed_attempt(rate_key)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)

        reset_failed_attempts(rate_key)
        
        # Log successful staff login
        db.add(AuditLog(
            actor=code,
            action=f"{entry.role}_LOGIN",
            entity="session",
            detail={"ip": ip, "role": entry.role}
        ))
        db.commit()

        token = create_access_token({
            "sub": code,
            "role": entry.role,
            "full_name": entry.full_name
        })

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=(settings.ENVIRONMENT == "production"),
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return LoginResponse(
            access_token=token,
            role=entry.role,
            employee_code=code,
            full_name=entry.full_name,
            device_token=None,
            attempt_id=None
        )

    # --- CANDIDATE FLOW ---
    reset_failed_attempts(rate_key)

    # Department-aware assessment matching (HR, CLAIM, TENDER, ADMIN)
    target_dept = (req.department or "HR").strip().upper()
    
    # Department validation check against roster
    cand_dept = (entry.department or "").upper()
    if target_dept in ("CLAIM", "TENDER", "ADMIN") and "HR" in cand_dept and target_dept not in cand_dept:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{entry.full_name} ({code}) is enrolled under the HR Department. Please select the HR section to take your assessment."
        )

    # Find matching assessment
    assessment = None
    all_assessments = db.query(Assessment).all()
    for a in all_assessments:
        dept_setting = (a.settings or {}).get("department", "").upper()
        short_setting = (a.settings or {}).get("short_code", "").upper()
        if target_dept in ("ASSESSMENT", "ASHTAPRADHAN"):
            if dept_setting in ("ASSESSMENT", "ASHTAPRADHAN") or short_setting in ("ASSESSMENT", "ASHTAPRADHAN") or "अष्टप्रधान" in a.title or "ASHTAPRADHAN" in a.title.upper():
                assessment = a
                break
        else:
            if dept_setting == target_dept or short_setting == target_dept or target_dept in a.title.upper():
                assessment = a
                break

    if not assessment:
        assessment = db.query(Assessment).filter_by(status="OPEN").first()

    if not assessment:
        assessment = db.query(Assessment).order_by(Assessment.id.desc()).first()

    if not assessment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active assessment found. Contact HR.")

    # Check if the assessment questionnaire has been loaded
    q_count = db.query(Question).filter_by(assessment_id=assessment.id).count()
    if assessment.status != "OPEN" and q_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The {target_dept} department assessment questionnaire is currently being finalized. Roster and questions will be active shortly."
        )

    now = datetime.now(timezone.utc)
    # Single attempt enforcement on server across assessments
    existing_attempt = db.query(Attempt).filter_by(employee_code=code).first()
    if existing_attempt and existing_attempt.status in ("SUBMITTED", "AUTO_SUBMITTED", "VOID"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have already attempted this test."
        )

    attempt = db.query(Attempt).filter_by(assessment_id=assessment.id, employee_code=code).first()

    device_token_to_return = None

    if attempt:
        # Check if already submitted
        if attempt.status in ("SUBMITTED", "AUTO_SUBMITTED", "VOID"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your assessment has already been submitted."
            )

        # Single-device check: compare hashed device token
        if attempt.device_token_hash == "RELEASED_BY_ADMIN":
            # Admin released device lock: issue new device token to this new machine
            raw_device_token = generate_device_token()
            attempt.device_token_hash = hash_device_token(raw_device_token)
            attempt.ip = ip
            if req.device_info:
                attempt.device_info = req.device_info
            device_token_to_return = raw_device_token
            db.add(AuditLog(
                actor=code,
                action="RESUME_ON_NEW_DEVICE",
                entity="attempt",
                detail={"attempt_id": attempt.id, "ip": ip}
            ))
            db.commit()
        elif req.device_token and hash_device_token(req.device_token) != attempt.device_token_hash:
            # Another distinct device token explicitly provided -> reject to enforce single device
            db.add(Event(
                attempt_id=attempt.id,
                kind="DEVICE_LOCK_REJECTION",
                detail={"ip": ip, "device_info": req.device_info}
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This employee code is already active on another device."
            )
        elif not req.device_token:
            # Reconnect resilience if token missing (e.g. browser cleared cache/reopened): re-issue and resume
            raw_device_token = generate_device_token()
            attempt.device_token_hash = hash_device_token(raw_device_token)
            attempt.ip = ip
            if req.device_info:
                attempt.device_info = req.device_info
            device_token_to_return = raw_device_token
            db.add(AuditLog(
                actor=code,
                action="RECONNECT_RESUME",
                entity="attempt",
                detail={"attempt_id": attempt.id, "ip": ip}
            ))
            db.commit()
        else:
            # Resuming on same device with valid token
            device_token_to_return = req.device_token
            attempt.ip = ip
            if req.device_info:
                attempt.device_info = req.device_info
            db.commit()
    else:
        # First-time login: create attempt and issue device token
        raw_device_token = generate_device_token()
        device_token_hash = hash_device_token(raw_device_token)
        device_token_to_return = raw_device_token

        # Cryptographically secure per-attempt Fisher-Yates shuffle
        questions = db.query(Question).filter_by(assessment_id=assessment.id).all()
        options_by_q = {q.id: db.query(Option).filter_by(question_id=q.id).order_by(Option.label).all() for q in questions}
        ordered_q_ids, option_order = generate_attempt_shuffle(questions, options_by_q)

        # Strict 60-minute duration backed by DB
        deadline_at = now + timedelta(minutes=assessment.duration_minutes)

        extra_info = dict(req.device_info or {})
        if req.current_department:
            extra_info["current_department"] = req.current_department
        if req.current_post:
            extra_info["current_post"] = req.current_post
        if req.mobile_number:
            extra_info["mobile_number"] = req.mobile_number
        if req.target_post:
            extra_info["target_post"] = req.target_post

        attempt = Attempt(
            assessment_id=assessment.id,
            employee_code=code,
            entered_name=entered_name,
            device_token_hash=device_token_hash,
            device_info=extra_info if extra_info else None,
            ip=ip,
            status="IN_PROGRESS",
            started_at=now,
            deadline_at=deadline_at,
            question_order=ordered_q_ids,
            option_order=option_order,
            warning_count=0,
            violation_count=0
        )
        db.add(attempt)
        db.add(AuditLog(
            actor=code,
            action="ATTEMPT_CREATED",
            entity="attempt",
            detail={"assessment_id": assessment.id, "deadline_at": deadline_at.isoformat()}
        ))
        db.commit()
        db.refresh(attempt)

        # Log attempt creation to Google Sheet Attempts tab (idempotent)
        sheet_attempt_row = [
            attempt.id,
            code,
            entry.full_name,
            entry.department or target_dept,
            target_dept,
            now.isoformat(),
            deadline_at.isoformat(),
            "in_progress",
            0,
            0,
            0,
            "",
            assessment.total_marks,
            json.dumps(ordered_q_ids),
            json.dumps(option_order)
        ]
        queue_or_write_sheet(
            db=db,
            operation="append_attempt",
            idempotency_key=f"attempt_{attempt.id}_init",
            payload={"row": sheet_attempt_row},
            attempt_id=attempt.id
        )

    token = create_access_token({
        "sub": code,
        "role": "CANDIDATE",
        "full_name": entry.full_name,
        "attempt_id": attempt.id,
        "device_token_hash": attempt.device_token_hash
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return LoginResponse(
        access_token=token,
        role="CANDIDATE",
        employee_code=code,
        full_name=entry.full_name,
        device_token=device_token_to_return,
        attempt_id=attempt.id
    )


@router.post("/logout")
def logout(response: Response, current_user = Depends(create_access_token)):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}
