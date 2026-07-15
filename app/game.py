"""Gioco 'Indovina la Regione': un indicatore alla volta, sei tentativi.

Stateless per design (come il resto del backend, nessuna sessione/DB): il
puzzle è ricostruito deterministicamente da un puzzle_id a ogni chiamata,
memoizzato come le altre funzioni di data.py/profiles.py. La sfida
giornaliera usa la data come seed (stessa regione per tutti, deterministica
tra i worker gunicorn perché random.Random(str) è basato su un hash
stabile, non su hash() randomizzato per processo). La modalità allenamento
usa un seed casuale generato dal server a ogni richiesta.

Questo significa che un client può, in linea di teoria, chiamare l'API con
attempt=6 e ottenere subito la soluzione: senza sessioni lato server non è
evitabile con costi ragionevoli, ma è un compromesso accettabile per un
gioco pubblico non competitivo.
"""

import random
import re
import secrets
from datetime import date

from app.cache import cache
from app.data import REGION_ORDER, get_indicator, indicator_year_average
from app.indicator_notes import MACRO_AREA_ORDER
from app import profiles

GAME_EPOCH = date(2026, 7, 15)  # giorno di lancio, puzzle numero 1
CLUES_PER_PUZZLE = len(MACRO_AREA_ORDER)  # un indizio per macro-area
MAX_ATTEMPTS = CLUES_PER_PUZZLE
CANDIDATES_PER_AREA = 3  # varietà tra puzzle diversi a parità di area

_DAILY_PREFIX = "daily:"
_PRACTICE_PREFIX = "practice:"
_PUZZLE_ID_RE = re.compile(r"^(?:daily:\d{4}-\d{2}-\d{2}|practice:[0-9a-f]+)$")

# Ripartizione geografica Istat semplificata, usata come indizio dopo il
# terzo tentativo sbagliato.
_RIPARTIZIONE_REGIONS = {
    "Nord": (
        "Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige",
        "Veneto", "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna",
    ),
    "Centro": ("Toscana", "Umbria", "Marche", "Lazio"),
    "Mezzogiorno": (
        "Abruzzo", "Molise", "Campania", "Puglia", "Basilicata",
        "Calabria", "Sicilia", "Sardegna",
    ),
}
RIPARTIZIONE = {
    region: area for area, regions in _RIPARTIZIONE_REGIONS.items() for region in regions
}


def is_valid_puzzle_id(puzzle_id):
    return isinstance(puzzle_id, str) and bool(_PUZZLE_ID_RE.match(puzzle_id))


def daily_puzzle_id(today=None):
    today = today or date.today()
    return f"{_DAILY_PREFIX}{today.isoformat()}", today


def new_practice_puzzle_id():
    return f"{_PRACTICE_PREFIX}{secrets.token_hex(8)}"


def puzzle_number(today=None):
    today = today or date.today()
    return max((today - GAME_EPOCH).days, 0) + 1


def _cycle_shuffle(cycle_index):
    """Le 20 regioni mescolate deterministicamente per un ciclo di 20 giorni,
    così nessuna regione si ripete finché il ciclo non è esaurito."""
    rng = random.Random(f"divario-regioni-cycle-{cycle_index}")
    regions = list(REGION_ORDER)
    rng.shuffle(regions)
    return regions


def region_for_puzzle(puzzle_id):
    if puzzle_id.startswith(_DAILY_PREFIX):
        iso_date = puzzle_id[len(_DAILY_PREFIX):]
        day_index = max((date.fromisoformat(iso_date) - GAME_EPOCH).days, 0)
        cycle_index, pos = divmod(day_index, len(REGION_ORDER))
        return _cycle_shuffle(cycle_index)[pos]
    rng = random.Random(puzzle_id)
    return rng.choice(REGION_ORDER)


def _pick_area_indicator(candidates, puzzle_id, area):
    top = sorted(candidates, key=lambda item: -abs(item["score"] - 50))[:CANDIDATES_PER_AREA]
    rng = random.Random(f"{puzzle_id}:{area}")
    return rng.choice(top)


def _clue_fields(item):
    return {
        "id": item["id"],
        "name": item["name"],
        "theme": item["theme"],
        "macro_area": item["macro_area"],
        "unit": item["unit"],
        "year": item["year"],
        "value": item["value"],
    }


@cache.memoize(timeout=3600)
def build_puzzle(puzzle_id):
    """Regione misteriosa + fino a CLUES_PER_PUZZLE indizi (uno per
    macro-area quando disponibile), ordinati dal meno al più distintivo per
    quella regione. Deterministico dato puzzle_id."""
    region = region_for_puzzle(puzzle_id)
    region_key = profiles.region_key_for(region)
    profile = profiles.region_profile(region_key)

    by_area = {}
    for item in profile["all_indicators"]:
        if item["score"] is None:
            continue
        by_area.setdefault(item["macro_area"], []).append(item)

    chosen = []
    used_ids = set()
    for area in MACRO_AREA_ORDER:
        candidates = [c for c in by_area.get(area, []) if c["id"] not in used_ids]
        if not candidates:
            continue
        pick = _pick_area_indicator(candidates, puzzle_id, area)
        used_ids.add(pick["id"])
        chosen.append(pick)

    # Ripescaggio se un'area non aveva indicatori scoreable per questa
    # regione: completa dal resto del pool ordinato per distintività.
    if len(chosen) < CLUES_PER_PUZZLE:
        pool = sorted(
            (item for item in profile["all_indicators"] if item["score"] is not None and item["id"] not in used_ids),
            key=lambda item: -abs(item["score"] - 50),
        )
        for item in pool:
            if len(chosen) >= CLUES_PER_PUZZLE:
                break
            chosen.append(item)
            used_ids.add(item["id"])

    chosen.sort(key=lambda item: abs(item["score"] - 50))  # meno -> più distintivo

    return {
        "region": region,
        "region_key": region_key,
        "clues": [_clue_fields(item) for item in chosen],
    }


def _guess_value(indicator_id, region_key, year):
    payload = get_indicator(indicator_id)
    if payload is None:
        return None
    for row in payload["series"]:
        if row["region_key"] == region_key and row["year"] == year:
            return row["value"]
    return None


def _compare(mystery_value, guess_value):
    if guess_value is None or mystery_value is None:
        return "unknown"
    diff = mystery_value - guess_value
    if abs(diff) < 1e-9:
        return "equal"
    return "higher" if diff > 0 else "lower"


def _recap_entry(clue):
    payload = get_indicator(clue["id"])
    series = payload["series"] if payload else []
    national_avg = indicator_year_average(series, clue["year"])
    return {
        "id": clue["id"],
        "name": clue["name"],
        "unit": clue["unit"],
        "year": clue["year"],
        "value": clue["value"],
        "national_avg": round(national_avg, 3) if national_avg is not None else None,
        "path": profiles.indicator_path(clue["id"], clue["name"]),
    }


def _puzzle_intro(puzzle_id, number=None, puzzle_date=None):
    puzzle = build_puzzle(puzzle_id)
    clues = puzzle["clues"]
    return {
        "puzzle_id": puzzle_id,
        "number": number,
        "date": puzzle_date.isoformat() if puzzle_date else None,
        "clues_total": len(clues),
        "attempts_total": MAX_ATTEMPTS,
        "clue": _clue_fields(clues[0]) if clues else None,
    }


def daily_payload():
    puzzle_id, today = daily_puzzle_id()
    return _puzzle_intro(puzzle_id, number=puzzle_number(today), puzzle_date=today)


def practice_payload():
    return _puzzle_intro(new_practice_puzzle_id())


def evaluate_guess(puzzle_id, region_key, attempt):
    """Valuta un tentativo, o None se l'input non è valido (il chiamante
    risponde 400)."""
    if not is_valid_puzzle_id(puzzle_id):
        return None
    if not isinstance(attempt, int) or attempt < 1 or attempt > MAX_ATTEMPTS:
        return None
    region_name = profiles.region_name(region_key)
    if region_name is None:
        return None

    puzzle = build_puzzle(puzzle_id)
    clues = puzzle["clues"]
    if len(clues) < MAX_ATTEMPTS and attempt > len(clues):
        return None
    mystery_key = puzzle["region_key"]
    revealed = clues[:attempt]

    correct = region_key == mystery_key
    finished = correct or attempt >= len(clues)

    feedback = [
        {
            "id": clue["id"],
            "name": clue["name"],
            "unit": clue["unit"],
            "comparison": "equal" if correct else _compare(clue["value"], _guess_value(clue["id"], region_key, clue["year"])),
        }
        for clue in revealed
    ]

    next_clue = None
    if not finished and attempt < len(clues):
        next_clue = _clue_fields(clues[attempt])

    ripartizione_hint = None
    if attempt >= 3 and not correct:
        ripartizione_hint = {"same": RIPARTIZIONE.get(region_name) == RIPARTIZIONE.get(puzzle["region"])}

    solution = None
    recap = None
    if finished:
        solution = {
            "region": puzzle["region"],
            "region_key": mystery_key,
            "path": f"/regione/{mystery_key}",
        }
        recap = [_recap_entry(clue) for clue in clues]

    return {
        "correct": correct,
        "attempt": attempt,
        "region": region_name,
        "region_key": region_key,
        "feedback": feedback,
        "next_clue": next_clue,
        "ripartizione_hint": ripartizione_hint,
        "finished": finished,
        "solution": solution,
        "recap": recap,
    }
