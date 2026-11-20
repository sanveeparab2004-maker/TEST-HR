import io
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generate_results_excel(results: List[Dict[str, Any]]) -> bytes:
    """Generates professional Excel workbook containing complete candidate results."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Assessment Results"

    # Header styling
    header_fill = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color="E2E8F0"),
        right=Side(style='thin', color="E2E8F0"),
        top=Side(style='thin', color="E2E8F0"),
        bottom=Side(style='thin', color="E2E8F0")
    )

    headers = [
        "Employee Code", "Full Name", "Department", "Status",
        "Score (/100)", "Percentage (%)", "Performance Band",
        "Warnings Count", "Total Violations", "Integrity Status",
        "Started At", "Submitted At"
    ]

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in results:
        row_data = [
            r.get("employee_code"),
            r.get("full_name"),
            r.get("department") or "N/A",
            r.get("status"),
            r.get("score") if r.get("score") is not None else "N/A",
            f"{r.get('percentage'):.2f}%" if r.get("percentage") is not None else "N/A",
            r.get("band") or "Pending",
            r.get("warning_count", 0),
            r.get("violation_count", 0),
            r.get("integrity_status", "Clean"),
            r.get("started_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("started_at") else "",
            r.get("submitted_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("submitted_at") else "",
        ]
        ws.append(row_data)

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def generate_candidate_pdf(candidate_data: Dict[str, Any]) -> bytes:
    """Generates official assessment scorecard PDF for an individual candidate."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E1B4B'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    section_title = ParagraphStyle(
        'SectionH',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#312E81'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    elements.append(Paragraph("HR TEAM – PROFESSIONAL ASSESSMENT", title_style))
    elements.append(Paragraph("Official Confidential Performance & Integrity Evaluation Report", subtitle_style))
    elements.append(Spacer(1, 15))

    # Candidate Meta Table
    meta_data = [
        [Paragraph("<b>Candidate Name:</b>", body_style), Paragraph(candidate_data.get("full_name", ""), body_style),
         Paragraph("<b>Employee Code:</b>", body_style), Paragraph(candidate_data.get("employee_code", ""), body_style)],
        [Paragraph("<b>Department:</b>", body_style), Paragraph(candidate_data.get("department", "HR Operations"), body_style),
         Paragraph("<b>Date:</b>", body_style), Paragraph(candidate_data.get("submitted_at", "N/A"), body_style)],
        [Paragraph("<b>Total Score:</b>", body_style), Paragraph(f"<b>{candidate_data.get('score', 0)} / 100 ({candidate_data.get('percentage', 0):.1f}%)</b>", body_style),
         Paragraph("<b>Performance Band:</b>", body_style), Paragraph(f"<b>{candidate_data.get('band', 'N/A')}</b>", body_style)],
        [Paragraph("<b>Proctor Warnings:</b>", body_style), Paragraph(f"{candidate_data.get('warning_count', 0)} / 3", body_style),
         Paragraph("<b>Integrity Status:</b>", body_style), Paragraph(f"<b>{candidate_data.get('integrity_status', 'Clean')}</b>", body_style)]
    ]

    t_meta = Table(meta_data, colWidths=[100, 170, 100, 170])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 15))

    # Section Breakdown Table
    elements.append(Paragraph("Competency & Section Breakdown", section_title))
    sec_data = [[
        Paragraph("<b>Section / Competency Area</b>", body_style),
        Paragraph("<b>Score</b>", body_style),
        Paragraph("<b>Max</b>", body_style),
        Paragraph("<b>Percentage</b>", body_style)
    ]]

    for s_name, s_info in (candidate_data.get("section_scores") or {}).items():
        if isinstance(s_info, dict):
            s_score = s_info.get("score", 0)
            s_max = s_info.get("max_score", 0)
            s_pct = f"{s_info.get('percentage', 0):.1f}%"
        else:
            s_score = s_info
            s_max = "-"
            s_pct = "-"
        sec_data.append([
            Paragraph(s_name, body_style),
            Paragraph(str(s_score), body_style),
            Paragraph(str(s_max), body_style),
            Paragraph(str(s_pct), body_style)
        ])

    t_sec = Table(sec_data, colWidths=[240, 100, 100, 100])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_sec)
    elements.append(Spacer(1, 15))

    # AI Advisory Summary if available
    ai_summary = candidate_data.get("ai_summary")
    if ai_summary and isinstance(ai_summary, dict):
        elements.append(Paragraph("Advisory Development Insights (AI-Generated)", section_title))
        strengths = "<br/>• ".join(ai_summary.get("strengths", []))
        weaknesses = "<br/>• ".join(ai_summary.get("weak_areas", []))
        rec = "<br/>• ".join(ai_summary.get("recommended_training", []))

        ai_data = [
            [Paragraph("<b>Key Strengths:</b>", body_style), Paragraph(f"• {strengths}", body_style)],
            [Paragraph("<b>Areas for Growth:</b>", body_style), Paragraph(f"• {weaknesses}", body_style)],
            [Paragraph("<b>Recommended Training:</b>", body_style), Paragraph(f"• {rec}", body_style)]
        ]
        t_ai = Table(ai_data, colWidths=[130, 410])
        t_ai.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAF5FF')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E9D5FF')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F3E8FF')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_ai)

    doc.build(elements)
    return buffer.getvalue()


def generate_backup_dump(db_session) -> bytes:
    """Generates complete JSON backup dump of attempts, answers, and violations."""
    from backend.app.models.models import Attempt, Answer, Violation

    attempts = db_session.query(Attempt).all()
    dump = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_attempts": len(attempts),
        "attempts": []
    }

    for a in attempts:
        answers = db_session.query(Answer).filter_by(attempt_id=a.id).all()
        violations = db_session.query(Violation).filter_by(attempt_id=a.id).all()

        dump["attempts"].append({
            "id": a.id,
            "employee_code": a.employee_code,
            "entered_name": a.entered_name,
            "status": a.status,
            "score": a.score,
            "percentage": float(a.percentage) if a.percentage else None,
            "band": a.band,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            "section_scores": a.section_scores,
            "warning_count": a.warning_count,
            "violation_count": a.violation_count,
            "answers": [
                {"question_id": ans.question_id, "option_id": ans.option_id, "flagged": ans.flagged}
                for ans in answers
            ],
            "violations": [
                {
                    "id": v.id,
                    "at": v.at.isoformat() if v.at else None,
                    "kind": v.kind,
                    "counted": v.counted,
                    "warning_number": v.warning_number,
                    "review_status": v.review_status,
                    "reviewed_by": v.reviewed_by
                }
                for v in violations
            ]
        })

    return json.dumps(dump, indent=2).encode("utf-8")


from typing import List, Dict, Any
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from backend.app.core.config import settings
from backend.app.models.models import Roster, Assessment, Section, Question, Option, Attempt, Answer, Violation, Restart


def generate_final_comprehensive_excel(db) -> bytes:
    """Generates multi-sheet Excel export containing:
    1. Dashboard summary
    2. All Candidates
    3. Department tabs (one per department)
    4. Question Analysis (item difficulty, discrimination index, % answered correct)
    5. Violations log
    6. Restarts log
    """
    wb = openpyxl.Workbook()
    
    # Styles
    navy_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    navy_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F2F4F8", end_color="F2F4F8", fill_type="solid")
    pass_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    pass_font = Font(name="Calibri", size=10, bold=True, color="375623")
    fail_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    fail_font = Font(name="Calibri", size=10, bold=True, color="C65911")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color="D9D9D9"),
        right=Side(style='thin', color="D9D9D9"),
        top=Side(style='thin', color="D9D9D9"),
        bottom=Side(style='thin', color="D9D9D9")
    )

    # 1. Dashboard Summary
    ws_dash = wb.active
    ws_dash.title = "Dashboard Summary"

    ws_dash.append(["ONLINE PROCTORED EXAM – FINAL AUDIT & PERFORMANCE SUMMARY"])
    ws_dash.cell(row=1, column=1).font = Font(size=14, bold=True, color="1F3864")
    ws_dash.append([])

    all_attempts = db.query(Attempt).filter(Attempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])).all()
    total_attempts = len(all_attempts)
    passed_attempts = [a for a in all_attempts if (a.score or 0) >= settings.PASS_MARKS]
    failed_attempts = [a for a in all_attempts if (a.score or 0) < settings.PASS_MARKS]
    pass_rate = (len(passed_attempts) / total_attempts * 100) if total_attempts > 0 else 0.0
    avg_score = (sum(a.score or 0 for a in all_attempts) / total_attempts) if total_attempts > 0 else 0.0
    highest_score = max([a.score or 0 for a in all_attempts], default=0)
    lowest_score = min([a.score or 0 for a in all_attempts], default=0)

    ws_dash.append(["Metric", "Value"])
    ws_dash.cell(row=3, column=1).fill = navy_fill
    ws_dash.cell(row=3, column=1).font = navy_font
    ws_dash.cell(row=3, column=2).fill = navy_fill
    ws_dash.cell(row=3, column=2).font = navy_font

    kpis = [
        ("Total Submissions", total_attempts),
        ("Passed Candidates (Score >= 35)", len(passed_attempts)),
        ("Failed Candidates (Score < 35)", len(failed_attempts)),
        ("Overall Pass Rate (%)", f"{pass_rate:.1f}%"),
        ("Average Score (/100)", f"{avg_score:.1f}"),
        ("Highest Score Achieved", highest_score),
        ("Lowest Score", lowest_score),
        ("Total Violations Recorded", sum(a.violation_count for a in all_attempts)),
        ("Total Restarts Triggered", sum(a.restart_count for a in all_attempts))
    ]
    for m, v in kpis:
        ws_dash.append([m, v])

    ws_dash.append([])
    ws_dash.append(["Department Performance Breakdown"])
    ws_dash.cell(row=len(kpis) + 5, column=1).font = Font(size=12, bold=True, color="1F3864")

    dept_headers = ["Department", "Submissions", "Passed", "Failed", "Pass %", "Average Score", "Top Score"]
    ws_dash.append(dept_headers)
    hdr_row = len(kpis) + 6
    for c in range(1, len(dept_headers) + 1):
        ws_dash.cell(row=hdr_row, column=c).fill = navy_fill
        ws_dash.cell(row=hdr_row, column=c).font = navy_font
        ws_dash.cell(row=hdr_row, column=c).alignment = center_align

    for dept in settings.DEPARTMENTS:
        d_attempts = [a for a in all_attempts if a.assessment and (a.assessment.settings or {}).get("department", "").upper() == dept.upper()]
        d_cnt = len(d_attempts)
        d_pass = len([a for a in d_attempts if (a.score or 0) >= settings.PASS_MARKS])
        d_fail = d_cnt - d_pass
        d_pct = (d_pass / d_cnt * 100) if d_cnt > 0 else 0.0
        d_avg = (sum(a.score or 0 for a in d_attempts) / d_cnt) if d_cnt > 0 else 0.0
        d_top = max([a.score or 0 for a in d_attempts], default=0)
        ws_dash.append([dept, d_cnt, d_pass, d_fail, f"{d_pct:.1f}%", f"{d_avg:.1f}", d_top])

    # 2. All Candidates
    ws_all = wb.create_sheet(title="All Candidates")
    cand_headers = [
        "Attempt ID", "Candidate Code", "Full Name", "Department", "Status",
        "Score (/100)", "Percentage (%)", "Result", "Time Taken (min)",
        "Tab Switches", "Face Violations", "Restarts", "Submitted At"
    ]
    ws_all.append(cand_headers)
    for c in range(1, len(cand_headers) + 1):
        cell = ws_all.cell(row=1, column=c)
        cell.fill = navy_fill
        cell.font = navy_font
        cell.alignment = center_align

    for idx, a in enumerate(all_attempts, start=2):
        dept = (a.assessment.settings or {}).get("department", "HR") if a.assessment else "HR"
        t_taken = round((a.submitted_at - a.started_at).total_seconds() / 60.0, 1) if (a.submitted_at and a.started_at) else 0.0
        is_pass = (a.score or 0) >= settings.PASS_MARKS
        row_vals = [
            a.id, a.employee_code, a.entered_name, dept, a.status,
            a.score, f"{float(a.percentage or 0.0):.2f}%",
            "PASS" if is_pass else "FAIL",
            t_taken, a.tab_switch_total, a.face_violation_total, a.restart_count,
            a.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if a.submitted_at else ""
        ]
        ws_all.append(row_vals)
        res_cell = ws_all.cell(row=idx, column=8)
        res_cell.fill = pass_fill if is_pass else fail_fill
        res_cell.font = pass_font if is_pass else fail_font
        res_cell.alignment = center_align

    # 3. Department Tabs
    for dept in settings.DEPARTMENTS:
        ws_dept = wb.create_sheet(title=f"Dept - {dept}")
        ws_dept.append(cand_headers)
        for c in range(1, len(cand_headers) + 1):
            cell = ws_dept.cell(row=1, column=c)
            cell.fill = navy_fill
            cell.font = navy_font
            cell.alignment = center_align

        d_attempts = [a for a in all_attempts if a.assessment and (a.assessment.settings or {}).get("department", "").upper() == dept.upper()]
        for idx, a in enumerate(d_attempts, start=2):
            t_taken = round((a.submitted_at - a.started_at).total_seconds() / 60.0, 1) if (a.submitted_at and a.started_at) else 0.0
            is_pass = (a.score or 0) >= settings.PASS_MARKS
            row_vals = [
                a.id, a.employee_code, a.entered_name, dept, a.status,
                a.score, f"{float(a.percentage or 0.0):.2f}%",
                "PASS" if is_pass else "FAIL",
                t_taken, a.tab_switch_total, a.face_violation_total, a.restart_count,
                a.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if a.submitted_at else ""
            ]
            ws_dept.append(row_vals)
            res_cell = ws_dept.cell(row=idx, column=8)
            res_cell.fill = pass_fill if is_pass else fail_fill
            res_cell.font = pass_font if is_pass else fail_font
            res_cell.alignment = center_align

    # 4. Question Analysis Tab
    ws_qa = wb.create_sheet(title="Question Analysis")
    qa_headers = [
        "Question ID", "Department", "Question Stem", "Total Attempts",
        "Correct Count", "Incorrect Count", "Accuracy % (Facility Value)", "Difficulty Level"
    ]
    ws_qa.append(qa_headers)
    for c in range(1, len(qa_headers) + 1):
        cell = ws_qa.cell(row=1, column=c)
        cell.fill = navy_fill
        cell.font = navy_font
        cell.alignment = center_align

    all_questions = db.query(Question).all()
    q_row_idx = 2
    for q in all_questions:
        q_answers = db.query(Answer).filter_by(question_id=q.id).all()
        correct_opt = db.query(Option).filter_by(question_id=q.id, is_correct=True).first()
        total_ans = len(q_answers)
        corr_cnt = sum(1 for ans in q_answers if correct_opt and ans.option_id == correct_opt.id)
        incorr_cnt = total_ans - corr_cnt
        acc_pct = (corr_cnt / total_ans * 100) if total_ans > 0 else 0.0
        
        diff = "Normal"
        if acc_pct >= 85:
            diff = "Easy"
        elif acc_pct < 40 and total_ans > 0:
            diff = "Hard"

        ws_qa.append([
            q.id, q.department or "HR", q.stem[:120], total_ans, corr_cnt, incorr_cnt, f"{acc_pct:.1f}%", diff
        ])
        q_row_idx += 1

    # 5. Violations Tab
    ws_viol = wb.create_sheet(title="Violations Log")
    viol_headers = ["Violation ID", "Timestamp", "Attempt ID", "Candidate Code", "Violation Kind", "Warning Number", "Action", "Status"]
    ws_viol.append(viol_headers)
    for c in range(1, len(viol_headers) + 1):
        cell = ws_viol.cell(row=1, column=c)
        cell.fill = navy_fill
        cell.font = navy_font
        cell.alignment = center_align

    all_viols = db.query(Violation).order_by(Violation.id.asc()).all()
    for v in all_viols:
        att = v.attempt
        cand_code = att.employee_code if att else ""
        ws_viol.append([
            v.id, v.at.strftime("%Y-%m-%d %H:%M:%S") if v.at else "",
            v.attempt_id, cand_code, v.kind, v.warning_number or "", v.action or "WARNING", v.review_status
        ])

    # 6. Restarts Log Tab
    ws_rest = wb.create_sheet(title="Restarts Log")
    rest_headers = ["Restart ID", "Timestamp", "Attempt ID", "Candidate Code", "Reason", "Restart Number"]
    ws_rest.append(rest_headers)
    for c in range(1, len(rest_headers) + 1):
        cell = ws_rest.cell(row=1, column=c)
        cell.fill = navy_fill
        cell.font = navy_font
        cell.alignment = center_align

    all_restarts = db.query(Restart).order_by(Restart.id.asc()).all()
    for r in all_restarts:
        ws_rest.append([
            r.id, r.at.strftime("%Y-%m-%d %H:%M:%S") if r.at else "",
            r.attempt_id, r.candidate_id or "", r.reason, r.restart_number
        ])

    # Auto-adjust column widths for all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
