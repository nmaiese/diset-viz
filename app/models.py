"""I modelli ORM dello stato mutabile.

Un solo `Base` per tutte le tabelle mutabili (stato vivo della catena, e piu'
avanti classifica e profili). Le colonne ricalcano bit per bit lo schema SQLite
che questi dati avevano prima della migrazione a Postgres, cosi' il passaggio e'
uno swap di store e non un cambio di semantica: tipi larghi (TEXT/INTEGER),
nessuna estensione Postgres-only in queste tabelle, quindi lo stesso modello gira
identico su SQLite (test/CI) e su Postgres (produzione).
"""

from sqlalchemy import CheckConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Profile(Base):
    """L'account: una riga per utente Supabase, upsert al primo login (e a ogni
    /api/auth/me, che aggiorna last_seen_at). `auth_id` e' l'UUID di auth.users
    dal JWT verificato, mai dal body. email/nickname denormalizzati per comodita'.
    Su tutte le tabelle account l'invariante e' la stessa: si filtra su `auth_id`
    ricavato dal JWT, la RLS e' difesa in profondita' (il backend gira BYPASSRLS)."""

    __tablename__ = "profiles"

    auth_id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, default="")
    nickname: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_seen_at: Mapped[str] = mapped_column(Text, nullable=False)


class Favorite(Base):
    """Un indicatore messo tra i preferiti da un utente (Fase 5.1). Chiave =
    l'id pubblico dell'indicatore (`meta.id` / SPA `item.id`, es. "105",
    "bes:10AMB002"), lo stesso che /api/indicator/<id> accetta. Solo con login:
    non esistono preferiti anonimi. Invariante: `auth_id` dal JWT verificato."""

    __tablename__ = "favorites"

    auth_id: Mapped[str] = mapped_column(Text, primary_key=True)
    indicator_id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class PlayerStat(Base):
    """Aggregati di gioco per (utente, modalita'), server-authoritative (Fase 5.2).
    Una riga per modalita' ('compare', 'order', 'daily'). Rekey da player_id ad
    auth_id: le stesse statistiche del profilo leggero pre-Supabase, ora legate
    all'account. Invariante: auth_id dal JWT verificato."""

    __tablename__ = "player_stats"

    auth_id: Mapped[str] = mapped_column(Text, primary_key=True)
    mode: Mapped[str] = mapped_column(Text, primary_key=True)
    best_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rounds_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_daily_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_daily_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_played_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class DailyResult(Base):
    """Lo storico della Regione del giorno per utente (Fase 5.2): una riga per
    data, non sovrascrivibile (niente replay che gonfia i numeri). Alimenta la
    streak giornaliera."""

    __tablename__ = "daily_results"

    auth_id: Mapped[str] = mapped_column(Text, primary_key=True)
    puzzle_date: Mapped[str] = mapped_column(Text, primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    solved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Achievement(Base):
    """Gli achievement sbloccati da un utente (Fase 5.2). Solo gli sblocchi: le
    definizioni vivono nel catalogo in codice (app/achievements.py)."""

    __tablename__ = "achievements"

    auth_id: Mapped[str] = mapped_column(Text, primary_key=True)
    achievement_id: Mapped[str] = mapped_column(Text, primary_key=True)
    unlocked_at: Mapped[str] = mapped_column(Text, nullable=False)


class Score(Base):
    """La classifica del quiz. Il punteggio salvato e' sempre la miglior streak
    verificata di una sessione firmata (app/quiz_tokens.py): il client non manda
    mai un punteggio arbitrario, vedi app/views.py. `user_id` e' l'UUID
    dell'account Supabase quando c'e' un JWT valido, nullo per gli anonimi (il
    gioco resta anonimo per chi non si registra).

    `created_at` e' una stringa ISO UTC con la Z finale, generata in Python: il
    confronto lessicografico su ISO e' cronologico, quindi ordinamento e finestra
    settimanale non hanno bisogno di funzioni-tempo SQL (che divergono fra i
    dialetti). `detail` e' JSON serializzato come testo, come prima."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("mode", "session_id", name="uq_scores_mode_session"),
        Index("idx_scores_rank", "mode", "score", "created_at"),
        CheckConstraint("mode IN ('compare','order')", name="ck_scores_mode"),
        CheckConstraint("score >= 1 AND score <= 10000", name="ck_scores_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class PipelineActivity(Base):
    """Lo stato vivo del cruscotto: una riga e' un battito (`beat`) o una PR
    aperta (`pr`). La chiave e' `beat:<run_id>` o `pr:<numero>`, come nello
    SQLite originale, cosi' l'upsert idempotente resta sullo stesso perno."""

    __tablename__ = "pipeline_activity"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="")
    indicator: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    run_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ci: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mergeable: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class PipelineToken(Base):
    """Il consumo token per run: telemetria durevole, non un battito. Tabella a
    parte perche' i battiti scadono e si cancellano, il costo di una run e'
    storia da tenere. Chiave = il `run_id` del ruolo, non del lanciatore."""

    __tablename__ = "pipeline_tokens"

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    indicator: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    role: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
