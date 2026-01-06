"""Add notified_forecasts table and improvement_threshold column

Revision ID: 0007_forecast_change_notifs
Revises: 0006_similar_dates
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_forecast_change_notifs"
down_revision = "0006_similar_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add improvement_threshold column to user_notifications
    op.add_column(
        "user_notifications",
        sa.Column(
            "improvement_threshold",
            sa.Float(),
            nullable=False,
            server_default=sa.text("15.0"),
        ),
    )

    # Create notified_forecasts table to track notification state per forecast date
    op.create_table(
        "notified_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("last_value", sa.Float(), nullable=False),
        sa.Column("last_event_type", sa.String(), nullable=False),
        sa.Column(
            "notified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["user_notifications.notification_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "forecast_date",
            name="uq_notified_forecast_rule_date",
        ),
    )
    op.create_index(
        "idx_notified_forecasts_lookup",
        "notified_forecasts",
        ["notification_id", "forecast_date"],
    )
    op.create_index(
        "idx_notified_forecasts_date",
        "notified_forecasts",
        ["forecast_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_notified_forecasts_date", table_name="notified_forecasts")
    op.drop_index("idx_notified_forecasts_lookup", table_name="notified_forecasts")
    op.drop_table("notified_forecasts")
    op.drop_column("user_notifications", "improvement_threshold")
