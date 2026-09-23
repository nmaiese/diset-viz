"""La ricerca trova i territori, non solo gli indicatori.

Fino al 23/9/2026 `/ricerca?q=Lecce` diceva "Nessun risultato", e la testata
prometteva di trovare "una regione". L'indice della ricerca conteneva solo
indicatori e articoli: le 20 regioni e le 107 province, che hanno una pagina
ciascuna, non c'erano.

Qui si cerca per nome, con le forme che la gente scrive davvero: senza accenti
("forli"), senza trattini ("emilia romagna"), con "provincia di" davanti, e con
le varianti che il nome ufficiale non contiene ("Bozen", "Reggio nell'Emilia").
"""
from __future__ import annotations

import re
import unicodedata

from app import profiles, province_profile

# Nomi che la gente scrive e che il nome ufficiale non contiene. La chiave e'
# la chiave della pagina, il valore le forme alternative gia' normalizzate.
ALIASES = {
    "bolzano": ("bozen", "bolzano bozen", "alto adige", "sudtirol", "suedtirol"),
    "reggio-emilia": ("reggio nell emilia",),
    "reggio-calabria": ("reggio di calabria",),
    "forli-cesena": ("forli", "cesena"),
    "pesaro-e-urbino": ("pesaro urbino",),
    "massa-carrara": ("massa carrara",),
    "barletta-andria-trani": ("bat", "barletta", "andria", "trani"),
    "monza-e-della-brianza": ("monza", "brianza", "monza brianza"),
    "trentino-alto-adige": ("trentino", "alto adige"),
    "friuli-venezia-giulia": ("friuli", "venezia giulia"),
    "valle-d-aosta": ("val d aosta", "vallee d aoste"),
}

# Le parole che si scrivono davanti al nome e non lo identificano.
_PREFIX = re.compile(
    r"^(?:(?:la |il )?(?:provincia|regione|citta metropolitana)(?: autonoma)?(?: di| del| della| dell)? )+"
)


def fold(value):
    """Minuscolo, senza accenti, trattini e apostrofi come spazi."""
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[-'’/]", " ", text.lower())
    return " ".join(text.split())


def clean_query(query):
    """La domanda senza "provincia di", "regione", "citta' metropolitana di"."""
    return _PREFIX.sub("", fold(query)).strip()


def _entries():
    overview = profiles.regions_overview()
    for key, region in overview.items():
        yield {
            "kind": "regione",
            "key": key,
            "name": region["region"],
            "path": region["path"],
            "context": "Regione",
        }
    for region_key, provinces in province_profile.by_region().items():
        for province in provinces:
            yield {
                "kind": "provincia",
                "key": province["key"],
                "name": province["name"],
                "path": province["path"],
                "context": f"Provincia, {overview[region_key]['region']}",
            }


def _score(names, query):
    """3 se un nome e' la domanda, 2 se la apre, 1 se la contiene o ci sta dentro."""
    best = 0
    words = f" {query} "
    for name in names:
        if name == query:
            return 3
        if name.startswith(query):
            best = max(best, 2)
        elif len(query) >= 3 and query in name:
            best = max(best, 1)
        elif len(name) >= 4 and f" {name} " in words:
            # "disoccupazione lecce": il territorio sta dentro una domanda
            # piu' lunga.
            best = max(best, 1)
    return best


def search_territories(query, limit=10):
    """Regioni e province che rispondono alla domanda, le piu' pertinenti prima.

    A parita' di pertinenza la provincia viene prima della regione: chi scrive
    "aosta" cerca piu' spesso la provincia che la Valle d'Aosta, e la regione
    resta subito sotto.
    """
    cleaned = clean_query(query)
    if len(cleaned) < 2:
        return []
    found = []
    for position, entry in enumerate(_entries()):
        names = (fold(entry["name"]), *ALIASES.get(entry["key"], ()))
        score = _score(names, cleaned)
        if score:
            found.append((-score, 0 if entry["kind"] == "provincia" else 1, position, entry))
    found.sort(key=lambda row: row[:3])
    return [row[3] for row in found[:limit]]
