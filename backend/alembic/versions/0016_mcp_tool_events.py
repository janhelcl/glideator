"""Add MCP tool usage analytics

Revision ID: 0016_mcp_tool_events
Revises: 0015_emberger_greifenburg_alias
Create Date: 2026-08-28

"""
from alembic import op
import sqlalchemy as sa


revision = "0016_mcp_tool_events"
down_revision = "0015_emberger_greifenburg_alias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_tool_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_type", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(op.f("ix_mcp_tool_events_event_id"), "mcp_tool_events", ["event_id"], unique=False)
    op.create_index(op.f("ix_mcp_tool_events_tool_name"), "mcp_tool_events", ["tool_name"], unique=False)
    op.create_index(op.f("ix_mcp_tool_events_success"), "mcp_tool_events", ["success"], unique=False)
    op.create_index(op.f("ix_mcp_tool_events_created_at"), "mcp_tool_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mcp_tool_events_created_at"), table_name="mcp_tool_events")
    op.drop_index(op.f("ix_mcp_tool_events_success"), table_name="mcp_tool_events")
    op.drop_index(op.f("ix_mcp_tool_events_tool_name"), table_name="mcp_tool_events")
    op.drop_index(op.f("ix_mcp_tool_events_event_id"), table_name="mcp_tool_events")
    op.drop_table("mcp_tool_events")
