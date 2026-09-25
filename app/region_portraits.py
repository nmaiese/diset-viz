"""Il ritratto di una regione: la prosa che sta in cima a /regione/<key>.

Fino al 25/9/2026 la pagina regione era solo righe "indicatore, valore,
posizione", e Search Console dava quindici regioni su venti "scansionate ma non
indicizzate". Il ritratto e' la parte che racconta il territorio a una persona.
Sta in `content/regioni/<key>.md`, con un frontmatter corto:

    titolo: l'H2 che dice la tesi
    fonti: gli URL esterni citati nella prosa

Le cifre del ritratto vengono dagli stessi dati della pagina, e si rileggono
quando i dati si aggiornano: a differenza delle sintesi, la prosa non si
ricalcola da sola.
"""
import re
from functools import lru_cache
from pathlib import Path

import frontmatter

CARTELLA = Path(__file__).resolve().parents[1] / "content" / "regioni"
DESCRIZIONE_MAX = 155


def _prima_frase(testo):
    piano = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", testo).strip()
    frase = re.split(r"(?<=[.!?])\s", piano, maxsplit=1)[0]
    if len(frase) <= DESCRIZIONE_MAX:
        return frase
    return frase[: DESCRIZIONE_MAX - 3].rsplit(" ", 1)[0] + "..."


@lru_cache(maxsize=None)
def get(region_key):
    path = CARTELLA / f"{region_key}.md"
    if not path.is_file():
        return None
    post = frontmatter.load(path)
    body = post.content.strip()
    if not body:
        return None
    return {
        "titolo": str(post.get("titolo") or "").strip(),
        "body": body,
        "fonti": [str(u) for u in (post.get("fonti") or [])],
        "descrizione": _prima_frase(body),
    }
