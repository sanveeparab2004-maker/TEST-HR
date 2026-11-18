import openpyxl
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import Roster, Attempt, Answer, Violation, Snapshot, Event, AuditLog
from backend.app.core.security import get_pin_hash


def load_real_roster_from_excel(excel_path: str = "data/hr_list.xlsx"):
    session = SessionLocal()
    try:
        print("[1/4] Purging dummy attempts, answers, violations, snapshots, and events...")
        session.query(Answer).delete(synchronize_session=False)
        session.query(Violation).delete(synchronize_session=False)
        session.query(Snapshot).delete(synchronize_session=False)
        session.query(Event).delete(synchronize_session=False)
        session.query(Attempt).delete(synchronize_session=False)
        session.query(AuditLog).delete(synchronize_session=False)
        session.query(Roster).delete(synchronize_session=False)
        session.commit()
        print("  ✓ Database cleared of all test and dummy data.")

        print("[2/4] Reading HR employee list from Excel:", excel_path)
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.active

        candidates_loaded = 0
        for r in range(2, sheet.max_row + 1):
            code = sheet.cell(row=r, column=2).value
            name = sheet.cell(row=r, column=4).value
            dept = sheet.cell(row=r, column=6).value
            desig = sheet.cell(row=r, column=7).value

            if code and name:
                code_clean = str(code).strip()
                name_clean = str(name).strip()
                dept_clean = str(dept or "HR Department").strip()
                desig_clean = str(desig or "").strip()
                full_dept = f"{dept_clean} - {desig_clean}" if desig_clean else dept_clean

                roster_entry = Roster(
                    employee_code=code_clean,
                    full_name=name_clean,
                    department=full_dept,
                    role="CANDIDATE",
                    pin_hash=None,
                    is_active=True
                )
                session.add(roster_entry)
                candidates_loaded += 1
                print(f"  + Added Candidate: {code_clean} | {name_clean} | {full_dept}")

        session.commit()
        print(f"  ✓ Total real candidates loaded from Excel: {candidates_loaded}")

        print("[3/4] Provisioning Staff and Administration Accounts...")
        # 1. Durvesh Parab (Admin & Proctoring Lead)
        durvesh_admin = Roster(
            employee_code="E-2606026",
            full_name="Durvesh Parab",
            department="HR Operations & Proctoring",
            role="ADMIN",
            pin_hash=get_pin_hash("123456"),
            is_active=True
        )
        session.add(durvesh_admin)

        # 2. Durvesh Parab Test Candidate Account
        durvesh_cand = Roster(
            employee_code="C-2606026",
            full_name="Durvesh Parab",
            department="HR Department",
            role="CANDIDATE",
            pin_hash=None,
            is_active=True
        )
        session.add(durvesh_cand)

        # 3. Standard backup Staff Monitor & Admin
        staff_monitor = Roster(
            employee_code="HR_MONITOR_01",
            full_name="Chief Exam Proctor",
            department="Staff Proctoring Desk",
            role="MONITOR",
            pin_hash=get_pin_hash("654321"),
            is_active=True
        )
        session.add(staff_monitor)

        staff_admin = Roster(
            employee_code="HR_ADMIN_01",
            full_name="Principal HR Administrator",
            department="Staff HR Administration",
            role="ADMIN",
            pin_hash=get_pin_hash("987123"),
            is_active=True
        )
        session.add(staff_admin)

        session.commit()
        print("  ✓ Staff Accounts provisioned successfully.")

        # Log system initialization audit entry
        session.add(AuditLog(
            actor="SYSTEM_INIT",
            action="LOAD_REAL_ROSTER",
            entity="roster",
            detail={"candidates_count": candidates_loaded, "source_file": excel_path}
        ))
        session.commit()

        print("[4/4] Verification check:")
        total_roster = session.query(Roster).count()
        total_candidates = session.query(Roster).filter_by(role="CANDIDATE").count()
        total_staff = session.query(Roster).filter(Roster.role.in_(["MONITOR", "ADMIN"])).count()
        print(f"  Total Roster: {total_roster} (Candidates: {total_candidates}, Staff: {total_staff})")
        print("  Ready for live assessment!")

    finally:
        session.close()


if __name__ == "__main__":
    load_real_roster_from_excel()
