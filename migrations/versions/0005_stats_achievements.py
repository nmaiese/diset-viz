"""account: player_stats + daily_results + achievements (Fase 5.2)

Revision ID: 0005_stats_achievements
Revises: 0004_favorites
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_stats_achievements"
down_revision = "0004_favorites"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "player_stats",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("mode", sa.Text(), primary_key=True),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rounds_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_daily_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_daily_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_played_at", sa.Text(), nullable=True),
    )
    op.create_table(
        "daily_results",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("puzzle_date", sa.Text(), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solved", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "achievements",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("achievement_id", sa.Text(), primary_key=True),
        sa.Column("unlocked_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("achievements")
    op.drop_table("daily_results")
    op.drop_table("player_stats")
