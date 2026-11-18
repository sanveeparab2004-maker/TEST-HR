from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=64)


class LookupResponse(BaseModel):
    requires_pin: bool


class LoginRequest(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=64)
    full_name: str = Field(..., min_length=1, max_length=200)
    pin: Optional[str] = None
    device_token: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    employee_code: str
    full_name: str
    device_token: Optional[str] = None
    attempt_id: Optional[int] = None


class SessionUser(BaseModel):
    employee_code: str
    full_name: str
    role: str
    attempt_id: Optional[int] = None
    device_token_hash: Optional[str] = None
