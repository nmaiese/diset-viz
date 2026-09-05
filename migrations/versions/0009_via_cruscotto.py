"""Via il cruscotto della catena: `pipeline_run` e `pipeline_agente`.

Revision ID: 0009_via_cruscotto
Revises: 0008_cruscotto_workflow

Il cruscotto `/_pipeline` serviva la catena editoriale, che dal 5 settembre 2026 vive
nel repo `redazione-ai`. Il poller che scriveva il battito stava in `lab/`, tolto con la
PR 220: da allora la rotta era viva e non la scriveva nessuno. Qui cadono le due tabelle
che restavano.

`downgrade()` le ricrea con le stesse colonne di `0008_cruscotto_workflow`: i dati non
tornano, la forma si'. Nessun altro oggetto dipende da queste due tabelle.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_via_cruscotto"
down_revision = "0008_cruscotto_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("pipeline_agente")
    op.drop_table("pipeline_run")


def downgrade():
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
