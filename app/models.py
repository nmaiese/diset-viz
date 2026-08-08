"""I modelli ORM dello stato mutabile.

Un solo `Base` per tutte le tabelle mutabili (stato vivo della catena, e più
avanti classifica e profili). Le colonne ricalcano bit per bit lo schema SQLite
che questi dati avevano prima della migrazione a Postgres, così il passaggio è
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
    /api/auth/me, che aggiorna last_seen_at). `auth_id` è l'UUID di auth.users
    dal JWT verificato, mai dal body. email/nickname denormalizzati per comodità.
    Su tutte le tabelle account l'invariante è la stessa: si filtra su `auth_id`
    ricavato dal JWT, la RLS è difesa in profondità (il backend gira BYPASSRLS)."""

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
    """Aggregati di gioco per (utente, modalità), server-authoritative (Fase 5.2).
    Una riga per modalità ('compare', 'order', 'daily'). Rekey da player_id ad
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


class SavedComparison(Base):
    """Un confronto salvato da un utente (Fase 5.3): titolo + configurazione
    (indicatori, regioni, anni, tipo) come JSON di testo. Niente public_slug:
    nessuna condivisione, quindi nessuna superficie RLS sfruttabile. Servito solo
    dal backend. Invariante: auth_id dal JWT verificato."""

    __tablename__ = "saved_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auth_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Score(Base):
    """La classifica del quiz. Il punteggio salvato è sempre la miglior streak
    verificata di una sessione firmata (app/quiz_tokens.py): il client non manda
    mai un punteggio arbitrario, vedi app/views.py. `user_id` è l'UUID
    dell'account Supabase quando c'è un JWT valido, nullo per gli anonimi (il
    gioco resta anonimo per chi non si registra).

    `created_at` è una stringa ISO UTC con la Z finale, generata in Python: il
    confronto lessicografico su ISO è cronologico, quindi ordinamento e finestra
    settimanale non hanno bisogno di funzioni-tempo SQL (che divergono fra i
    dialetti). `detail` è JSON serializzato come testo, come prima."""

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
    """Lo stato vivo del cruscotto: una riga è un battito (`beat`) o una PR
    aperta (`pr`). La chiave è `beat:<run_id>` o `pr:<numero>`, come nello
    SQLite originale, così l'upsert idempotente resta sullo stesso perno."""

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
    parte perché i battiti scadono e si cancellano, il costo di una run è
    storia da tenere. Chiave = il `run_id` del ruolo, non del lanciatore."""

    __tablename__ = "pipeline_tokens"

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    indicator: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    role: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class PipelineOutcome(Base):
    """Lo stato di ciclo di vita di UN indicatore, come lo ha ricostruito
    l'agente al momento del merge, POSTato al sito perché il cruscotto sia
    aggiornato senza aspettare il redeploy dell'immagine.

    Durevole come `PipelineToken`, non un battito: non scade a 6h. Il dossier
    committato in git resta la verità e la storia; questa riga è un overlay che
    vive nella finestra fra 'fuso su master' e 'immagine deployatà, e la board
    lo ritira da sola quando il committato lo raggiunge (vedi
    `scripts/pipeline_monitor.py::_apply_outcomes`).

    Chiave = `indicator` (la forma-id del dossier: `651`, `dem:BIRTHRATE`,
    `bes:09PAE009-N25`), un solo stato corrente per indicatore, l'ultimo vince.
    Tipi larghi come le altre tabelle della catena: le strutture
    (`completed_stages`, `required_stages`, `flags`) sono JSON serializzato in
    `Text`, `published`/`verification_valid` sono interi nullable per tenere il
    tri-stato (1/0/None = ignoto), così il modello gira identico su SQLite
    (test/CI) e Postgres (produzione)."""

    __tablename__ = "pipeline_outcomes"

    indicator: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    at: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_commit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[str] = mapped_column(Text, nullable=False, default="")
    entered_at: Mapped[str] = mapped_column(Text, nullable=False, default="")
    completed_stages: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    required_stages: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    flags: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    published: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_valid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_eligible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
