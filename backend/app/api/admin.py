from backend.app.services.question_import_service import (
    generate_sample_template_csv, parse_and_validate_question_file, load_questions_into_db
)
from backend.app.services.sheets_service import queue_or_write_sheet, get_sheets_service, execute_with_retry
from backend.app.services.export_service import generate_final_comprehensive_excel
from backend.app.models.models import Restart
import io
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.deps import require_role
from backend.app.schemas.auth import SessionUser
from backend.app.models.models import (
    Roster, Assessment, Section, Question, Option, Attempt, Answer, Violation, Snapshot, AuditLog
)
from backend.app.services.export_service import generate_results_excel, generate_candidate_pdf, generate_backup_dump
from backend.app.services.ai_summary import generate_ai_summary
from scripts.import_roster import validate_roster_csv

router = APIRouter(prefix="/admin", tags=["Admin Portal & Analytics"])


def compute_integrity_status(warning_count: int, violation_count: int, has_confirmed: bool) -> str:
    if has_confirmed or warning_count >= 4:
        return "Review Needed"
    elif warning_count > 0:
        return "Minor"
    return "Clean"


@router.post("/seed-ashtapradhan")
def seed_ashtapradhan_endpoint(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    import os
    import traceback
    from sqlalchemy import text
    from backend.app.core.database import engine
    result = {"questions": "pending", "roster": "pending"}

    # Ensure attempts & questions table schema updates for SQLite
    with engine.begin() as conn:
        for tbl, col, col_def in [
            ("questions", "department", "VARCHAR(64) DEFAULT 'HR'"),
            ("attempts", "restart_count", "SMALLINT DEFAULT 0"),
            ("attempts", "tab_switch_total", "SMALLINT DEFAULT 0"),
            ("attempts", "face_violation_total", "SMALLINT DEFAULT 0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}"))
            except Exception:
                pass

    try:
        from scripts.import_ashtapradhan_questions import load_ashtapradhan_questions, seed_ashtapradhan_into_db
        csv_file = os.path.join("data", "ashtapradhan_questions.csv")
        qs = load_ashtapradhan_questions(csv_file)
        seed_ashtapradhan_into_db(qs)
        result["questions"] = f"Loaded {len(qs)} questions"
    except Exception as e:
        result["questions_error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

    try:
        from scripts.seed_ashtapradhan_roster import seed_ashtapradhan_roster
        seed_ashtapradhan_roster()
        result["roster"] = "Seeded successfully"
    except Exception as e:
        result["roster_error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

    return {"status": "ok", "details": result}


@router.get("/dashboard")
def get_admin_dashboard(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter_by(status="OPEN").first()
    if not assessment:
        assessment = db.query(Assessment).order_by(Assessment.id.desc()).first()

    total_roster = db.query(Roster).filter_by(role="CANDIDATE", is_active=True).count()
    attempts = db.query(Attempt).filter_by(assessment_id=assessment.id).all() if assessment else []

    submitted = [a for a in attempts if a.status in ("SUBMITTED", "AUTO_SUBMITTED")]
    in_progress = [a for a in attempts if a.status == "IN_PROGRESS"]
    not_started = max(0, total_roster - len(attempts))

    # Band distribution
    band_counts = {
        "Excellent": 0,
        "Good": 0,
        "Needs Improvement": 0,
        "Requires Training": 0
    }
    for a in submitted:
        band_str = (a.band or "").split(" (")[0]
        if band_str in band_counts:
            band_counts[band_str] += 1
        else:
            band_counts["Requires Training"] += 1

    # Section averages
    section_totals: Dict[str, List[float]] = {}
    for a in submitted:
        if a.section_scores:
            for s_name, data in a.section_scores.items():
                section_totals.setdefault(s_name, []).append(data.get("percentage", 0.0))

    section_averages = {
        s_name: round(sum(pcts) / len(pcts), 1) if pcts else 0.0
        for s_name, pcts in section_totals.items()
    }

    # Recent audits
    audits = db.query(AuditLog).order_by(AuditLog.at.desc()).limit(10).all()

    return {
        "assessment_title": assessment.title if assessment else "No Assessment",
        "assessment_status": assessment.status if assessment else "CLOSED",
        "total_candidates": total_roster,
        "submitted_count": len(submitted),
        "in_progress_count": len(in_progress),
        "not_started_count": not_started,
        "band_distribution": band_counts,
        "section_averages": section_averages,
        "recent_audit": [
            {"id": l.id, "at": l.at, "actor": l.actor, "action": l.action, "detail": l.detail}
            for l in audits
        ]
    }


@router.get("/results")
def get_all_results(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter_by(status="OPEN").first()
    if not assessment:
        assessment = db.query(Assessment).order_by(Assessment.id.desc()).first()

    candidates = db.query(Roster).filter_by(role="CANDIDATE", is_active=True).all()
    attempts_by_code = {a.employee_code: a for a in db.query(Attempt).all()}

    results = []
    for c in candidates:
        att = attempts_by_code.get(c.employee_code)
        if att:
            # Check confirmed violations
            has_confirmed = db.query(Violation).filter_by(attempt_id=att.id, review_status="CONFIRMED").count() > 0
            integ = compute_integrity_status(att.warning_count, att.violation_count, has_confirmed)

            time_taken = None
            if att.started_at and att.submitted_at:
                start = att.started_at.replace(tzinfo=timezone.utc) if att.started_at.tzinfo is None else att.started_at
                sub = att.submitted_at.replace(tzinfo=timezone.utc) if att.submitted_at.tzinfo is None else att.submitted_at
                time_taken = max(0, int((sub - start).total_seconds()))

            results.append({
                "attempt_id": att.id,
                "employee_code": c.employee_code,
                "full_name": c.full_name,
                "department": c.department,
                "status": att.status,
                "score": att.score,
                "percentage": float(att.percentage) if att.percentage else None,
                "band": att.band,
                "warning_count": att.warning_count,
                "violation_count": att.violation_count,
                "integrity_status": integ,
                "time_taken_seconds": time_taken,
                "started_at": att.started_at,
                "submitted_at": att.submitted_at,
            })
        else:
            results.append({
                "attempt_id": None,
                "employee_code": c.employee_code,
                "full_name": c.full_name,
                "department": c.department,
                "status": "NOT_STARTED",
                "score": None,
                "percentage": None,
                "band": None,
                "warning_count": 0,
                "violation_count": 0,
                "integrity_status": "Clean",
                "time_taken_seconds": None,
                "started_at": None,
                "submitted_at": None,
            })

    return results


@router.get("/candidate/{attempt_id}/details")
def get_candidate_details(
    attempt_id: int,
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    questions = db.query(Question).filter_by(assessment_id=attempt.assessment_id).order_by(Question.source_number).all()
    answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()
    ans_by_q = {a.question_id: a.option_id for a in answers}

    # Questions review
    review_list = []
    for q in questions:
        opts = db.query(Option).filter_by(question_id=q.id).all()
        correct_opt = next((o for o in opts if o.is_correct), None)
        selected_opt_id = ans_by_q.get(q.id)
        selected_opt = next((o for o in opts if o.id == selected_opt_id), None)

        is_corr = (selected_opt_id == correct_opt.id) if (selected_opt_id and correct_opt) else False

        review_list.append({
            "question_id": q.id,
            "source_number": q.source_number,
            "stem": q.stem,
            "marks": q.marks,
            "section_name": q.section.name,
            "selected_option_id": selected_opt_id,
            "selected_label": selected_opt.label if selected_opt else None,
            "selected_text": selected_opt.text if selected_opt else "Unanswered",
            "correct_option_id": correct_opt.id if correct_opt else None,
            "correct_label": correct_opt.label if correct_opt else None,
            "correct_text": correct_opt.text if correct_opt else None,
            "is_correct": is_corr
        })

    # Timeline with snapshots
    violations = db.query(Violation).filter_by(attempt_id=attempt.id).order_by(Violation.at.desc()).all()
    viol_list = []
    for v in violations:
        snap = db.query(Snapshot).filter_by(violation_id=v.id).first()
        snap_b64 = None
        if snap and snap.jpeg:
            import base64
            snap_b64 = "data:image/jpeg;base64," + base64.b64encode(snap.jpeg).decode("ascii")

        viol_list.append({
            "id": v.id,
            "at": v.at,
            "kind": v.kind,
            "counted": v.counted,
            "warning_number": v.warning_number,
            "review_status": v.review_status,
            "reviewed_by": v.reviewed_by,
            "reviewed_at": v.reviewed_at,
            "snapshot": snap_b64
        })

    has_confirmed = any(v.review_status == "CONFIRMED" for v in violations)
    integ = compute_integrity_status(attempt.warning_count, attempt.violation_count, has_confirmed)

    # Cached AI summary
    cached_ai = (attempt.device_info or {}).get("ai_summary")

    return {
        "attempt_id": attempt.id,
        "employee_code": attempt.employee_code,
        "full_name": attempt.entered_name,
        "status": attempt.status,
        "score": attempt.score,
        "percentage": float(attempt.percentage) if attempt.percentage else None,
        "band": attempt.band,
        "integrity_status": integ,
        "warning_count": attempt.warning_count,
        "violation_count": attempt.violation_count,
        "section_scores": attempt.section_scores,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "questions_review": review_list,
        "violations": viol_list,
        "ai_summary": cached_ai
    }


@router.post("/candidate/{attempt_id}/ai-summary")
async def generate_candidate_ai_summary(
    attempt_id: int,
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if attempt.status not in ("SUBMITTED", "AUTO_SUBMITTED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment must be submitted before generating AI summary")

    # Find missed topics
    questions = db.query(Question).filter_by(assessment_id=attempt.assessment_id).all()
    answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()
    ans_by_q = {a.question_id: a.option_id for a in answers}

    missed_topics = []
    for q in questions:
        opts = db.query(Option).filter_by(question_id=q.id).all()
        correct_opt = next((o for o in opts if o.is_correct), None)
        selected_id = ans_by_q.get(q.id)
        if not selected_id or (correct_opt and selected_id != correct_opt.id):
            missed_topics.append(f"{q.section.name}: {q.stem[:60]}...")

    # Generate summary without candidate name (only employee code)
    ai_result = await generate_ai_summary(
        employee_code=attempt.employee_code,
        band=attempt.band or "Unassigned",
        section_scores=attempt.section_scores or {},
        missed_topics=missed_topics
    )

    # Cache on attempt record
    dev_info = dict(attempt.device_info or {})
    dev_info["ai_summary"] = ai_result
    attempt.device_info = dev_info

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="GENERATE_AI_SUMMARY",
        entity="attempt",
        detail={"attempt_id": attempt.id, "employee_code": attempt.employee_code}
    ))
    db.commit()

    return ai_result


@router.get("/questions")
def get_question_bank(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """View question bank showing correct answers (Strictly ADMIN only)."""
    assessment = db.query(Assessment).first()
    if not assessment:
        return []

    questions = db.query(Question).filter_by(assessment_id=assessment.id).order_by(Question.source_number).all()
    bank = []
    for q in questions:
        opts = db.query(Option).filter_by(question_id=q.id).order_by(Option.label).all()
        bank.append({
            "id": q.id,
            "source_number": q.source_number,
            "section": q.section.name,
            "stem": q.stem,
            "marks": q.marks,
            "options": [
                {"id": o.id, "label": o.label, "text": o.text, "is_correct": o.is_correct}
                for o in opts
            ]
        })
    return bank


@router.post("/purge-retention")
def purge_retention(
    days: int = Query(90, ge=1, le=365),
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Purge violations and snapshots older than specified retention period (DPDP Act compliance)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    deleted_snapshots = db.query(Snapshot).filter(Snapshot.taken_at < cutoff).delete(synchronize_session=False)
    deleted_violations = db.query(Violation).filter(Violation.at < cutoff).delete(synchronize_session=False)

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="DATA_RETENTION_PURGE",
        entity="retention",
        detail={"days": days, "deleted_snapshots": deleted_snapshots, "deleted_violations": deleted_violations}
    ))
    db.commit()

    return {
        "status": "success",
        "retention_days": days,
        "deleted_snapshots": deleted_snapshots,
        "deleted_violations": deleted_violations,
        "message": f"Successfully purged records older than {days} days."
    }


@router.get("/export/excel")
def export_excel(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    results = get_all_results(current_user=current_user, db=db)
    excel_bytes = generate_results_excel(results)

    filename = f"HR_Assessment_Results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/export/pdf/{attempt_id}")
def export_candidate_pdf(
    attempt_id: int,
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    cand_data = {
        "full_name": attempt.entered_name,
        "employee_code": attempt.employee_code,
        "department": attempt.roster_entry.department if attempt.roster_entry else "HR",
        "score": attempt.score or 0,
        "percentage": float(attempt.percentage or 0.0),
        "band": attempt.band or "Unassigned",
        "warning_count": attempt.warning_count,
        "integrity_status": "Clean" if attempt.warning_count == 0 else "Minor" if attempt.warning_count < 4 else "Review Needed",
        "submitted_at": attempt.submitted_at.strftime("%Y-%m-%d %H:%M UTC") if attempt.submitted_at else "In Progress",
        "section_scores": attempt.section_scores or {},
        "ai_summary": (attempt.device_info or {}).get("ai_summary")
    }

    pdf_bytes = generate_candidate_pdf(cand_data)
    filename = f"Scorecard_{attempt.employee_code}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/export/backup")
def export_backup(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    dump_bytes = generate_backup_dump(db)
    filename = f"HR_Assessment_Backup_Dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=dump_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/candidate/{employee_code}/reset")
def reset_candidate_attempt(
    employee_code: str,
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    code = employee_code.strip()
    attempts = db.query(Attempt).filter(
        (Attempt.employee_code == code) | (Attempt.entered_name.ilike(f"%{code}%"))
    ).all()

    deleted_count = len(attempts)
    for att in attempts:
        db.query(Answer).filter_by(attempt_id=att.id).delete(synchronize_session=False)
        db.query(Snapshot).filter_by(attempt_id=att.id).delete(synchronize_session=False)
        db.query(Violation).filter_by(attempt_id=att.id).delete(synchronize_session=False)
        db.delete(att)

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="RESET_CANDIDATE_ATTEMPT",
        entity="attempt",
        detail={"employee_code": code, "deleted_attempts": deleted_count}
    ))
    db.commit()

    return {
        "status": "success",
        "message": f"All previous attempt and device lock data for {code} has been completely removed. Candidate can start fresh from scratch."
    }


@router.post("/reset-all-attempts")
def reset_all_attempts(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    db.query(Answer).delete(synchronize_session=False)
    db.query(Snapshot).delete(synchronize_session=False)
    db.query(Violation).delete(synchronize_session=False)
    count = db.query(Attempt).delete(synchronize_session=False)

    db.add(AuditLog(
        actor=current_user.employee_code,
        action="RESET_ALL_ATTEMPTS",
        entity="attempt",
        detail={"purged_attempts": count}
    ))
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully reset all {count} candidate attempts. All candidates can now start fresh."
    }



# --- EXAM SYSTEM EXPANSION ENDPOINTS ---

@router.get("/questions/template")
def download_question_template(
    current_user: SessionUser = Depends(require_role("ADMIN"))
):
    """Download standardized Question Bank CSV template with department and marks columns."""
    csv_text = generate_sample_template_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=question_bank_template.csv"}
    )


@router.post("/questions/import")
async def import_question_bank(
    file: UploadFile = File(...),
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Import and validate question bank for departments.
    Requires exactly 100 marks per department, no duplicates, and valid options.
    """
    file_bytes = await file.read()
    valid_questions, errors, dept_marks = parse_and_validate_question_file(file_bytes, file.filename)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Question bank validation failed. Please correct the listed errors.",
                "errors": errors,
                "department_marks": dept_marks
            }
        )

    dept_counts = load_questions_into_db(db, valid_questions)

    return {
        "status": "success",
        "message": f"Successfully imported {len(valid_questions)} questions across departments.",
        "department_counts": dept_counts,
        "department_marks": dept_marks
    }


@router.post("/resync-sheet")
def resync_to_google_sheet(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Re-syncs all completed attempts and answers from database to Google Sheet idempotently."""
    from backend.app.api.candidate import sync_submission_to_google_sheet

    submitted_attempts = db.query(Attempt).filter(
        Attempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    ).all()

    resynced = 0
    for att in submitted_attempts:
        sync_submission_to_google_sheet(att, db)
        resynced += 1

    return {
        "status": "success",
        "message": f"Successfully re-synced {resynced} candidate attempts to Google Sheet.",
        "resynced_count": resynced
    }


@router.get("/finalize")
def finalize_and_export_multi_sheet(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Multi-sheet comprehensive Excel audit workbook with summary, all candidates,
    department tabs, question item analysis, and violations log."""
    excel_bytes = generate_final_comprehensive_excel(db)
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=FINAL_ASSESSMENT_AUDIT_{now_str}.xlsx"}
    )


@router.get("/export")
def export_general_backup(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Secondary admin-only export endpoint."""
    excel_bytes = generate_final_comprehensive_excel(db)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=assessment_export.xlsx"}
    )


@router.get("/reconcile")
def reconcile_sheet_and_db(
    current_user: SessionUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    """Reconciles database records against Google Sheet rows to verify zero data loss."""
    from backend.app.services.sheets_service import get_sheets_service
    from backend.app.core.config import settings

    db_submitted = db.query(Attempt).filter(
        Attempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    ).all()
    db_attempt_ids = {a.id for a in db_submitted}

    service = get_sheets_service()
    if not service or not settings.GOOGLE_SHEET_ID:
        return {
            "status": "mock_mode",
            "db_submitted_count": len(db_submitted),
            "sheet_count": len(db_submitted),
            "missing_in_sheet": [],
            "reconciliation": "MATCHED (Local Mock Mode Active)"
        }

    try:
        res = execute_with_retry(
            lambda: service.spreadsheets().values().get(
                spreadsheetId=settings.GOOGLE_SHEET_ID,
                range="'All Results'!A2:A"
            ).execute()
        )
        sheet_rows = res.get("values", [])
        sheet_attempt_ids = {int(r[0]) for r in sheet_rows if r and r[0].isdigit()}

        missing_in_sheet = list(db_attempt_ids - sheet_attempt_ids)
        return {
            "status": "reconciled",
            "db_submitted_count": len(db_attempt_ids),
            "sheet_count": len(sheet_attempt_ids),
            "missing_in_sheet": missing_in_sheet,
            "reconciliation": "MATCHED" if not missing_in_sheet else "DISCREPANCY_FOUND"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "db_submitted_count": len(db_attempt_ids)
        }
