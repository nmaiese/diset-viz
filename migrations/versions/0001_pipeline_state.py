"""stato vivo della catena: pipeline_activity + pipeline_tokens

Revision ID: 0001_pipeline_state
Revises:
Create Date: 2026-07-31

Prima migrazione del backend mutabile. Ricalca lo schema SQLite che queste due
tabelle avevano prima: colonne larghe, nessun tipo Postgres-only, così la
semantica non cambia col dialetto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_pipeline_state"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pipeline_activity",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default=""),
        sa.Column("indicator", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("run_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("pr", sa.Integer(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=False, server_default=""),
        sa.Column("ci", sa.Text(), nullable=False, server_default=""),
        sa.Column("mergeable", sa.Text(), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_activity_kind", "pipeline_activity", ["kind", "updated_at"])
    op.create_table(
        "pipeline_tokens",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("indicator", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("role", sa.Text(), nullable=False, server_default=""),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("pipeline_tokens")
    op.drop_index("idx_activity_kind", table_name="pipeline_activity")
    op.drop_table("pipeline_activity")
