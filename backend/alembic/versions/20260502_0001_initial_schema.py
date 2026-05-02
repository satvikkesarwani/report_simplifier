"""initial schema

Revision ID: 20260502_0001
Revises:
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=128), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("structured_data", sa.Text(), nullable=True),
        sa.Column("simplified_output", sa.Text(), nullable=True),
        sa.Column("processing_result", sa.Text(), nullable=True),
        sa.Column("evaluation", sa.Text(), nullable=True),
        sa.Column("abnormal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("readability_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
        sa.Column("processed_at", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"], unique=False)

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(length=128), nullable=False),
        sa.Column("comprehension_score", sa.Integer(), nullable=True),
        sa.Column("usefulness_score", sa.Integer(), nullable=True),
        sa.Column("highlighting_score", sa.Integer(), nullable=True),
        sa.Column("recommendation_score", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
    )
    op.create_index("ix_feedback_report_id", "feedback", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_report_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
