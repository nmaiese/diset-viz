"""classifica quiz: tabella scores (con user_id nullable)

Revision ID: 0002_scores
Revises: 0001_pipeline_state
Create Date: 2026-07-31

Ricalca lo schema SQLite della classifica, più la colonna `user_id` (UUID
dell'account Supabase, nullable: gli anonimi restano). `created_at` è testo ISO
generato in Python, non un DEFAULT SQL, così non dipende da funzioni-tempo di
dialetto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_scores"
down_revision = "0001_pipeline_state"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("nickname", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("mode", "session_id", name="uq_scores_mode_session"),
        sa.CheckConstraint("mode IN ('compare','order')", name="ck_scores_mode"),
        sa.CheckConstraint("score >= 1 AND score <= 10000", name="ck_scores_range"),
    )
    op.create_index("idx_scores_rank", "scores", ["mode", "score", "created_at"])


def downgrade():
    op.drop_index("idx_scores_rank", table_name="scores")
    op.drop_table("scores")
