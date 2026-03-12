"""add_profile_fields_to_users

Revision ID: a1b2c3d4e5f6
Revises: 37f7b52f5964
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "37f7b52f5964"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(length=128), nullable=True),
        schema="eagle",
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(length=128), nullable=True),
        schema="eagle",
    )
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=64), nullable=True),
        schema="eagle",
    )
    op.add_column(
        "users",
        sa.Column("language_code", sa.String(length=8), nullable=True),
        schema="eagle",
    )
    op.add_column(
        "users",
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        schema="eagle",
    )


def downgrade() -> None:
    op.drop_column("users", "photo_url", schema="eagle")
    op.drop_column("users", "language_code", schema="eagle")
    op.drop_column("users", "username", schema="eagle")
    op.drop_column("users", "last_name", schema="eagle")
    op.drop_column("users", "first_name", schema="eagle")