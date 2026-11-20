import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.models import Assessment


DEPARTMENTS = [
    {
        "code": "HR",
        "title": "CS CREATIVE SOLUTIONS – HR ASSESSMENT",
        "status": "OPEN",
        "duration_minutes": 60,
        "total_marks": 100,
        "marks_per_question": 1,
        "description": "Recruitment Planning, Sourcing, Operations, Excel MIS & Communication"
    },
    {
        "code": "CLAIM",
        "title": "CS CREATIVE SOLUTIONS – CLAIM ASSESSMENT",
        "status": "DRAFT",
        "duration_minutes": 60,
        "total_marks": 100,
        "marks_per_question": 1,
        "description": "Claims Adjudication, Verification, Policy Compliance & Investigation"
    },
    {
        "code": "TENDER",
        "title": "CS CREATIVE SOLUTIONS – TENDER ASSESSMENT",
        "status": "DRAFT",
        "duration_minutes": 60,
        "total_marks": 100,
        "marks_per_question": 1,
        "description": "Bidding Management, Tender Documentation, Evaluation & Vendor Relations"
    },
    {
        "code": "ADMIN",
        "title": "CS CREATIVE SOLUTIONS – ADMIN ASSESSMENT",
        "status": "DRAFT",
        "duration_minutes": 60,
        "total_marks": 100,
        "marks_per_question": 1,
        "description": "Office Operations, Facilities, General Administration & MIS"
    }
]


def seed_departments():
    db = SessionLocal()
    try:
        print("[*] Seeding Department Assessment tracks (HR, CLAIM, TENDER, ADMIN)...")
        for dept in DEPARTMENTS:
            existing = db.query(Assessment).filter(Assessment.title.ilike(f"%{dept['code']}%")).first()
            if not existing:
                new_a = Assessment(
                    title=dept["title"],
                    duration_minutes=dept["duration_minutes"],
                    total_marks=dept["total_marks"],
                    marks_per_question=dept["marks_per_question"],
                    status=dept["status"],
                    settings={
                        "department": dept["code"],
                        "description": dept["description"],
                        "max_warnings": 3,
                        "look_away_limit_seconds": 4,
                        "no_face_limit_seconds": 5,
                        "window_blur_limit_seconds": 2,
                        "data_retention_days": 90
                    }
                )
                db.add(new_a)
                print(f"  + Created assessment: {dept['title']} ({dept['code']})")
            else:
                existing.title = dept["title"]
                existing.marks_per_question = dept["marks_per_question"]
                st = dict(existing.settings or {})
                st["department"] = dept["code"]
                st["description"] = dept["description"]
                existing.settings = st
                print(f"  ✓ Updated assessment: {existing.title} (ID {existing.id})")
        db.commit()
        print("[✓] All department assessments ready.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_departments()
