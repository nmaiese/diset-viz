"""The half of the writing rubric a regex can actually check, over every article.

`docs/WRITING_RUBRIC.md` scores an article on ten criteria. Six of them need a
reader: whether the lead makes a point, whether one thread runs through the four
sections, whether a cross-reference earns its place. Four do not, and those four
are the ones that rot quietly across hundreds of articles, because each instance
looks like a small stylistic slip and only the count makes it a problem.

So this is not a gate and it does not fail a build. It answers two questions the
rubric on its own cannot:

    which articles should a reviewer open first, of the ones with no other flag
    is the catalogue getting better or worse since the last batch

The second is why the aggregate exists. Before this, "the prose reads better now"
was an opinion. `--summary` turns it into a number that has to move.

Deliberately NOT checked here, and left in the rubric for a person: the rule of
three, the nut graf, the through-line, whether a digression earns its place.
An Italian sentence listing three nouns is ordinary prose, and a regex that
flagged it would cost more attention than it saves. A linter that cries wolf on
correct writing gets ignored, and then it protects nothing.

Pure stdlib, like every script in the chain: a cloud agent runs it on a fresh
checkout, before any venv exists.

    python3 scripts/prose_lint.py                  # i peggiori, in ordine
    python3 scripts/prose_lint.py --summary        # il totale, per misurare i progressi
    python3 scripts/prose_lint.py --show 178       # un articolo solo
    python3 scripts/prose_lint.py --json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEXTS_PATH = PROJECT_ROOT / "app" / "static" / "data" / "indicator_texts.json"

# Words that survive in a draft when nobody chose them. Most are ordinary Italian
# and none is banned outright, but they cluster in machine-written prose and each
# one has a plainer replacement: "sottolinea" is "dice", "gioca un ruolo" is
# "conta", "il tessuto produttivo" is "le imprese".
SPY_WORDS = re.compile(
    r"\b(cruciale|cruciali|panorama|tessuto|plasmare|plasma|plasmato|"
    r"sottolinea\w*|evidenzia\w*|gioca(?:no)? un ruolo|"
    r"non da ultimo|a tal proposito|degno di nota|va detto che)\b",
    re.I,
)
# "Dal Nord al Sud" reads as a span when the two ends are categories, not a
# continuum, and the atlas is full of indicators where the middle of that
# supposed range is where the story is.
FALSE_RANGE = re.compile(
    r"\b(dal Nord al Sud|da Nord a Sud|dalle Alpi (?:alla|al|a) \w+|"
    r"dai piccoli comuni alle grandi citt\w+|dalle grandi citt\w+ ai piccoli)\b",
    re.I,
)
# A 600-word article does not need a recap of itself.
RECAP = re.compile(
    r"(?:^|[.!?]\s+)(Nel complesso|In generale|In conclusione|In sintesi|"
    r"Insomma|In definitiva|Tirando le somme)\b",
)
# The tell the reviewer has been told to kill on sight, counted here so the
# backlog is a number instead of an impression.
CLOSING_QUESTION = re.compile(r"\?\s*$")
# "quasi la metà (48%)": the image and the figure glued together, so the reader
# is handed the same fact twice and the sentence stops moving (ONS style guide).
DOUBLE_NUMBER = re.compile(
    r"\b(quasi |circa |poco (?:più|meno) di |oltre |più di )?"
    r"(la metà|un terzo|un quarto|due terzi|tre quarti|un quinto|un decimo|"
    r"\w+ su (?:due|tre|quattro|cinque|dieci|cento))"
    r"[^.()]{0,25}\(\s*\d",
    re.I,
)
# Structures that read as a template even when each instance is defensible.
SLOGAN = re.compile(
    r"\b(non solo [^.,]{1,40},? ma anche|"
    r"non (?:è|e') [^.,]{1,30},? (?:è|e') |"
    r"leggere [^.]{1,30} significa leggere)",
    re.I,
)

# "quasi nove anni" in una sezione e "8,9" in un'altra: lo stesso fatto due
# volte, che e' la regola ONS che STYLE.md gia' porta ("o l'immagine o la
# cifra"), applicata a distanza invece che dentro la parentesi. Due giudici
# indipendenti l'hanno indicata come il difetto residuo dei pezzi buoni, con tre
# istanze verificate. Vive fuori da CHECKS perche' non e' una ricerca di
# pattern nel testo: confronta due numeri.
WORD_NUMBERS = {
    "mezzo": 0.5, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5,
    "sei": 6, "sette": 7, "otto": 8, "nove": 9, "dieci": 10, "undici": 11,
    "dodici": 12, "tredici": 13, "quattordici": 14, "quindici": 15, "sedici": 16,
    "diciassette": 17, "diciotto": 18, "diciannove": 19, "venti": 20, "trenta": 30,
    "quaranta": 40, "cinquanta": 50, "sessanta": 60, "settanta": 70, "ottanta": 80,
    "novanta": 90, "cento": 100,
}
# The approximation says which side of the round number the real one sits on,
# and using it is what separates a repetition from a coincidence. In ter-408
# "quasi tre punti" is the 2,79 gap, and a tolerance alone also matched the 3,31
# and the 3,48 that the same article discusses in the same unit. Those are three
# different quantities that happen to round the same way.
APPROX_BELOW = ("quasi", "poco meno di", "meno di", "sotto i")
APPROX_ABOVE = ("oltre", "poco più di", "più di", "sopra i")
APPROX = "|".join(sorted(APPROX_BELOW + APPROX_ABOVE + ("circa",), key=len, reverse=True))
IMAGE_NUMBER = re.compile(
    rf"\b({APPROX})\s+(" + "|".join(WORD_NUMBERS) + r")\s+(\w+)", re.I,
)
FIGURE = re.compile(r"\b(\d{1,3}(?:\.\d{3})*),(\d+)\s*(\w+)?")
# How close the figure has to sit to the round number it is being restated as.
# The epsilon is not decoration: 9,3 - 9 is 0.30000000000000071 in binary
# floating point, so a bare `> NEAR` drops the exact boundary case.
NEAR = 0.3
EPSILON = 1e-9

CHECKS = (
    ("lessico", SPY_WORDS, "lessico spia, c'e' quasi sempre una parola piu comune"),
    ("intervallo", FALSE_RANGE, "falso intervallo: gli estremi non stanno su un continuo"),
    ("riassunto", RECAP, "riassunto compulsivo in un pezzo da 600 parole"),
    ("doppio", DOUBLE_NUMBER, "il numero scritto due volte, immagine piu cifra"),
    ("slogan", SLOGAN, "struttura parallela da stampo"),
)

# Every signal the report can emit, in one place: the summary prints them all
# even at zero, and a check missing from that list reads as a check that passed.
EXTRA_SIGNALS = {
    "domanda": "domanda retorica in chiusura di paragrafo",
    "ripetuto": "la stessa quantita' come immagine e come cifra",
}
ALL_SIGNALS = tuple(name for name, _, _ in CHECKS) + tuple(EXTRA_SIGNALS)

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def load_texts(path=None):
    return json.loads(Path(path or TEXTS_PATH).read_text(encoding="utf-8"))


def prose_fields(entry):
    """(field, text) for every piece of hand-written prose in an entry."""
    out = []
    if (entry.get("lead") or "").strip():
        out.append(("lead", entry["lead"]))
    for section in entry.get("sections") or []:
        if (section.get("body") or "").strip():
            out.append((f"sections.{section.get('role')}", section["body"]))
    return out


def _closing_questions(fields):
    """A paragraph that ends on a question it does not answer.

    Counted per paragraph rather than per article: the migrated notes often end
    two sections that way, and one occurrence is a choice while three is a habit.
    """
    found = []
    for field, text in fields:
        for paragraph in text.split("\n"):
            stripped = paragraph.strip()
            if stripped and CLOSING_QUESTION.search(stripped):
                found.append(stripped.split(". ")[-1][:70])
    return found


def _same_number_twice(fields):
    """The same quantity given once as an image and once as a figure.

    STYLE.md bans "quasi la metà (48%)", where the two sit in one breath. The
    version that survives an editor is the one spread across sections: "quasi
    nove anni" in the quadro and "8,9" in the dinamica. The reader gets the same
    fact twice and the second time it tells them nothing.

    Only across different fields, because inside one paragraph a writer is
    usually elaborating rather than repeating, and the unit noun has to match so
    that nine years and nine points are not confused for each other.
    """
    images, figures = [], {}
    for field, text in fields:
        for match in IMAGE_NUMBER.finditer(text):
            images.append((
                field, match.group(1).lower(),
                WORD_NUMBERS[match.group(2).lower()], match.group(3).lower(),
                match.group(0),
            ))
        for match in FIGURE.finditer(text):
            unit = (match.group(3) or "").lower()
            if not unit:
                continue
            value = float(f"{match.group(1).replace('.', '')}.{match.group(2)}")
            figures.setdefault(unit, []).append((field, value, match.group(0)))

    found = []
    for field, approx, value, unit, raw in images:
        for other_field, figure, figure_raw in figures.get(unit, []):
            if other_field == field or abs(figure - value) > NEAR + EPSILON or figure == value:
                continue
            if approx in APPROX_BELOW and figure > value:
                continue
            if approx in APPROX_ABOVE and figure < value:
                continue
            found.append(f"{raw} / {figure_raw}")
    return sorted(set(found))


def inspect(entry):
    """Every mechanical tell in one article, plus what it links to."""
    fields = prose_fields(entry)
    if not fields:
        return None
    text = "\n".join(body for _, body in fields)
    hits = {}
    for name, pattern, _ in CHECKS:
        found = sorted({match.group(0).strip().lower() for match in pattern.finditer(text)})
        if found:
            hits[name] = found
    questions = _closing_questions(fields)
    if questions:
        hits["domanda"] = questions
    repeated = _same_number_twice(fields)
    if repeated:
        hits["ripetuto"] = repeated
    internal = [
        url for _, url in LINK.findall(text)
        if url.startswith("/") and not url.startswith("//")
    ]
    return {
        "hits": hits,
        "count": sum(len(found) for found in hits.values()),
        "internal_links": internal,
        "words": len(text.split()),
    }


def build_report(texts=None):
    texts = texts if texts is not None else load_texts()
    rows = []
    for key, entry in texts.items():
        found = inspect(entry)
        if found is None:
            continue
        rows.append({"id": key, **found})
    rows.sort(key=lambda row: (-row["count"], row["id"]))
    return rows


def summarize(rows):
    """The catalogue-wide numbers, which are the point of running this at all."""
    labels = {name: label for name, _, label in CHECKS} | EXTRA_SIGNALS
    per_check = {}
    for name in ALL_SIGNALS:
        carrying = [row for row in rows if name in row["hits"]]
        per_check[name] = {
            "label": labels[name],
            "articles": len(carrying),
            "occurrences": sum(len(row["hits"][name]) for row in carrying),
        }
    linked = [row for row in rows if row["internal_links"]]
    return {
        "articles": len(rows),
        "clean": sum(1 for row in rows if not row["hits"]),
        "checks": per_check,
        "with_internal_links": len(linked),
        "internal_links": sum(len(row["internal_links"]) for row in linked),
    }


def _print_summary(summary):
    print(f"ARTICOLI ESAMINATI  {summary['articles']}")
    print(f"  senza nessun tell meccanico   {summary['clean']}")
    print()
    print(f"  {'segnale':<12} {'articoli':>9} {'occorrenze':>11}   che cos'e'")
    for name, data in sorted(
        summary["checks"].items(), key=lambda item: -item[1]["articles"]
    ):
        print(f"  {name:<12} {data['articles']:>9} {data['occurrences']:>11}   {data['label']}")
    print()
    print("INCROCI  (un articolo che non linka nessun altro indicatore vive da solo)")
    print(f"  articoli con almeno un link interno   {summary['with_internal_links']} su {summary['articles']}")
    print(f"  link interni in tutto                 {summary['internal_links']}")


def _print_rows(rows, limit):
    labels = {name: label for name, _, label in CHECKS} | EXTRA_SIGNALS
    for row in rows[:limit]:
        if not row["hits"]:
            continue
        links = len(row["internal_links"])
        print(f"{row['id']}   {row['count']} segnali, {row['words']} parole, "
              f"{links} link {'interno' if links == 1 else 'interni'}")
        for name, found in row["hits"].items():
            print(f"  [{name}] {labels[name]}")
            print(f"        {' | '.join(str(item) for item in found[:4])}")
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--summary", action="store_true",
                        help="solo il totale del catalogo, per misurare i progressi")
    parser.add_argument("--show", help="un articolo solo, per id interno (178, bes:01SAL001)")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--texts", help="un file diverso da quello in repo")
    args = parser.parse_args(argv)

    texts = load_texts(args.texts)
    if args.show:
        entry = texts.get(args.show)
        if entry is None:
            print(f"nessun articolo per {args.show}")
            return 1
        texts = {args.show: entry}

    rows = build_report(texts)
    summary = summarize(rows)

    if args.json:
        print(json.dumps({"summary": summary, "articles": rows}, ensure_ascii=False, indent=1))
        return 0
    if args.summary:
        _print_summary(summary)
        return 0
    if args.show:
        if not rows or not rows[0]["hits"]:
            print(f"{args.show}: nessun tell meccanico")
            print(f"  link interni: {len(rows[0]['internal_links']) if rows else 0}")
            return 0
        _print_rows(rows, 1)
        return 0

    _print_rows(rows, args.limit)
    print(f"...{len(rows)} articoli esaminati, {args.limit} mostrati. "
          f"Il totale sta in --summary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
