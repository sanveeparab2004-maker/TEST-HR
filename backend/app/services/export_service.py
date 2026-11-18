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
