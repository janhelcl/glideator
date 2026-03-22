"""Remove contact_email from feedback_submissions

Revision ID: 0010_drop_feedback_contact_email
Revises: 0009_feedback_submissions
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


revision = "0010_drop_feedback_contact_email"
down_revision = "0009_feedback_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("feedback_submissions", "contact_email")


def downgrade() -> None:
    op.add_column(
        "feedback_submissions",
        sa.Column("contact_email", sa.String(), nullable=True),
    )
