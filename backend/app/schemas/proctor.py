from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ViolationReportRequest(BaseModel):
    kind: str = Field(..., description="Violation kind, e.g. TAB_SWITCH, WINDOW_BLUR, FULLSCREEN_EXIT, NO_FACE, MULTIPLE_FACES, LOOKING_AWAY, CAMERA_OFF, COPY_PASTE, DEV_TOOLS_KEY")
    detail: Optional[Dict[str, Any]] = None
    snapshot: Optional[str] = Field(None, description="Base64 encoded 320px JPEG snapshot")


class ViolationReportResponse(BaseModel):
    violation_id: int
    warning_count: int
    warning_tier: str  # WARNING_1, WARNING_2, WARNING_3, FINAL_WARNING, POST_FINAL_NOTED, UNCOUNTED
    counted: bool
    message: str
    server_time: datetime
    action: Optional[str] = "WARNING"
    restart_count: Optional[int] = 0


class HeartbeatRequest(BaseModel):
    timestamp: float
    current_question_id: Optional[int] = None
    fullscreen_active: bool = True
    camera_active: bool = True


class HeartbeatResponse(BaseModel):
    status: str
    warning_count: int
    remaining_seconds: int
    server_time: datetime
    action: Optional[str] = "WARNING"
    restart_count: Optional[int] = 0
