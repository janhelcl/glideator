"""Add similar_dates table

Revision ID: 0006_similar_dates
Revises: 0005_scaled_features
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0006_similar_dates"
down_revision = "0005_scaled_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "similar_dates",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("past_date", sa.Date(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("forecast_9", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("forecast_12", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("forecast_15", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("gfs_forecast_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.site_id"]),
        sa.PrimaryKeyConstraint("site_id", "forecast_date", "past_date"),
    )
    op.create_index("idx_similar_dates_site_id", "similar_dates", ["site_id"])
    op.create_index("idx_similar_dates_forecast_date", "similar_dates", ["forecast_date"])


def downgrade() -> None:
    op.drop_index("idx_similar_dates_forecast_date", table_name="similar_dates")
    op.drop_index("idx_similar_dates_site_id", table_name="similar_dates")
    op.drop_table("similar_dates")

