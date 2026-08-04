"""pipeline: outcomes (overlay di stato vivo, senza deploy)

Revision ID: 0007_pipeline_outcomes
Revises: 0006_saved_comparisons
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_pipeline_outcomes"
down_revision = "0006_saved_comparisons"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pipeline_outcomes",
        sa.Column("indicator", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("at", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_commit", sa.Text(), nullable=False, server_default=""),
        sa.Column("state", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.Text(), nullable=False, server_default=""),
        sa.Column("entered_at", sa.Text(), nullable=False, server_default=""),
        sa.Column("completed_stages", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("required_stages", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("flags", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("published", sa.Integer(), nullable=True),
        sa.Column("verification_valid", sa.Integer(), nullable=True),
        sa.Column("score_eligible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("pipeline_outcomes")
