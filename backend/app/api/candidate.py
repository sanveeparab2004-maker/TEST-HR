import json
from backend.app.core.config import settings
from backend.app.services.sheets_service import queue_or_write_sheet
from backend.app.models.models import Roster
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



def sync_submission_to_google_sheet(attempt: Attempt, db: Session):
    """Sync completed exam results to Google Sheet (Attempts, Answers, All Results, and Dept tabs)."""
    now = datetime.now(timezone.utc)
    assessment = attempt.assessment
    roster_entry = db.query(Roster).filter_by(employee_code=attempt.employee_code).first()
    dept_name = (roster_entry.department if roster_entry else None) or (assessment.settings or {}).get("department", "HR")

    # Pass / Fail evaluation (pass mark: 35)
    pass_status = "PASS" if (attempt.score or 0) >= settings.PASS_MARKS else "FAIL"

    # Time taken in minutes
    time_taken_min = 0.0
    if attempt.started_at and attempt.submitted_at:
        diff_sec = (attempt.submitted_at - attempt.started_at).total_seconds()
        time_taken_min = round(max(0.0, diff_sec / 60.0), 1)

    # Rank calculations with tie-breaker (higher score, then lower time taken)
    def attempt_sort_key(a):
        t = (a.submitted_at - a.started_at).total_seconds() if (a.submitted_at and a.started_at) else 99999
        return (-(a.score or 0), t)

    all_dept_attempts = db.query(Attempt).filter(
        Attempt.assessment_id == attempt.assessment_id,
        Attempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    ).all()
    sorted_dept = sorted(all_dept_attempts, key=attempt_sort_key)
    rank_dept = next((idx for idx, a in enumerate(sorted_dept, 1) if a.id == attempt.id), 1)

    all_attempts = db.query(Attempt).filter(
        Attempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    ).all()
    sorted_all = sorted(all_attempts, key=attempt_sort_key)
    rank_overall = next((idx for idx, a in enumerate(sorted_all, 1) if a.id == attempt.id), 1)

    # 1. Update Attempts tab
    attempt_row = [
        attempt.id,
        attempt.employee_code,
        attempt.entered_name,
        attempt.employee_code,
        dept_name,
        attempt.started_at.isoformat() if attempt.started_at else "",
        attempt.submitted_at.isoformat() if attempt.submitted_at else "",
        attempt.status.lower(),
        attempt.restart_count,
        attempt.tab_switch_total,
        attempt.face_violation_total,
        attempt.score,
        assessment.total_marks if assessment else settings.TOTAL_MARKS,
        json.dumps(attempt.question_order or []),
        json.dumps(attempt.option_order or {})
    ]
    queue_or_write_sheet(
        db=db,
        operation="append_attempt",
        idempotency_key=f"attempt_{attempt.id}_final",
        payload={"row": attempt_row},
        attempt_id=attempt.id
    )

    # 2. Append Answers rows
    answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()
    q_map = {q.id: q for q in db.query(Question).filter_by(assessment_id=attempt.assessment_id).all()}
    opt_map = {o.id: o for o in db.query(Option).filter(Option.question_id.in_(list(q_map.keys()))).all()}

    answer_rows = []
    for ans in answers:
        q = q_map.get(ans.question_id)
        selected_opt = opt_map.get(ans.option_id) if ans.option_id else None
        correct_opt = next((o for o in opt_map.values() if o.question_id == ans.question_id and o.is_correct), None)

        is_corr = (selected_opt and correct_opt and selected_opt.id == correct_opt.id)
        marks_awd = (q.marks if q else 2) if is_corr else 0

        answer_rows.append([
            attempt.id,
            attempt.employee_code,
            ans.question_id,
            f"{selected_opt.label}: {selected_opt.text}" if selected_opt else "UNANSWERED",
            f"{correct_opt.label}: {correct_opt.text}" if correct_opt else "",
            "CORRECT" if is_corr else "INCORRECT",
            marks_awd,
            ans.answered_at.isoformat() if ans.answered_at else ""
        ])

    if answer_rows:
        queue_or_write_sheet(
            db=db,
            operation="append_answers",
            idempotency_key=f"answers_{attempt.id}",
            payload={"rows": answer_rows},
            attempt_id=attempt.id
        )

    # 3. Append All Results and Dept tab row
    all_results_row = [
        attempt.id,
        attempt.employee_code,
        attempt.entered_name,
        dept_name,
        attempt.score,
        assessment.total_marks if assessment else settings.TOTAL_MARKS,
        f"{float(attempt.percentage or 0.0):.2f}%",
        pass_status,
        rank_dept,
        rank_overall,
        time_taken_min,
        attempt.violation_count,
        attempt.restart_count,
        attempt.submitted_at.isoformat() if attempt.submitted_at else ""
    ]
    queue_or_write_sheet(
        db=db,
        operation="sync_all_results",
        idempotency_key=f"results_{attempt.id}",
        payload={"row": all_results_row, "department": dept_name},
        attempt_id=attempt.id
    )

    attempt.sheet_synced = True
    attempt.sheet_synced_at = now
    db.commit()

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
        sync_submission_to_google_sheet(attempt, db)
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

    # Use candidate's unique cryptographically shuffled order
    ordered_q_ids = attempt.question_order or []
    option_order_map = attempt.option_order or {}

    raw_questions = db.query(Question).filter_by(assessment_id=assessment.id).all()
    q_dict = {q.id: q for q in raw_questions}

    raw_options = db.query(Option).filter(Option.question_id.in_([q.id for q in raw_questions])).all()
    opts_dict = {o.id: o for o in raw_options}

    sec_counts: Dict[int, int] = {s.id: 0 for s in sections}
    for q in raw_questions:
        sec_counts[q.section_id] = sec_counts.get(q.section_id, 0) + 1

    shuffled_questions = []
    labels = ["A", "B", "C", "D", "E", "F"]

    # If ordered_q_ids is empty for legacy attempts, fallback to source_number
    display_q_ids = ordered_q_ids if ordered_q_ids else [q.id for q in sorted(raw_questions, key=lambda x: x.source_number)]

    for disp_idx, q_id in enumerate(display_q_ids, start=1):
        q = q_dict.get(q_id)
        if not q:
            continue

        shuffled_opt_ids = option_order_map.get(str(q_id), [])
        cand_options = []

        if shuffled_opt_ids:
            for l_idx, opt_id in enumerate(shuffled_opt_ids):
                opt_obj = opts_dict.get(opt_id)
                if opt_obj:
                    cand_options.append(CandidateOptionSchema(
                        id=opt_obj.id,
                        label=labels[l_idx] if l_idx < len(labels) else str(l_idx + 1),
                        text=opt_obj.text
                    ))
        else:
            opts_for_q = sorted([o for o in raw_options if o.question_id == q_id], key=lambda x: x.label)
            for opt_obj in opts_for_q:
                cand_options.append(CandidateOptionSchema(
                    id=opt_obj.id,
                    label=opt_obj.label,
                    text=opt_obj.text
                ))

        shuffled_questions.append(CandidateQuestionSchema(
            id=q.id,
            display_number=disp_idx,
            source_number=q.source_number,
            stem=q.stem,
            marks=q.marks,
            section_id=q.section_id,
            section_name=sec_map.get(q.section_id, "General"),
            options=cand_options
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
        questions=shuffled_questions,
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
    sync_submission_to_google_sheet(attempt, db)

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
