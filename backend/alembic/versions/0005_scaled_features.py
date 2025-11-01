"""Add scaled_features table

Revision ID: 0005_scaled_features
Revises: 0004_notifications
Create Date: 2025-10-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005_scaled_features"
down_revision = "0004_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scaled_features",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("features", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.site_id"]),
        sa.PrimaryKeyConstraint("site_id", "date"),
    )
    op.create_index("idx_scaled_features_date", "scaled_features", ["date"])


def downgrade() -> None:
    op.drop_index("idx_scaled_features_date", table_name="scaled_features")
    op.drop_table("scaled_features")

