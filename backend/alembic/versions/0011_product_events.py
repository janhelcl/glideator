"""Add product analytics events

Revision ID: 0011_product_events
Revises: 0010_drop_feedback_contact_email
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa


revision = "0011_product_events"
down_revision = "0010_drop_feedback_contact_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
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
    op.create_index(
        op.f("ix_product_events_event_id"),
        "product_events",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_events_event_name"),
        "product_events",
        ["event_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_events_anonymous_id"),
        "product_events",
        ["anonymous_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_events_session_id"),
        "product_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_events_created_at"),
        "product_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_product_events_created_at"), table_name="product_events")
    op.drop_index(op.f("ix_product_events_session_id"), table_name="product_events")
    op.drop_index(op.f("ix_product_events_anonymous_id"), table_name="product_events")
    op.drop_index(op.f("ix_product_events_event_name"), table_name="product_events")
    op.drop_index(op.f("ix_product_events_event_id"), table_name="product_events")
    op.drop_table("product_events")
