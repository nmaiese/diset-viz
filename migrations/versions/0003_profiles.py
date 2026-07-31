"""account: tabella profiles

Revision ID: 0003_profiles
Revises: 0002_scores
Create Date: 2026-07-31

L'account utente (Fase 5). Upsert al login. auth_id = UUID di auth.users.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_profiles"
down_revision = "0002_scores"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "profiles",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, server_default=""),
        sa.Column("nickname", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("profiles")
