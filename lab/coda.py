"""What still needs an editor, ranked by how much it would matter.

The article schema has four roles per indicator and 634 indicators, so "what is
left to write" is not a question anyone can hold in their head. This prints the
worklist.

Priority is deliberately not "least written first". An indexable page with a lot
of siblings is worth more than a noindex variant nobody reaches, and an article
whose figures are older than the data is worse than one that was never written,
because a stale figure is wrong while a composed section is merely plain.

    bin/py -m lab.coda                 # top of the queue
    bin/py -m lab.coda --all           # everything
    bin/py -m lab.coda --stale         # only stale vintages
    bin/py -m lab.coda --csv           # for a spreadsheet
"""

import argparse
import csv
import io

# Il criterio sta in `app/editorial_state.py`, non qui: lo legge anche l'app
# servita, che mostra questa stessa classifica nel cruscotto, e `lab/` non entra
# nell'immagine Docker. Qui resta la riga di comando.
from app.editorial_state import assess, build_queue, da_scrivere  # noqa: F401  (re-export)
from app.indicator_universe import all_indicator_refs  # noqa: F401  (re-export)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true", help="print every indicator, not just the top")
    parser.add_argument("--stale", action="store_true", help="only articles whose vintage is behind the data")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args(argv)

    rows = build_queue()
    complete = [row for row in rows if not da_scrivere(row)]
    if args.stale:
        rows = [row for row in rows if row["stale"]]
    pending = [row for row in rows if da_scrivere(row)]

    if args.csv:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "code", "id", "level", "name", "theme", "indexable", "year_max", "vintage",
            "stale", "lead", "written", "sections", "missing", "score",
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
        print(f"{row['code']:<16} {level:<10} {row['written']}/{row['sections']} {flag:>6}  "
              f"{'si' if row['indexable'] else 'no':<4} {missing:<34} {row['name'][:44]}")
    if not args.all and len(pending) > args.limit:
        print(f"\n... e altri {len(pending) - args.limit}. Usa --all per l'elenco completo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
