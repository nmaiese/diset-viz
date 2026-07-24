"""Loader for the analyst-voice indicator notes.

The prose lives in ``app/static/data/analyst_notes.json`` (never in the .py, per
the editorial pipeline), keyed by indicator id. Numeric ids match the atlas
catalog directly; BES and Multiscopo indicators are keyed with their ``bes:`` /
``multiscopo:`` namespace in the JSON, while the quality-of-life page passes the
bare id, so the lookup tries the namespaced forms too.

Loaded once for the life of the process (``lru_cache``), like the core data
loaders. Editing the JSON requires a gunicorn restart to take effect, same as
the other on-disk artifacts.
"""

import functools
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "static" / "data" / "analyst_notes.json"


@functools.lru_cache(maxsize=1)
def _load():
    try:
        with open(_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get_analyst_note(indicator_id):
    """Return the note dict for an indicator id, or None if absent.

    Tries the bare id first (numeric atlas ids and any already-namespaced key),
    then the BES and Multiscopo namespaced variants used by the quality-of-life
    pages.
    """
    data = _load()
    if not data:
        return None
    iid = str(indicator_id)
    for key in (iid, f"bes:{iid}", f"multiscopo:{iid}"):
        note = data.get(key)
        if note:
            return note
    return None


def note_vintage(indicator_id):
    """Data year the note's hand-written figures were validated against, or None.

    The drift guard (tests/test_analyst_notes.py) compares this to the
    indicator's current year_max so a note is flagged for review once the data
    moves past the vintage it was written for.
    """
    note = get_analyst_note(indicator_id)
    if not note:
        return None
    value = note.get("vintage")
    return int(value) if isinstance(value, int) else None
