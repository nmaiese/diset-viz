"""Indovina la Provincia: una provincia al giorno, sei indizi di dato, sei tentativi.

La provincia del giorno e' una sola, uguale per tutti e per i due livelli:

- **"della regione indicata"** (`stessa_regione`): al giocatore si dice la
  regione e si indovina fra le sue province;
- **"di tutta Italia"** (`province`): si indovina fra le 107.

Il livello e' la sola cosa che cambia: la provincia, gli indizi e la soluzione
sono gli stessi. Per questo la provincia si sceglie fra le giocabili
(`game_daily.province_pool(solo_giocabili=True)`) **di una regione idonea**
(`eligible_regions(3)`): altrimenti il livello facile non avrebbe fra chi scegliere.

Il giorno e' quello di Roma (`game_daily.today_rome`) e il seed esce da
`game_daily.day_seed("provincia", giorno)`, cioe' da un HMAC con una chiave
che non sta nel repo: la soluzione di domani non si calcola leggendo il codice.

**Anti-spoiler.** Lo stato dei tentativi sta nel server, non nel solo client: il
client non dice mai a che tentativo e'. Porta un token firmato (`itsdangerous`,
sale propria) con il `puzzle_id`, il livello e le chiavi gia' tentate; il server
deriva il numero del tentativo da quel token, rifiuta chiavi ripetute o fuori
dalle opzioni del livello, e mette la soluzione nella risposta solo a partita
finita. Il `puzzle_id` vale solo se e' la giornaliera di oggi. Un token piu'
vecchio di uno gia' usato dalla stessa sessione si rifiuta (`token_superato`,
per processo: un solo worker con piu' thread).
Limite noto: chi chiede un payload nuovo apre una sessione nuova, quindi puo'
riprovare dall'inizio. Non svela la soluzione (i tentativi di una sessione sono
sei) ma consente di sondare. Le rotte sono a frequenza limitata.

**Gli indizi** sono sei dati dell'Istat (BES dei Territori) presi da
`Assoluti_Provincia.csv` tramite `province_profile._serie()`: solo gli
indicatori di `config/game_indicators.csv` con il flag provincia, con un valore
per tutte e 107 le province nell'ultimo anno (`n_province_latest == 107`) e un
ultimo anno dal 2022 in poi. Uno per famiglia quando si puo', scelti dal seed e
ordinati dal meno al piu' distintivo per quella provincia (la distanza della sua
posizione dalla meta' della classifica).

Il risultato non entra in `player_stats.record_daily`: quello resta alla
giornaliera di Indovina la Regione. Serie e classifica sono dell'ondata 3.
"""

from __future__ import annotations

import csv
import random
from functools import lru_cache
from statistics import fmean

from itsdangerous import BadData, URLSafeTimedSerializer

from app import app, bes_data, game_daily, province_profile, sources
from app.cache import cache
from app.design import maps

ATTEMPTS = 6
LEVELS = ("province", "stessa_regione")
MIN_YEAR = 2022
EXPECTED_PROVINCES = 107

_SALT = "game-provincia"
_TOKEN_MAX_AGE_S = 2 * 24 * 3600
_MANIFEST_CSV = game_daily.ROOT / "app" / "static" / "data" / "province_manifest.csv"


class ProvinceError(Exception):
    """Un tentativo che non si valuta. `code` e' una parola per il client,
    `status` il codice HTTP."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


# Gli indizi ammessi


@lru_cache(maxsize=1)
def _manifest():
    with _MANIFEST_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle, delimiter=";")}


@lru_cache(maxsize=1)
def allowed_clues():
    """Gli indicatori che possono fare da indizio, nell'ordine del file di
    configurazione: (id BES, nome leggibile, unita', famiglia, tema, anno)."""
    manifest = _manifest()
    allowed = []
    for entry in game_daily.game_indicators():
        if not entry["provincia"]:
            continue
        raw = game_daily.provincial_id(entry["id"])
        row = manifest.get(raw)
        if row is None:
            continue
        year = int(row["year_max"])
        if int(row["n_province_latest"]) != EXPECTED_PROVINCES or year < MIN_YEAR:
            continue
        values = (province_profile._serie().get(raw) or {}).get(year)
        if not values or len(values["valori"]) != EXPECTED_PROVINCES:
            continue
        allowed.append({
            "id": raw,
            "name": entry["name"],
            "unit": entry["unit"],
            "family": entry["family"],
            "theme": row["domain_name"],
            "year": year,
        })
    return tuple(allowed)


# La sfida del giorno


def puzzle_id(day):
    return f"daily:{day.isoformat()}"


def daily_province(day, key=None):
    """La provincia misteriosa di un giorno: una giocabile di una regione
    idonea, dal seed. `chiave` serve ai test."""
    eligible = set(game_daily.eligible_regions(game_daily.MIN_PROVINCES_COMPARE))
    candidate = sorted(
        (p for p in game_daily.province_pool(solo_giocabili=True) if p["region"] in eligible),
        key=lambda p: p["key"],
    )
    rng = random.Random(game_daily.day_seed("provincia", day, key))
    return rng.choice(candidate)


def _clue_fields(ind, province_key):
    """L'indizio di un indicatore per una provincia: valore, posizione fra le
    107, anno e fonte. Le spiegazioni e il link alla scheda seguono il recap."""
    year = ind["year"]
    series = province_profile._serie()[ind["id"]][year]
    explanation = bes_data.get_bes_manifest("provincia")[ind["id"]]["explain"]
    return {
        "id": ind["id"],
        "name": ind["name"],
        "theme": ind["theme"],
        "unit": ind["unit"],
        "year": year,
        "value": series["valori"][province_key],
        "rank": series["posizioni"][province_key],
        "province_count": EXPECTED_PROVINCES,
        "source_label": sources.SOURCES["bes"]["label"],
        "source_url": bes_data.BES_SOURCE_URLS["provincia"],
        "path": bes_data.bes_level_path(ind["id"], "provincia"),
        "description": explanation["plain"],
        "value_explanation": explanation["example"],
        "reading": explanation["reading"],
    }


def daily_clues(day, key=None):
    """I sei indizi della provincia del giorno, dal meno al piu' distintivo."""
    mystery = daily_province(day, key)["key"]
    rng = random.Random(game_daily.day_seed("provincia-indizi", day, key))
    candidates = sorted(allowed_clues(), key=lambda i: i["id"])
    rng.shuffle(candidates)
    picked, families = [], set()
    for ind in candidates:  # un indizio per famiglia finche' ce ne sono
        if ind["family"] not in families and len(picked) < ATTEMPTS:
            picked.append(ind)
            families.add(ind["family"])
    for ind in candidates:
        if ind not in picked and len(picked) < ATTEMPTS:
            picked.append(ind)
    clues = [_clue_fields(ind, mystery) for ind in picked]
    midpoint = (EXPECTED_PROVINCES + 1) / 2
    clues.sort(key=lambda c: (abs(c["rank"] - midpoint), c["id"]))
    return clues


def options(level, day, key=None):
    """Le province fra cui si indovina a un livello, con il centroide per la
    mappa. Non dicono quali sono giocabili e non dicono qual e' la misteriosa."""
    mystery = daily_province(day, key)
    pool = game_daily.province_pool()
    if level == "stessa_regione":
        pool = [p for p in pool if p["region"] == mystery["region"]]
    return [
        {"key": p["key"], "name": p["name"], "region": p["region"], "x": p["x"], "y": p["y"]}
        for p in sorted(pool, key=lambda p: p["name"])
    ]


# Il token


def _serializer():
    return URLSafeTimedSerializer(app.secret_key, salt=_SALT)


def _sign(state):
    return _serializer().dumps(state)


def _read(token):
    if not token or not isinstance(token, str):
        raise ProvinceError("token_non_valido")
    try:
        state = _serializer().loads(token, max_age=_TOKEN_MAX_AGE_S)
    except BadData:
        raise ProvinceError("token_non_valido") from None
    if (
        not isinstance(state, dict)
        or state.get("l") not in LEVELS
        or not isinstance(state.get("p"), str)
        or not isinstance(state.get("g"), list)
        or not isinstance(state.get("sid"), str)
    ):
        raise ProvinceError("token_non_valido")
    return state


def _check_level(level):
    if level not in LEVELS:
        raise ProvinceError("livello_sconosciuto")


# Le risposte


def payload(level, now=None, key=None):
    """La sfida di OGGI (a Roma) a un livello: mai una data a scelta del client.
    Porta il primo indizio e le opzioni, mai la provincia ne' gli altri indizi."""
    _check_level(level)
    day = game_daily.today_rome(now)
    mystery = daily_province(day, key)
    clues = daily_clues(day, key)
    region = None
    if level == "stessa_regione":
        region_key = mystery["region_key"]
        region = {"name": mystery["region"], "key": region_key, "viewbox": maps.zoom(region_key)["viewbox"]}
    token = _sign({"p": puzzle_id(day), "l": level, "g": [], "sid": _new_session()})
    response = {
        "puzzle_id": puzzle_id(day),
        "number": game_daily.challenge_number(day),
        "date": day.isoformat(),
        "next_puzzle_at": game_daily.next_challenge_rome(day),
        "level": level,
        "attempts_total": ATTEMPTS,
        "clues_total": len(clues),
        "region": region,
        "provinces": options(level, day, key),
        "clue": dict(clues[0]),
        "token": token,
    }
    if level == "stessa_regione":
        # Le province delle altre regioni, solo nome e regione: il client le usa per dire
        # "Milano non e' in Puglia" a chi scrive una provincia che non e' fra le opzioni. La regione
        # e' gia' nel payload e la misteriosa e' fra le opzioni, quindi niente si svela.
        response["other_provinces"] = [
            {"name": p["name"], "region": p["region"]}
            for p in sorted(game_daily.province_pool(), key=lambda p: p["name"])
            if p["region"] != mystery["region"]
        ]
    return response


@lru_cache(maxsize=1)
def _registry():
    return {p["key"]: p for p in game_daily.province_pool()}


def _new_session():
    return random.SystemRandom().randbytes(8).hex()


def _comparison(mystery_value, attempt_value):
    """Come in `game._compare`: descrive il valore TENTATO rispetto al mistero."""
    if attempt_value is None or mystery_value is None:
        return "unknown"
    if abs(attempt_value - mystery_value) < 1e-9:
        return "equal"
    return "higher" if attempt_value > mystery_value else "lower"


def _recap(clues):
    rows = []
    for clue in clues:
        values = province_profile._serie()[clue["id"]][clue["year"]]["valori"]
        rows.append({**clue, "province_avg": round(fmean(values.values()), 3)})
    return rows


def evaluate_attempt(token, province_key, now=None, key=None):
    """Valuta un tentativo e ritorna il risultato, o solleva `ProvinceError`.
    Il numero del tentativo lo decide il token, mai il client."""
    state = _read(token)
    day = game_daily.today_rome(now)
    if state["p"] != puzzle_id(day):
        raise ProvinceError("sfida_scaduta", 410)
    level, attempted = state["l"], state["g"]
    attempt = len(attempted) + 1
    if attempt > ATTEMPTS:
        raise ProvinceError("partita_conclusa", 409)
    mystery = daily_province(day, key)
    if attempted and attempted[-1] == mystery["key"]:
        raise ProvinceError("partita_conclusa", 409)
    if not isinstance(province_key, str) or province_key not in {
        o["key"] for o in options(level, day, key)
    }:
        raise ProvinceError("provincia_non_valida")
    if province_key in attempted:
        raise ProvinceError("provincia_gia_tentata")
    seen = cache.get(f"provincia:{state['sid']}") or 0
    if len(attempted) < seen:
        raise ProvinceError("token_superato", 409)
    cache.set(f"provincia:{state['sid']}", attempt, timeout=_TOKEN_MAX_AGE_S)

    clues = daily_clues(day, key)
    correct = province_key == mystery["key"]
    finished = correct or attempt >= ATTEMPTS
    guessed_province = _registry()[province_key]
    km, direction = game_daily.distance_km_direction(province_key, mystery["key"])

    comparisons = []
    for clue in clues[:attempt]:
        series = province_profile._serie()[clue["id"]][clue["year"]]
        value = series["valori"].get(province_key)
        comparisons.append({
            "id": clue["id"],
            "name": clue["name"],
            "unit": clue["unit"],
            "comparison": "equal" if correct else _comparison(clue["value"], value),
            "guess_value": value,
            "guess_rank": series["posizioni"].get(province_key),
            "mystery_rank": clue["rank"],
            "province_count": EXPECTED_PROVINCES,
        })

    solution = recap = None
    if finished:
        solution = {
            "province": mystery["name"],
            "province_key": mystery["key"],
            "path": f"/provincia/{mystery['key']}",
            "region": mystery["region"],
            "region_key": mystery["region_key"],
            "region_path": f"/regione/{mystery['region_key']}",
        }
        recap = _recap(clues)

    new_token = _sign({**state, "g": [*attempted, province_key]})
    return {
        "correct": correct,
        "level": level,
        "attempt": attempt,
        "province": guessed_province["name"],
        "province_key": province_key,
        "distance_km": km,
        "direction": direction,
        "same_region": guessed_province["region"] == mystery["region"],
        "feedback": comparisons,
        "next_clue": None if finished else dict(clues[attempt]),
        "finished": finished,
        "solution": solution,
        "recap": recap,
        "token": new_token,
    }
