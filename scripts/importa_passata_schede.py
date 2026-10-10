#!/usr/bin/env python3
"""Importa la passata v2 delle schede (struttura a quattro sezioni) in `content/indicators/`.

    bin/py scripts/importa_passata_schede.py --blocco TESTI_v2.json --dry-run
    bin/py scripts/importa_passata_schede.py --blocco TESTI_v2.json --solo schede.csv --proposta ARRICCHIRE --guardia

Il blocco è un oggetto JSON: la chiave è il percorso della scheda
(`/indicatore/<slug>/<acronimo>-<id>`, con o senza `/province`), il valore ha
`lead`, `misura_titolo` + `misura`, `quadro_titolo` + `quadro`,
`cambiamento_titolo` + `cambiamento` (assenti se la serie è corta),
`lettura_titolo` + `lettura`, `parole`. `il_lettore_capisce` e `fonte_dati` sono
note di redazione e non si importano (`fonte_dati` direbbe al lettore che la
fonte del dato è una pagina del sito). Una voce con `non_pubblicare` al posto
del testo è un dato da verificare: si salta e si dice.

Mappatura sui ruoli dello store: `lead` è il lead; `misura` la sezione
`definizione`; `quadro` la `quadro` (sostituisce); `cambiamento` la `dinamica`
(se manca nel blocco, la `dinamica` della scheda resta com'è); `lettura` la
`limiti` (sostituisce). Ordine: definizione, quadro, dinamica, limiti. Una
scheda con una sezione `libera` è un errore: non si perde in silenzio.

Tutto o niente per scheda: una scheda con errori non si scrive e le altre sì.
Gli errori sono gli assoluti tipografici di `content/STYLE.md` in qualunque
campo (titoli compresi), titoli di sezione vuoti o ripetuti fra due schede dello
stesso lancio, campi obbligatori mancanti. Il lead fuori da 30-45 parole e le
`parole` dichiarate contro il testo sono avvisi.

`--solo <file>` limita il lancio: un percorso per riga, oppure un CSV con la
colonna `percorso` (e `--proposta` per filtrare la colonna `proposta`).
`--max N` taglia il lancio alle prime N schede. Scrive solo con
`indicator_store.write`, quindi due esecuzioni di fila non lasciano nessun diff.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import indicator_store  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LEAD_WORDS = (30, 45)
WORDS_TOLERANCE = 0.15

FORBIDDEN = ("—", "–", ";", "…")

# (campo del blocco, campo del titolo, ruolo nello store), nell'ordine dello store.
SECTIONS = (
    ("misura", "misura_titolo", "definizione"),
    ("quadro", "quadro_titolo", "quadro"),
    ("cambiamento", "cambiamento_titolo", "dinamica"),
    ("lettura", "lettura_titolo", "limiti"),
)
OPTIONAL = {"cambiamento"}
ROLE_ORDER = [role for _f, _t, role in SECTIONS]
TEXT_FIELDS = ("lead",) + tuple(f for pair in SECTIONS for f in pair[:2])


@dataclass
class Outcome:
    written: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    errors: list = field(default_factory=list)      # (path, reason)
    skipped: list = field(default_factory=list)     # (path, reason)
    warnings: list = field(default_factory=list)    # (path, text)
    guard: dict = field(default_factory=dict)       # key -> (exit code, output)
    diffs: dict = field(default_factory=dict)       # key -> unified diff
    keys: dict = field(default_factory=dict)        # path -> chiave dello store
    total: int = 0                                  # voci del lancio, dopo --solo e --max


def code_of(path: str) -> str:
    """`/indicatore/<slug>/<acronimo>-<id>[/province]` -> `<acronimo>-<id>`."""
    parts = [p for p in str(path).strip().split("/") if p]
    if parts and parts[-1] == "province":
        parts.pop()
    if len(parts) != 3 or parts[0] != "indicatore":
        raise ValueError(f"percorso non riconosciuto: {path!r}")
    return parts[2]


def resolve(path: str, keys) -> str:
    """La chiave dello store del percorso, o ValueError se sconosciuto o ambiguo."""
    code = code_of(path)
    key = indicator_store.resolve_key(keys, code)
    if key is None:
        raise ValueError(f"nessuna scheda (o più di una) per {code!r}")
    return key


def count_words(*texts) -> int:
    return sum(len(re.findall(r"\S+", t or "")) for t in texts)


def compose(entry: dict, item: dict) -> dict:
    """La nuova entrata: la vecchia con lead e le sezioni del blocco sostituiti."""
    new = dict(entry)
    new["lead"] = item["lead"].strip()
    old = {s.get("role"): s for s in entry.get("sections") or []}
    sections = []
    for body_field, title_field, role in SECTIONS:
        if (item.get(body_field) or "").strip():
            # Gli eventuali campi extra della sezione (claims...) restano.
            sections.append({**old.get(role, {}), "role": role,
                             "h": item[title_field].strip(), "body": item[body_field].strip()})
        elif role in old:
            sections.append(dict(old[role]))
    # Le sezioni di un ruolo fuori dalla mappatura restano dopo le quattro.
    sections += [dict(s) for s in entry.get("sections") or [] if s.get("role") not in ROLE_ORDER]
    new["sections"] = sections
    return new


def check_item(path: str, item: dict, entry: dict, outcome: Outcome) -> list[str]:
    """Gli errori bloccanti della voce. Gli avvisi vanno in `outcome`."""
    errors = []
    if any(s.get("role") == "libera" for s in entry.get("sections") or []):
        errors.append("la scheda ha una sezione libera: l'import non la gestisce, a mano")
    if not (item.get("lead") or "").strip():
        errors.append("campo lead vuoto o mancante")
    for body_field, title_field, _role in SECTIONS:
        has_body = (item.get(body_field) or "").strip()
        has_title = (item.get(title_field) or "").strip()
        if body_field in OPTIONAL and not has_body and not has_title:
            continue
        for name, present in ((body_field, has_body), (title_field, has_title)):
            if not present:
                errors.append(f"campo {name} vuoto o mancante")
    for name in TEXT_FIELDS:
        found = sorted({c for c in FORBIDDEN if c in (item.get(name) or "")})
        if found:
            errors.append(f"{name}: caratteri vietati da content/STYLE.md ({' '.join(found)})")
    lead_words = count_words(item.get("lead"))
    if item.get("lead") and not LEAD_WORDS[0] <= lead_words <= LEAD_WORDS[1]:
        outcome.warnings.append((path, f"lead di {lead_words} parole (atteso {LEAD_WORDS[0]}-{LEAD_WORDS[1]})"))
    declared = item.get("parole")
    if isinstance(declared, int) and declared > 0:
        actual = count_words(*(item.get(f) for f in ("lead", "misura", "quadro", "cambiamento", "lettura")))
        if abs(actual - declared) > declared * WORDS_TOLERANCE:
            outcome.warnings.append((path, f"parole dichiarate {declared}, nel testo {actual} "
                                           f"(oltre ±{int(WORDS_TOLERANCE * 100)}%)"))
    return errors


def _make_diff(key: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"{key} (prima)", tofile=f"{key} (dopo)"))


def import_block(block: dict, root=None, dry_run: bool = False, guard: bool = False,
                 only=None, max_n: int | None = None) -> Outcome:
    """`only`: insieme di codici (`<acronimo>-<id>`) a cui limitare il lancio."""
    outcome = Outcome()
    entries = indicator_store.load_all(root)
    keys = set(entries)

    items = list(block.items())
    if only is not None:
        items = [(p, i) for p, i in items if code_of(p) in only]
    if max_n is not None:
        items = items[:max_n]
    outcome.total = len(items)

    plan = []   # (path, key, item)
    seen = {}
    for path, item in items:
        if item.get("non_pubblicare"):
            outcome.skipped.append((path, f"non_pubblicare: {item['non_pubblicare'][:90]}..."))
            continue
        try:
            key = resolve(path, keys)
        except ValueError as exc:
            outcome.errors.append((path, str(exc)))
            continue
        outcome.keys[path] = key
        if key in seen:
            outcome.errors.append((path, f"stessa scheda di {seen[key]}"))
            continue
        seen[key] = path
        errors = check_item(path, item, entries[key], outcome)
        if errors:
            outcome.errors.extend((path, e) for e in errors)
            continue
        plan.append((path, key, item))

    # Titoli ripetuti fra due schede dello stesso lancio: errore per la seconda,
    # che esce dal piano (la prima si scrive).
    for _body, name, _role in SECTIONS:
        first_seen = {}
        for entry in list(plan):
            path, _key, item = entry
            title = (item.get(name) or "").strip()
            if not title:
                continue
            if title in first_seen:
                outcome.errors.append(
                    (path, f"{name} {title!r} uguale a quello di {first_seen[title]}"))
                if entry in plan:
                    plan.remove(entry)
            else:
                first_seen[title] = path

    for _path, key, item in plan:
        old = entries[key]
        new = compose(old, item)
        before = indicator_store.rendi(key, old)
        after = indicator_store.rendi(key, new)
        if before == after:
            outcome.unchanged.append(key)
            continue
        outcome.diffs[key] = _make_diff(key, before, after)
        outcome.written.append(key)
        if not dry_run:
            indicator_store.write(key, new, root=root)

    if guard and not dry_run:
        for key in outcome.written:
            outcome.guard[key] = _run_guard(key)
    return outcome


def _run_guard(key: str) -> tuple[int, str]:
    """`scripts.editoriale.guardia` legge lo store committato, non una root di prova."""
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.editoriale.guardia", key],
        cwd=PROJECT_ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def read_only(path: Path, proposta: str | None) -> set[str]:
    """I codici delle schede di `--solo`: righe di percorsi, o un CSV con `percorso`."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        rows = csv.DictReader(text.splitlines())
        return {code_of(r["percorso"]) for r in rows
                if proposta is None or r.get("proposta") == proposta}
    if proposta:
        raise ValueError("--proposta vale solo per un CSV")
    return {code_of(line) for line in text.splitlines() if line.strip()}


def report(outcome: Outcome, dry_run: bool, total: int) -> None:
    if dry_run:
        for diff in outcome.diffs.values():
            print(diff)
    for path, reason in outcome.errors:
        print(f"ERRORE {path}: {reason}", file=sys.stderr)
    for path, reason in outcome.skipped:
        print(f"SALTATA {path}: {reason}")
    for path, text in outcome.warnings:
        print(f"AVVISO {path}: {text}")
    for key, (code, output) in outcome.guard.items():
        first = output.splitlines()[0] if output else ""
        print(f"GUARDIA {key}: {'ok' if code == 0 else 'DIFETTI'} {first}")
        if code != 0:
            print(output, file=sys.stderr)
    bad = len({p for p, _ in outcome.errors})
    verb = "da scrivere" if dry_run else "scritte"
    print(f"{total} voci nel lancio: {len(outcome.written)} {verb}, "
          f"{len(outcome.unchanged)} invariate, {len(outcome.skipped)} saltate, "
          f"{bad} schede in errore ({len(outcome.errors)} errori)")
    if outcome.errors:
        print("le schede in errore non sono state scritte", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--blocco", required=True, type=Path, help="TESTI_v2.json della direzione")
    parser.add_argument("--dry-run", action="store_true", help="stampa il diff per scheda, non scrive")
    parser.add_argument("--guardia", action="store_true",
                        help="lancia scripts.editoriale.guardia su ogni scheda scritta")
    parser.add_argument("--solo", type=Path, default=None,
                        help="file con un percorso per riga, o CSV con colonna `percorso`")
    parser.add_argument("--proposta", default=None, help="con un CSV di --solo: filtra la colonna `proposta`")
    parser.add_argument("--max", dest="max_n", type=int, default=None, help="al massimo N schede")
    parser.add_argument("--root", type=Path, default=None,
                        help="radice dello store (default: content/indicators)")
    args = parser.parse_args(argv)

    if not args.blocco.is_file():
        parser.error(f"il blocco {args.blocco} non esiste")
    block = json.loads(args.blocco.read_text(encoding="utf-8"))
    if not isinstance(block, dict):
        parser.error("il blocco deve essere un oggetto JSON")
    only = None
    if args.solo:
        if not args.solo.is_file():
            parser.error(f"il file --solo {args.solo} non esiste")
        try:
            only = read_only(args.solo, args.proposta)
        except (ValueError, KeyError) as exc:
            parser.error(f"--solo: {exc}")

    outcome = import_block(block, root=args.root, dry_run=args.dry_run, guard=args.guardia,
                           only=only, max_n=args.max_n)
    report(outcome, args.dry_run, outcome.total)
    if outcome.errors or any(code != 0 for code, _ in outcome.guard.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
