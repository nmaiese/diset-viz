"""One-shot conversion of the analyst notes into the indicator article schema.

The old note had three loose prose fields written against three separate briefs
(`attacco`, `spunto`, `limite`) plus sources and a vintage. The page now renders
one article with four ordered roles, and the writer agent owns all four.

The mapping is a role reassignment, not a rename:

    attacco -> lead                 the standalone opening, still the SERP description
    spunto  -> sections[quadro]     the interpretation of the current picture
    limite  -> sections[limiti]     what the number does not capture

`definizione` and `dinamica` are left unwritten on purpose. The page composes
them from the data until the writer passes, so every indicator renders the same
four-section skeleton from day one, and scripts/text_queue.py can list exactly
what still needs a human pass.

Headings are left null: the template falls back to the role's default title, and
the agent replaces it with one written for this indicator.

    .venv/bin/python -m scripts.migrate_notes_to_texts

Reads app/static/data/analyst_notes.json and writes indicator_texts.json beside
it. The source file is left in place: the mapping above must be reviewed on
rendered pages before the original prose is thrown away.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "data"
NOTES = DATA_DIR / "analyst_notes.json"
TEXTS = DATA_DIR / "indicator_texts.json"


def migrate(notes):
    texts = {}
    for indicator_id, note in notes.items():
        sections = []
        for role, field in (("quadro", "spunto"), ("limiti", "limite")):
            body = (note.get(field) or "").strip()
            if body:
                sections.append({"role": role, "h": None, "body": body})
        entry = {
            "lead": (note.get("attacco") or "").strip() or None,
            "sections": sections,
            "fonti": note.get("fonti") or [],
        }
        if isinstance(note.get("vintage"), int):
            entry["vintage"] = note["vintage"]
        texts[indicator_id] = entry
    return texts


def main():
    notes = json.loads(NOTES.read_text(encoding="utf-8"))
    texts = migrate(notes)
    TEXTS.write_text(
        json.dumps(texts, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    written = sum(len(entry["sections"]) for entry in texts.values())
    leads = sum(1 for entry in texts.values() if entry["lead"])
    print(f"{len(texts)} indicators, {leads} leads, {written} authored sections -> {TEXTS}")


if __name__ == "__main__":
    main()
