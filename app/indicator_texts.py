"""The editorial layer of an indicator page: one article, four ordered roles.

The page used to concatenate eight independent prose slots, each written against
its own local brief and none written to lead into the next. That is why the text
read as disconnected even when every sentence was individually correct. It also
meant the writer agent only owned three of those slots and the rest stayed
procedural.

Now there is one article. Its structure is fixed so 621 pages stay uniform, its
surface is not: the agent writes the heading as well as the body, because
identical H2s across the whole catalogue read like a stamp (content/STYLE.md).

    definizione   what it measures, the perimeter, what a value means
    quadro        how it is distributed right now, and what that says
    dinamica      how it moved, over the series and in the latest year
    limiti        what the number does not capture

Roles the JSON does not carry are composed from the data at render time by the
template, never frozen into the file. Two reasons: composed text cannot silently
age behind a data refresh, and the vintage guard then applies only to sentences a
human or an agent actually wrote.

The prose lives in ``content/indicators/``, one file per article (never in the
.py, per the editorial pipeline), and is loaded once for the life of the
process like the other on-disk artifacts. Editing it requires a gunicorn
restart.

The layout and the reason for it live in ``scripts/indicator_store.py``, which
owns the files. The short version: writer and reviewer are the only two stages
that may touch prose, they run daily, and one JSON object holding 365 articles
made every pair of concurrent runs a merge conflict on a file no agent can
resolve by reading it.
"""

import functools

from app import sources
from scripts import indicator_store

# Ordered. The default heading is a fallback for pages the agent has not reached
# yet; an authored `h` always wins.
ROLES = (
    ("definizione", "Che cosa misura, in concreto"),
    ("quadro", "Come si distribuisce oggi"),
    ("dinamica", "Come è cambiato nel tempo"),
    ("limiti", "Che cosa questo dato non dice"),
)
ROLE_ORDER = [role for role, _ in ROLES]
DEFAULT_HEADINGS = dict(ROLES)

# The level an entry describes when it does not say. Every article written so
# far is regional, and every family except BES has regions as its only level.
DEFAULT_LEVEL = "regione"

# Namespaces to try when a caller passes a bare id (the quality-of-life pages
# do). Read from the source registry so a new family is looked up the day it is
# registered, instead of being invisible to the editorial layer until someone
# remembers this list.
_NAMESPACES = tuple(
    meta["internal_prefix"] for meta in sources.SOURCES.values() if meta["internal_prefix"]
)


@functools.lru_cache(maxsize=1)
def _load():
    try:
        return indicator_store.load_all()
    except (OSError, ValueError, indicator_store.StoreError):
        return {}


def get_text(indicator_id):
    """The stored entry for an indicator id, or None.

    Tries the bare id first (territorial ids and any already-namespaced key),
    then the namespaced variants, because the quality-of-life callers pass the
    bare id.
    """
    data = _load()
    if not data:
        return None
    iid = str(indicator_id)
    for key in (iid, *(f"{prefix}{iid}" for prefix in _NAMESPACES)):
        entry = data.get(key)
        if entry:
            return entry
    return None


def build_article(indicator_id, level_key=DEFAULT_LEVEL):
    """The four sections in order, each flagged authored or composed.

    `body` is None for a composed section: the template renders that role from
    the data instead. Callers must not treat None as an empty section.

    Prose is written against one territorial level and cites that level's
    figures. The 31 BES articles that exist for two-level indicators were all
    written against the regions, so on ``?livello=provincia`` they would name
    Umbria and Piemonte under a cockpit of provinces. An entry therefore
    declares the level it describes and is used only there; every other level
    falls back to the composed skeleton, which reads the level it is given.
    """
    entry = get_text(indicator_id) or {}
    if (entry.get("level") or DEFAULT_LEVEL) != (level_key or DEFAULT_LEVEL):
        entry = {}
    authored = {
        section["role"]: section
        for section in entry.get("sections") or []
        if section.get("role") in DEFAULT_HEADINGS and (section.get("body") or "").strip()
    }
    sections = []
    for role in ROLE_ORDER:
        written = authored.get(role)
        heading = (written.get("h") or "").strip() if written else ""
        sections.append({
            "role": role,
            "heading": heading or DEFAULT_HEADINGS[role],
            "body": written["body"].strip() if written else None,
            "authored": written is not None,
        })
    return {
        "lead": (entry.get("lead") or "").strip() or None,
        "sections": sections,
        "fonti": entry.get("fonti") or [],
        "vintage": entry.get("vintage") if isinstance(entry.get("vintage"), int) else None,
        "authored_count": len(authored),
    }


def composed_lead(meta, level):
    """The opening line for an indicator nobody has written a lead for yet.

    It states what the page holds, never what the numbers are. The previous
    version opened with the best region, the worst region and the mean, which is
    exactly what the KPI row prints a few centimetres below it, so 260 pages read
    as a stat dump repeated twice. It is also the SERP description and the
    Dataset JSON-LD description, so it has to stand alone and be unique per
    indicator: the plain definition supplies both.
    """
    plain = (meta.get("explain") or {}).get("plain") or ""
    count = len(level["observations"])
    noun = level["singular"] if count == 1 else level["plural"]
    institution = meta.get("institution") or "Istat"
    span = (
        f"dal {level['year_min']} al {level['year_max']}"
        if level["year_min"] != level["year_max"]
        else f"nel {level['year_max']}"
    )
    views = "con mappa, classifica e serie storica" if level["has_map"] else "con classifica e serie storica"
    if level["year_min"] == level["year_max"]:
        views = "con mappa e classifica" if level["has_map"] else "con la classifica completa"
    second = f"Dati {institution} per {count} {noun}, {span}, {views}."
    return f"{plain} {second}".strip() if plain else second


def text_vintage(indicator_id):
    """Data year the hand-written figures were validated against, or None.

    The drift guard compares this to the indicator's current year_max, so an
    article is flagged for review once the data moves past what it describes.
    """
    entry = get_text(indicator_id)
    if not entry:
        return None
    value = entry.get("vintage")
    return int(value) if isinstance(value, int) else None
