"""account: tabella favorites (preferiti indicatore)

Revision ID: 0004_favorites
Revises: 0003_profiles
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_favorites"
down_revision = "0003_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "favorites",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("indicator_id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("favorites")
