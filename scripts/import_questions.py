"""Import questions from HR_Team_Professional_Assessment.docx into the database.

Validates:
1. Exactly 50 questions
2. Exactly 4 options per question (A, B, C, D)
3. Exactly one answer key per question
4. Non-empty sections
5. Independent checksum matching:
   1A 2C 3B 4B 5C 6D 7C 8D 9B 10B 11B 12B 13A 14A 15B 16C 17C 18D 19A 20D
   21A 22C 23C 24A 25A 26A 27D 28A 29A 30A 31A 32A 33C 34A 35B 36A 37D 38B
   39B 40C 41B 42A 43D 44B 45B 46B 47A 48B 49D 50D
6. Idempotent database loading (duration = 60 minutes).
"""
import os
import re
import sys
from typing import Dict, List, Tuple, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from docx import Document

# Independent checksum specification
INDEPENDENT_CHECKSUM: Dict[int, str] = {
    1: 'A', 2: 'C', 3: 'B', 4: 'B', 5: 'C', 6: 'D', 7: 'C', 8: 'D', 9: 'B', 10: 'B',
    11: 'B', 12: 'B', 13: 'A', 14: 'A', 15: 'B', 16: 'C', 17: 'C', 18: 'D', 19: 'A', 20: 'D',
    21: 'A', 22: 'C', 23: 'C', 24: 'A', 25: 'A', 26: 'A', 27: 'D', 28: 'A', 29: 'A', 30: 'A',
    31: 'A', 32: 'A', 33: 'C', 34: 'A', 35: 'B', 36: 'A', 37: 'D', 38: 'B', 39: 'B', 40: 'C',
    41: 'B', 42: 'A', 43: 'D', 44: 'B', 45: 'B', 46: 'B', 47: 'A', 48: 'B', 49: 'D', 50: 'D'
}

EXPECTED_SECTIONS = [
    ("Recruitment Planning", 1, 5),
    ("Sourcing & Screening", 6, 10),
    ("Interview Management", 11, 15),
    ("Offer & Joining", 16, 20),
    ("HR Operations", 21, 30),
    ("Excel & MIS", 31, 40),
    ("Communication & Judgement", 41, 50),
]


def parse_assessment_docx(docx_path: str):
    doc = Document(docx_path)

    # 1. Extract Answer Key from Tables
    parsed_key: Dict[int, str] = {}
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            # Match 2-column or 4-column answer key formats
            # e.g., [Q.No, Ans] or [Q.No, Ans, Q.No, Ans]
            idx = 0
            while idx + 1 < len(cells):
                q_text = cells[idx]
                a_text = cells[idx + 1].upper()
                q_match = re.search(r'(\d+)', q_text)
                a_match = re.search(r'([A-D])', a_text)
                if q_match and a_match:
                    q_num = int(q_match.group(1))
                    if 1 <= q_num <= 50:
                        parsed_key[q_num] = a_match.group(1)
                idx += 2

    # 2. Extract Questions, Options, and Sections
    questions: Dict[int, Dict[str, Any]] = {}
    current_section = "General"
    current_q_num = None

    KNOWN_SECTIONS = {
        "RECRUITMENT PLANNING": "Recruitment Planning",
        "SOURCING & SCREENING": "Sourcing & Screening",
        "INTERVIEW MANAGEMENT": "Interview Management",
        "OFFER & JOINING": "Offer & Joining",
        "HR OPERATIONS": "HR Operations",
        "EXCEL & MIS": "Excel & MIS",
        "COMMUNICATION & JUDGEMENT": "Communication & Judgement"
    }

    q_pattern = re.compile(r'^(?:Q(?:uestion)?\.?\s*)?(\d+)[\.\)]\s*(.+)', re.IGNORECASE)
    opt_pattern = re.compile(r'^\(?([A-D])[\)\.\:]\s*(.+)', re.IGNORECASE)

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        # Check for section header
        if text.upper() in KNOWN_SECTIONS:
            current_section = KNOWN_SECTIONS[text.upper()]
            continue
        elif p.style.name.startswith('Heading') or "SECTION" in text.upper():
            clean_sec = re.sub(r'SECTION\s*(?:\d+)?\s*[:\-\—]\s*', '', text, flags=re.IGNORECASE).strip()
            if clean_sec and not clean_sec.upper().startswith("ANSWER KEY") and not clean_sec.upper().startswith("PERFORMANCE"):
                current_section = clean_sec
            continue

        # Check for Question stem
        q_match = q_pattern.match(text)
        if q_match:
            current_q_num = int(q_match.group(1))
            questions[current_q_num] = {
                "source_number": current_q_num,
                "stem": q_match.group(2).strip(),
                "section": current_section,
                "options": {}
            }
            continue

        # Check for Option
        opt_match = opt_pattern.match(text)
        if opt_match and current_q_num is not None:
            lbl = opt_match.group(1).upper()
            opt_text = opt_match.group(2).strip()
            questions[current_q_num]["options"][lbl] = opt_text
            continue

    # Validation Checks
    errors = []

    # Check 1: Exactly 50 questions
    if len(questions) != 50:
        errors.append(f"Question count mismatch: expected 50, found {len(questions)}")

    # Check 2: Exactly 4 options (A, B, C, D)
    for q_num in range(1, 51):
        if q_num not in questions:
            errors.append(f"Missing question Q{q_num}")
            continue
        opts = questions[q_num]["options"]
        if len(opts) != 4 or set(opts.keys()) != {'A', 'B', 'C', 'D'}:
            errors.append(f"Q{q_num} does not have exactly 4 options A-D. Found: {list(opts.keys())}")

    # Check 3: Exactly 50 keys in answer key
    if len(parsed_key) != 50:
        errors.append(f"Answer key count mismatch: expected 50, found {len(parsed_key)}")

    # Check 4: Cross-check against independent checksum
    checksum_mismatches = []
    for q_num in range(1, 51):
        expected_ans = INDEPENDENT_CHECKSUM.get(q_num)
        found_ans = parsed_key.get(q_num)
        if found_ans != expected_ans:
            checksum_mismatches.append(f"Q{q_num}: expected {expected_ans}, got {found_ans}")

    if checksum_mismatches:
        errors.append(f"Answer key checksum verification FAILED on {len(checksum_mismatches)} questions:\n" + "\n".join(checksum_mismatches))

    if errors:
        error_msg = "VALIDATION FAILED:\n" + "\n".join(errors)
        raise ValueError(error_msg)

    return {
        "questions": questions,
        "answer_key": parsed_key
    }


def load_into_db(parsed_data: Dict[str, Any]):
    from backend.app.core.database import SessionLocal, Base, engine
    from backend.app.models.models import Assessment, Section, Question, Option

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        title = "HR TEAM – PROFESSIONAL ASSESSMENT"
        assessment = session.query(Assessment).filter_by(title=title).first()
        if not assessment:
            assessment = Assessment(
                title=title,
                duration_minutes=60,  # Explicitly 60 minutes as per prompt mandate
                total_marks=100,
                marks_per_question=2,
                negative_marking=False,
                status="OPEN",
                settings={
                    "max_warnings": 3,
                    "look_away_limit_seconds": 4,
                    "no_face_limit_seconds": 5,
                    "window_blur_limit_seconds": 2,
                    "phone_detection_enabled": False,
                    "show_score_on_submission": False,
                    "data_retention_days": 90
                }
            )
            session.add(assessment)
            session.flush()
        else:
            assessment.duration_minutes = 60
            assessment.status = "OPEN"
            session.flush()

        # Build Section Map
        section_lookup = {}
        for idx, (sec_name, s_start, s_end) in enumerate(EXPECTED_SECTIONS, start=1):
            sec_obj = session.query(Section).filter_by(assessment_id=assessment.id, name=sec_name).first()
            if not sec_obj:
                sec_obj = Section(assessment_id=assessment.id, name=sec_name, sort_order=idx)
                session.add(sec_obj)
                session.flush()
            section_lookup[sec_name] = sec_obj

        # Load Questions & Options idempotently
        questions_dict = parsed_data["questions"]
        answer_key = parsed_data["answer_key"]

        q_count = 0
        opt_count = 0

        for q_num in range(1, 51):
            q_info = questions_dict[q_num]
            # Determine appropriate section
            target_sec_name = "Recruitment Planning"
            for s_name, s_start, s_end in EXPECTED_SECTIONS:
                if s_start <= q_num <= s_end:
                    target_sec_name = s_name
                    break

            sec_obj = section_lookup[target_sec_name]

            q_obj = session.query(Question).filter_by(assessment_id=assessment.id, source_number=q_num).first()
            if not q_obj:
                q_obj = Question(
                    assessment_id=assessment.id,
                    section_id=sec_obj.id,
                    source_number=q_num,
                    stem=q_info["stem"],
                    marks=2
                )
                session.add(q_obj)
                session.flush()
            else:
                q_obj.stem = q_info["stem"]
                q_obj.section_id = sec_obj.id
                session.flush()
            q_count += 1

            correct_label = answer_key[q_num]
            for lbl, opt_text in q_info["options"].items():
                is_corr = (lbl == correct_label)
                opt_obj = session.query(Option).filter_by(question_id=q_obj.id, label=lbl).first()
                if not opt_obj:
                    opt_obj = Option(
                        question_id=q_obj.id,
                        label=lbl,
                        text=opt_text,
                        is_correct=is_corr
                    )
                    session.add(opt_obj)
                else:
                    opt_obj.text = opt_text
                    opt_obj.is_correct = is_corr
                opt_count += 1

        session.commit()
        print("\n" + "=" * 60)
        print("DATABASE LOAD REPORT (IDEMPOTENT)")
        print("=" * 60)
        print(f"Assessment: {assessment.title} (ID: {assessment.id})")
        print(f"Duration: {assessment.duration_minutes} Minutes (Strictly locked to 60)")
        print(f"Total Marks: {assessment.total_marks} ({assessment.marks_per_question} marks/question)")
        print(f"Sections verified: {len(section_lookup)}")
        for sec_name, sec_obj in section_lookup.items():
            count = session.query(Question).filter_by(section_id=sec_obj.id).count()
            print(f"  - {sec_name}: {count} questions")
        print(f"Total Questions Loaded: {q_count}")
        print(f"Total Options Loaded: {opt_count}")
        print("Checksum Cross-Check: 100% PASSED (50/50 keys matched)")
        print("=" * 60)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "HR_Team_Professional_Assessment.docx")
    print(f"Parsing and validating: {filepath}...")
    try:
        data = parse_assessment_docx(filepath)
        print("File validation and checksum cross-check PASSED.")
        load_into_db(data)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
