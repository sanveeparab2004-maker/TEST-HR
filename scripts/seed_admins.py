"""Seed or update initial Monitor and Admin accounts in the roster table."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.security import get_pin_hash
from backend.app.models.models import Roster, AuditLog


def seed_accounts():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Seed Monitor
        monitor = session.query(Roster).filter_by(employee_code=settings.DEFAULT_MONITOR_CODE).first()
        monitor_pin_hash = get_pin_hash(settings.DEFAULT_MONITOR_PIN)
        if not monitor:
            monitor = Roster(
                employee_code=settings.DEFAULT_MONITOR_CODE,
                full_name=settings.DEFAULT_MONITOR_NAME,
                department="HR Proctoring",
                role="MONITOR",
                pin_hash=monitor_pin_hash,
                is_active=True
            )
            session.add(monitor)
            session.add(AuditLog(
                actor="SYSTEM_SEED",
                action="CREATE_ACCOUNT",
                entity="roster",
                detail={"employee_code": monitor.employee_code, "role": "MONITOR"}
            ))
            print(f"Created Monitor Account: {settings.DEFAULT_MONITOR_CODE}")
        else:
            monitor.full_name = settings.DEFAULT_MONITOR_NAME
            monitor.pin_hash = monitor_pin_hash
            monitor.role = "MONITOR"
            monitor.is_active = True
            print(f"Updated Monitor Account: {settings.DEFAULT_MONITOR_CODE}")

        # Seed Admin
        admin = session.query(Roster).filter_by(employee_code=settings.DEFAULT_ADMIN_CODE).first()
        admin_pin_hash = get_pin_hash(settings.DEFAULT_ADMIN_PIN)
        if not admin:
            admin = Roster(
                employee_code=settings.DEFAULT_ADMIN_CODE,
                full_name=settings.DEFAULT_ADMIN_NAME,
                department="HR Operations",
                role="ADMIN",
                pin_hash=admin_pin_hash,
                is_active=True
            )
            session.add(admin)
            session.add(AuditLog(
                actor="SYSTEM_SEED",
                action="CREATE_ACCOUNT",
                entity="roster",
                detail={"employee_code": admin.employee_code, "role": "ADMIN"}
            ))
            print(f"Created Admin Account: {settings.DEFAULT_ADMIN_CODE}")
        else:
            admin.full_name = settings.DEFAULT_ADMIN_NAME
            admin.pin_hash = admin_pin_hash
            admin.role = "ADMIN"
            admin.is_active = True
            print(f"Updated Admin Account: {settings.DEFAULT_ADMIN_CODE}")

        session.commit()
        print("Initial Monitor and Admin accounts seeded successfully.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_accounts()
