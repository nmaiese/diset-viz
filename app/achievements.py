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
from app.models import Achievement, DailyResult, DailyScore

# Le quattro sfide del giorno. `indovina` sta in `daily_results`, le altre in
# `daily_scores` (una riga per account, gioco e data).
GIOCHI_DEL_GIORNO = ("indovina", "provincia", "compare", "order")
GIORNI_FEDELE = 30


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


def _giorni_del_giro(auth_id):
    """Le date in cui l'account ha chiuso la sfida del giorno di tutti e quattro
    i giochi. Indovina conta se risolta, la provincia se indovinata al livello
    "tutta Italia" (`provincia`: il livello "della regione" scrive
    `provincia_regione` e non conta, perche' svela la regione del livello
    difficile), Chi è maggiore? e Ordina se la partita è stata giocata fino in fondo."""
    with session_scope() as s:
        indovina = set(s.execute(select(DailyResult.puzzle_date).where(
            DailyResult.auth_id == auth_id, DailyResult.solved == 1)).scalars())
        righe = s.execute(select(DailyScore.gioco, DailyScore.data, DailyScore.punteggio)
                          .where(DailyScore.auth_id == auth_id)).all()
    per_gioco = {"indovina": indovina, "provincia": set(), "compare": set(), "order": set()}
    for gioco, data, punteggio in righe:
        if gioco == "provincia" and punteggio < 1:
            continue
        if gioco in per_gioco:
            per_gioco[gioco].add(data)
    return set.intersection(*per_gioco.values())


def _provincia_indovinata(auth_id):
    """Solo il livello difficile ("tutta Italia"), gioco `provincia`."""
    with session_scope() as s:
        return s.execute(select(DailyScore.data).where(
            DailyScore.auth_id == auth_id, DailyScore.gioco == "provincia",
            DailyScore.punteggio >= 1).limit(1)).first() is not None


def _giorni_di_fila(auth_id):
    """La serie piu' lunga di giorni giocati (almeno una sfida del giorno), con il
    giorno di riposo automatico: la definizione e' `player_stats.play_streak`."""
    return player_stats.play_streak_for(auth_id)["max"]


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
     "description": "7 giorni di fila con la Regione del giorno risolta",
     "criterion": lambda s: s["daily"]["max_daily_streak"] >= 7},
    {"id": "all_rounder", "icon": "🎖️", "title": "Tuttologo",
     "description": "Giocati tutti e tre i giochi.",
     "criterion": _played_all},
    {"id": "veteran_50", "icon": "🏛️", "title": "Veterano",
     "description": "50 round giocati in totale.",
     "criterion": lambda s: _total_rounds(s) >= 50},
    {"id": "geografo", "icon": "📍", "title": "Geografo",
     "description": "Prima Provincia del giorno indovinata al livello tutta Italia.",
     "criterion": lambda s: s["_provincia_indovinata"]},
    {"id": "giro_ditalia", "icon": "🧭", "title": "Giro d'Italia",
     "description": "Le sfide del giorno di tutti e quattro i giochi risolte nello stesso giorno.",
     "criterion": lambda s: s["_giri_completi"] >= 1},
    {"id": "fedele", "icon": "🛡️", "title": "Fedele",
     "description": "30 giorni di fila con almeno una sfida del giorno.",
     "criterion": lambda s: s["_giorni_di_fila"] >= GIORNI_FEDELE},
]


# I traguardi con una soglia: id -> (valore di chi gioca dalle statistiche, soglia). Ne
# esce `progress: {value, target}` nella vetrina, col valore fermo alla soglia.
PROGRESS = {
    "compare_10": (lambda s: s["compare"]["best_streak"], 10),
    "compare_25": (lambda s: s["compare"]["best_streak"], 25),
    "order_10": (lambda s: s["order"]["best_streak"], 10),
    "daily_streak_7": (lambda s: s["daily"]["max_daily_streak"], 7),
    "veteran_50": (_total_rounds, 50),
    "fedele": (lambda s: s["_giorni_di_fila"], GIORNI_FEDELE),
}


def _public(item, unlocked=False, unlocked_at=None):
    return {"id": item["id"], "icon": item["icon"],
            "icon_url": f"/static/img/gioco/traguardi/{item['id']}.svg", "title": item["title"],
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


def _stats_per_criteri(auth_id):
    """`stats_map` più i dati delle sfide del giorno che i nuovi traguardi
    leggono (chiavi con il trattino basso: non sono una modalità)."""
    stats = player_stats.stats_map(auth_id)
    stats["_provincia_indovinata"] = _provincia_indovinata(auth_id)
    stats["_giri_completi"] = len(_giorni_del_giro(auth_id))
    stats["_giorni_di_fila"] = _giorni_di_fila(auth_id)
    return stats


def evaluate(auth_id):
    """Registra gli achievement appena raggiunti e li restituisce (voci
    pubbliche). Idempotente: uno già sbloccato non si ripropone. Tollerante:
    se il DB non risponde, nessuno sblocco (la risposta di gioco non deve cadere)."""
    if not auth_id:
        return []
    try:
        stats = _stats_per_criteri(auth_id)
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
    stats = _stats_per_criteri(auth_id) if auth_id else None
    voci = []
    for item in CATALOG:
        voce = _public(item, item["id"] in unlocked, unlocked.get(item["id"]))
        if item["id"] in PROGRESS:
            leggi, soglia = PROGRESS[item["id"]]
            voce["progress"] = {"value": min(leggi(stats), soglia) if stats else 0, "target": soglia}
        voci.append(voce)
    return voci
