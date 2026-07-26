"""What a human still has to read: articles ranked by editorial risk.

`text_queue` answers "what is left to write". This answers the other question,
the one that grows instead of shrinking: **of the articles that exist, which
ones are most likely to be wrong?**

The mechanical guards in `tests/test_indicator_texts.py` check what a regex can
check: style, structure, vintage, decimal figures attributed to a region, and
thresholds asserted over a list of regions. Everything they cannot check is
listed in `docs/INDICATOR_PAGES.md` and needs eyes. That list is not a vague
warning, it is a set of patterns, and a pattern can be looked for:

    universale      "ovunque", "sempre", "da anni": one counter-example makes it false
    causale         "grazie a", "spinto da": the indicator shows no mechanism
    esterno         a claim about Europe or a national ranking with no source in `fonti`
    provincia       figures on a provincial article, which the region regex cannot read
    eco             a figure the cockpit already prints, restated in the prose
    mestiere        the bot tells content/STYLE.md names, from scripts/prose_lint

None of these is a defect by itself. They are the sentences where a defect
hides, so they decide reading order rather than pass or fail. An article the
reviewer has signed off carries `reviewed_at` and leaves the queue until its
text or its data changes.

    .venv/bin/python -m scripts.review_queue                # top of the queue
    .venv/bin/python -m scripts.review_queue --all
    .venv/bin/python -m scripts.review_queue --flag causale
    .venv/bin/python -m scripts.review_queue --csv
    .venv/bin/python -m scripts.review_queue --show dem:OLDAGEDEPR
"""

import argparse
import csv
import io
import json
import re
from pathlib import Path

from app import indicator_texts, sources
from app.indicator_view import build_indicator_view
from scripts import prose_lint

TEXTS_PATH = Path(indicator_texts.__file__).resolve().parent / "static" / "data" / "indicator_texts.json"

# A claim that holds "everywhere" or "always" is false the moment one territory
# disagrees, and the brief has a block (SI MUOVONO CONTROCORRENTE) that settles
# it in one look. Two real notes shipped with this exact mistake.
UNIVERSAL = re.compile(
    r"\b(ovunque|sempre|storicamente|da anni|in ogni regione|in tutte le regioni|"
    r"in nessuna regione|nessuna regione|tutte le regioni|senza eccezioni|"
    r"in ogni provincia|in tutte le province)\b", re.I,
)
# A territorial indicator shows a level, never a mechanism. These are the
# phrasings that quietly turn a correlation into a cause.
CAUSAL = re.compile(
    r"\b(grazie a|grazie all|spinto da|spinta da|trainato da|per effetto|"
    r"a causa d|dovuto a|dovuta a|per merito|complice|colpa d|"
    r"si spiega con|dipende dal|dipende dalla)\w*", re.I,
)
# Anything comparing outside this dataset needs a verified source in `fonti`.
EXTERNAL_CLAIM = re.compile(
    r"\b(europ\w+|\bUE\b|\bOCSE\b|\bOECD\b|media nazionale|in Italia|"
    r"primato|record|il più alto d|la più alta d|il più basso d|la più bassa d)", re.I,
)
DECIMAL = re.compile(r"\d+,\d+")
# The bot tells live in `scripts/prose_lint`, which owns the patterns and the
# catalogue-wide counts. Borrowed rather than restated: a second copy of the spy
# lexicon here would drift from the one the writer lints its draft against, and
# the two would then disagree about the same sentence.
#
# The closing question is deliberately left out of the flag. It is on 340 of the
# 364 articles, so as a *reading order* signal it is a constant added to almost
# every row, which changes nothing and hides the rest. It stays a backlog number
# in `prose_lint --summary` and an instruction in the reviewer's prompt.
CRAFT_TELLS = tuple(name for name, _, _ in prose_lint.CHECKS)

FLAG_LABELS = {
    "universale": "afferma un andamento generale",
    "causale": "attribuisce una causa",
    "esterno": "confronto fuori dal dataset senza fonte",
    "provincia": "cifre provinciali, non verificate dalle guardie",
    "eco": "ripete una cifra del cruscotto",
    "mestiere": "tell da bot che STYLE.md nomina",
    "rilettura": "i dati si sono mossi dopo la firma",
}
# Weights: how much each pattern moves an article up the reading order. A causal
# claim is the worst because it is invisible to every guard and reads as fact.
FLAG_WEIGHT = {
    # `rilettura` outranks the risk flags on purpose. The others mark a sentence
    # that *might* be wrong; this one marks an article whose figures have been
    # rewritten since anybody read it, so nothing in it has been checked at all.
    "rilettura": 45,
    "causale": 40, "esterno": 30, "universale": 25, "provincia": 20,
    # Below `provincia` on purpose. A bot tell makes an article read badly, the
    # flags above mark one that may be false, and a false sentence outranks an
    # ugly one every time.
    "mestiere": 15, "eco": 10,
}


def load_texts(path=None):
    path = Path(path) if path else TEXTS_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def prose_fields(entry):
    """(field, text) for every piece of hand-written prose in an entry."""
    out = []
    if entry.get("lead"):
        out.append(("lead", entry["lead"]))
    for section in entry.get("sections") or []:
        if (section.get("body") or "").strip():
            out.append((f"sections.{section.get('role')}", section["body"]))
    return out


def _cockpit_figures(level):
    """The numbers the cockpit prints on its own, to two decimals as strings.

    Restating one of these is the duplication the layout was rebuilt to remove
    (docs/INDICATOR_PAGES.md), and no guard catches it because the figure is
    correct. It is only redundant.
    """
    stats = level["stats"]
    values = [
        stats.get("year_avg"), stats.get("gap_abs"),
        (level.get("best") or {}).get("value"), (level.get("worst") or {}).get("value"),
    ]
    annual = level.get("annual_change") or {}
    values.append(annual.get("average_delta"))
    out = set()
    for value in values:
        if isinstance(value, (int, float)):
            out.add(f"{value:.2f}".replace(".", ","))
    return out


def assess(key, entry, view=None):
    """Risk flags and a reading-order score for one article."""
    if view is None:
        family, raw_id = sources.split_internal_id(key)
        view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    level_key = entry.get("level") or indicator_texts.DEFAULT_LEVEL
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), None)
    if level is None:
        return None

    fields = prose_fields(entry)
    text = " ".join(body for _, body in fields)
    has_sources = bool(entry.get("fonti"))
    cockpit = _cockpit_figures(level)

    hits = {}
    for flag, pattern in (
        ("universale", UNIVERSAL), ("causale", CAUSAL), ("esterno", EXTERNAL_CLAIM),
    ):
        found = sorted({m.group(0).lower() for m in pattern.finditer(text)})
        if found and not (flag == "esterno" and has_sources):
            hits[flag] = found
    if level_key != "regione" and DECIMAL.search(text):
        hits["provincia"] = sorted({m.group(0) for m in DECIMAL.finditer(text)})[:5]
    echoed = sorted({m.group(0) for m in DECIMAL.finditer(text)} & cockpit)
    if echoed:
        hits["eco"] = echoed
    linted = prose_lint.inspect(entry) or {"hits": {}}
    tells = [
        found for name in CRAFT_TELLS for found in linted["hits"].get(name, [])
    ]
    if tells:
        hits["mestiere"] = tells

    meta = view["meta"]
    score = sum(FLAG_WEIGHT[flag] for flag in hits)
    if meta["indexable"]:
        score += 15
    if meta.get("quality_life_scored"):
        score += 10
    reviewed = (entry.get("reviewed_at") or "").strip()
    vintage = entry.get("vintage")
    reviewed_vintage = entry.get("reviewed_vintage")
    # A signature is a statement about a text *and* about the numbers under it,
    # so it expires when the numbers move. The writer refreshes an article whose
    # vintage has fallen behind, which rewrites the figures in every sentence:
    # the reader who signed off did not read those sentences. Without this the
    # queue would drain once and never refill, and the chain would look finished
    # while the published catalogue quietly aged underneath it.
    #
    # Keyed on the vintage, not on a calendar interval: a series that has not
    # published a new year has nothing new to read, and re-reading it on a timer
    # is churn dressed up as diligence.
    stale_signature = bool(reviewed) and reviewed_vintage != vintage
    if reviewed and not stale_signature:
        # Signed off and still current: it stays in --all for the record, out of
        # the reading order.
        score = 0
    elif stale_signature:
        hits["rilettura"] = [f"firmato sul {reviewed_vintage or 'ignoto'}, ora {vintage}"]
        score += FLAG_WEIGHT["rilettura"]
    return {
        "id": key,
        "code": sources.indicator_code(meta["family"], meta["raw_id"]),
        "level": level_key,
        "name": meta["name"],
        "indexable": meta["indexable"],
        "written": sum(1 for field, _ in fields if field.startswith("sections.")),
        "reviewed_at": "" if stale_signature else reviewed,
        "signed_vintage": reviewed_vintage,
        "vintage": vintage,
        "flags": hits,
        "score": score,
    }


def build_queue(texts=None):
    texts = texts if texts is not None else load_texts()
    rows = []
    for key, entry in texts.items():
        assessed = assess(key, entry)
        if assessed is not None:
            rows.append(assessed)
    rows.sort(key=lambda row: (-row["score"], row["name"]))
    return rows


def _print_one(key, entry, row):
    print(f"{row['code']}  ({row['id']}, livello {row['level']})")
    print(f"  {row['name']}")
    print(f"  indicizzabile: {'si' if row['indexable'] else 'no'}   "
          f"sezioni scritte: {row['written']}/4   "
          f"revisionato: {row['reviewed_at'] or 'mai'}")
    if not row["flags"]:
        print("  nessun segnale di rischio")
    for flag, found in row["flags"].items():
        print(f"  [{flag}] {FLAG_LABELS[flag]}")
        print(f"        {', '.join(str(f) for f in found[:6])}")
    print()
    for field, body in prose_fields(entry):
        print(f"  --- {field} ---")
        for line in body.split("\n"):
            if line.strip():
                print(f"  {line}")
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true", help="include articles already reviewed")
    parser.add_argument("--flag", help="only articles carrying this flag")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--show", help="print one article in full, with its flags")
    args = parser.parse_args(argv)

    texts = load_texts()
    if args.show:
        entry = texts.get(args.show)
        if entry is None:
            print(f"nessun articolo per {args.show}")
            return 1
        row = assess(args.show, entry)
        if row is None:
            print(f"{args.show}: indicatore non risolvibile")
            return 1
        _print_one(args.show, entry, row)
        return 0

    rows = build_queue(texts)
    if args.flag:
        rows = [row for row in rows if args.flag in row["flags"]]
    pending = [row for row in rows if not row["reviewed_at"]]

    if args.csv:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "code", "id", "level", "name", "indexable", "written", "reviewed_at", "flags", "score",
        ], extrasaction="ignore")
        writer.writeheader()
        for row in (rows if args.all else pending):
            writer.writerow({**row, "flags": " ".join(row["flags"])})
        print(out.getvalue(), end="")
        return 0

    reviewed = sum(1 for row in rows if row["reviewed_at"])
    print(f"{len(rows)} articoli scritti, {reviewed} gia revisionati, "
          f"{len(pending)} da leggere.")
    counts = {}
    for row in pending:
        for flag in row["flags"]:
            counts[flag] = counts.get(flag, 0) + 1
    if counts:
        print("segnali: " + ", ".join(f"{flag} {n}" for flag, n in sorted(counts.items())))
    print()
    shown = (rows if args.all else pending)[: None if args.all else args.limit]
    print(f"{'codice':<18} {'liv':<10} {'idx':<4} {'segnali':<34} nome")
    print("-" * 118)
    for row in shown:
        flags = ",".join(row["flags"]) or ("ok" if row["reviewed_at"] else "-")
        print(f"{row['code']:<18} {row['level']:<10} "
              f"{'si' if row['indexable'] else 'no':<4} {flags:<34} {row['name'][:44]}")
    if not args.all and len(pending) > args.limit:
        print(f"\n... e altri {len(pending) - args.limit}. Usa --all per l'elenco completo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
