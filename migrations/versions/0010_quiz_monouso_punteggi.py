"""Round monouso del quiz e punteggi delle sfide del giorno.

Revision ID: 0010_quiz_monouso_punteggi
Revises: 0009_via_cruscotto

`quiz_answered` tiene i round gia' risposti, chiave `(sid, q)`: e' il round monouso e
vive nel DB perche' Cloud Run ha piu' istanze. `daily_scores` e' lo schema per le
sfide del giorno, una riga per `(auth_id, gioco, data)`.
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_quiz_monouso_punteggi"
down_revision = "0009_via_cruscotto"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_answered",
        sa.Column("sid", sa.Text(), primary_key=True),
        sa.Column("q", sa.Integer(), primary_key=True),
        sa.Column("answered_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_quiz_answered_at", "quiz_answered", ["answered_at"])
    op.create_table(
        "daily_scores",
        sa.Column("auth_id", sa.Text(), primary_key=True),
        sa.Column("gioco", sa.Text(), primary_key=True),
        sa.Column("data", sa.Text(), primary_key=True),
        sa.Column("punteggio", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("daily_scores")
    op.drop_index("idx_quiz_answered_at", table_name="quiz_answered")
    op.drop_table("quiz_answered")
