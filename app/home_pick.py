"""L'indicatore in evidenza della home: uno a caso a ogni visita.

La home mostrava sempre il PIL pro capite, con tre alternative fisse in un
selettore. Adesso a ogni caricamento esce una coppia (indicatore, livello) dal
catalogo delle pagine indicizzabili, quello di sitemap e llms-full: una scheda
non indicizzabile (serie ferma, variante, copertura parziale) non e' un buon
biglietto da visita, e la home non deve mandare i lettori dove i motori non
vanno.

**Prima il livello, poi l'indicatore.** Le coppie regionali sono circa sette
volte quelle provinciali: pescando fra tutte insieme le province uscirebbero una
volta su otto. Scegliendo prima il livello escono una volta su due, che e' la
promessa della home ("o per regione o per provincia").

`?indicatore=ter-901&livello=provincia` fissa la scelta: serve alle prove e a
chi vuole condividere quello che vede. `?indicator=901`, il parametro del
selettore di prima, resta valido per i link gia' in giro.
"""

from __future__ import annotations

import random

from app import indicator_universe, indicator_view, sources

LEVELS = ("regione", "provincia")

# Sotto queste soglie la striscia del divario e la classifica dicono poco: una
# serie regionale con meta' delle regioni, una provinciale con un terzo delle
# province. Nel catalogo di oggi nessuna coppia indicizzabile ci cade, la soglia
# e' una guardia.
MIN_TERRITORIES = {"regione": 15, "provincia": 60}


def pool() -> dict[str, list[tuple[str, str]]]:
    """{livello: [(famiglia, raw_id), ...]} dal catalogo indicizzabile.

    Non si mette in cache: il catalogo lo e' gia' (`synchronized_cache`, per la
    vita del processo), e questo e' un giro di qualche centinaio di record."""
    out: dict[str, list[tuple[str, str]]] = {key: [] for key in LEVELS}
    for record in indicator_universe.indexable_catalog():
        code = record["meta"]["canonical_path"].rstrip("/").rsplit("/", 1)[-1]
        parsed = sources.parse_indicator_code(code)
        if parsed is None:
            continue
        for level in record["levels"]:
            key = level["key"]
            if key in out and (level.get("territory_count") or 0) >= MIN_TERRITORIES[key]:
                out[key].append(parsed)
    return out


def _requested(code: str | None) -> tuple[str, str] | None:
    """(famiglia, raw_id) da `ter-901`, o da `901` come nel selettore di prima."""
    if not code:
        return None
    code = code.strip()
    parsed = sources.parse_indicator_code(code)
    if parsed is None and code.isdigit():
        parsed = ("territorial", code)
    return parsed


def _choice(view: dict | None, level_key: str, candidates: dict, requested: bool = False) -> dict | None:
    """La scelta, se la coppia (indicatore, livello) sta nel pool: vale anche
    per quella chiesta con `?indicatore=`, cosi' un link non porta in home una
    scheda che il catalogo indicizzabile non ha, o un livello con poche righe.
    `other_level` e' l'altro livello dello stesso indicatore, solo se anche
    quello sta nel pool, e `other` il suo livello intero: la home li disegna
    tutti e due e passa dall'uno all'altro senza ricaricare."""
    if view is None:
        return None
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), None)
    code = view["meta"]["canonical_path"].rstrip("/").rsplit("/", 1)[-1]
    pair = sources.parse_indicator_code(code)
    if level is None or pair not in candidates.get(level_key, ()):
        return None
    other = next((key for key in LEVELS if key != level_key and pair in candidates.get(key, ())), None)
    other_view = next((lv for lv in view["levels"] if lv["key"] == other), None) if other else None
    return {"meta": view["meta"], "level": level, "other_level": other if other_view else None,
            "other": other_view, "requested": requested,
            # I livelli che la scheda ha davvero, anche fuori dal pool: la home
            # non deve dire "c'e' solo per regione" se la scheda ha le province.
            "available": [lv["key"] for lv in view["levels"]]}


def pick(code: str | None = None, level_key: str | None = None,
         rng: random.Random | None = None) -> dict | None:
    """L'indicatore in evidenza: `meta`, il `level` intero della scheda, l'altro
    livello se c'e' e se la scelta viene dall'URL. Quello chiesto se sta nel
    pool, se no uno a caso. `rng` serve alle prove, che vogliono estrazioni
    ripetibili."""
    choice = rng.choice if rng is not None else random.choice
    candidates = {key: set(pairs) for key, pairs in pool().items()}
    requested = _requested(code)
    if requested is not None:
        view = indicator_view.build_indicator_view(*requested)
        keys = [level_key] if level_key in LEVELS else list(LEVELS)
        for key in keys:
            chosen = _choice(view, key, candidates, requested=True)
            if chosen is not None:
                return chosen

    levels = [key for key in LEVELS if candidates[key]]
    if not levels:
        return None
    key = level_key if level_key in levels else choice(levels)
    family, raw_id = choice(sorted(candidates[key]))
    return _choice(indicator_view.build_indicator_view(family, raw_id), key, candidates)
