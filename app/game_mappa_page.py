"""La pagina `/quiz/province-italiane` di "Dov'è la provincia?": che cosa serve al template.

Il gioco (sessione, risposta, punteggio) sta in `app/game_mappa.py`. Qui c'e' solo cio' che la
pagina scrive in chiaro, e che non puo' dipendere da nessun payload ne' dal seed (la pagina
risponde 200 anche senza `GAME_SEED_KEY`):

- i gruppi di sagome per regione, con il riquadro di ogni regione (`maps.zoom`) che il client
  usa per stringere la mappa. La mappa si disegna dal template e il client la rende viva
  dall'esterno: i centri per la tastiera li legge dal DOM con `getBBox()`;
- l'elenco alfabetico indicizzabile delle province, da `game_mappa.static_list()` (non si
  duplica: le forme ufficiali stanno in `game_mappa.OFFICIAL_NAMES`);
- la riga di attribuzione dei confini, composta da `sources.PROVINCE_BOUNDARIES`;
- la frase sulla Sardegna, col numero delle province che viene dal pool.

Nessun nome di provincia e nessuna coordinata stanno scritti a mano nel template: la risposta
di una domanda e' lo slug sulla sagoma, e non si puo' nascondere (il server valuta comunque), ma
almeno non si moltiplica.
"""

from __future__ import annotations

from functools import lru_cache

from markupsafe import Markup, escape

from app import game_daily, game_mappa, sources
from app.data import REGION_ORDER
from app.design import maps
from app.profiles import region_key_for

PATH = "/quiz/province-italiane"
GAME_NAME = "Dov'è la provincia?"
H1 = "Quiz sulle province italiane"

# Il numero di unita' dell'Istat dal 1 gennaio 2026 e' un fatto dell'Istat, non viene dal pool
# (che e' a 107): tiene il suo posto qui e non si ricava da nessun dato del sito.
ISTAT_UNITS_2026 = 110


def sardinia_note(total: int) -> str:
    """La frase sulla Sardegna: i tracciati e i dati sono quelli in vigore fino al 31
    dicembre 2025, e il giocatore che conosce la Sardegna di oggi deve saperlo. `total` e' il
    numero di province del pool, mai scritto a mano."""
    return (
        f"La mappa mostra le {total} province in vigore fino al 31 dicembre 2025, con i confini "
        "Istat del 2023. Dal 1° gennaio 2026 la Sardegna ha un nuovo assetto, con due città "
        f"metropolitane e sei province, e l'Istat conta {ISTAT_UNITS_2026} unità territoriali: "
        "in questa mappa la Sardegna è ancora quella precedente."
    )


def attribution(site_name: str) -> Markup:
    """La riga sotto la mappa: "Confini delle province: Istat (CC BY 4.0), ridistribuiti da
    openpolis, semplificati e riproiettati da Divario Italia." con tre link. Dai campi di
    `sources.PROVINCE_BOUNDARIES`, mai scritta in un template. "Semplificati e riproiettati"
    e' vero: `design/v1/tools/province_map.py` semplifica i tracciati (`simplify`) e li
    proietta nel viewBox delle regioni."""
    b = sources.PROVINCE_BOUNDARIES

    def link(testo: str, url: str) -> str:
        return f'<a href="{escape(url)}">{escape(testo)}</a>'

    return Markup(
        "Confini delle province: "
        f"{link(b['institution'], b['institution_url'])} ({link(b['license_label'], b['license_url'])}), "
        f"ridistribuiti da {link(b['redistributor'], b['redistributor_url'])}, "
        f"semplificati e riproiettati da {escape(site_name)}."
    )


@lru_cache(maxsize=1)
def region_groups() -> tuple[dict, ...]:
    """Per ogni regione, nell'ordine di `REGION_ORDER`: `{key, viewbox, provinces}`, con le
    chiavi delle sue province in ordine di chiave. Il riquadro e' quello di `maps.zoom`, lo
    stesso che usa Indovina la Provincia. Non cambia fra un giorno e l'altro."""
    per_region: dict[str, list[str]] = {}
    for p in game_daily.province_pool():
        per_region.setdefault(p["region_key"], []).append(p["key"])
    return tuple(
        {
            "key": key,
            "viewbox": maps.zoom(key)["viewbox"],
            "provinces": tuple(sorted(per_region.get(key, ()))),
        }
        for key in (region_key_for(r) for r in REGION_ORDER)
    )


def page(site_name: str) -> dict:
    """Il contesto del template. Il totale delle province e' sempre `len(province_pool())`."""
    total = len(game_daily.province_pool())
    return {
        "province_total": total,
        "groups": region_groups(),
        "list": game_mappa.static_list(),
        "attribution": attribution(site_name),
        "sardinia_note": sardinia_note(total),
    }
