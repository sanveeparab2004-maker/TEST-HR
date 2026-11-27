"""Import and seed Ashtapradhan Assessment (अष्टप्रधान – संचालक कार्यालय मूल्यांकन).

Features:
- Total questions: 25
- Marks: 4 marks per question = 100 marks total
- Duration: 60 minutes
- Pass mark: 35
- Bilingual (Marathi & English)
- Stored under department track: ASSESSMENT / ASHTAPRADHAN
"""
import os
import sys
import csv
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.models import Assessment, Section, Question, Option


def load_ashtapradhan_questions(csv_path: str = "data/ashtapradhan_questions.csv") -> List[Dict[str, Any]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    questions = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q_num = int(row["source_number"])
            questions.append({
                "source_number": q_num,
                "section": row["section"].strip(),
                "stem": row["question_text"].strip(),
                "marks": int(row["marks"]),
                "correct_option": row["correct_option"].strip().upper(),
                "options": {
                    "A": row["option_a"].strip(),
                    "B": row["option_b"].strip(),
                    "C": row["option_c"].strip(),
                    "D": row["option_d"].strip(),
                }
            })

    if len(questions) != 25:
        raise ValueError(f"Expected 25 questions, got {len(questions)}")

    total_marks = sum(q["marks"] for q in questions)
    if total_marks != 100:
        raise ValueError(f"Expected 100 total marks, got {total_marks}")

    return questions


def seed_ashtapradhan_into_db(questions: List[Dict[str, Any]]):
    session = SessionLocal()
    try:
        # Check existing assessment by title or settings
        assessment = session.query(Assessment).filter(
            (Assessment.title.ilike("%अष्टप्रधान%")) |
            (Assessment.title.ilike("%ASHTAPRADHAN%"))
        ).first()

        if not assessment:
            # Check if an assessment with department setting "ASSESSMENT" exists
            all_a = session.query(Assessment).all()
            for a in all_a:
                if (a.settings or {}).get("department", "").upper() in ("ASSESSMENT", "ASHTAPRADHAN"):
                    assessment = a
                    break

        if not assessment:
            assessment = Assessment(
                title="CS CREATIVE SOLUTIONS – अष्टप्रधान संचालक कार्यालय मूल्यांकन",
                duration_minutes=60,
                total_marks=100,
                marks_per_question=4,
                status="OPEN",
                settings={
                    "department": "ASSESSMENT",
                    "short_code": "ASHTAPRADHAN",
                    "description": "CS Creative Solutions • अष्टप्रधान संचालक कार्यालय निवड व मूल्यांकन परीक्षा"
                }
            )
            session.add(assessment)
            session.flush()
        else:
            assessment.title = "CS CREATIVE SOLUTIONS – अष्टप्रधान संचालक कार्यालय मूल्यांकन"
            assessment.status = "OPEN"
            assessment.duration_minutes = 60
            assessment.total_marks = 100
            assessment.marks_per_question = 4
            st = dict(assessment.settings or {})
            st["department"] = "ASSESSMENT"
            st["short_code"] = "ASHTAPRADHAN"
            st["description"] = "CS Creative Solutions • अष्टप्रधान संचालक कार्यालय निवड व मूल्यांकन परीक्षा"
            assessment.settings = st
            session.flush()

        # Section lookup or creation
        section_lookup: Dict[str, Section] = {}
        # Keep original order of appearance
        ordered_sections = []
        for q in questions:
            if q["section"] not in ordered_sections:
                ordered_sections.append(q["section"])

        for idx, sec_name in enumerate(ordered_sections, start=1):
            sec_obj = session.query(Section).filter_by(assessment_id=assessment.id, name=sec_name).first()
            if not sec_obj:
                sec_obj = Section(assessment_id=assessment.id, name=sec_name, sort_order=idx)
                session.add(sec_obj)
                session.flush()
            else:
                sec_obj.sort_order = idx
                session.flush()
            section_lookup[sec_name] = sec_obj

        # Load 25 Questions & Options
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
                    marks=q_info["marks"],
                    department="ASSESSMENT"
                )
                session.add(q_obj)
                session.flush()
            else:
                q_obj.stem = q_info["stem"]
                q_obj.section_id = sec_obj.id
                q_obj.marks = q_info["marks"]
                q_obj.department = "ASSESSMENT"
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
        print("ASHTAPRADHAN ASSESSMENT DATABASE SEED REPORT")
        print("=" * 60)
        print(f"Assessment: {assessment.title} (ID: {assessment.id})")
        print(f"Status: {assessment.status}")
        print(f"Duration: {assessment.duration_minutes} Minutes")
        print(f"Total Marks: {assessment.total_marks} ({assessment.marks_per_question} marks/question)")
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
    csv_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "ashtapradhan_questions.csv")
    print(f"Loading Ashtapradhan Questions from {csv_file}...")
    questions = load_ashtapradhan_questions(csv_file)
    seed_ashtapradhan_into_db(questions)


if __name__ == "__main__":
    main()
