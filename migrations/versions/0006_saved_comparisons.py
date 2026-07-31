"""account: saved_comparisons (Fase 5.3)

Revision ID: 0006_saved_comparisons
Revises: 0005_stats_achievements
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_saved_comparisons"
down_revision = "0005_stats_achievements"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("auth_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_saved_comparisons_user", "saved_comparisons", ["auth_id", "updated_at"])


def downgrade():
    op.drop_index("idx_saved_comparisons_user", table_name="saved_comparisons")
    op.drop_table("saved_comparisons")
