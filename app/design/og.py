"""Le immagini da condividere di regioni e province, e dove stanno.

Le disegna `scripts/og_territori.py`, una volta, e si committano come PNG in
`app/static/img/og/territori/`: nessuna conversione a runtime, come le
copertine del blog (`scripts/rasterize_og_images.py`). Qui c'e' solo il nome
del file, uno per territorio, e la risposta alla domanda che fa il template:
questo territorio ha la sua figura, o si ripiega su quella del sito?
"""

from __future__ import annotations

import re
from pathlib import Path

LEVELS = ("regione", "provincia")
WIDTH = 1200
HEIGHT = 630
DIRECTORY = Path(__file__).resolve().parents[1] / "static" / "img" / "og" / "territori"
PUBLIC_ROOT = "/static/img/og/territori"

# Le chiavi dei territori sono slug: una chiave con un punto o una barra non e'
# un territorio, e non deve diventare un percorso sul disco.
_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def filename(level_key: str, key: str) -> str:
    """Il nome del PNG di un territorio: `provincia-isernia.png`.

    Solleva ValueError su un livello che non e' regione o provincia, o su una
    chiave che non e' uno slug: e' un errore di chi chiama, non un territorio
    senza figura.
    """
    if level_key not in LEVELS:
        raise ValueError(f"livello sconosciuto per l'immagine da condividere: {level_key!r}")
    if not isinstance(key, str) or not _KEY.match(key):
        raise ValueError(f"chiave di territorio non valida: {key!r}")
    return f"{level_key}-{key}.png"


def og_image(level_key: str, key: str) -> str | None:
    """Il percorso pubblico dell'immagine del territorio, o None se il file non c'e'.

    None vuol dire "questo territorio non ha ancora la sua figura", e il
    template tiene quella del sito. Un livello sconosciuto solleva ValueError:
    e' un errore di cablaggio, e un None lo nasconderebbe. Una chiave che non
    e' uno slug non puo' avere un file, quindi da' None.
    """
    if level_key not in LEVELS:
        raise ValueError(f"livello sconosciuto per l'immagine da condividere: {level_key!r}")
    if not isinstance(key, str) or not _KEY.match(key):
        return None
    name = filename(level_key, key)
    if (DIRECTORY / name).is_file():
        return f"{PUBLIC_ROOT}/{name}"
    return None
