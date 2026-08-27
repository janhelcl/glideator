"""Add Greifenburg alias for Emberger Alm.

Revision ID: 0015_emberger_greifenburg_alias
Revises: 0014_expand_site_aliases
Create Date: 2026-08-27

"""
from alembic import op


revision = "0015_emberger_greifenburg_alias"
down_revision = "0014_expand_site_aliases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, 'Greifenburg', 'greifenburg'
        FROM sites
        WHERE name = 'Emberger Alm'
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM site_aliases
        WHERE site_id IN (
            SELECT site_id FROM sites WHERE name = 'Emberger Alm'
        )
          AND alias_normalized = 'greifenburg'
        """
    )
