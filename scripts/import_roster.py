"""CSV Roster Import Utility for HR Assessment Portal.

Features:
- Dry-run validation mode (prints row errors without writing)
- Idempotent upsert (updates existing, adds new)
- Normalization (whitespace stripped, uppercase employee_code)
- Role verification (CANDIDATE, MONITOR, ADMIN)
"""
import os
import sys
import csv
from typing import List, Dict, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, AuditLog


def validate_roster_csv(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Roster file not found at: {filepath}")

    rows = []
    errors = []
    seen_codes = set()

    with open(filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip().lower() for fn in (reader.fieldnames or [])]
        
        if "employee_code" not in fieldnames or "full_name" not in fieldnames:
            raise ValueError("CSV must contain 'employee_code' and 'full_name' columns")

        for row_idx, raw_row in enumerate(reader, start=2):
            normalized = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}
            emp_code = normalized.get("employee_code", "").strip().upper()
            full_name = normalized.get("full_name", "").strip()
            dept = normalized.get("department", "").strip() or None
            role = normalized.get("role", "CANDIDATE").strip().upper() or "CANDIDATE"

            if not emp_code:
                errors.append(f"Row {row_idx}: Empty employee_code")
                continue
            if not full_name:
                errors.append(f"Row {row_idx} ({emp_code}): Empty full_name")
                continue
            if role not in ("CANDIDATE", "MONITOR", "ADMIN"):
                errors.append(f"Row {row_idx} ({emp_code}): Invalid role '{role}' (must be CANDIDATE, MONITOR, or ADMIN)")
                continue

            if emp_code in seen_codes:
                errors.append(f"Row {row_idx} ({emp_code}): Duplicate employee_code in CSV")
                continue
            seen_codes.add(emp_code)

            rows.append({
                "employee_code": emp_code,
                "full_name": full_name,
                "department": dept,
                "role": role,
                "is_active": True
            })

    return rows, errors


def import_roster(filepath: str, dry_run: bool = False, actor: str = "CLI_ROSTER_IMPORT"):
    rows, errors = validate_roster_csv(filepath)

    print(f"\nRoster File: {filepath}")
    print(f"Validated Entries: {len(rows)}")
    print(f"Errors Found: {len(errors)}")

    if errors:
        print("\n--- VALIDATION ERRORS ---")
        for err in errors:
            print(f"  [X] {err}")
        if dry_run or len(rows) == 0:
            print("\nAborting import due to validation errors.")
            return False

    if dry_run:
        print("\n[DRY RUN] No database changes applied.")
        return len(errors) == 0

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        created_count = 0
        updated_count = 0

        for r in rows:
            entry = session.query(Roster).filter_by(employee_code=r["employee_code"]).first()
            if not entry:
                entry = Roster(
                    employee_code=r["employee_code"],
                    full_name=r["full_name"],
                    department=r["department"],
                    role=r["role"],
                    is_active=r["is_active"]
                )
                session.add(entry)
                created_count += 1
            else:
                entry.full_name = r["full_name"]
                entry.department = r["department"]
                entry.role = r["role"]
                entry.is_active = r["is_active"]
                updated_count += 1

        session.add(AuditLog(
            actor=actor,
            action="ROSTER_IMPORT",
            entity="roster",
            detail={"total_rows": len(rows), "created": created_count, "updated": updated_count}
        ))
        session.commit()
        print("\n--- IMPORT SUMMARY ---")
        print(f"Successfully Created: {created_count}")
        print(f"Successfully Updated: {updated_count}")
        print("Roster import completed successfully.")
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    csv_path = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    target_csv = csv_path[0] if csv_path else os.path.join("data", "sample_roster.csv")
    import_roster(target_csv, dry_run=dry)
