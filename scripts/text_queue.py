"""What still needs an editor, ranked by how much it would matter.

The article schema has four roles per indicator and 621 indicators, so "what is
left to write" is not a question anyone can hold in their head. This prints the
worklist.

Priority is deliberately not "least written first". An indexable page with a lot
of siblings is worth more than a noindex variant nobody reaches, and an article
whose figures are older than the data is worse than one that was never written,
because a stale figure is wrong while a composed section is merely plain.

    .venv/bin/python -m scripts.text_queue                 # top of the queue
    .venv/bin/python -m scripts.text_queue --all           # everything
    .venv/bin/python -m scripts.text_queue --stale         # only stale vintages
    .venv/bin/python -m scripts.text_queue --csv           # for a spreadsheet
"""

import argparse
import csv
import io

from app import sources
from app.atlas_catalog import get_atlas_catalog
from app.bes_data import all_bes_indicators
from app.indicator_texts import ROLE_ORDER, build_article
from app.indicator_view import build_indicator_view
from app.multiscopo_data import all_multiscopo_indicators


def _all_indicator_refs():
    """(family, raw_id) for every indicator that has a public page."""
    seen = set()
    refs = []
    for item in get_atlas_catalog()["indicators"]:
        family, raw_id = sources.split_internal_id(str(item["id"]))
        if str(item["id"]) not in seen:
            seen.add(str(item["id"]))
            refs.append((family, raw_id))
    for raw_id in (item["id"] for item in all_bes_indicators()):
        if sources.internal_id("bes", raw_id) not in seen:
            seen.add(sources.internal_id("bes", raw_id))
            refs.append(("bes", raw_id))
    for raw_id in (item["id"] for item in all_multiscopo_indicators()):
        if sources.internal_id("multiscopo", raw_id) not in seen:
            seen.add(sources.internal_id("multiscopo", raw_id))
            refs.append(("multiscopo", raw_id))
    return refs


def assess(family, raw_id, level_key=None):
    """The editorial state of one indicator at one territorial level.

    Level-aware on purpose. This used to read `levels[0]` and call
    `build_article` with no level, so the 34 two-level BES indicators were only
    ever judged on their regional half: a provincial article, once written,
    still showed as `0/4` and could never be reported as done, while the
    provincial page of every other one was invisible to the worklist.
    """
    view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    meta = view["meta"]
    level = next(
        (lv for lv in view["levels"] if lv["key"] == level_key),
        view["levels"][0],
    )
    article = build_article(meta["id"], level["key"])
    missing = [s["role"] for s in article["sections"] if not s["authored"]]
    vintage = article["vintage"]
    stale = vintage is not None and vintage < level["year_max"]

    # A stale figure is wrong, a missing section is only plain: staleness wins.
    # Then how much of the article is missing, then whether anyone will see it.
    score = 0
    if stale:
        score += 100
    if not article["lead"]:
        score += 20
    score += 10 * len(missing)
    if meta["indexable"]:
        score += 15
    return {
        "id": meta["id"],
        "code": f"{sources.SOURCES[family]['acronym']}-{raw_id}",
        "level": level["key"],
        "levels": len(view["levels"]),
        "name": meta["name"],
        "theme": meta["theme"],
        "indexable": meta["indexable"],
        "year_max": level["year_max"],
        "vintage": vintage,
        "stale": stale,
        "lead": bool(article["lead"]),
        "missing": missing,
        "written": len(ROLE_ORDER) - len(missing),
        "score": score,
    }


def build_queue():
    """One row per (indicator, territorial level), because that is the unit of
    work: an article is written against one level and used only there."""
    rows = []
    for family, raw_id in _all_indicator_refs():
        view = build_indicator_view(family, raw_id)
        if view is None:
            continue
        for level in view["levels"]:
            entry = assess(family, raw_id, level["key"])
            if entry is not None:
                rows.append(entry)
    rows.sort(key=lambda row: (-row["score"], row["name"], row["level"]))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true", help="print every indicator, not just the top")
    parser.add_argument("--stale", action="store_true", help="only articles whose vintage is behind the data")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args(argv)

    rows = build_queue()
    complete = [row for row in rows if not row["missing"] and row["lead"] and not row["stale"]]
    if args.stale:
        rows = [row for row in rows if row["stale"]]
    pending = [row for row in rows if row["missing"] or not row["lead"] or row["stale"]]

    if args.csv:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "code", "id", "level", "name", "theme", "indexable", "year_max", "vintage",
            "stale", "lead", "written", "missing", "score",
        ], extrasaction="ignore")
        writer.writeheader()
        for row in (rows if args.all else pending):
            writer.writerow({**row, "missing": " ".join(row["missing"])})
        print(out.getvalue(), end="")
        return 0

    total = len(rows)
    print(f"{len(complete)} articoli completi su {total} pagine "
          f"(indicatore piu livello territoriale). "
          f"{len([r for r in rows if r['stale']])} con vintage arretrato.")
    print()
    shown = (rows if args.all else pending)[: None if args.all else args.limit]
    print(f"{'codice':<16} {'liv':<10} {'sez':>4} {'vint':>6}  {'idx':<4} {'mancano':<34} nome")
    print("-" * 120)
    for row in shown:
        flag = "STALE" if row["stale"] else (str(row["vintage"]) if row["vintage"] else "-")
        missing = ",".join(row["missing"]) + ("" if row["lead"] else " +lead")
        # The level is shown only where there is more than one, so 587 single
        # level rows stay readable and the 34 two-level ones are unambiguous.
        level = row["level"] if row["levels"] > 1 else ""
        print(f"{row['code']:<16} {level:<10} {row['written']}/4 {flag:>6}  "
              f"{'si' if row['indexable'] else 'no':<4} {missing:<34} {row['name'][:44]}")
    if not args.all and len(pending) > args.limit:
        print(f"\n... e altri {len(pending) - args.limit}. Usa --all per l'elenco completo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
