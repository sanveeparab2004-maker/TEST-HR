from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.deps import require_role
from backend.app.schemas.auth import SessionUser
from backend.app.schemas.candidate import (
    CandidateStatusResponse, ConsentRequest, CandidateExamResponse,
    CandidateQuestionSchema, CandidateOptionSchema, SectionInfo,
    AnswerSaveRequest, AnswerSaveResponse, SubmitResponse
)
from backend.app.models.models import Attempt, Assessment, Section, Question, Option, Answer, AuditLog
from backend.app.services.grading import grade_attempt

router = APIRouter(prefix="/candidate", tags=["Candidate Exam Flow"])


def auto_submit_if_expired(attempt: Attempt, db: Session) -> bool:
    """Helper to automatically submit expired attempts."""
    now = datetime.now(timezone.utc)
    # Ensure deadline_at has timezone
    deadline = attempt.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if now >= deadline and attempt.status == "IN_PROGRESS":
        # Auto-submit
        attempt.status = "AUTO_SUBMITTED"
        attempt.submitted_at = now

        # Compute grade
        assessment = attempt.assessment
        questions = db.query(Question).filter_by(assessment_id=assessment.id).all()
        sections = db.query(Section).filter_by(assessment_id=assessment.id).all()
        answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()

        q_key_map = {}
        for q in questions:
            opts = db.query(Option).filter_by(question_id=q.id).all()
            correct_opt = next((o for o in opts if o.is_correct), None)
            q_key_map[q.id] = {
                "correct_option_id": correct_opt.id if correct_opt else None,
                "marks": q.marks,
                "section_id": q.section_id,
                "source_number": q.source_number,
                "stem": q.stem,
                "options": {o.id: {"label": o.label, "text": o.text} for o in opts}
            }

        sec_map = {s.id: s.name for s in sections}
        ans_map = {a.question_id: a.option_id for a in answers}

        grade_res = grade_attempt(ans_map, q_key_map, sec_map, negative_marking=assessment.negative_marking)

        attempt.score = grade_res["score"]
        attempt.percentage = grade_res["percentage"]
        attempt.band = grade_res["band"]
        attempt.section_scores = grade_res["section_scores"]

        db.add(AuditLog(
            actor="SYSTEM_AUTO_SUBMIT",
            action="AUTO_SUBMIT",
            entity="attempt",
            detail={"attempt_id": attempt.id, "score": attempt.score, "band": attempt.band}
        ))
        db.commit()
        return True
    return False


@router.get("/status", response_model=CandidateStatusResponse)
def get_status(
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    auto_submit_if_expired(attempt, db)

    now = datetime.now(timezone.utc)
    deadline = attempt.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    remaining = max(0, int((deadline - now).total_seconds())) if attempt.status == "IN_PROGRESS" else 0

    show_score = attempt.assessment.settings.get("show_score_on_submission", False) if attempt.assessment else False

    return CandidateStatusResponse(
        employee_code=attempt.employee_code,
        full_name=attempt.entered_name,
        consent_at=attempt.consent_at,
        status=attempt.status,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        remaining_seconds=remaining,
        warning_count=attempt.warning_count,
        show_score=show_score,
        score=attempt.score if show_score else None,
        percentage=attempt.percentage if show_score else None,
        band=attempt.band if show_score else None
    )


@router.post("/consent")
def give_consent(
    req: ConsentRequest,
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    if not req.consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent is mandatory to proceed.")

    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    attempt.consent_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Consent recorded successfully", "consent_at": attempt.consent_at}


@router.get("/exam", response_model=CandidateExamResponse)
def get_exam(
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    if auto_submit_if_expired(attempt, db) or attempt.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Assessment is already {attempt.status}."
        )

    assessment = attempt.assessment
    sections = db.query(Section).filter_by(assessment_id=assessment.id).order_by(Section.sort_order).all()
    sec_map = {s.id: s.name for s in sections}

    # Query all questions ordered strictly by source_number 1 to 50 line-wise
    raw_questions = db.query(Question).filter_by(assessment_id=assessment.id).order_by(Question.source_number).all()

    # Query all options ordered by label A, B, C, D
    raw_options = db.query(Option).filter(Option.question_id.in_([q.id for q in raw_questions])).order_by(Option.label).all()
    options_by_q: Dict[int, List[Option]] = {}
    for opt in raw_options:
        options_by_q.setdefault(opt.question_id, []).append(opt)

    sequential_questions = []
    sec_counts: Dict[int, int] = {s.id: 0 for s in sections}

    for q in raw_questions:
        sec_counts[q.section_id] = sec_counts.get(q.section_id, 0) + 1

        opts_list = options_by_q.get(q.id, [])
        candidate_options = []
        for opt_obj in opts_list:
            candidate_options.append(CandidateOptionSchema(
                id=opt_obj.id,
                label=opt_obj.label,
                text=opt_obj.text
                # Security: is_correct is strictly NOT included!
            ))

        sequential_questions.append(CandidateQuestionSchema(
            id=q.id,
            display_number=q.source_number,
            source_number=q.source_number,
            stem=q.stem,
            marks=q.marks,
            section_id=q.section_id,
            section_name=sec_map.get(q.section_id, "General"),
            options=candidate_options
        ))

    # Saved answers and flags
    saved_answers_records = db.query(Answer).filter_by(attempt_id=attempt.id).all()
    answers_map = {a.question_id: a.option_id for a in saved_answers_records}
    flagged_map = {a.question_id: a.flagged for a in saved_answers_records}

    now = datetime.now(timezone.utc)
    deadline = attempt.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    remaining = max(0, int((deadline - now).total_seconds()))

    sections_info = [
        SectionInfo(
            id=s.id,
            name=s.name,
            sort_order=s.sort_order,
            question_count=sec_counts.get(s.id, 0)
        )
        for s in sections
    ]

    return CandidateExamResponse(
        assessment_title=assessment.title,
        duration_minutes=assessment.duration_minutes,
        remaining_seconds=remaining,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        sections=sections_info,
        questions=sequential_questions,
        answers=answers_map,
        flagged=flagged_map,
        warning_count=attempt.warning_count,
        status=attempt.status
    )


@router.post("/answer", response_model=AnswerSaveResponse)
def save_answer(
    req: AnswerSaveRequest,
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    if auto_submit_if_expired(attempt, db) or attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot save answers: assessment is closed.")

    # Validate option belongs to question if option_id provided
    if req.option_id is not None:
        opt = db.query(Option).filter_by(id=req.option_id, question_id=req.question_id).first()
        if not opt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid option for question")

    ans = db.query(Answer).filter_by(attempt_id=attempt.id, question_id=req.question_id).first()
    now = datetime.now(timezone.utc)

    if not ans:
        ans = Answer(
            attempt_id=attempt.id,
            question_id=req.question_id,
            option_id=req.option_id,
            flagged=req.flagged if req.flagged is not None else False,
            answered_at=now
        )
        db.add(ans)
    else:
        if req.option_id is not None or "option_id" in req.model_dump(exclude_unset=True):
            ans.option_id = req.option_id
        if req.flagged is not None:
            ans.flagged = req.flagged
        ans.answered_at = now

    db.commit()

    deadline = attempt.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    remaining = max(0, int((deadline - now).total_seconds()))

    return AnswerSaveResponse(
        status="saved",
        question_id=req.question_id,
        option_id=ans.option_id,
        flagged=ans.flagged,
        saved_at=ans.answered_at,
        remaining_seconds=remaining
    )


@router.post("/submit", response_model=SubmitResponse)
def submit_exam(
    current_user: SessionUser = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=current_user.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt record not found")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment is already {attempt.status}."
        )

    now = datetime.now(timezone.utc)
    attempt.status = "SUBMITTED"
    attempt.submitted_at = now

    # Grade attempt
    assessment = attempt.assessment
    questions = db.query(Question).filter_by(assessment_id=assessment.id).all()
    sections = db.query(Section).filter_by(assessment_id=assessment.id).all()
    answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()

    q_key_map = {}
    for q in questions:
        opts = db.query(Option).filter_by(question_id=q.id).all()
        correct_opt = next((o for o in opts if o.is_correct), None)
        q_key_map[q.id] = {
            "correct_option_id": correct_opt.id if correct_opt else None,
            "marks": q.marks,
            "section_id": q.section_id,
            "source_number": q.source_number,
            "stem": q.stem,
            "options": {o.id: {"label": o.label, "text": o.text} for o in opts}
        }

    sec_map = {s.id: s.name for s in sections}
    ans_map = {a.question_id: a.option_id for a in answers}

    grade_res = grade_attempt(ans_map, q_key_map, sec_map, negative_marking=assessment.negative_marking)

    attempt.score = grade_res["score"]
    attempt.percentage = grade_res["percentage"]
    attempt.band = grade_res["band"]
    attempt.section_scores = grade_res["section_scores"]

    db.add(AuditLog(
        actor=attempt.employee_code,
        action="CANDIDATE_SUBMIT",
        entity="attempt",
        detail={"attempt_id": attempt.id, "score": attempt.score, "band": attempt.band}
    ))
    db.commit()

    show_score = assessment.settings.get("show_score_on_submission", False)

    return SubmitResponse(
        status="SUBMITTED",
        submitted_at=attempt.submitted_at,
        message="Your assessment has been submitted successfully.",
        show_score=show_score,
        score=attempt.score if show_score else None,
        percentage=attempt.percentage if show_score else None,
        band=attempt.band if show_score else None
    )
