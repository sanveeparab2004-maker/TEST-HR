from datetime import datetime, timezone
import io
import csv
from typing import Dict, List, Any, Tuple, Optional
import openpyxl
from backend.app.core.config import settings


TEMPLATE_COLUMNS = [
    "question_id", "department", "question_text", "option_a",
    "option_b", "option_c", "option_d", "correct_option", "marks"
]


def generate_sample_template_csv() -> str:
    """Generate a sample CSV template with instructions and valid sample rows."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_COLUMNS)
    # Add sample rows that sum to 100
    # Template: 100 questions of 1 mark each for HR and CLAIM
    for dept in ["HR", "CLAIM"]:
        for i in range(1, 101):
            writer.writerow([
                f"{dept}_{i:03d}",
                dept,
                f"Sample question {i} for {dept} department?",
                f"Option A text for Q{i}",
                f"Option B text for Q{i}",
                f"Option C text for Q{i}",
                f"Option D text for Q{i}",
                "A" if (i % 4 == 1) else ("B" if i % 4 == 2 else ("C" if i % 4 == 3 else "D")),
                1
            ])
    return output.getvalue()


def parse_and_validate_question_file(
    content_bytes: bytes,
    filename: str
) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, int]]:
    """Parse Excel or CSV bytes and validate all constraints.
    
    Returns:
        (valid_questions, error_messages, department_mark_totals)
    """
    rows = []
    errors = []

    # 1. Parse CSV or XLSX
    is_xlsx = filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls")
    if is_xlsx:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
            sheet = wb.active
            header_row = [str(cell.value or "").strip().lower() for cell in next(sheet.iter_rows(values_only=False))]
            # Map column index
            col_map = {name: idx for idx, name in enumerate(header_row)}
            missing_cols = [c for c in TEMPLATE_COLUMNS if c not in col_map]
            if missing_cols:
                return [], [f"Missing required columns in Excel: {', '.join(missing_cols)}"], {}

            row_idx = 1
            for row_cells in sheet.iter_rows(min_row=2, values_only=True):
                row_idx += 1
                if not any(row_cells):
                    continue
                row_dict = {c: str(row_cells[col_map[c]] if col_map[c] < len(row_cells) and row_cells[col_map[c]] is not None else "").strip() for c in TEMPLATE_COLUMNS}
                rows.append((row_idx, row_dict))
        except Exception as e:
            return [], [f"Failed to read Excel workbook: {str(e)}"], {}
    else:
        try:
            text = content_bytes.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            # Normalize headers
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames or []]
            missing_cols = [c for c in TEMPLATE_COLUMNS if c not in reader.fieldnames]
            if missing_cols:
                return [], [f"Missing required columns in CSV: {', '.join(missing_cols)}"], {}

            for idx, r in enumerate(reader, start=2):
                if not any(r.values()):
                    continue
                row_dict = {c: str(r.get(c, "") or "").strip() for c in TEMPLATE_COLUMNS}
                rows.append((idx, row_dict))
        except Exception as e:
            return [], [f"Failed to parse CSV file: {str(e)}"], {}

    if not rows:
        return [], ["The uploaded question file contains no question rows."], {}

    # 2. Row-by-Row Validation
    seen_ids = set()
    dept_marks: Dict[str, int] = {}
    valid_questions = []

    for row_num, r in rows:
        qid = r["question_id"]
        dept = r["department"].upper()
        stem = r["question_text"]
        opt_a = r["option_a"]
        opt_b = r["option_b"]
        opt_c = r["option_c"]
        opt_d = r["option_d"]
        correct = r["correct_option"].upper()
        marks_str = r["marks"]

        # Validate ID
        if not qid:
            errors.append(f"Row {row_num}: 'question_id' is empty.")
        elif qid in seen_ids:
            errors.append(f"Row {row_num}: Duplicate question_id '{qid}'.")
        seen_ids.add(qid)

        # Validate Department
        if not dept:
            errors.append(f"Row {row_num}: 'department' is empty.")

        # Validate Question Stem
        if not stem:
            errors.append(f"Row {row_num}: 'question_text' is blank.")

        # Validate Options
        if not opt_a or not opt_b or not opt_c or not opt_d:
            errors.append(f"Row {row_num}: All 4 options (A, B, C, D) must be non-blank.")

        # Validate Correct Option
        if correct not in ("A", "B", "C", "D"):
            # Check if correct_option matches option text exactly
            if correct.lower() == opt_a.lower():
                correct = "A"
            elif correct.lower() == opt_b.lower():
                correct = "B"
            elif correct.lower() == opt_c.lower():
                correct = "C"
            elif correct.lower() == opt_d.lower():
                correct = "D"
            else:
                errors.append(f"Row {row_num}: 'correct_option' must be 'A', 'B', 'C', or 'D' (found: '{r['correct_option']}').")

        # Validate Marks
        try:
            marks = int(marks_str)
            if marks <= 0:
                errors.append(f"Row {row_num}: 'marks' must be greater than 0.")
        except ValueError:
            errors.append(f"Row {row_num}: 'marks' must be a valid integer.")
            marks = 0

        # Accumulate marks per department (and ALL)
        dept_marks[dept] = dept_marks.get(dept, 0) + marks

        valid_questions.append({
            "question_id": qid,
            "department": dept,
            "stem": stem,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "correct_option": correct,
            "marks": marks
        })

    # 3. Department Marks Sum Validation (Must add up to exactly 100)
    # Questions marked "ALL" apply to every department
    common_marks = dept_marks.get("ALL", 0)
    for dept, total in dept_marks.items():
        if dept == "ALL":
            continue
        effective_total = total + common_marks
        if effective_total != settings.TOTAL_MARKS:
            errors.append(
                f"Department '{dept}' total marks equal {effective_total}, but must add up to exactly {settings.TOTAL_MARKS}."
            )

    if errors:
        return [], errors, dept_marks

    return valid_questions, [], dept_marks


def load_questions_into_db(db, questions_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """Saves validated questions into database and creates/links department assessments."""
    from backend.app.models.models import Assessment, Section, Question, Option
    from backend.app.services.sheets_service import queue_or_write_sheet

    # Group questions by department
    by_dept: Dict[str, List[Dict[str, Any]]] = {}
    common_questions = []
    for q in questions_list:
        dept = q["department"].upper()
        if dept == "ALL":
            common_questions.append(q)
        else:
            by_dept.setdefault(dept, []).append(q)

    # For each department, ensure assessment and insert questions
    dept_counts: Dict[str, int] = {}
    sheet_rows = []

    for dept, q_items in by_dept.items():
        all_for_dept = q_items + common_questions

        # Find or create assessment
        assessment = db.query(Assessment).filter(
            Assessment.settings.op("->>")("department") == dept
        ).first()

        if not assessment:
            assessment = Assessment(
                title=f"{dept} TEAM – PROFESSIONAL ASSESSMENT",
                duration_minutes=settings.EXAM_DURATION_MINUTES,
                total_marks=settings.TOTAL_MARKS,
                marks_per_question=2,
                negative_marking=(settings.NEGATIVE_MARKING > 0),
                status="OPEN",
                settings={"department": dept}
            )
            db.add(assessment)
            db.flush()

        # Find or create default section
        section = db.query(Section).filter_by(assessment_id=assessment.id).first()
        if not section:
            section = Section(
                assessment_id=assessment.id,
                name=f"{dept} Core Assessment",
                sort_order=1
            )
            db.add(section)
            db.flush()

        # Delete existing questions for this assessment to cleanly reload
        db.query(Question).filter_by(assessment_id=assessment.id).delete()
        db.flush()

        # Insert questions and options
        for idx, q_data in enumerate(all_for_dept, start=1):
            q_row = Question(
                assessment_id=assessment.id,
                section_id=section.id,
                source_number=idx,
                stem=q_data["stem"],
                marks=q_data["marks"],
                department=dept
            )
            db.add(q_row)
            db.flush()

            # Options A, B, C, D
            opts = [
                ("A", q_data["option_a"]),
                ("B", q_data["option_b"]),
                ("C", q_data["option_c"]),
                ("D", q_data["option_d"]),
            ]
            for label, text in opts:
                is_corr = (label == q_data["correct_option"])
                db.add(Option(
                    question_id=q_row.id,
                    label=label,
                    text=text,
                    is_correct=is_corr
                ))

            # Record for Sheet Question Bank tab
            sheet_rows.append([
                q_data["question_id"],
                dept,
                q_data["stem"],
                q_data["option_a"],
                q_data["option_b"],
                q_data["option_c"],
                q_data["option_d"],
                q_data["correct_option"],
                q_data["marks"]
            ])

        dept_counts[dept] = len(all_for_dept)

    db.commit()

    # Sync read-only Question Bank to Google Sheet
    if sheet_rows:
        queue_or_write_sheet(
            db=db,
            operation="sync_question_bank",
            idempotency_key=f"qbank_import_{len(sheet_rows)}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            payload={"rows": sheet_rows}
        )

    return dept_counts
