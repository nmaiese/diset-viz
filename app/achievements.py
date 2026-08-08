"""Catalogo achievement e valutazione server-side (Fase 5.2).

Il catalogo è dichiarativo e vive nel codice (`CATALOG`): ogni voce ha un
criterio, una funzione pura sugli aggregati di `player_stats.stats_map`. Il DB
conserva solo gli sblocchi (tabella `achievements`), non le definizioni: aggiungere
o ritoccare un traguardo è codice, senza migrazioni.

Raccolto dal branch pre-Supabase e ri-chiavato da player_id ad auth_id, sopra
l'ORM. Solo con login: le stats anonime stanno in localStorage e il server non le
vede, quindi non c'è un secondo percorso di valutazione non fidato.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app import player_stats
from app.db import session_scope
from app.models import Achievement


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quiz_correct(stats):
    return stats["compare"]["correct"] + stats["order"]["correct"] + stats["daily"]["wins"]


def _total_rounds(stats):
    return (stats["compare"]["rounds_played"] + stats["order"]["rounds_played"]
            + stats["daily"]["games_played"])


def _played_all(stats):
    return (stats["compare"]["rounds_played"] > 0
            and stats["order"]["rounds_played"] > 0
            and stats["daily"]["games_played"] > 0)


# id, icona (emoji), titolo, descrizione, criterio(stats_map) -> bool.
# L'ordine è quello di visualizzazione nella vetrina del profilo.
CATALOG = [
    {"id": "first_correct", "icon": "🎯", "title": "Battesimo del fuoco",
     "description": "La tua prima risposta giusta.",
     "criterion": lambda s: _quiz_correct(s) >= 1},
    {"id": "compare_10", "icon": "🔥", "title": "In serie",
     "description": "Serie da 10 in Chi è maggiore?",
     "criterion": lambda s: s["compare"]["best_streak"] >= 10},
    {"id": "compare_25", "icon": "⚡", "title": "Imbattibile",
     "description": "Serie da 25 in Chi è maggiore?",
     "criterion": lambda s: s["compare"]["best_streak"] >= 25},
    {"id": "order_first", "icon": "🧩", "title": "Ordine perfetto",
     "description": "Il tuo primo ordinamento senza errori.",
     "criterion": lambda s: s["order"]["best_streak"] >= 1},
    {"id": "order_10", "icon": "📊", "title": "Metodico",
     "description": "10 ordinamenti perfetti di fila.",
     "criterion": lambda s: s["order"]["best_streak"] >= 10},
    {"id": "daily_solver", "icon": "🗺️", "title": "Cartografo",
     "description": "Prima Regione del giorno indovinata.",
     "criterion": lambda s: s["daily"]["wins"] >= 1},
    {"id": "daily_streak_7", "icon": "📅", "title": "Costante",
     "description": "7 sfide del giorno risolte di fila.",
     "criterion": lambda s: s["daily"]["max_daily_streak"] >= 7},
    {"id": "all_rounder", "icon": "🎖️", "title": "Tuttologo",
     "description": "Giocati tutti e tre i giochi.",
     "criterion": _played_all},
    {"id": "veteran_50", "icon": "🏛️", "title": "Veterano",
     "description": "50 round giocati in totale.",
     "criterion": lambda s: _total_rounds(s) >= 50},
]


def _public(item, unlocked=False, unlocked_at=None):
    return {"id": item["id"], "icon": item["icon"], "title": item["title"],
            "description": item["description"], "unlocked": unlocked, "unlocked_at": unlocked_at}


def unlocked_map(auth_id):
    """{achievement_id: unlocked_at} degli achievement già sbloccati."""
    if not auth_id:
        return {}
    with session_scope() as s:
        rows = s.execute(
            select(Achievement.achievement_id, Achievement.unlocked_at)
            .where(Achievement.auth_id == auth_id)).all()
    return {aid: at for aid, at in rows}


def evaluate(auth_id):
    """Registra gli achievement appena raggiunti e li restituisce (voci
    pubbliche). Idempotente: uno già sbloccato non si ripropone. Tollerante:
    se il DB non risponde, nessuno sblocco (la risposta di gioco non deve cadere)."""
    if not auth_id:
        return []
    try:
        stats = player_stats.stats_map(auth_id)
        already = unlocked_map(auth_id)
        newly = [item for item in CATALOG
                 if item["id"] not in already and item["criterion"](stats)]
        if not newly:
            return []
        now = _now_iso()
        with session_scope() as s:
            for item in newly:
                if s.get(Achievement, {"auth_id": auth_id, "achievement_id": item["id"]}) is None:
                    s.add(Achievement(auth_id=auth_id, achievement_id=item["id"], unlocked_at=now))
        return [_public(item, unlocked=True) for item in newly]
    except Exception:  # noqa: BLE001
        return []


def list_for(auth_id):
    """Intero catalogo con lo stato sblocco, per la vetrina (mostra anche quelli
    da conquistare)."""
    unlocked = unlocked_map(auth_id)
    return [_public(item, item["id"] in unlocked, unlocked.get(item["id"])) for item in CATALOG]
