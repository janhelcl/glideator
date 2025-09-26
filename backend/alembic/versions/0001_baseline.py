"""Baseline for existing models (sites, predictions, forecasts, flight_stats, spots, sites_info, site_tags)

Revision ID: 0001_baseline
Revises: 
Create Date: 2025-09-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sites',
        sa.Column('site_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('altitude', sa.Integer(), nullable=False),
        sa.Column('lat_gfs', sa.Float(), nullable=False),
        sa.Column('lon_gfs', sa.Float(), nullable=False),
    )
    op.create_index('ix_sites_name', 'sites', ['name'], unique=True)
    op.create_index('ix_sites_site_id', 'sites', ['site_id'])

    op.create_table(
        'predictions',
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('computed_at', sa.DateTime(), nullable=False),
        sa.Column('gfs_forecast_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id']),
        sa.PrimaryKeyConstraint('site_id', 'date', 'metric')
    )

    op.create_table(
        'forecasts',
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('computed_at', sa.DateTime(), nullable=False),
        sa.Column('gfs_forecast_at', sa.DateTime(), nullable=False),
        sa.Column('lat_gfs', sa.Float(), nullable=False),
        sa.Column('lon_gfs', sa.Float(), nullable=False),
        sa.Column('forecast_9', sa.JSON(), nullable=False),
        sa.Column('forecast_12', sa.JSON(), nullable=False),
        sa.Column('forecast_15', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('date', 'lat_gfs', 'lon_gfs')
    )

    op.create_table(
        'flight_stats',
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('avg_days_over_0', sa.Float(), nullable=False),
        sa.Column('avg_days_over_10', sa.Float(), nullable=False),
        sa.Column('avg_days_over_20', sa.Float(), nullable=False),
        sa.Column('avg_days_over_30', sa.Float(), nullable=False),
        sa.Column('avg_days_over_40', sa.Float(), nullable=False),
        sa.Column('avg_days_over_50', sa.Float(), nullable=False),
        sa.Column('avg_days_over_60', sa.Float(), nullable=False),
        sa.Column('avg_days_over_70', sa.Float(), nullable=False),
        sa.Column('avg_days_over_80', sa.Float(), nullable=False),
        sa.Column('avg_days_over_90', sa.Float(), nullable=False),
        sa.Column('avg_days_over_100', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id']),
        sa.PrimaryKeyConstraint('site_id', 'month')
    )

    op.create_table(
        'spots',
        sa.Column('spot_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('altitude', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('wind_direction', sa.String(), nullable=True),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id'])
    )

    op.create_table(
        'sites_info',
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('site_name', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('html', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id']),
        sa.PrimaryKeyConstraint('site_id')
    )

    op.create_table(
        'site_tags',
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id']),
        sa.PrimaryKeyConstraint('site_id', 'tag')
    )


def downgrade() -> None:
    op.drop_table('site_tags')
    op.drop_table('sites_info')
    op.drop_table('spots')
    op.drop_table('flight_stats')
    op.drop_table('forecasts')
    op.drop_table('predictions')
    op.drop_index('ix_sites_site_id', table_name='sites')
    op.drop_index('ix_sites_name', table_name='sites')
    op.drop_table('sites')


