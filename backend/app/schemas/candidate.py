from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CandidateOptionSchema(BaseModel):
    id: int
    label: str  # Display label in candidate's shuffled order
    text: str
    # CRITICAL SECURITY RULE: is_correct is intentionally excluded!


class CandidateQuestionSchema(BaseModel):
    id: int
    display_number: int  # 1 to 50 in candidate's shuffled order
    source_number: int
    stem: str
    marks: int
    section_id: int
    section_name: str
    options: List[CandidateOptionSchema]


class SectionInfo(BaseModel):
    id: int
    name: str
    sort_order: int
    question_count: int


class CandidateExamResponse(BaseModel):
    assessment_title: str
    duration_minutes: int
    remaining_seconds: int
    started_at: datetime
    deadline_at: datetime
    sections: List[SectionInfo]
    questions: List[CandidateQuestionSchema]
    answers: Dict[int, Optional[int]]  # question_id -> selected_option_id
    flagged: Dict[int, bool]           # question_id -> bool
    warning_count: int
    status: str


class AnswerSaveRequest(BaseModel):
    question_id: int
    option_id: Optional[int] = None
    flagged: Optional[bool] = None


class AnswerSaveResponse(BaseModel):
    status: str
    question_id: int
    option_id: Optional[int]
    flagged: bool
    saved_at: datetime
    remaining_seconds: int


class ConsentRequest(BaseModel):
    consent: bool = Field(..., description="Mandatory true consent")


class CandidateStatusResponse(BaseModel):
    employee_code: str
    full_name: str
    consent_at: Optional[datetime]
    status: str
    started_at: Optional[datetime]
    deadline_at: Optional[datetime]
    remaining_seconds: int
    warning_count: int
    show_score: bool = False
    score: Optional[int] = None
    percentage: Optional[float] = None
    band: Optional[str] = None
    result: Optional[str] = None
    correct_count: Optional[int] = None
    wrong_count: Optional[int] = None
    unanswered_count: Optional[int] = None
    time_taken_formatted: Optional[str] = None


class SubmitRequest(BaseModel):
    answers: Optional[Dict[str, Optional[int]]] = None


class SubmitResponse(BaseModel):
    status: str
    submitted_at: datetime
    message: str
    show_score: bool
    score: Optional[int] = None
    percentage: Optional[float] = None
    band: Optional[str] = None
    result: Optional[str] = None
    correct_count: Optional[int] = None
    wrong_count: Optional[int] = None
    unanswered_count: Optional[int] = None
    time_taken_formatted: Optional[str] = None
