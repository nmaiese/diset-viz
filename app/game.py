"""Gioco 'Indovina la Regioné: un indicatore alla volta, sei tentativi.

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
from datetime import date, datetime, timedelta, timezone

from app.cache import cache
from app.data import REGION_ORDER, get_indicator, indicator_year_average
from app.taxonomy import MACRO_AREA_ORDER
from app import profiles

GAME_EPOCH = date(2026, 7, 15)  # giorno di lancio, puzzle numero 1
CLUES_PER_PUZZLE = 6
MAX_ATTEMPTS = CLUES_PER_PUZZLE
CANDIDATES_PER_AREA = 3  # varietà tra puzzle diversi a parità di area
ARCHIVE_LIMIT = 30

_DAILY_PREFIX = "daily:"
_PRACTICE_PREFIX = "practice:"
_PRACTICE_ID_RE = re.compile(r"^practice:[0-9a-f]+$")

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


def _daily_date(puzzle_id):
    """Parse+validate the date embedded in a daily puzzle_id. Returns a date
    in [GAME_EPOCH, today] or None if it isn't a valid, currently playable
    daily puzzle: malformed, before launch, or (this is the anti-spoiler
    check) a future date whose solution shouldn't be computable yet."""
    if not puzzle_id.startswith(_DAILY_PREFIX):
        return None
    try:
        day = date.fromisoformat(puzzle_id[len(_DAILY_PREFIX):])
    except ValueError:
        return None
    if day < GAME_EPOCH or day > date.today():
        return None
    return day


def is_valid_puzzle_id(puzzle_id):
    if not isinstance(puzzle_id, str):
        return False
    if puzzle_id.startswith(_DAILY_PREFIX):
        return _daily_date(puzzle_id) is not None
    return bool(_PRACTICE_ID_RE.match(puzzle_id))


def daily_puzzle_id(today=None):
    today = today or date.today()
    return f"{_DAILY_PREFIX}{today.isoformat()}", today


def new_practice_puzzle_id():
    return f"{_PRACTICE_PREFIX}{secrets.token_hex(8)}"


def puzzle_number(today=None):
    today = today or date.today()
    return max((today - GAME_EPOCH).days, 0) + 1


def _next_puzzle_at(today):
    """ISO 8601 UTC timestamp of the next daily puzzle's release (midnight
    UTC the following day), so the client can render a countdown without
    needing to know the server's timezone."""
    next_day = today + timedelta(days=1)
    midnight_utc = datetime.combine(next_day, datetime.min.time(), tzinfo=timezone.utc)
    return midnight_utc.isoformat()


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
        "description": item.get("description", ""),
        "value_explanation": item.get("value_explanation", ""),
        "reading": item.get("reading", ""),
        "year": item["year"],
        "value": item["value"],
        "rank": item["rank"],
        "region_count": item["region_count"],
        "source_label": item["source_label"],
        "source_url": item["source_url"],
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


def _guessed_region_index(region_key):
    """id -> {value, rank} for every core indicator of the guessed region,
    reusing the same memoized profile the region page itself serves."""
    profile = profiles.region_profile(region_key)
    if profile is None:
        return {}
    return {item["id"]: item for item in profile["all_indicators"]}


def _compare(mystery_value, guess_value):
    """"higher"/"lower" descrivono il valore INDOVINATO rispetto al mistero
    (es. "higher" = il tuo tentativo ha un valore più alto): il frontend
    mostra questo esito subito dopo il valore del tentativo, quindi il verso
    deve riferirsi a quello, non al mistero."""
    if guess_value is None or mystery_value is None:
        return "unknown"
    diff = guess_value - mystery_value
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
        "description": clue.get("description", ""),
        "value_explanation": clue.get("value_explanation", ""),
        "reading": clue.get("reading", ""),
    }


def _puzzle_intro(puzzle_id, number=None, puzzle_date=None, next_puzzle_at=None):
    puzzle = build_puzzle(puzzle_id)
    clues = puzzle["clues"]
    return {
        "puzzle_id": puzzle_id,
        "number": number,
        "date": puzzle_date.isoformat() if puzzle_date else None,
        "next_puzzle_at": next_puzzle_at,
        "clues_total": len(clues),
        "attempts_total": MAX_ATTEMPTS,
        "clue": _clue_fields(clues[0]) if clues else None,
    }


def daily_payload():
    puzzle_id, today = daily_puzzle_id()
    return _puzzle_intro(
        puzzle_id,
        number=puzzle_number(today),
        puzzle_date=today,
        next_puzzle_at=_next_puzzle_at(today),
    )


def daily_payload_for_date(iso_date):
    """Payload for a specific archived daily puzzle, or None if the date is
    malformed, before launch, or in the future (same rule as evaluate_guess,
    so the archive can never leak tomorrow's solution either)."""
    try:
        day = date.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return None
    if day < GAME_EPOCH or day > date.today():
        return None
    puzzle_id, _ = daily_puzzle_id(day)
    return _puzzle_intro(puzzle_id, number=puzzle_number(day), puzzle_date=day)


def archive_list(limit=ARCHIVE_LIMIT):
    """Most-recent-first list of past playable daily puzzles (today
    excluded, that's the main "Sfida del giorno" tab already)."""
    today = date.today()
    past_days = max((today - GAME_EPOCH).days, 0)
    count = min(limit, past_days)
    return [
        {
            "date": (day := today - timedelta(days=offset)).isoformat(),
            "number": puzzle_number(day),
        }
        for offset in range(1, count + 1)
    ]


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

    guess_index = _guessed_region_index(region_key)
    feedback = []
    for clue in revealed:
        guess_item = guess_index.get(clue["id"])
        guess_value = guess_item["value"] if guess_item else None
        guess_rank = guess_item["rank"] if guess_item else None
        feedback.append({
            "id": clue["id"],
            "name": clue["name"],
            "unit": clue["unit"],
            "comparison": "equal" if correct else _compare(clue["value"], guess_value),
            "guess_value": guess_value,
            "guess_rank": guess_rank,
            "mystery_rank": clue["rank"],
            "region_count": clue["region_count"],
        })

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
