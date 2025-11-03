"""Add notification and push subscription tables

Revision ID: 0004_notifications
Revises: 0003_profiles_and_favorites
Create Date: 2025-10-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_notifications"
down_revision = "0003_profiles_and_favorites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("comparison", sa.String(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("lead_time_hours", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["site_id"], ["sites.site_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notification_id"),
        sa.UniqueConstraint(
            "user_id",
            "site_id",
            "metric",
            "comparison",
            "threshold",
            "lead_time_hours",
            name="uq_user_notification_rule",
        ),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
    op.create_index("ix_user_notifications_site_id", "user_notifications", ["site_id"])
    op.create_index("ix_user_notifications_notification_id", "user_notifications", ["notification_id"])

    op.create_table(
        "push_subscriptions",
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("client_info", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subscription_id"),
        sa.UniqueConstraint("endpoint", name="uq_push_subscription_endpoint"),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index("ix_push_subscriptions_subscription_id", "push_subscriptions", ["subscription_id"])

    op.create_table(
        "notification_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("delivery_status", sa.String(), nullable=False, server_default=sa.text("'queued'")),
        sa.ForeignKeyConstraint(["notification_id"], ["user_notifications.notification_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["push_subscriptions.subscription_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_notification_events_notification_id", "notification_events", ["notification_id"])
    op.create_index("ix_notification_events_subscription_id", "notification_events", ["subscription_id"])
    op.create_index("ix_notification_events_event_id", "notification_events", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_events_event_id", table_name="notification_events")
    op.drop_index("ix_notification_events_subscription_id", table_name="notification_events")
    op.drop_index("ix_notification_events_notification_id", table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index("ix_push_subscriptions_subscription_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

    op.drop_index("ix_user_notifications_notification_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_site_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
