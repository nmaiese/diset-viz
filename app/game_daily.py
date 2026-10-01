"""Sfida del giorno: il giorno di Roma, il seed e i payload dei giochi a livelli.

Tre cose stanno qui, perche' devono restare d'accordo fra loro.

**Il giorno e' quello di Roma.** Un'unica funzione, `today_rome()`, dice che
giorno e' per il gioco. Il server gira in UTC (Cloud Run): senza questa funzione
la sfida nuova uscirebbe all'una o alle due di notte in Italia, e un punto che
usa `date.today()` darebbe un giorno diverso da quello che il giocatore vede. I
timestamp restano in UTC.

**Il seed e' onesto.** Il repo e' pubblico: il vecchio seed di Indovina la
Regione (`random.Random("divario-regioni-cycle-N")`) si calcola leggendo il
codice, e chiunque puo' sapere la soluzione di domani. Dal giorno `SEED_CUTOVER`
in avanti le soluzioni escono da `HMAC(GAME_SEED_KEY, "<gioco>|<data>")`, con una
chiave che non sta nel repo. Le date PRECEDENTI al passaggio tengono il seed
vecchio, cosi' l'archivio e il `localStorage` per `puzzleId` restano coerenti.

    RUOTARE `GAME_SEED_KEY` CAMBIA TUTTE LE SFIDE DAL CUTOVER IN POI, ANCHE QUELLE
    GIA' GIOCATE: ogni giorno dal cutover si ricalcola con la chiave corrente, quindi
    l'archivio cambia insieme alle sfide future, e i risultati salvati per data non
    corrispondono piu' alla sfida che si rivede. Restano uguali solo i giorni prima
    del cutover. Va fatto solo di proposito, e mai a meta' giornata: chi ha gia'
    giocato oggi vedrebbe un'altra soluzione ricaricando la pagina.

Senza la variabile d'ambiente si usa `DEV_SEED_KEY`, che e' scritta qui e
quindi NON E' SEGRETA: va bene in locale e nei test, non in produzione. Dove
`K_SERVICE` e' impostata (Cloud Run) e la chiave manca, `seed_key` solleva
`SeedKeyMissing` e le rotte rispondono 503, invece di servire sfide prevedibili.
`SEED_CUTOVER` e' il primo giorno con il seed segreto (2 ottobre 2026: il giorno
del deploy piu' uno). Se il deploy slitta oltre quel giorno, la data va spostata
PRIMA del merge: i giorni fra il cutover e il deploy sarebbero gia' stati serviti
col seed vecchio e cambierebbero nell'archivio.

**I giochi con le province.** Il pool dei territori (107 province, centroidi,
province "giocabili"), l'elenco curato degli indicatori da gioco
(`config/game_indicators.csv`) e i payload della sfida del giorno di "Chi e'
maggiore?" e "Ordina": funzioni pure e deterministiche sul seed, che non
rivelano mai un valore. Come si valutano le risposte non e' qui.

`config/game_indicators.csv`: una riga per indicatore. L'`id` e' quello del pool
regionale del quiz (`105`, `bes:10AMB009`, `multiscopo:...`) quando
`livello_regione` e' 1, oppure l'id BES delle province (`04BEC001P`) quando
l'indicatore esiste solo a livello provinciale. Con `livello_provincia` 1 i dati
provinciali si leggono sotto l'id senza il prefisso `bes:`. `campionario` e' 1 per
le serie che vengono da un'indagine campionaria, e nel dubbio: il fatto di fine
partita (`game_facts.is_sample_survey`) allora non scrive la posizione esatta. Il
prefisso non basta a dirlo: `426` e' Multiscopo, `57` Forze di lavoro, `72` ICT
nelle imprese, e nessuno dei tre ha un prefisso. Le righe `bes:`, `multiscopo:` e
quelle solo provinciali (BES) sono tutte 1. Una riga senza il valore conta come 1.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import logging
import math
import os
import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

ROME_TZ = ZoneInfo("Europe/Rome")
GAME_EPOCH = date(2026, 7, 15)  # giorno di lancio, puzzle numero 1

# Il primo giorno con il seed segreto: il giorno del deploy piu' uno (vedi sopra).
SEED_CUTOVER = date(2026, 10, 2)
# NON SEGRETA: vale solo finche' `GAME_SEED_KEY` non e' impostata.
DEV_SEED_KEY = "divario-chiave-di-sviluppo-non-segreta"

LEVELS = ("regioni", "stessa_regione", "province")
COMPARE_PAIRS = 10
ORDER_TERRITORIES = 5
# Province minime in una regione perche' "stessa regione" abbia senso.
MIN_PROVINCES_COMPARE = 3
MIN_PROVINCES_ORDER = 5

ROOT = Path(__file__).resolve().parents[1]
GAMES_CSV = ROOT / "config" / "game_indicators.csv"
CENTROIDS_JSON = ROOT / "app" / "static" / "data" / "province_centroidi.json"

# Lato minore (unita' del viewBox 560x660) del poligono principale di una
# provincia, sotto il quale la sagoma e' illeggibile sulla mappa a 390 px. Fra
# Trieste (12,7) e Gorizia (16,3) non cade nessuna provincia: la soglia sta nel
# vuoto, non taglia a caso.
PLAYABLE_THRESHOLD = 14.0
# Chilometri per unita' del viewBox: media di tre distanze note (Milano-Roma,
# Torino-Trieste, Palermo-Bolzano) fra centroidi. Il viewBox e' un Mercatore,
# quindi la scala varia con la latitudine: i km sono approssimati.
KM_PER_UNIT = 1.90

# Livello di difficolta' (0 facile, 4 duro) per giorno della settimana, lunedi' = 0.
WEEKDAY_DIFFICULTY = (0, 1, 1, 2, 3, 3, 4)
# Finestra (min, max) della distanza fra i due valori in gara, come frazione
# degli indici distinti disponibili: a livello 0 la coppia e' lontana in
# classifica, ai livelli alti quasi adiacente.
_COMPARE_WINDOW = {0: (0.63, 1.0), 1: (0.42, 0.58), 2: (0.26, 0.37), 3: (0.16, 0.21), 4: (0.05, 0.11)}
# Per Ordina: quanta parte della classifica puo' coprire l'insieme dei cinque.
_ORDER_WINDOW = {0: 1.0, 1: 0.7, 2: 0.5, 3: 0.35, 4: 0.22}
_MIN_DISTINCT_REGIONS = 6

_log = logging.getLogger(__name__)


# Il giorno di Roma

def today_rome(now=None):
    """Il giorno corrente a Roma. `now` (datetime con fuso) serve ai test."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ROME_TZ).date()


def next_challenge_rome(today=None):
    """ISO 8601 UTC della mezzanotte di Roma che apre il giorno dopo `oggi`."""
    today = today or today_rome()
    midnight = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=ROME_TZ)
    return midnight.astimezone(timezone.utc).isoformat()


def challenge_number(day):
    return max((day - GAME_EPOCH).days, 0) + 1


# Il seed

@lru_cache(maxsize=1)
def _warn_dev_seed_key():
    _log.warning("GAME_SEED_KEY non impostata: le sfide usano la chiave di sviluppo, che non e' segreta")


class SeedKeyMissing(RuntimeError):
    """In produzione (Cloud Run imposta `K_SERVICE`) senza `GAME_SEED_KEY`: le sfide
    calcolate con la chiave di sviluppo, che sta nel repo, sarebbero prevedibili da
    chiunque. Le rotte che usano il seed nuovo rispondono 503."""


def seed_key():
    key = os.environ.get("GAME_SEED_KEY")
    if key:
        return key
    if os.environ.get("K_SERVICE"):
        raise SeedKeyMissing("GAME_SEED_KEY non impostata su Cloud Run: le sfide nuove sarebbero prevedibili")
    _warn_dev_seed_key()
    return DEV_SEED_KEY


def day_seed(game, day, key=None):
    """Il seed intero di `gioco` nel `giorno`: HMAC-SHA256 di "<gioco>|<data>"."""
    key = seed_key() if key is None else key
    message = f"{game}|{day.isoformat()}".encode()
    digest = hmac.new(key.encode(), message, hashlib.sha256).digest()
    return int.from_bytes(digest, "big")


def _rng(game, day, key=None):
    return random.Random(day_seed(game, day, key))


def _legacy_cycle(cycle_index, ordering):
    """Il seed di prima del cutover: calcolabile da chiunque, conservato
    perche' le sfide gia' servite restano le stesse."""
    rng = random.Random(f"divario-regioni-cycle-{cycle_index}")
    regions = list(ordering)
    rng.shuffle(regions)
    return regions


def daily_region(day, ordering, cutover=None, key=None):
    """La regione di Indovina per un giorno. Prima del cutover il ciclo vecchio
    di 20 giorni, dopo lo stesso schema (nessuna ripetizione nel ciclo) con un
    mescolamento che esce dall'HMAC. `ordine` e' l'elenco delle regioni."""
    cutover = SEED_CUTOVER if cutover is None else cutover
    if day < cutover:
        index = max((day - GAME_EPOCH).days, 0)
        cycle, pos = divmod(index, len(ordering))
        return _legacy_cycle(cycle, ordering)[pos]
    cycle, pos = divmod((day - cutover).days, len(ordering))
    start = cutover + timedelta(days=cycle * len(ordering))
    regions = list(ordering)
    _rng("regioni", start, key).shuffle(regions)
    return regions[pos]


# I territori

@lru_cache(maxsize=1)
def _provinces():
    from app import bes_data, profiles

    with bes_data.PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        codes = list(csv.DictReader(handle, delimiter=";"))
    centroids = json.loads(CENTROIDS_JSON.read_text(encoding="utf-8"))["province"]
    pool = []
    for row in codes:
        key = row["province_key"]
        c = centroids[key]
        pool.append({
            "key": key,
            "name": row["name"],
            "region": row["region"],
            "region_key": profiles.region_key_for(row["region"]),
            "x": c["x"],
            "y": c["y"],
            "w": c["w"],
            "h": c["h"],
            "giocabile": min(c["w"], c["h"]) >= PLAYABLE_THRESHOLD,
        })
    return tuple(pool)


def province_pool(playable_only=False):
    """Le 107 province con chiave, nome, regione e centroide (`x`, `y` nel
    viewBox 560x660). `giocabile` dice se la sagoma e' leggibile sulla mappa;
    `playable_only` restituisce solo quelle. Non modificare le voci."""
    return [p for p in _provinces() if p["giocabile"] or not playable_only]


def excluded_provinces():
    return [p["key"] for p in _provinces() if not p["giocabile"]]


def eligible_regions(minimum):
    """Le regioni con almeno `minimo` province (5 per Ordina, 3 per gli altri
    giochi), nell'ordine di `REGION_ORDER`."""
    from app.data import REGION_ORDER

    counts = {}
    for p in _provinces():
        counts[p["region"]] = counts.get(p["region"], 0) + 1
    return [r for r in REGION_ORDER if counts.get(r, 0) >= minimum]


def _province_by_key(key):
    for p in _provinces():
        if p["key"] == key:
            return p
    raise KeyError(key)


_COMPASS_POINTS = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


def distance_km_direction(a, b):
    """(km approssimati, direzione in otto punti) per andare dalla provincia `a`
    alla `b`, fra i centroidi. I km sono una stima: vanno dichiarati tali."""
    pa, pb = _province_by_key(a), _province_by_key(b)
    dx, dy = pb["x"] - pa["x"], pb["y"] - pa["y"]
    km = round(math.hypot(dx, dy) * KM_PER_UNIT)
    if km == 0:
        return 0, None
    bearing = math.degrees(math.atan2(dx, -dy)) % 360  # l'asse y dell'SVG scende
    return km, _COMPASS_POINTS[int((bearing + 22.5) // 45) % 8]


# L'elenco curato

@lru_cache(maxsize=1)
def game_indicators():
    """Le righe di `config/game_indicators.csv`, con i flag come bool."""
    with GAMES_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    return tuple(
        {
            "id": r["id"],
            "family": r["famiglia"],
            "name": r["nome_leggibile"],
            "unit": r["unita"],
            "regione": r["livello_regione"] == "1",
            "provincia": r["livello_provincia"] == "1",
            "note": r["note"],
            # Nel dubbio campionario: una riga senza il valore non da' la posizione esatta.
            "sample_survey": (r.get("campionario") or "").strip() != "0",
        }
        for r in rows
    )


def provincial_id(id_):
    return id_[len("bes:"):] if id_.startswith("bes:") else id_


def _quiz_index():
    """{id: voce} del pool regionale del quiz. Costruirlo costa circa 0,7 ms: in
    `_candidates` (96 indicatori) lo si fa una volta per passata e non una volta per
    indicatore, e non sopravvive alla passata, cosi' non puo' andare fuori sincrono
    con il pool che `quiz` tiene in cache."""
    from app import quiz

    return {p["id"]: p for p in quiz._quiz_indicators()}


def _indicator_rows(ind, scope, index=None):
    """(anno, [{key, name, region, value}]) di un indicatore a un livello
    territoriale, o None se il dato non c'e'. `ambito` e' "regioni" o "province".
    `indice` e' l'`_quiz_index()` gia' costruito da chi chiama in un ciclo."""
    if scope == "regioni":
        entry = (index if index is not None else _quiz_index()).get(ind["id"])
        if entry is None:
            return None
        rows = [
            {"key": r["region_key"], "name": r["region"], "region": r["region"], "value": r["value"]}
            for r in entry["ranking"]
        ]
        return entry["year"], rows
    from app import bes_data, province_profile

    raw = provincial_id(ind["id"])
    info = bes_data.get_bes_manifest("provincia").get(raw)
    if info is None:
        return None
    values = (province_profile._serie().get(raw) or {}).get(info["year_max"])
    if not values:
        return None
    registry = {p["key"]: p for p in _provinces()}
    rows = [
        {"key": k, "name": registry[k]["name"], "region": registry[k]["region"], "value": v}
        for k, v in sorted(values["valori"].items()) if k in registry
    ]
    return info["year_max"], rows


def _indicator_fields(ind, year):
    return {"id": ind["id"], "name": ind["name"], "unit": ind["unit"], "year": year, "family": ind["family"]}


def _territory_fields(row):
    return {"key": row["key"], "name": row["name"], "region": row["region"]}


def _distinct(rows):
    """Valori distinti dal piu' alto al piu' basso, e le righe di ciascuno."""
    by_value = {}
    for r in rows:
        by_value.setdefault(r["value"], []).append(r)
    ordering = sorted(by_value, reverse=True)
    return ordering, by_value


def _scope(level, game, day, key):
    """(ambito dei dati, filtro sulle righe, regione) per un livello. Per
    "stessa regione" la regione del giorno esce dal seed."""
    if level == "regioni":
        return "regioni", (lambda r: True), None
    if level == "province":
        return "province", (lambda r: True), None
    minimum = MIN_PROVINCES_ORDER if game == "order" else MIN_PROVINCES_COMPARE
    eligible = eligible_regions(minimum)
    region = _rng(f"{game}-regione", day, key).choice(eligible)
    return "province", (lambda r: r["region"] == region), region


def _candidates(level, scope, row_filter, min_distinct, rng):
    """Gli indicatori utilizzabili in quell'ambito, in ordine mescolato dal
    seed: una lista di (indicatore, anno, righe filtrate)."""
    flag = "regione" if scope == "regioni" else "provincia"
    listing = sorted((i for i in game_indicators() if i[flag]), key=lambda i: i["id"])
    rng.shuffle(listing)
    minimum = min_distinct if level == "stessa_regione" else max(min_distinct, _MIN_DISTINCT_REGIONS)
    usable = []
    index = _quiz_index() if scope == "regioni" else None
    for ind in listing:
        found = _indicator_rows(ind, scope, index)
        if found is None:
            continue
        year, rows = found
        rows = [r for r in rows if r["value"] is not None and row_filter(r)]
        if len({r["value"] for r in rows}) >= minimum:
            usable.append((ind, year, rows))
    return usable


def _check_level(level):
    if level not in LEVELS:
        raise ValueError(f"livello sconosciuto: {level!r}")


def daily_compare(day, level, key=None):
    """Le 10 coppie di "Chi e' maggiore?" per un giorno e un livello (vedi `_compare`).
    In cache per `(giorno, livello, chiave)`: la chiave e' risolta PRIMA della cache,
    cosi' una sfida calcolata prima non aggira il controllo di `seed_key`."""
    _check_level(level)
    return _compare(day, level, seed_key() if key is None else key)


@lru_cache(maxsize=6)
def _compare(day, level, key):
    """Le 10 coppie di "Chi e' maggiore?" per un giorno e un livello: per
    ciascuna un indicatore e due territori, MAI i valori. La difficolta' cresce
    da lunedi' (coppie lontane in classifica) a domenica (quasi adiacenti)."""
    _check_level(level)
    difficulty = WEEKDAY_DIFFICULTY[day.weekday()]
    rng = _rng(f"compare-{level}", day, key)
    scope, row_filter, region = _scope(level, "compare", day, key)
    usable = _candidates(level, scope, row_filter, 2, rng)
    lo, hi = _COMPARE_WINDOW[difficulty]
    pairs = []
    for i in range(COMPARE_PAIRS):
        ind, year, rows = usable[i % len(usable)]
        distinct, by_value = _distinct(rows)
        maximum = len(distinct) - 1
        gap_min = max(1, math.ceil(lo * maximum))
        gap_max = min(max(gap_min, math.floor(hi * maximum)), maximum)
        gap = rng.randint(gap_min, gap_max)
        j = rng.randint(0, maximum - gap)
        pair = [rng.choice(by_value[distinct[j]]), rng.choice(by_value[distinct[j + gap]])]
        rng.shuffle(pair)
        pairs.append({
            "indicator": _indicator_fields(ind, year),
            "a": _territory_fields(pair[0]),
            "b": _territory_fields(pair[1]),
        })
    return {"level": level, "difficulty": difficulty, "region": region, "pairs": pairs}


def daily_order(day, level, key=None):
    """Il round di "Ordina" per un giorno e un livello (vedi `_order`), in cache come
    `daily_compare`."""
    _check_level(level)
    return _order(day, level, seed_key() if key is None else key)


@lru_cache(maxsize=6)
def _order(day, level, key):
    """Il round di "Ordina" per un giorno e un livello: cinque territori e un
    indicatore, senza valori ne' ordine (i territori sono mescolati). Le
    finestre di difficolta' stringono l'intervallo che i cinque coprono."""
    _check_level(level)
    difficulty = WEEKDAY_DIFFICULTY[day.weekday()]
    rng = _rng(f"order-{level}", day, key)
    scope, row_filter, region = _scope(level, "order", day, key)
    usable = _candidates(level, scope, row_filter, ORDER_TERRITORIES, rng)
    ind, year, rows = usable[0]
    distinct, by_value = _distinct(rows)
    n = len(distinct)
    window = min(n, max(ORDER_TERRITORIES, math.ceil(_ORDER_WINDOW[difficulty] * n)))
    start = rng.randint(0, n - window)
    indices = sorted(rng.sample(range(start, start + window), ORDER_TERRITORIES))
    picked = [rng.choice(by_value[distinct[i]]) for i in indices]
    rng.shuffle(picked)
    return {
        "level": level,
        "difficulty": difficulty,
        "region": region,
        "indicator": _indicator_fields(ind, year),
        "territories": [_territory_fields(r) for r in picked],
    }


# I payload delle rotte

def challenge_payload(game, level, now=None):
    """Il payload della sfida di OGGI (a Roma): mai una data a scelta del
    client, cosi' una soluzione futura non puo' uscire."""
    day = today_rome(now)
    body = (daily_compare if game == "compare" else daily_order)(day, level)
    return {
        "puzzle_id": f"daily:{day.isoformat()}",
        "number": challenge_number(day),
        "date": day.isoformat(),
        "next_puzzle_at": next_challenge_rome(day),
        **body,
    }


# Le fonti dei giochi, per il JSON-LD delle pagine /quiz/*

def _family_of(indicator_id):
    """La famiglia di `app/sources.py` di un id del pool: il prefisso interno
    (`bes:`, `multiscopo:`, `dem:`, `eur:`), e nessun prefisso e' la territoriale."""
    from app import sources

    for family, meta in sources.SOURCES.items():
        prefix = meta["internal_prefix"]
        if prefix and indicator_id.startswith(prefix):
            return family
    return "territorial"


@lru_cache(maxsize=8)
def game_families(game):
    """Le famiglie di fonti davvero presenti nel pool di un gioco (`regione`,
    `compare`, `order`, `provincia`), nell'ordine del registro. Indovina la Regione
    pesca dal profilo regionale dell'atlante. Chi e' maggiore e Ordina pescano dal
    pool del quiz e, ai livelli con le province, dal BES provinciale. Indovina la
    Provincia dal BES."""
    from app import profiles, quiz, sources
    from app.data import REGION_ORDER

    if game == "regione":
        profile = profiles.region_profile(profiles.region_key_for(REGION_ORDER[0]))
        families = {_family_of(entry["id"]) for entry in profile["all_indicators"]}
    elif game in ("compare", "order"):
        families = {_family_of(entry["id"]) for entry in quiz._quiz_indicators()} | {"bes"}
    elif game == "provincia":
        families = {"bes"}
    else:
        raise ValueError(f"gioco sconosciuto: {game!r}")
    return tuple(f for f in sources.SOURCES if f in families)


def game_source(game):
    """Chi pubblica i dati di un gioco, per il JSON-LD: `istituzioni` (frase in
    chiaro, "Istat ed Eurostat"), `creator` (le organizzazioni, una per istituzione) e
    `licenze` (gli URL delle licenze dichiarate dalle famiglie, senza ripetizioni). Tutto
    da `app/sources.py`: la stringa "Istat" da sola ha gia' attribuito a Istat una serie
    Eurostat."""
    from app import sources

    families = game_families(game)
    institutions = list(dict.fromkeys(sources.SOURCES[f]["institution"] for f in families))
    licenses = list(dict.fromkeys(u for u in (sources.family_license_url(f) for f in families) if u))
    return {
        "istituzioni": sources.institutions_label(families),
        "creator": [{"@type": "Organization", "name": name} for name in institutions],
        "licenze": licenses,
    }


def _register_in_templates():
    from app import app

    app.jinja_env.globals["game_source"] = game_source


_register_in_templates()
