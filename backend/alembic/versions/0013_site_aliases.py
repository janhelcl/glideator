"""Add first-class site aliases.

Revision ID: 0013_site_aliases
Revises: 0012_bot_events
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa


revision = "0013_site_aliases"
down_revision = "0012_bot_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_aliases",
        sa.Column("alias_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("alias_normalized", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.site_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("alias_id"),
        sa.UniqueConstraint(
            "site_id",
            "alias_normalized",
            name="uq_site_alias_site_normalized",
        ),
    )
    op.create_index(
        op.f("ix_site_aliases_alias_id"),
        "site_aliases",
        ["alias_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_site_aliases_site_id"),
        "site_aliases",
        ["site_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_site_aliases_alias_normalized"),
        "site_aliases",
        ["alias_normalized"],
        unique=False,
    )

    # Seed only aliases that add semantics beyond accent/case normalization.
    # INSERT ... SELECT keeps fresh/empty databases valid if sites are seeded later.
    op.execute(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, 'Monte Grappa', 'monte grappa'
        FROM sites
        WHERE name = 'Bassano'
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, 'Bassano del Grappa', 'bassano del grappa'
        FROM sites
        WHERE name = 'Bassano'
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, 'Monte Valinis', 'monte valinis'
        FROM sites
        WHERE name = 'Meduno'
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, 'Valinis', 'valinis'
        FROM sites
        WHERE name = 'Meduno'
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_site_aliases_alias_normalized"), table_name="site_aliases")
    op.drop_index(op.f("ix_site_aliases_site_id"), table_name="site_aliases")
    op.drop_index(op.f("ix_site_aliases_alias_id"), table_name="site_aliases")
    op.drop_table("site_aliases")
