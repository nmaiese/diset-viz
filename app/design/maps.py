"""I tracciati delle mappe della 1.0, e lo sprite che li porta una volta sola.

Le regioni stanno in `italy_paths.json`, le province in `province_paths.json`
(`design/v1/tools/province_map.py`), nello stesso viewBox 560x660: i confini
regionali si disegnano sopra le province e combaciano.

La home ne disegna cinque, fra regioni e province. Con i tracciati scritti in
ogni mappa pesavano circa 67 KB compressi in piu', perche' il gzip non vede
due copie distanti piu' di 32 KB: lo sprite li scrive una volta in un `<svg>`
nascosto, e ogni mappa li richiama con `<use>`. Il colore lo prende l'`<use>`,
e il tracciato nello sprite non ne ha uno suo, cosi' lo eredita.
"""

from __future__ import annotations

import json
from pathlib import Path

from markupsafe import Markup

HERE = Path(__file__).resolve().parent
REGION_PATHS: dict[str, str] = json.loads((HERE / "italy_paths.json").read_text(encoding="utf-8"))
PROVINCE_PATHS: dict[str, str] = json.loads((HERE / "province_paths.json").read_text(encoding="utf-8"))
PREFIX = {"regione": "mr-", "provincia": "mp-"}


def paths(level_key: str) -> dict[str, str]:
    return REGION_PATHS if level_key == "regione" else PROVINCE_PATHS


def sprite(level_key: str | None = None) -> Markup:
    """L'`<svg>` con i tracciati di un livello (o di tutti e due), da mettere
    una volta in pagina prima della prima mappa che li usa. La home mette le
    regioni prima della testata (la mappa accanto alla ricerca) e le province
    dopo: 41 KB di tracciati davanti al titolo ne ritardavano il testo."""
    levels = [level_key] if level_key else list(PREFIX)
    defs = "".join(f'<path id="{PREFIX[lv]}{k}" d="{d}"/>' for lv in levels for k, d in paths(lv).items())
    return Markup(f'<svg class="map-sprite" aria-hidden="true" focusable="false"><defs>{defs}</defs></svg>')
