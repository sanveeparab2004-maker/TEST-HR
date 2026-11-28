import time
import logging
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from backend.app.core.config import settings

logger = logging.getLogger("assess.database")

# Fix Render/Heroku postgres:// URI schema if present
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")

engine_kwargs = {
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_engine(db_url, **engine_kwargs)

# On SQLite, enable foreign keys and concurrent WAL mode for zero lockups
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=15000")
        except Exception:
            pass
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for DB session with auto-close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection(retries: int = 3, backoff: float = 1.0) -> bool:
    """Neon cold-start resilient connection check."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection verified successfully.")
            return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
    return False


def run_advisory_lock_migration():
    """Run migrations with advisory lock on PostgreSQL to avoid race conditions, or ensure SQLite schema."""
    import backend.app.models.models  # Ensure all model tables are registered in Base.metadata
    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        with engine.begin() as conn:
            # Check attempts table
            try:
                cursor = conn.execute(text("PRAGMA table_info(attempts)"))
                existing_cols = {row[1] for row in cursor.fetchall()}
                missing_patches = {
                    "device_info": "TEXT",
                    "consent_at": "DATETIME",
                    "submitted_at": "DATETIME",
                    "restart_count": "SMALLINT DEFAULT 0",
                    "tab_switch_total": "SMALLINT DEFAULT 0",
                    "face_violation_total": "SMALLINT DEFAULT 0",
                    "sheet_synced": "BOOLEAN DEFAULT 0",
                    "sheet_synced_at": "DATETIME",
                    "score": "SMALLINT",
                    "percentage": "NUMERIC(5, 2)",
                    "band": "TEXT",
                    "section_scores": "TEXT",
                }
                for col, col_def in missing_patches.items():
                    if col not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE attempts ADD COLUMN {col} {col_def}"))
                        except Exception:
                            pass
            except Exception:
                pass

            # Check questions table
            try:
                cursor = conn.execute(text("PRAGMA table_info(questions)"))
                existing_q_cols = {row[1] for row in cursor.fetchall()}
                if "department" not in existing_q_cols:
                    try:
                        conn.execute(text("ALTER TABLE questions ADD COLUMN department VARCHAR(64) DEFAULT 'HR'"))
                    except Exception:
                        pass
            except Exception:
                pass

            # Check violations table
            try:
                cursor = conn.execute(text("PRAGMA table_info(violations)"))
                existing_v_cols = {row[1] for row in cursor.fetchall()}
                v_patches = {
                    "warning_number": "SMALLINT",
                    "action": "VARCHAR(20) DEFAULT 'WARNING'",
                    "review_status": "VARCHAR(20) DEFAULT 'PENDING'",
                    "reviewed_by": "TEXT",
                    "reviewed_at": "DATETIME",
                }
                for col, col_def in v_patches.items():
                    if col not in existing_v_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE violations ADD COLUMN {col} {col_def}"))
                        except Exception:
                            pass
            except Exception:
                pass
        return
    ADVISORY_LOCK_ID = 892374823
    try:
        with engine.connect() as conn:
            conn.execute(text(f"SELECT pg_advisory_lock({ADVISORY_LOCK_ID})"))
            logger.info("Acquired Postgres advisory lock for migrations.")
            # Lock will be released when connection closes or explicitly
            try:
                from alembic import command
                from alembic.config import Config
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                logger.info("Alembic migrations completed successfully.")
            finally:
                conn.execute(text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_ID})"))
                logger.info("Released Postgres advisory lock.")
    except Exception as e:
        logger.error(f"Migration error: {e}")
