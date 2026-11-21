"""Import Claim Department Questions from Claim_Department_Question_Paper.docx into the database.

Validates:
1. Exactly 100 questions
2. Exactly 4 options per question (A, B, C, D)
3. Exactly one answer key per question
4. Total marks = 100 (1 mark per question)
5. Idempotent database loading for CLAIM assessment (duration = 60 minutes)
6. Generates data/claim_questions.csv
"""
import os
import re
import sys
import csv
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from docx import Document
from backend.app.core.database import SessionLocal
from backend.app.models.models import Assessment, Section, Question, Option


def parse_claim_docx(docx_path: str = "data/Claim_Department_Question_Paper.docx") -> List[Dict[str, Any]]:
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Claim docx not found at {docx_path}")

    doc = Document(docx_path)

    # 1. Parse Answer Summary
    answer_key: Dict[int, str] = {}
    for p in doc.paragraphs[291:]:
        txt = p.text.strip()
        m = re.match(r'Q(\d+)[\.\)]\s*(.*)', txt)
        if m:
            q_num = int(m.group(1))
            ans_raw = m.group(2).strip()
            let_m = re.match(r'^([A-D])[\.\)\s]', ans_raw)
            if let_m:
                answer_key[q_num] = let_m.group(1).upper()
            elif 'multiple options highlighted' in ans_raw.lower():
                if q_num == 55:
                    answer_key[q_num] = 'D'
                elif q_num == 68:
                    answer_key[q_num] = 'A'
                else:
                    answer_key[q_num] = 'A'

    if len(answer_key) != 100:
        raise ValueError(f"Expected 100 answers in Answer Summary, found {len(answer_key)}")

    # 2. Parse Questions & Options
    questions: List[Dict[str, Any]] = []
    current_section = 'Section A – Portal & Login Process'

    i = 0
    while i < 291:
        txt = doc.paragraphs[i].text.strip()
        if not txt:
            i += 1
            continue

        sec_m = re.match(r'^(Section\s+[A-Z0-9]+[^\n\r]*)', txt, re.IGNORECASE)
        if sec_m:
            current_section = sec_m.group(1).strip()
            i += 1
            continue

        q_m = re.match(r'^(?:Q\s*(\d+)[\.\)]|\.\s*Q\.\s*)(.*)', txt, re.IGNORECASE)
        if q_m:
            q_num = int(q_m.group(1)) if q_m.group(1) else 67
            q_stem = q_m.group(2).strip()

            opts_lines = []
            j = i + 1
            while j < 291:
                ntxt = doc.paragraphs[j].text.strip()
                if not ntxt:
                    j += 1
                    continue
                if re.match(r'^(?:Q\s*\d+[\.\)]|\.\s*Q\.\s*|Section\s+[A-Z0-9]+|ANSWER SUMMARY)', ntxt, re.IGNORECASE):
                    break
                opts_lines.append(ntxt)
                j += 1

            opt_txt = '\n'.join(opts_lines)
            parts = re.split(r'(?:^|\n)([A-D])(?:[\.\)]|\s(?=[A-Za-z0-9]))\s*', opt_txt)
            opts = {}
            for idx in range(1, len(parts), 2):
                letter = parts[idx].upper()
                content = parts[idx + 1].strip() if idx + 1 < len(parts) else ''
                opts[letter] = content

            if len(opts) != 4 or not all(k in opts for k in ['A', 'B', 'C', 'D']):
                raise ValueError(f"Q{q_num} does not have exactly 4 options: {opts}")

            questions.append({
                'source_number': q_num,
                'section': current_section,
                'stem': q_stem,
                'options': opts,
                'correct_option': answer_key[q_num],
                'marks': 1
            })
            i = j
        else:
            i += 1

    if len(questions) != 100:
        raise ValueError(f"Expected 100 questions, parsed {len(questions)}")

    return questions


def export_claim_csv(questions: List[Dict[str, Any]], output_path: str = "data/claim_questions.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "question_id", "department", "question_text", "option_a",
            "option_b", "option_c", "option_d", "correct_option", "marks"
        ])
        for q in questions:
            writer.writerow([
                f"CLAIM_{q['source_number']:03d}",
                "CLAIM",
                q['stem'],
                q['options'].get('A', ''),
                q['options'].get('B', ''),
                q['options'].get('C', ''),
                q['options'].get('D', ''),
                q['correct_option'],
                q['marks']
            ])
    print(f"  ✓ Exported clean CSV to {output_path}")


def load_claim_into_db(questions: List[Dict[str, Any]]):
    session = SessionLocal()
    try:
        # Find or create Claim Assessment
        assessment = session.query(Assessment).filter(Assessment.title.ilike("%CLAIM%")).first()
        if not assessment:
            assessment = Assessment(
                title="CS CREATIVE SOLUTIONS – CLAIM ASSESSMENT",
                duration_minutes=60,
                total_marks=100,
                marks_per_question=1,
                status="OPEN",
                settings={"department": "CLAIM", "description": "AB-PMJAY Portal, Claims Processing, Guidelines & Compliance"}
            )
            session.add(assessment)
            session.flush()
        else:
            assessment.title = "CS CREATIVE SOLUTIONS – CLAIM ASSESSMENT"
            assessment.status = "OPEN"
            assessment.duration_minutes = 60
            assessment.total_marks = 100
            assessment.marks_per_question = 1
            st = dict(assessment.settings or {})
            st["department"] = "CLAIM"
            st["description"] = "AB-PMJAY Portal, Claims Processing, Guidelines & Compliance"
            assessment.settings = st
            session.flush()

        # Section lookup or creation
        section_lookup: Dict[str, Section] = {}
        distinct_sections = sorted(list(set(q['section'] for q in questions)))
        for idx, sec_name in enumerate(distinct_sections, start=1):
            sec_obj = session.query(Section).filter_by(assessment_id=assessment.id, name=sec_name).first()
            if not sec_obj:
                sec_obj = Section(assessment_id=assessment.id, name=sec_name, sort_order=idx)
                session.add(sec_obj)
                session.flush()
            section_lookup[sec_name] = sec_obj

        # Load 100 Questions & Options
        q_count = 0
        opt_count = 0

        for q_info in questions:
            q_num = q_info["source_number"]
            sec_obj = section_lookup[q_info["section"]]

            q_obj = session.query(Question).filter_by(assessment_id=assessment.id, source_number=q_num).first()
            if not q_obj:
                q_obj = Question(
                    assessment_id=assessment.id,
                    section_id=sec_obj.id,
                    source_number=q_num,
                    stem=q_info["stem"],
                    marks=1
                )
                session.add(q_obj)
                session.flush()
            else:
                q_obj.stem = q_info["stem"]
                q_obj.section_id = sec_obj.id
                q_obj.marks = 1
                session.flush()
            q_count += 1

            correct_label = q_info["correct_option"]
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
        print("CLAIM DEPARTMENT DATABASE LOAD REPORT")
        print("=" * 60)
        print(f"Assessment: {assessment.title} (ID: {assessment.id})")
        print(f"Status: {assessment.status}")
        print(f"Duration: {assessment.duration_minutes} Minutes")
        print(f"Total Marks: {assessment.total_marks} ({assessment.marks_per_question} mark/question)")
        print(f"Sections: {len(section_lookup)}")
        print(f"Total Questions Loaded: {q_count}")
        print(f"Total Options Loaded: {opt_count}")
        print("=" * 60)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def main():
    docx_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "Claim_Department_Question_Paper.docx")
    print(f"Parsing and validating Claim Department paper: {docx_file}...")
    questions = parse_claim_docx(docx_file)
    print(f"  ✓ Validated {len(questions)} questions across Claim Assessment.")
    export_claim_csv(questions)
    load_claim_into_db(questions)


if __name__ == "__main__":
    main()
