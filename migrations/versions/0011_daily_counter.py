"""Il contatore delle sfide del giorno finite.

Revision ID: 0011_daily_counter
Revises: 0010_quiz_monouso_punteggi

`daily_counter` e' una misura lato server, indipendente dal consenso: una riga per
`(gioco, data, punteggio)` con quante partite sono finite cosi'. Niente account,
sessione, IP o altro identificativo: solo contatori aggregati.
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_daily_counter"
down_revision = "0010_quiz_monouso_punteggi"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daily_counter",
        sa.Column("gioco", sa.Text(), primary_key=True),
        sa.Column("data", sa.Text(), primary_key=True),
        sa.Column("punteggio", sa.Integer(), primary_key=True),
        sa.Column("conteggio", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("daily_counter")
