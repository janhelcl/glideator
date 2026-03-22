"""Add feedback_submissions table

Revision ID: 0009_feedback_submissions
Revises: 0008_deterioration_threshold
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


revision = "0009_feedback_submissions"
down_revision = "0008_deterioration_threshold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feedback_submissions_id"),
        "feedback_submissions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feedback_submissions_user_id"),
        "feedback_submissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_submissions_user_id"), table_name="feedback_submissions")
    op.drop_index(op.f("ix_feedback_submissions_id"), table_name="feedback_submissions")
    op.drop_table("feedback_submissions")
