"""Add deterioration_threshold column to user_notifications

Revision ID: 0008_deterioration_threshold
Revises: 0007_forecast_change_notifs
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008_deterioration_threshold"
down_revision = "0007_forecast_change_notifs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_notifications",
        sa.Column(
            "deterioration_threshold",
            sa.Float(),
            nullable=False,
            server_default=sa.text("15.0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_notifications", "deterioration_threshold")
