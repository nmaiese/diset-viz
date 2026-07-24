"""Motore quiz condiviso per le modalità a domanda rapida.

Copre "Chi è maggiore?" (confronto a due regioni con difficoltà progressiva)
e "Ordina le regioni" (ordinamento a credito parziale). A differenza di
"Indovina la Regione" (app/game.py) qui non c'è alcun seed giornaliero né
anti-spoiler: ogni round è un'estrazione casuale indipendente e i valori
sono comunque pubblici sulle pagine indicatore. Per questo gli endpoint di
risposta non usano id opachi: rileggono i dati e restano l'unica fonte di
verità sul confronto (il client non decide mai chi ha vinto).

Solo il pool di indicatori idonei è memoizzato. Le funzioni di round NON
vanno memoizzate: devono variare a ogni chiamata.
"""

import math
import random

from app.cache import cache
from app.data import REGION_GEO_AREA, get_catalog, get_indicator_year
from app.bes_data import (
    BES_SOURCE_URLS,
    MIN_PUBLIC_COVERAGE,
    bes_indicator_path,
    get_bes_manifest,
    get_bes_rows,
)
from app.multiscopo_data import (
    SOURCE_URL as MULTISCOPO_SOURCE_URL,
    get_multiscopo_manifest,
    get_multiscopo_rows,
    has_multiscopo_data,
    multiscopo_indicator_path,
)
from app.eurostat_atlas import all_eurostat_indicators, get_eurostat_atlas_indicator, has_eurostat_data
from app.taxonomy import DUPLICATE_BES_IDS, category_metadata
from app import profiles

COMPARE_CHOICES = ("region_a", "region_b", "timeout")
ORDER_COUNTS = (3, 5)
MAX_DIFFICULTY = 4
# Finestra (min, max) di distanza tra i due VALORI DISTINTI in gara, come
# frazione dell'intervallo di indici distinti disponibili: a livello 0 la
# coppia è lontana in classifica (facile capire chi è maggiore), ai livelli
# alti è quasi adiacente. Espressa come rapporto (non come conteggio fisso di
# rank) perché il numero di valori distinti varia da un indicatore all'altro
# quando ci sono pareggi: le stesse proporzioni restano valide indipendentemente
# da quanti valori distinti abbia l'indicatore pescato (sempre >= _MIN_DISTINCT_VALUES).
_DIFFICULTY_GAP_RATIO = {0: (0.63, 1.0), 1: (0.42, 0.58), 2: (0.26, 0.37), 3: (0.16, 0.21), 4: (0.05, 0.11)}
# Il pool richiede almeno questo numero di valori distinti nell'anno più
# recente, così lo stesso pool serve anche l'ordinamento a 5 senza pareggi.
_MIN_DISTINCT_VALUES = 6
_BES_PREFIX = "bes:"
_BES_MIN_YEAR = 2025
_MULTI_PREFIX = "multiscopo:"
_MULTI_MIN_YEAR = 2023
_EUR_PREFIX = "eur:"


@cache.memoize(timeout=3600)
def _bes_region_payload(indicator_id, year):
    """Adapt one national BES regional indicator to the atlas quiz shape."""
    raw_id = indicator_id[len(_BES_PREFIX):] if indicator_id.startswith(_BES_PREFIX) else indicator_id
    info = get_bes_manifest("regione").get(raw_id)
    if info is None or info["year_max"] != year or year < _BES_MIN_YEAR:
        return None
    values = [
        {
            "region": row["territory"],
            "region_key": row["territory_key"],
            "value": row["value"],
        }
        for row in get_bes_rows("regione")
        if row["id"] == raw_id and row["year"] == year
        and row["territory_key"] and row["value"] is not None
    ]
    values.sort(key=lambda row: row["value"], reverse=True)
    public_theme = category_metadata(info["domain_name"])
    return {
        "metadata": {
            "id": f"{_BES_PREFIX}{raw_id}",
            "name": info["name"],
            **public_theme,
            "unit": info["unit"],
            "year": year,
            "source_label": "Istat, BES nazionale",
            "source_url": BES_SOURCE_URLS["regione"],
            "description": info["explain"]["plain"],
            "value_explanation": info["explain"]["example"],
            "path": bes_indicator_path(raw_id, info["name"]),
        },
        "values": values,
    }


@cache.memoize(timeout=3600)
def _multi_region_payload(indicator_id, year):
    """Adapt one Multiscopo regional indicator to the atlas quiz shape."""
    raw_id = indicator_id[len(_MULTI_PREFIX):] if indicator_id.startswith(_MULTI_PREFIX) else indicator_id
    info = get_multiscopo_manifest().get(raw_id)
    if info is None or info["year_max"] != year or year < _MULTI_MIN_YEAR:
        return None
    values = [
        {
            "region": row["territory"],
            "region_key": row["territory_key"],
            "value": row["value"],
        }
        for row in get_multiscopo_rows()
        if row["id"] == raw_id and row["year"] == year
        and row["territory_key"] and row["value"] is not None
    ]
    values.sort(key=lambda row: row["value"], reverse=True)
    public_theme = category_metadata(info["domain_name"])
    return {
        "metadata": {
            "id": f"{_MULTI_PREFIX}{raw_id}",
            "name": info["name"],
            **public_theme,
            "unit": info["unit"],
            "year": year,
            "source_label": "Istat, Indagine Multiscopo sulle famiglie",
            "source_url": MULTISCOPO_SOURCE_URL,
            "description": info["explain"]["plain"],
            "value_explanation": info["explain"]["example"],
            "path": multiscopo_indicator_path(raw_id, info["name"]),
        },
        "values": values,
    }


@cache.memoize(timeout=3600)
def _eurostat_region_payload(indicator_id, year):
    """Adapt one Eurostat regional indicator to the atlas quiz shape."""
    payload = get_eurostat_atlas_indicator(indicator_id)
    if payload is None or payload["metadata"]["year_max"] != year:
        return None
    meta = payload["metadata"]
    values = sorted(
        (
            {"region": row["region"], "region_key": row["region_key"], "value": row["value"]}
            for row in payload["series"]
            if row["year"] == year and row["region_key"] and row["value"] is not None
        ),
        key=lambda row: row["value"],
        reverse=True,
    )
    return {
        "metadata": {
            "id": meta["id"],
            "name": meta["name"],
            "theme": meta["theme"],
            "source_theme": meta.get("source_theme"),
            "macro_area": meta["macro_area"],
            "unit": meta["unit"],
            "year": year,
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta["explain"]["plain"],
            "value_explanation": meta["explain"]["example"],
            "path": meta["path"],
        },
        "values": values,
    }


def _quiz_indicator_payload(indicator_id, year):
    if indicator_id.startswith(_BES_PREFIX):
        return _bes_region_payload(indicator_id, year)
    if indicator_id.startswith(_MULTI_PREFIX):
        return _multi_region_payload(indicator_id, year)
    if indicator_id.startswith(_EUR_PREFIX):
        return _eurostat_region_payload(indicator_id, year)
    return get_indicator_year(indicator_id, year)


@cache.memoize(timeout=3600)
def _bes_quiz_indicators():
    pool = []
    manifest = get_bes_manifest("regione")
    for raw_id, info in manifest.items():
        if raw_id in DUPLICATE_BES_IDS:
            continue
        if info["year_max"] < _BES_MIN_YEAR or info["coverage_latest"] < MIN_PUBLIC_COVERAGE:
            continue
        payload = _bes_region_payload(f"{_BES_PREFIX}{raw_id}", info["year_max"])
        if payload is None:
            continue
        values = payload["values"]
        if len({row["value"] for row in values}) < _MIN_DISTINCT_VALUES:
            continue
        meta = payload["metadata"]
        pool.append({
            "id": meta["id"],
            "name": meta["name"],
            "theme": meta["theme"],
            "source_theme": meta["source_theme"],
            "macro_area": meta["macro_area"],
            "unit": meta["unit"],
            "year": info["year_max"],
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta["description"],
            "value_explanation": meta["value_explanation"],
            "ranking": values,
        })
    return pool


@cache.memoize(timeout=3600)
def _multiscopo_quiz_indicators():
    if not has_multiscopo_data():
        return []
    pool = []
    manifest = get_multiscopo_manifest()
    for raw_id, info in manifest.items():
        if info["year_max"] < _MULTI_MIN_YEAR or info["coverage_latest"] < MIN_PUBLIC_COVERAGE:
            continue
        payload = _multi_region_payload(f"{_MULTI_PREFIX}{raw_id}", info["year_max"])
        if payload is None:
            continue
        values = payload["values"]
        if len({row["value"] for row in values}) < _MIN_DISTINCT_VALUES:
            continue
        meta = payload["metadata"]
        pool.append({
            "id": meta["id"],
            "name": meta["name"],
            "theme": meta["theme"],
            "source_theme": meta["source_theme"],
            "macro_area": meta["macro_area"],
            "unit": meta["unit"],
            "year": info["year_max"],
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta["description"],
            "value_explanation": meta["value_explanation"],
            "ranking": values,
        })
    return pool


@cache.memoize(timeout=3600)
def _eurostat_quiz_indicators():
    if not has_eurostat_data():
        return []
    pool = []
    for item in all_eurostat_indicators():
        year = item["year_max"]
        payload = _eurostat_region_payload(item["id"], year)
        if payload is None:
            continue
        values = payload["values"]
        if len({row["value"] for row in values}) < _MIN_DISTINCT_VALUES:
            continue
        meta = payload["metadata"]
        pool.append({
            "id": meta["id"],
            "name": meta["name"],
            "theme": meta["theme"],
            "source_theme": meta["source_theme"],
            "macro_area": meta["macro_area"],
            "unit": meta["unit"],
            "year": year,
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta["description"],
            "value_explanation": meta["value_explanation"],
            "ranking": values,
        })
    return pool


@cache.memoize(timeout=3600)
def _quiz_indicators():
    """Indicatori idonei alle modalità quiz: core (completi e recenti), non
    varianti di genere, con abbastanza valori distinti nell'anno più recente.
    Ogni voce porta la classifica per valore già ordinata (decrescente)."""
    pool = []
    for item in get_catalog()["indicators"]:
        if not profiles.is_core(item) or profiles.is_gender_variant(item):
            continue
        year = item["year_max"]
        payload = get_indicator_year(item["id"], year)
        if payload is None:
            continue
        rows = payload["values"]  # non-null, già ordinati per valore desc
        if len({row["value"] for row in rows}) < _MIN_DISTINCT_VALUES:
            continue
        pool.append({
            "id": item["id"],
            "name": item["name"],
            # get_catalog() already carries the canonical category (see app/data.py).
            "category_slug": item.get("category_slug"),
            "theme_slug": item.get("theme_slug"),
            "theme": item["theme"],
            "source_theme": item.get("source_theme"),
            "macro_area": item["macro_area"],
            "unit": item["unit"],
            "year": year,
            "source_label": item["source_label"],
            "source_url": item["source_url"],
            "description": item["explain"]["plain"],
            "value_explanation": item["explain"]["example"],
            "ranking": [
                {"region": row["region"], "region_key": row["region_key"], "value": row["value"]}
                for row in rows
            ],
        })
    # The comparison and ordering games can safely mix the atlas with the
    # current national BES regional series. IDs are namespaced as ``bes:...``
    # so answer validation remains unambiguous even when source codes overlap.
    pool.extend(_bes_quiz_indicators())
    pool.extend(_multiscopo_quiz_indicators())
    pool.extend(_eurostat_quiz_indicators())
    return pool


def _indicator_fields(entry):
    # La spiegazione chiarisce la metrica senza rivelare valori o ordinamento,
    # quindi può accompagnare la domanda fin dall'inizio del round.
    return {
        "id": entry["id"],
        "name": entry["name"],
        "theme": entry["theme"],
        "source_theme": entry.get("source_theme"),
        "macro_area": entry["macro_area"],
        "unit": entry["unit"],
        "year": entry["year"],
        "source_label": entry["source_label"],
        "source_url": entry["source_url"],
        "description": entry["description"],
        "value_explanation": entry["value_explanation"],
    }


def _region_fields(row):
    # geo_area is the Istat geographic partition (Nord/Centro/Sud/Isole), used
    # only as a label under the region name in the quiz UI. BES rows carry no
    # region_key in REGION_GEO_AREA for aggregate territories, hence the .get.
    return {
        "region": row["region"],
        "region_key": row["region_key"],
        "geo_area": REGION_GEO_AREA.get(row["region_key"]),
    }


def _clamp_difficulty(difficulty):
    try:
        level = int(difficulty)
    except (TypeError, ValueError):
        return 0
    return max(0, min(level, MAX_DIFFICULTY))


def _distinct_values(ranking):
    """Valori distinti nella classifica, ordinati dal più alto al più basso,
    e l'indice (nella classifica originale) di una riga per ciascun valore.
    Costruito una volta per round: rende la scelta della coppia un'operazione
    diretta invece di un tentativo-ed-errore su valori potenzialmente ripetuti."""
    seen = {}
    order = []
    for row in ranking:
        if row["value"] not in seen:
            seen[row["value"]] = []
            order.append(row["value"])
        seen[row["value"]].append(row)
    return order, seen


def compare_round(difficulty=0):
    """Round di "Chi è maggiore?": un indicatore e due regioni con distanza
    (tra valori distinti) via via più stretta al crescere della difficoltà.
    Mai i valori. Nessun tentativo-ed-errore: la coppia è scelta direttamente
    tra valori diversi, quindi il risultato è sempre valido al primo colpo."""
    level = _clamp_difficulty(difficulty)
    ratio_min, ratio_max = _DIFFICULTY_GAP_RATIO[level]
    entry = random.choice(_quiz_indicators())
    distinct, rows_by_value = _distinct_values(entry["ranking"])
    n = len(distinct)  # sempre >= _MIN_DISTINCT_VALUES

    max_index_gap = n - 1
    # ceil/floor rispettano davvero i limiti proporzionali. round() poteva
    # produrre, per esempio, 4/7 al livello facile, sotto la soglia minima.
    min_gap = max(1, math.ceil(ratio_min * max_index_gap))
    max_gap = max(min_gap, math.floor(ratio_max * max_index_gap))
    max_gap = min(max_gap, max_index_gap)
    gap = random.randint(min_gap, max_gap)
    i = random.randint(0, n - 1 - gap)

    a = random.choice(rows_by_value[distinct[i]])
    b = random.choice(rows_by_value[distinct[i + gap]])

    pair = [a, b]
    random.shuffle(pair)
    return {
        "indicator": _indicator_fields(entry),
        "region_a": _region_fields(pair[0]),
        "region_b": _region_fields(pair[1]),
        "difficulty": level,
    }


def _value_for(indicator_id, year, region_key):
    payload = _quiz_indicator_payload(indicator_id, year)
    if payload is None:
        return None
    for row in payload["values"]:
        if row["region_key"] == region_key:
            return row["value"]
    return None


def evaluate_compare(indicator_id, year, region_a_key, region_b_key, choice):
    """Valuta una risposta di "Chi è maggiore?", o None se l'input non è
    valido (il chiamante risponde 400). "timeout" conta come errore ma la
    risposta rivela comunque vincitore e valori."""
    if choice not in COMPARE_CHOICES:
        return None
    if not isinstance(indicator_id, str) or not isinstance(year, int):
        return None
    if region_a_key == region_b_key:
        return None
    name_a = profiles.region_name(region_a_key)
    name_b = profiles.region_name(region_b_key)
    if name_a is None or name_b is None:
        return None
    payload = _quiz_indicator_payload(indicator_id, year)
    if payload is None or not payload["values"]:
        return None
    value_a = _value_for(indicator_id, year, region_a_key)
    value_b = _value_for(indicator_id, year, region_b_key)
    if value_a is None or value_b is None or value_a == value_b:
        return None

    winner = "region_a" if value_a > value_b else "region_b"
    meta = payload["metadata"]
    public_theme = category_metadata(meta.get("source_theme") or meta["theme"])
    return {
        "correct": choice == winner,
        "choice": choice,
        "winner": winner,
        "indicator": {
            "id": meta["id"],
            "name": meta["name"],
            **public_theme,
            "unit": meta["unit"],
            "year": year,
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta.get("description") or meta["explain"]["plain"],
            "value_explanation": meta.get("value_explanation") or meta["explain"]["example"],
        },
        "region_a": {"region": name_a, "region_key": region_a_key, "value": value_a},
        "region_b": {"region": name_b, "region_key": region_b_key, "value": value_b},
    }


def order_round(count):
    """Round di "Ordina le regioni": un indicatore e `count` regioni con
    valori tutti distinti, restituite in ordine casuale e senza valori.
    Nessun tentativo-ed-errore: `random.sample` su indici di valori distinti
    garantisce `count` valori diversi in un colpo solo (il pool richiede
    sempre almeno _MIN_DISTINCT_VALUES valori distinti, quindi la scelta
    esiste sempre per ogni count ammesso)."""
    if count not in ORDER_COUNTS:
        return None
    entry = random.choice(_quiz_indicators())
    distinct, rows_by_value = _distinct_values(entry["ranking"])

    indices = random.sample(range(len(distinct)), count)
    chosen = [random.choice(rows_by_value[distinct[i]]) for i in indices]

    shuffled = list(chosen)
    random.shuffle(shuffled)
    return {
        "indicator": _indicator_fields(entry),
        "regions": [_region_fields(row) for row in shuffled],
        "count": count,
    }


def evaluate_order(indicator_id, year, region_keys):
    """Valuta un ordinamento proposto (dal valore più alto al più basso), o
    None se l'input non è valido. Credito parziale: un punto per ogni
    regione nella posizione esatta."""
    if not isinstance(indicator_id, str) or not isinstance(year, int):
        return None
    if not isinstance(region_keys, list) or len(region_keys) not in ORDER_COUNTS:
        return None
    if len(set(region_keys)) != len(region_keys):
        return None
    names = {}
    for key in region_keys:
        name = profiles.region_name(key)
        if name is None:
            return None
        names[key] = name

    payload = _quiz_indicator_payload(indicator_id, year)
    if payload is None or not payload["values"]:
        return None
    values = {}
    for key in region_keys:
        value = _value_for(indicator_id, year, key)
        if value is None:
            return None
        values[key] = value
    if len(set(values.values())) != len(region_keys):
        return None  # con un pareggio non esiste un ordine corretto univoco

    correct_keys = sorted(region_keys, key=lambda key: values[key], reverse=True)
    correct_position = {key: idx + 1 for idx, key in enumerate(correct_keys)}

    positions = []
    score = 0
    for idx, key in enumerate(region_keys):
        guessed = idx + 1
        right = correct_position[key]
        hit = guessed == right
        if hit:
            score += 1
        positions.append({
            "region": names[key],
            "region_key": key,
            "value": values[key],
            "guessed_position": guessed,
            "correct_position": right,
            "correct": hit,
        })

    meta = payload["metadata"]
    return {
        "score": score,
        "total": len(region_keys),
        "positions": positions,
        "correct_order": [
            {"region": names[key], "region_key": key, "value": values[key]}
            for key in correct_keys
        ],
        "indicator": {
            "id": meta["id"],
            "name": meta["name"],
            "unit": meta["unit"],
            "year": year,
            "source_label": meta["source_label"],
            "source_url": meta["source_url"],
            "description": meta.get("description") or meta["explain"]["plain"],
            "value_explanation": meta.get("value_explanation") or meta["explain"]["example"],
        },
    }
