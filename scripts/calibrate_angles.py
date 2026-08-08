"""Misura i rilevatori su tutto il catalogo e scrive packs/calibration.json.

Perché esiste: la dimensione di un effetto non dice se quell'effetto è
notevole. Una graduatoria di venti valori ha sempre un salto più largo degli
altri, e in quasi ogni serie qualcuno si muove controcorrente: ordinare per
dimensione grezza faceva aprire il 90% degli articoli a due soli tipi di
angolo, il che è l'uniformità che il pacchetto esiste per togliere.

Con questa tabella la forza di un angolo diventa il posto che occupa nella
distribuzione del proprio tipo, quindi confrontabile fra tipi diversi davvero e
non per modo di dire.

    python3 -m scripts.calibrate_angles              # riscrive la tabella
    python3 -m scripts.calibrate_angles --dry-run    # mostra e non scrive
    python3 -m scripts.calibrate_angles --report     # come cambia chi apre

Va rigenerata quando entra una famiglia di dati nuova. Non è un file da
scrivere a mano: è una misura, e il giorno che qualcuno la ritocca a mano la
forza torna a essere un'opinione.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict

from app import sources
from app.atlas_catalog import get_atlas_catalog
from app.indicator_view import build_indicator_view
from packs import angles as angles_module
from packs import build as build_module
from packs import calibration


def _levels_of(indicator_id):
    family, raw = sources.split_internal_id(indicator_id)
    view = build_indicator_view(family, raw)
    return view["levels"] if view else []


def collect(limit=None):
    """{tipo: [dimensioni osservate]} su ogni indicatore e ogni suo livello."""
    catalog = get_atlas_catalog()
    ids = [item["id"] for item in catalog["indicators"]]
    if limit:
        ids = ids[:limit]

    samples = defaultdict(list)
    seen = 0
    for indicator_id in ids:
        try:
            levels = _levels_of(indicator_id)
        except Exception:
            continue
        for level in levels:
            matrix = build_module.matrix_by_name(level)
            if not matrix:
                continue
            found = angles_module.raw_angles(
                matrix, groups=build_module.groups_by_name(level))
            for angle in found:
                samples[angle["type"]].append(angle["raw"])
            seen += 1
    return samples, seen


def _report(limit=None):
    """Chi apre l'articolo, con la tabella attualmente su disco."""
    catalog = get_atlas_catalog()
    ids = [item["id"] for item in catalog["indicators"]]
    if limit:
        ids = ids[:limit]
    openers = Counter()
    words = []
    for indicator_id in ids:
        family, raw = sources.split_internal_id(indicator_id)
        try:
            pack = build_module.build_pack(family, raw)
        except Exception:
            continue
        if not pack or not pack["angles"]:
            continue
        openers[pack["angles"][0]["type"]] += 1
        words.append(pack["words"]["atteso"])
    total = sum(openers.values()) or 1
    print(f"\nCHI APRE L'ARTICOLO  ({total} indicatori)")
    for kind, count in openers.most_common():
        print(f"  {kind:26} {count:4}  {count / total:6.1%}")
    if words:
        words.sort()
        print(f"\nparole attese: min {words[0]}  mediana {words[len(words) // 2]}  "
              f"max {words[-1]}")
    return openers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", action="store_true",
                        help="stampa la distribuzione delle aperture e basta")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    if args.report:
        _report(args.limit)
        return 0

    samples, seen = collect(args.limit)
    table = calibration.build_table(samples)
    skipped = sorted(set(samples) - set(table))

    print(f"serie misurate: {seen}")
    for kind in sorted(table):
        values = samples[kind]
        print(f"  {kind:26} {len(values):5} campioni  "
              f"[{table[kind][0]:.3f} .. {table[kind][-1]:.3f}]")
    if skipped:
        print(f"  non calibrati (troppo pochi campioni): {', '.join(skipped)}")

    if args.dry_run:
        return 0
    with open(calibration.TABLE_PATH, "w", encoding="utf-8") as handle:
        json.dump(table, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"\nscritta {calibration.TABLE_PATH}")
    calibration.reload_table()
    _report(args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
