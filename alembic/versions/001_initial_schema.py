"""Initial schema for assess schema and portal tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-17 14:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    schema = "assess" if is_pg else None

    if is_pg:
        op.execute("CREATE SCHEMA IF NOT EXISTS assess;")
        op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # 1. Roster
    op.create_table(
        'roster',
        sa.Column('employee_code', sa.String(64), primary_key=True),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('department', sa.Text(), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='CANDIDATE'),
        sa.Column('pin_hash', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.CheckConstraint("role IN ('CANDIDATE', 'MONITOR', 'ADMIN')", name='roster_role_check'),
        schema=schema
    )

    # 2. Assessments
    op.create_table(
        'assessments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('duration_minutes', sa.SmallInteger(), nullable=False, server_default='60'),
        sa.Column('total_marks', sa.SmallInteger(), nullable=False, server_default='100'),
        sa.Column('marks_per_question', sa.SmallInteger(), nullable=False, server_default='2'),
        sa.Column('negative_marking', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
        sa.Column('opens_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closes_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.CheckConstraint("status IN ('DRAFT', 'OPEN', 'CLOSED')", name='assessment_status_check'),
        schema=schema
    )

    # 3. Sections
    assessment_fk = f"{schema}.assessments.id" if schema else "assessments.id"
    op.create_table(
        'sections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('assessment_id', sa.Integer(), sa.ForeignKey(assessment_fk, ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.SmallInteger(), nullable=False),
        schema=schema
    )

    # 4. Questions
    section_fk = f"{schema}.sections.id" if schema else "sections.id"
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('assessment_id', sa.Integer(), sa.ForeignKey(assessment_fk, ondelete='CASCADE'), nullable=False),
        sa.Column('section_id', sa.Integer(), sa.ForeignKey(section_fk, ondelete='CASCADE'), nullable=False),
        sa.Column('source_number', sa.SmallInteger(), nullable=False),
        sa.Column('stem', sa.Text(), nullable=False),
        sa.Column('marks', sa.SmallInteger(), nullable=False, server_default='2'),
        schema=schema
    )

    # 5. Options
    question_fk = f"{schema}.questions.id" if schema else "questions.id"
    op.create_table(
        'options',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey(question_fk, ondelete='CASCADE'), nullable=False),
        sa.Column('label', sa.String(1), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        schema=schema
    )
    if is_pg:
        op.execute("CREATE UNIQUE INDEX one_correct_per_question ON assess.options(question_id) WHERE is_correct;")

    # 6. Attempts
    roster_fk = f"{schema}.roster.employee_code" if schema else "roster.employee_code"
    op.create_table(
        'attempts',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column('assessment_id', sa.Integer(), sa.ForeignKey(assessment_fk), nullable=False),
        sa.Column('employee_code', sa.String(64), sa.ForeignKey(roster_fk), nullable=False),
        sa.Column('entered_name', sa.Text(), nullable=False),
        sa.Column('device_token_hash', sa.Text(), nullable=False),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('ip', sa.String(45), nullable=True),
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('question_order', sa.JSON(), nullable=False),
        sa.Column('option_order', sa.JSON(), nullable=False),
        sa.Column('warning_count', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('violation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.SmallInteger(), nullable=True),
        sa.Column('percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('band', sa.Text(), nullable=True),
        sa.Column('section_scores', sa.JSON(), nullable=True),
        sa.UniqueConstraint('assessment_id', 'employee_code', name='uq_attempt_assessment_employee'),
        sa.CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'AUTO_SUBMITTED', 'VOID')", name='attempt_status_check'),
        schema=schema
    )

    # 7. Answers
    attempt_fk = f"{schema}.attempts.id" if schema else "attempts.id"
    option_fk = f"{schema}.options.id" if schema else "options.id"
    op.create_table(
        'answers',
        sa.Column('attempt_id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey(attempt_fk, ondelete='CASCADE'), primary_key=True),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey(question_fk), primary_key=True),
        sa.Column('option_id', sa.Integer(), sa.ForeignKey(option_fk), nullable=True),
        sa.Column('flagged', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        schema=schema
    )

    # 8. Violations
    op.create_table(
        'violations',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column('attempt_id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey(attempt_fk, ondelete='CASCADE'), nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('counted', sa.Boolean(), nullable=False),
        sa.Column('warning_number', sa.SmallInteger(), nullable=True),
        sa.Column('review_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("review_status IN ('PENDING', 'DISMISSED', 'CONFIRMED')", name='violation_review_status_check'),
        schema=schema
    )

    # 9. Snapshots
    violation_fk = f"{schema}.violations.id" if schema else "violations.id"
    op.create_table(
        'snapshots',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column('violation_id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), sa.ForeignKey(violation_fk, ondelete='SET NULL'), nullable=True),
        sa.Column('attempt_id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column('jpeg', sa.LargeBinary(), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        schema=schema
    )

    # 10. Events
    op.create_table(
        'events',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column('attempt_id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=True),
        sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('kind', sa.Text(), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        schema=schema
    )

    # 11. Audit Log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actor', sa.Text(), nullable=True),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('entity', sa.Text(), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        schema=schema
    )

    # Security Triggers for PostgreSQL
    if is_pg:
        # Trigger 1: Immutability of audit_log
        op.execute("""
        CREATE OR REPLACE FUNCTION assess.prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log table is append-only. UPDATE and DELETE are prohibited.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_audit_log_immutable
        BEFORE UPDATE OR DELETE ON assess.audit_log
        FOR EACH ROW EXECUTE FUNCTION assess.prevent_audit_log_modification();
        """)

        # Trigger 2: Prevent DELETE on violations
        op.execute("""
        CREATE OR REPLACE FUNCTION assess.prevent_violation_deletion()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'violations records cannot be deleted. Use review_status to dismiss or confirm.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_violations_no_delete
        BEFORE DELETE ON assess.violations
        FOR EACH ROW EXECUTE FUNCTION assess.prevent_violation_deletion();
        """)

        # Trigger 3: Prevent answers/score modification after attempt leaves IN_PROGRESS
        op.execute("""
        CREATE OR REPLACE FUNCTION assess.prevent_post_submission_answers_change()
        RETURNS TRIGGER AS $$
        DECLARE
            att_status TEXT;
        BEGIN
            SELECT status INTO att_status FROM assess.attempts WHERE id = NEW.attempt_id;
            IF att_status <> 'IN_PROGRESS' THEN
                RAISE EXCEPTION 'Cannot modify answers for attempt % that is already %', NEW.attempt_id, att_status;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_answers_lock_on_submit
        BEFORE INSERT OR UPDATE ON assess.answers
        FOR EACH ROW EXECUTE FUNCTION assess.prevent_post_submission_answers_change();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    schema = "assess" if is_pg else None

    if is_pg:
        op.execute("DROP TRIGGER IF EXISTS trg_answers_lock_on_submit ON assess.answers;")
        op.execute("DROP FUNCTION IF EXISTS assess.prevent_post_submission_answers_change();")
        op.execute("DROP TRIGGER IF EXISTS trg_violations_no_delete ON assess.violations;")
        op.execute("DROP FUNCTION IF EXISTS assess.prevent_violation_deletion();")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON assess.audit_log;")
        op.execute("DROP FUNCTION IF EXISTS assess.prevent_audit_log_modification();")

    op.drop_table('audit_log', schema=schema)
    op.drop_table('events', schema=schema)
    op.drop_table('snapshots', schema=schema)
    op.drop_table('violations', schema=schema)
    op.drop_table('answers', schema=schema)
    op.drop_table('attempts', schema=schema)
    op.drop_table('options', schema=schema)
    op.drop_table('questions', schema=schema)
    op.drop_table('sections', schema=schema)
    op.drop_table('assessments', schema=schema)
    op.drop_table('roster', schema=schema)

    if is_pg:
        op.execute("DROP SCHEMA IF EXISTS assess CASCADE;")
