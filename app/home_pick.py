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


def _choice(view: dict | None, level_key: str | None) -> dict | None:
    if view is None or not view.get("levels"):
        return None
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), view["levels"][0])
    if level["key"] not in LEVELS or len(level.get("observations") or []) < 2:
        return None
    return {
        "meta": view["meta"],
        "level": level,
        "levels": [lv["key"] for lv in view["levels"] if lv["key"] in LEVELS],
    }


def pick(code: str | None = None, level_key: str | None = None,
         rng: random.Random | None = None) -> dict | None:
    """L'indicatore in evidenza: `meta`, il `level` intero della scheda e i
    livelli che l'indicatore ha. Quello chiesto se esiste, se no uno a caso.
    `rng` serve alle prove, che vogliono estrazioni ripetibili."""
    choice = rng.choice if rng is not None else random.choice
    requested = _requested(code)
    if requested is not None:
        chosen = _choice(indicator_view.build_indicator_view(*requested), level_key)
        if chosen is not None:
            return chosen

    candidates = pool()
    levels = [key for key in LEVELS if candidates[key]]
    if not levels:
        return None
    key = level_key if level_key in levels else choice(levels)
    family, raw_id = choice(candidates[key])
    return _choice(indicator_view.build_indicator_view(family, raw_id), key)
