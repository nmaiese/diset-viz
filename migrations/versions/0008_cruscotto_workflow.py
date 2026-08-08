"""cruscotto: una run e' un workflow, non un indicatore che attraversa stadi

Via le tre tabelle della catena editoriale autonoma, che e' stata ritirata
insieme a `pipeline_launch.py` e `pipeline_merge.py`: da allora non le scrive
piu' nessuno. Al loro posto le due che descrivono la catena che esiste, cioe'
un workflow con dentro N agenti.

Il `downgrade()` ricrea le tabelle vuote ma non le righe: il drop e'
irreversibile per la storia che c'e' dentro, che e' quella della catena
ritirata e che il modello nuovo non saprebbe leggere comunque.

Revision ID: 0008_cruscotto_workflow
Revises: 0007_pipeline_outcomes
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_cruscotto_workflow"
down_revision = "0007_pipeline_outcomes"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("pipeline_outcomes")
    op.drop_table("pipeline_tokens")
    op.drop_table("pipeline_activity")

    op.create_table(
        "pipeline_run",
        sa.Column("run_id", sa.Text(), primary_key=True),
        # --- battito ---
        sa.Column("avviata_il", sa.Text(), nullable=False, server_default=""),
        sa.Column("ultimo_battito", sa.Text(), nullable=False, server_default=""),
        sa.Column("fase_stimata", sa.Text(), nullable=False, server_default=""),
        sa.Column("agenti_visti", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sessione", sa.Text(), nullable=False, server_default=""),
        sa.Column("progetto", sa.Text(), nullable=False, server_default=""),
        # --- consuntivo ---
        sa.Column("workflow", sa.Text(), nullable=True),
        sa.Column("args", sa.Text(), nullable=True),
        sa.Column("stato", sa.Text(), nullable=True),
        sa.Column("durata_ms", sa.Integer(), nullable=True),
        sa.Column("fasi", sa.Text(), nullable=True),
        sa.Column("esito", sa.Text(), nullable=True),
        sa.Column("logs", sa.Text(), nullable=True),
        sa.Column("agenti", sa.Integer(), nullable=True),
        sa.Column("turni", sa.Integer(), nullable=True),
        sa.Column("tool", sa.Integer(), nullable=True),
        sa.Column("token_in", sa.Integer(), nullable=True),
        sa.Column("token_cache_w", sa.Integer(), nullable=True),
        sa.Column("token_cache_r", sa.Integer(), nullable=True),
        sa.Column("token_out", sa.Integer(), nullable=True),
        sa.Column("advisor_in", sa.Integer(), nullable=True),
        sa.Column("advisor_out", sa.Integer(), nullable=True),
        sa.Column("advisor_chiamate", sa.Integer(), nullable=True),
        sa.Column("costo", sa.Float(), nullable=True),
        sa.Column("costo_pavimento", sa.Integer(), nullable=True),
        sa.Column("consuntivo_il", sa.Text(), nullable=True),
    )

    op.create_table(
        "pipeline_agente",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("agent_id", sa.Text(), primary_key=True),
        # --- battito ---
        sa.Column("agent_type", sa.Text(), nullable=False, server_default=""),
        sa.Column("fase_stimata", sa.Text(), nullable=False, server_default=""),
        sa.Column("indicatore", sa.Text(), nullable=False, server_default=""),
        sa.Column("avviato_il", sa.Text(), nullable=False, server_default=""),
        sa.Column("chiuso_il", sa.Text(), nullable=False, server_default=""),
        sa.Column("stato_vivo", sa.String(8), nullable=False, server_default="aperto"),
        sa.Column("risultato", sa.Text(), nullable=False, server_default=""),
        # --- consuntivo ---
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("fase", sa.Text(), nullable=True),
        sa.Column("modello", sa.Text(), nullable=True),
        sa.Column("stato", sa.Text(), nullable=True),
        sa.Column("turni", sa.Integer(), nullable=True),
        sa.Column("tool", sa.Integer(), nullable=True),
        sa.Column("strumenti", sa.Text(), nullable=True),
        sa.Column("token_in", sa.Integer(), nullable=True),
        sa.Column("token_cache_w", sa.Integer(), nullable=True),
        sa.Column("token_cache_r", sa.Integer(), nullable=True),
        sa.Column("token_out", sa.Integer(), nullable=True),
        sa.Column("advisor_in", sa.Integer(), nullable=True),
        sa.Column("advisor_out", sa.Integer(), nullable=True),
        sa.Column("advisor_chiamate", sa.Integer(), nullable=True),
        sa.Column("costo", sa.Float(), nullable=True),
    )


def downgrade():
    op.drop_table("pipeline_agente")
    op.drop_table("pipeline_run")

    op.create_table(
        "pipeline_activity",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("kind", sa.String(8), nullable=False),
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
    op.create_table(
        "pipeline_tokens",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("indicator", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("role", sa.Text(), nullable=False, server_default=""),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
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
