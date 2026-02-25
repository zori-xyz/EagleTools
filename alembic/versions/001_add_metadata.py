"""add_metadata_to_jobs

Revision ID: 001_metadata
Revises:
Create Date: 2026-02-12 00:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '001_metadata'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые колонки в таблицу jobs
    op.add_column('jobs', sa.Column('title', sa.String(length=512), nullable=True))
    op.add_column('jobs', sa.Column('source_url', sa.String(length=2048), nullable=True))
    op.add_column('jobs', sa.Column('size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('jobs', sa.Column('extractor', sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column('jobs', 'extractor')
    op.drop_column('jobs', 'size_bytes')
    op.drop_column('jobs', 'source_url')
    op.drop_column('jobs', 'title')