import time
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.models import Roster, Attempt
from backend.app.schemas.auth import SessionUser

security_bearer = HTTPBearer(auto_error=False)

# In-memory rate limiting for failed login attempts
# Format: {ip_or_code: [timestamps]}
_failed_attempts: Dict[str, list] = {}
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_FAILED_ATTEMPTS = 5


def check_rate_limit(key: str) -> bool:
    """Returns True if within allowed limit, False if rate limited."""
    now = time.time()
    attempts = _failed_attempts.get(key, [])
    # Filter attempts within window
    recent = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    _failed_attempts[key] = recent
    return len(recent) < MAX_FAILED_ATTEMPTS


def record_failed_attempt(key: str):
    now = time.time()
    attempts = _failed_attempts.get(key, [])
    attempts.append(now)
    _failed_attempts[key] = attempts


def reset_failed_attempts(key: str):
    if key in _failed_attempts:
        del _failed_attempts[key]


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> SessionUser:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Check HttpOnly cookie
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    emp_code = payload.get("sub")
    role = payload.get("role")
    full_name = payload.get("full_name")
    attempt_id = payload.get("attempt_id")
    device_token_hash = payload.get("device_token_hash")

    if not emp_code or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Verify roster record is active
    roster_entry = db.query(Roster).filter_by(employee_code=emp_code).first()
    if not roster_entry or not roster_entry.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account inactive or removed")

    return SessionUser(
        employee_code=emp_code,
        full_name=full_name or roster_entry.full_name,
        role=role,
        attempt_id=attempt_id,
        device_token_hash=device_token_hash
    )


def require_role(*allowed_roles: str):
    def role_checker(current_user: SessionUser = Depends(get_current_user)) -> SessionUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {allowed_roles}"
            )
        return current_user
    return role_checker
