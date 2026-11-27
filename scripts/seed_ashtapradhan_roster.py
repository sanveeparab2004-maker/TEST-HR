"""Seed and authorize the official candidate roster for the Ashtapradhan Assessment.

Loads from data/ashtapradhan_roster.xlsx and ensures:
1. Only authorized candidates in this list can take the Ashtapradhan Assessment.
2. Clears any prior test attempts or violations for these candidates for a clean fresh start.
3. Preserves Staff/Admin accounts (E-2606026, HR_ADMIN_01, HR_MONITOR_01, C-2606026).
"""
import os
import sys
import openpyxl

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.models import Roster, Attempt, Answer, Violation, Snapshot, Event, Restart, PendingSheetWrite


OFFICIAL_ASHTAPRADHAN_CANDIDATES = [
    {"code": "I-2607039", "name": "Nitin Appaso Shinde", "dept": "ASSESSMENT"},
    {"code": "I-2607003", "name": "Omkar Pravin Kadam", "dept": "ASSESSMENT"},
    {"code": "I-2608037", "name": "Manaswi Santosh Kanade", "dept": "ASSESSMENT"},
    {"code": "I-2608035", "name": "Avantika Khanderao Jadhav", "dept": "ASSESSMENT"},
    {"code": "I-2607034", "name": "Vaibhav Dilip Bongane", "dept": "ASSESSMENT"},
    {"code": "I-2607007", "name": "Vaibhav Bhagawan Jadhav", "dept": "ASSESSMENT"},
    {"code": "I-2609029", "name": "Shital Mahadev Jadhav", "dept": "ASSESSMENT"},
]


def load_candidates_from_excel(xlsx_path: str = "data/ashtapradhan_roster.xlsx"):
    candidates = []
    if os.path.exists(xlsx_path):
        try:
            wb = openpyxl.load_workbook(xlsx_path, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                # Look for employee code pattern (e.g. I-260...) and name
                non_empty = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if len(non_empty) >= 2:
                    code = None
                    name = None
                    for item in non_empty:
                        if item.upper().startswith("I-") or item.upper().startswith("E-") or item.upper().startswith("C-"):
                            code = item.upper()
                        elif not any(char.isdigit() for char in item) and len(item.split()) >= 2:
                            name = item
                    if code and name:
                        candidates.append({"code": code, "name": name, "dept": "ASSESSMENT"})
        except Exception as e:
            print(f"  [!] Notice reading Excel: {e}, using verified roster list.")

    # Fallback to verified official list if Excel parsing yielded fewer
    if len(candidates) < len(OFFICIAL_ASHTAPRADHAN_CANDIDATES):
        return OFFICIAL_ASHTAPRADHAN_CANDIDATES
    return candidates


def seed_ashtapradhan_roster():
    session = SessionLocal()
    try:
        candidates = load_candidates_from_excel()
        cand_codes = [c["code"] for c in candidates]

        print("=" * 60)
        print("SEEDING ASHTAPRADHAN OFFICIAL CANDIDATE ROSTER")
        print("=" * 60)
        print(f"Total authorized candidates found: {len(candidates)}")

        # Ensure attempts table columns exist on SQLite
        try:
            from sqlalchemy import text
            with session.connection() as conn:
                for col, col_type in [
                    ("restart_count", "SMALLINT DEFAULT 0"),
                    ("tab_switch_total", "SMALLINT DEFAULT 0"),
                    ("face_violation_total", "SMALLINT DEFAULT 0"),
                ]:
                    try:
                        conn.execute(text(f"ALTER TABLE attempts ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
        except Exception:
            pass

        # 1. Clear any prior test attempts for these candidates (guarantee fresh start)
        prior_attempts = session.query(Attempt).filter(Attempt.employee_code.in_(cand_codes)).all()
        if prior_attempts:
            att_ids = [a.id for a in prior_attempts]
            print(f"[*] Clearing {len(prior_attempts)} prior attempts for fresh exam start...")
            session.query(Answer).filter(Answer.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(Violation).filter(Violation.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(Snapshot).filter(Snapshot.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(Event).filter(Event.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(Restart).filter(Restart.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(PendingSheetWrite).filter(PendingSheetWrite.attempt_id.in_(att_ids)).delete(synchronize_session=False)
            session.query(Attempt).filter(Attempt.id.in_(att_ids)).delete(synchronize_session=False)
            session.commit()
            print("  ✓ Prior attempts wiped cleanly.")

        # 2. Add / Update each candidate in the official Roster
        for c in candidates:
            code = c["code"]
            name = c["name"]
            existing = session.query(Roster).filter_by(employee_code=code).first()
            if not existing:
                entry = Roster(
                    employee_code=code,
                    full_name=name,
                    department="ASSESSMENT",
                    role="CANDIDATE",
                    is_active=True
                )
                session.add(entry)
                print(f"  + Enrolled Candidate: {code} | {name}")
            else:
                existing.full_name = name
                existing.department = "ASSESSMENT"
                existing.role = "CANDIDATE"
                existing.is_active = True
                print(f"  ✓ Updated Candidate: {code} | {name}")

        # Ensure test candidate C-2606026 exists
        test_cand = session.query(Roster).filter_by(employee_code="C-2606026").first()
        if not test_cand:
            session.add(Roster(
                employee_code="C-2606026",
                full_name="Durvesh Parab",
                department="ASSESSMENT",
                role="CANDIDATE",
                is_active=True
            ))

        session.commit()
        print("=" * 60)
        print("[✓] Ashtapradhan Candidate Roster Successfully Configured.")
        print("=" * 60)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_ashtapradhan_roster()
