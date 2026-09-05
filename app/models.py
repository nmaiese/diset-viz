"""I modelli ORM dello stato mutabile.

Un solo `Base` per tutte le tabelle mutabili (stato vivo della catena, e più
avanti classifica e profili). Le colonne ricalcano bit per bit lo schema SQLite
che questi dati avevano prima della migrazione a Postgres, così il passaggio è
uno swap di store e non un cambio di semantica: tipi larghi (TEXT/INTEGER),
nessuna estensione Postgres-only in queste tabelle, quindi lo stesso modello gira
identico su SQLite (test/CI) e su Postgres (produzione).
"""

from sqlalchemy import CheckConstraint, Float, Index, Integer, String, Text, UniqueConstraint
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


class PipelineRun(Base):
    """Una run della catena, che adesso vuol dire **un workflow**.

    Le colonne stanno in due gruppi che non si toccano mai, ed è la cosa
    importante di questa tabella. Il **battito** (il poller che stava in `lab/`, tolto il 5 settembre 2026, che
    legge i trascritti mentre girano) scrive il primo gruppo e non conosce i
    token, perché il workflow non li conosce. Il **consuntivo** (lo stesso
    lettore, quando vede comparire `<runId>.json`) scrive il secondo e non
    tocca il primo. Così un consuntivo ripetuto, o arrivato in ritardo, non
    può cancellare quello che il vivo aveva già registrato.

    `costo_pavimento` non è un vezzo: un trascritto reale ha registrato
    `output_tokens: 2` sulla richiesta che restituiva una bozza intera, quindi
    ogni totale è un **pavimento**, e a dirlo deve essere la riga, non
    l'etichetta di una pagina che qualcuno può riscrivere.

    Tipi larghi come le altre tabelle mutabili (TEXT/INTEGER, strutture in JSON
    serializzato), così il modello gira identico su SQLite (test/CI) e su
    Postgres (produzione)."""

    __tablename__ = "pipeline_run"

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)

    # --- scritte solo dal battito ---
    avviata_il: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ultimo_battito: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fase_stimata: Mapped[str] = mapped_column(Text, nullable=False, default="")
    agenti_visti: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sessione: Mapped[str] = mapped_column(Text, nullable=False, default="")
    progetto: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # --- scritte solo dal consuntivo, nulle finché la run non è finita ---
    # `workflow` e `args` sono qui e non fra i campi del battito perché dal vivo
    # non esistono: il nome del workflow compare solo in `<runId>.json`.
    workflow: Mapped[str | None] = mapped_column(Text, nullable=True)
    args: Mapped[str | None] = mapped_column(Text, nullable=True)
    stato: Mapped[str | None] = mapped_column(Text, nullable=True)
    durata_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fasi: Mapped[str | None] = mapped_column(Text, nullable=True)
    esito: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    agenti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turni: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cache_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cache_r: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_chiamate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    costo: Mapped[float | None] = mapped_column(Float, nullable=True)
    costo_pavimento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consuntivo_il: Mapped[str | None] = mapped_column(Text, nullable=True)


class PipelineAgente(Base):
    """Un agente dentro una run, con la stessa spaccatura in due gruppi.

    Dal vivo si sa il `agent_type` (sta in `agent-<id>.meta.json`), da che
    indicatore lavora (si legge nel prompt) e il **valore di ritorno completo**
    quando chiude (`journal.jsonl`). Non si sa la `label` né la fase: quelle
    stanno solo in `<runId>.json`, che il runtime scrive a run finita. Per
    questo il vivo porta `fase_stimata`, derivata dal tipo di agente, e il
    consuntivo porta `fase` e `label`, che sono la verità: due colonne, non una
    che si sovrascrive.

    `risultato` è JSON troncato: la bozza di un articolo intero non deve
    riempire una riga di cruscotto."""

    __tablename__ = "pipeline_agente"

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agent_id: Mapped[str] = mapped_column(Text, primary_key=True)

    # --- scritte solo dal battito ---
    agent_type: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fase_stimata: Mapped[str] = mapped_column(Text, nullable=False, default="")
    indicatore: Mapped[str] = mapped_column(Text, nullable=False, default="")
    avviato_il: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chiuso_il: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stato_vivo: Mapped[str] = mapped_column(String(8), nullable=False, default="aperto")
    risultato: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # --- scritte solo dal consuntivo ---
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    fase: Mapped[str | None] = mapped_column(Text, nullable=True)
    modello: Mapped[str | None] = mapped_column(Text, nullable=True)
    stato: Mapped[str | None] = mapped_column(Text, nullable=True)
    turni: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strumenti: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cache_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cache_r: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_chiamate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    costo: Mapped[float | None] = mapped_column(Float, nullable=True)
