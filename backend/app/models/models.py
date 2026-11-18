from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, SmallInteger, BigInteger, String, Text, Boolean,
    DateTime, ForeignKey, Numeric, JSON, LargeBinary, CheckConstraint,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base, is_sqlite

SCHEMA_NAME = None if is_sqlite else "assess"


def schema_args(*constraints, **kwargs):
    args = list(constraints)
    table_kwargs = dict(kwargs)
    if SCHEMA_NAME:
        table_kwargs["schema"] = SCHEMA_NAME
    return (*args, table_kwargs) if table_kwargs else (*args,)


class Roster(Base):
    __tablename__ = "roster"
    __table_args__ = schema_args(
        CheckConstraint("role IN ('CANDIDATE', 'MONITOR', 'ADMIN')", name="roster_role_check")
    )

    employee_code = Column(String(64), primary_key=True)
    full_name = Column(Text, nullable=False)
    department = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="CANDIDATE")
    pin_hash = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    attempts = relationship("Attempt", back_populates="roster_entry")


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = schema_args(
        CheckConstraint("status IN ('DRAFT', 'OPEN', 'CLOSED')", name="assessment_status_check")
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    duration_minutes = Column(SmallInteger, nullable=False, default=60)
    total_marks = Column(SmallInteger, nullable=False, default=100)
    marks_per_question = Column(SmallInteger, nullable=False, default=2)
    negative_marking = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="DRAFT")
    opens_at = Column(DateTime(timezone=True), nullable=True)
    closes_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, nullable=False, default=dict)

    sections = relationship("Section", back_populates="assessment", cascade="all, delete-orphan", order_by="Section.sort_order")
    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="assessment")


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = schema_args()

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.assessments.id" if SCHEMA_NAME else "assessments.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    sort_order = Column(SmallInteger, nullable=False)

    assessment = relationship("Assessment", back_populates="sections")
    questions = relationship("Question", back_populates="section", cascade="all, delete-orphan", order_by="Question.source_number")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = schema_args()

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.assessments.id" if SCHEMA_NAME else "assessments.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.sections.id" if SCHEMA_NAME else "sections.id", ondelete="CASCADE"), nullable=False)
    source_number = Column(SmallInteger, nullable=False)
    stem = Column(Text, nullable=False)
    marks = Column(SmallInteger, nullable=False, default=2)

    assessment = relationship("Assessment", back_populates="questions")
    section = relationship("Section", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan", order_by="Option.label")


class Option(Base):
    __tablename__ = "options"
    __table_args__ = schema_args(
        *(
            [Index("one_correct_per_question", "question_id", unique=True, postgresql_where=(Column("is_correct") == True))]
            if not is_sqlite else []
        )
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.questions.id" if SCHEMA_NAME else "questions.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(1), nullable=False)  # A, B, C, D
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)

    question = relationship("Question", back_populates="options")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = schema_args(
        UniqueConstraint("assessment_id", "employee_code", name="uq_attempt_assessment_employee"),
        CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'AUTO_SUBMITTED', 'VOID')", name="attempt_status_check")
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.assessments.id" if SCHEMA_NAME else "assessments.id"), nullable=False)
    employee_code = Column(String(64), ForeignKey(f"{SCHEMA_NAME}.roster.employee_code" if SCHEMA_NAME else "roster.employee_code"), nullable=False)
    entered_name = Column(Text, nullable=False)
    device_token_hash = Column(Text, nullable=False)
    device_info = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)
    consent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="IN_PROGRESS")
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    question_order = Column(JSON, nullable=False)  # List[int] stored as JSON for portable support
    option_order = Column(JSON, nullable=False)    # Dict[str(qid), List[int]]
    warning_count = Column(SmallInteger, nullable=False, default=0)
    violation_count = Column(Integer, nullable=False, default=0)
    score = Column(SmallInteger, nullable=True)
    percentage = Column(Numeric(5, 2), nullable=True)
    band = Column(Text, nullable=True)
    section_scores = Column(JSON, nullable=True)

    assessment = relationship("Assessment", back_populates="attempts")
    roster_entry = relationship("Roster", back_populates="attempts")
    answers = relationship("Answer", back_populates="attempt", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="attempt", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = schema_args()

    attempt_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey(f"{SCHEMA_NAME}.attempts.id" if SCHEMA_NAME else "attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.questions.id" if SCHEMA_NAME else "questions.id"), primary_key=True)
    option_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.options.id" if SCHEMA_NAME else "options.id"), nullable=True)
    flagged = Column(Boolean, nullable=False, default=False)
    answered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    attempt = relationship("Attempt", back_populates="answers")
    question = relationship("Question")
    option = relationship("Option")


class Violation(Base):
    __tablename__ = "violations"
    __table_args__ = schema_args(
        CheckConstraint("review_status IN ('PENDING', 'DISMISSED', 'CONFIRMED')", name="violation_review_status_check")
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    attempt_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey(f"{SCHEMA_NAME}.attempts.id" if SCHEMA_NAME else "attempts.id", ondelete="CASCADE"), nullable=False)
    at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    kind = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)
    counted = Column(Boolean, nullable=False)
    warning_number = Column(SmallInteger, nullable=True)
    review_status = Column(String(20), nullable=False, default="PENDING")
    reviewed_by = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    attempt = relationship("Attempt", back_populates="violations")
    snapshot = relationship("Snapshot", uselist=False, back_populates="violation")


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = schema_args()

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    violation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey(f"{SCHEMA_NAME}.violations.id" if SCHEMA_NAME else "violations.id", ondelete="SET NULL"), nullable=True)
    attempt_id = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=False)
    jpeg = Column(LargeBinary, nullable=False)
    taken_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    violation = relationship("Violation", back_populates="snapshot")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = schema_args()

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    attempt_id = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    kind = Column(Text, nullable=True)
    detail = Column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = schema_args()

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    actor = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    entity = Column(Text, nullable=True)
    detail = Column(JSON, nullable=True)
