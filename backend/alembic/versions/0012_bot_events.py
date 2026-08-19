"""Add bot analytics events

Revision ID: 0012_bot_events
Revises: 0011_product_events
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa


revision = "0012_bot_events"
down_revision = "0011_product_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("bot_name", sa.String(length=80), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("anonymous_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(op.f("ix_bot_events_event_id"), "bot_events", ["event_id"], unique=False)
    op.create_index(op.f("ix_bot_events_bot_name"), "bot_events", ["bot_name"], unique=False)
    op.create_index(op.f("ix_bot_events_event_name"), "bot_events", ["event_name"], unique=False)
    op.create_index(op.f("ix_bot_events_anonymous_id"), "bot_events", ["anonymous_id"], unique=False)
    op.create_index(op.f("ix_bot_events_session_id"), "bot_events", ["session_id"], unique=False)
    op.create_index(op.f("ix_bot_events_created_at"), "bot_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bot_events_created_at"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_session_id"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_anonymous_id"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_event_name"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_bot_name"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_event_id"), table_name="bot_events")
    op.drop_table("bot_events")
