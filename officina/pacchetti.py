"""Scrive i pacchetti su disco e restituisce i percorsi. Un comando, una volta.

È lo stadio `prepara` del workflow, e la sua forma nasce da una misura. Nella
prima run ogni scrittore cercava da solo il proprio pacchetto: quattro turni
per trovare l'interprete, poi altri per capire quali `role` fossero legali,
tutti e quattro con lo stesso `grep`. Ogni turno si rilegge da tutti i turni
successivi, quindi il costo cresce col quadrato: 40-51 turni a scrittore, e
$3,13 contro i $0,14 di un giudice che riceveva tutto nel prompt.

**Il pacchetto va su disco, e ciò che viaggia è il percorso.** Non il
contenuto: ciò che un agente restituisce è output, a venticinque dollari per
milione di token. Un pacchetto pesa 6-12 mila token, quindi cinquanta
indicatori sarebbero mezzo milione di token di puro transito da un agente solo,
oltre i limiti pratici di una risposta. Il percorso ne pesa venti.

    bin/py -m officina.pacchetti ter-176 ter-203
    bin/py -m officina.pacchetti ter-176 --out data/packs --json

Stdlib pura più `packs/`. Non tocca `content/`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from officina import brief

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join("data", "packs")


def write_pack(code: str, out_dir: str, level: str | None = None) -> str | None:
    """Il pacchetto di un indicatore, già montato come testo. None se non esiste."""
    constant, variable = brief.compose(code, level)
    if constant is None:
        return None
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{code}.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(constant)
        handle.write("\n")
        handle.write(variable)
        handle.write("\n")
    return os.path.abspath(path)


def build(codes, out_dir: str, level: str | None = None) -> list[dict]:
    packs = []
    for code in codes:
        path = write_pack(code, out_dir, level)
        packs.append({"code": code, "path": path,
                      "bytes": os.path.getsize(path) if path else 0})
    return packs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codes", nargs="+", help="i codici, es. ter-176 ter-203")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"cartella (default {DEFAULT_OUT})")
    parser.add_argument("--level", default=None)
    parser.add_argument("--json", action="store_true",
                        help="una riga JSON invece dei percorsi nudi")
    args = parser.parse_args(argv)

    packs = build(args.codes, args.out, args.level)
    missing = [pack["code"] for pack in packs if not pack["path"]]

    if args.json:
        print(json.dumps({"packs": packs, "mancanti": missing}, ensure_ascii=False))
    else:
        for pack in packs:
            print(pack["path"] or f"MANCANTE {pack['code']}")

    if missing:
        print(f"nessun indicatore per: {', '.join(missing)}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
