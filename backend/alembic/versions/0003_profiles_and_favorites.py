"""Add user_profiles and user_favorites

Revision ID: 0003_profiles_and_favorites
Revises: 0002_add_users
Create Date: 2025-09-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_profiles_and_favorites'
down_revision = '0002_add_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('home_lat', sa.Float(), nullable=True),
        sa.Column('home_lon', sa.Float(), nullable=True),
        sa.Column('preferred_metric', sa.String(), nullable=False, server_default=sa.text("'XC0'")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('user_id')
    )

    op.create_table(
        'user_favorites',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id']),
        sa.PrimaryKeyConstraint('user_id', 'site_id')
    )
    op.create_index('ix_user_favorites_user_id', 'user_favorites', ['user_id'])
    op.create_index('ix_user_favorites_site_id', 'user_favorites', ['site_id'])


def downgrade() -> None:
    op.drop_index('ix_user_favorites_site_id', table_name='user_favorites')
    op.drop_index('ix_user_favorites_user_id', table_name='user_favorites')
    op.drop_table('user_favorites')
    op.drop_table('user_profiles')


