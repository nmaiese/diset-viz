#!/usr/bin/env python3
"""Importa un blocco della passata schede nelle schede `content/indicators/`.

    bin/py scripts/importa_passata_schede.py --blocco blocco-1.json --dry-run
    bin/py scripts/importa_passata_schede.py --blocco blocco-1.json --guardia

Il blocco è un oggetto JSON: la chiave è il percorso della scheda
(`/indicatore/<slug>/<acronimo>-<id>`, con o senza `/province`), il valore ha
`titolo`, `lead`, `lead_breve`, `parole_semplici`, `non_dice`,
`titolo_parole_semplici`, `titolo_non_dice`, `fonte_dati`, `il_lettore_capisce` e
`parole`. `il_lettore_capisce` è una nota di redazione e non si importa. Una voce con `non_pubblicare` al posto del testo è un dato da verificare: si
salta e si dice.

Per ogni scheda `lead_breve` (la prima frase del `lead`) diventa il lead
dell'entrata; le frasi che nel `lead` lo seguono aprono la sezione `definizione`,
in un paragrafo, prima di `parole_semplici`. `non_dice` è la sezione `limiti`
(che sostituisce quella che c'era). I titoli delle due sezioni sono obbligatori,
non possono contenere i caratteri vietati e non possono ripetersi fra due schede
del blocco. `quadro`, `dinamica`, `libera` e il frontmatter restano come
stavano. `fonte_dati` non si importa: nel blocco 1 è la nota «pagina del sito
del 09/10/2026», cioè da dove la direzione ha letto, mentre `fonti` dello store è
una lista di `{testo, url}` che il lettore vede come fonte del dato. Metterci
quella nota la pubblicherebbe come fonte.

Scrive solo con `indicator_store.write`, quindi due esecuzioni di fila non
lasciano nessun diff. Prima di scrivere controlla gli assoluti tipografici di
`content/STYLE.md` (errore: nessuna scheda del blocco si scrive), il lead oltre
320 caratteri e le `parole` dichiarate contro il testo (avvisi: si scrive lo
stesso).
"""

from __future__ import annotations

import argparse
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

# Sopra questa lunghezza il lead non sta più intero in una meta description.
LEAD_MAX = 320
WORDS_TOLERANCE = 0.15

FORBIDDEN = ("—", "–", ";", "…")

# Una `definizione` nuova va prima del primo di questi ruoli.
REQUIRED = ("lead", "lead_breve", "parole_semplici", "non_dice",
            "titolo_parole_semplici", "titolo_non_dice")

ROLES_AFTER_DEFINITION = ("quadro", "dinamica")


@dataclass
class Outcome:
    written: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    errors: list = field(default_factory=list)      # (path, reason)
    skipped: list = field(default_factory=list)     # (path, reason)
    warnings: list = field(default_factory=list)    # (path, text)
    long_leads: list = field(default_factory=list)
    guard: dict = field(default_factory=dict)       # key -> (exit code, output)
    diffs: dict = field(default_factory=dict)       # key -> unified diff


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


def _section(role: str, title: str, body: str) -> dict:
    return {"role": role, "h": title, "body": body.strip()}


def compose(entry: dict, item: dict) -> dict:
    """La nuova entrata: la vecchia con lead, definizione e limiti sostituiti."""
    new = dict(entry)
    lead_short = item["lead_breve"].strip()
    tail = item["lead"].strip()[len(lead_short):].strip()
    new["lead"] = lead_short
    body = f"{tail}\n\n{item['parole_semplici'].strip()}" if tail else item["parole_semplici"]
    definition = _section("definizione", item["titolo_parole_semplici"].strip(), body)
    limits = _section("limiti", item["titolo_non_dice"].strip(), item["non_dice"])

    sections = [dict(s) for s in entry.get("sections") or []]
    for role, section in (("definizione", definition), ("limiti", limits)):
        index = next((i for i, s in enumerate(sections) if s.get("role") == role), None)
        if index is not None:
            # Gli eventuali campi extra della sezione (claims...) restano.
            sections[index] = {**sections[index], **section}
        elif role == "limiti":
            sections.append(section)
        else:
            first = next((i for i, s in enumerate(sections)
                          if s.get("role") in ROLES_AFTER_DEFINITION), 0)
            sections.insert(first, section)
    new["sections"] = sections
    return new


def check_item(path: str, item: dict, outcome: Outcome) -> list[str]:
    """Gli errori bloccanti della voce. Gli avvisi vanno in `outcome`."""
    errors = []
    for name in REQUIRED:
        if not (item.get(name) or "").strip():
            errors.append(f"campo {name} vuoto o mancante")
    fields = ("lead", "lead_breve", "parole_semplici", "non_dice",
              "titolo_parole_semplici", "titolo_non_dice")
    for name in fields:
        found = sorted({c for c in FORBIDDEN if c in (item.get(name) or "")})
        if found:
            errors.append(f"{name}: caratteri vietati da content/STYLE.md ({' '.join(found)})")
    lead = (item.get("lead") or "").strip()
    short = (item.get("lead_breve") or "").strip()
    if lead and short and not lead.startswith(short):
        errors.append("lead_breve non è l'inizio del lead")
    elif short and len(short) > LEAD_MAX:
        outcome.long_leads.append(path)
        outcome.warnings.append((path, f"lead_breve di {len(short)} caratteri (> {LEAD_MAX}): "
                                       "la meta description lo accorcia"))
    declared = item.get("parole")
    if isinstance(declared, int) and declared > 0:
        actual = count_words(item.get("lead"), item.get("parole_semplici"), item.get("non_dice"))
        if abs(actual - declared) > declared * WORDS_TOLERANCE:
            outcome.warnings.append((path, f"parole dichiarate {declared}, nel testo {actual} "
                                           f"(oltre ±{int(WORDS_TOLERANCE * 100)}%)"))
    return errors


def _make_diff(key: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"{key} (prima)", tofile=f"{key} (dopo)"))


def import_block(block: dict, root=None, dry_run: bool = False, guard: bool = False) -> Outcome:
    outcome = Outcome()
    entries = indicator_store.load_all(root)
    keys = set(entries)

    plan = []   # (path, key, item)
    seen = {}
    for path, item in block.items():
        if item.get("non_pubblicare"):
            outcome.skipped.append((path, f"non_pubblicare: {item['non_pubblicare'][:90]}..."))
            continue
        try:
            key = resolve(path, keys)
        except ValueError as exc:
            outcome.errors.append((path, str(exc)))
            continue
        if key in seen:
            outcome.errors.append((path, f"stessa scheda di {seen[key]}"))
            continue
        seen[key] = path
        errors = check_item(path, item, outcome)
        if errors:
            outcome.errors.extend((path, e) for e in errors)
            continue
        plan.append((path, key, item))

    for name in ("titolo_parole_semplici", "titolo_non_dice"):
        first_seen = {}
        for path, _key, item in plan:
            title = item[name].strip()
            if title in first_seen:
                outcome.errors.append(
                    (path, f"{name} {title!r} uguale a quello di {first_seen[title]}"))
            else:
                first_seen[title] = path

    # Un errore su una scheda = nessuna scrittura per nessuna: il blocco si
    # corregge e si rilancia intero, invece di restare importato a metà.
    if outcome.errors:
        return outcome

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
    verb = "da scrivere" if dry_run else "scritte"
    print(f"{total} voci nel blocco: {len(outcome.written)} {verb}, "
          f"{len(outcome.unchanged)} invariate, {len(outcome.skipped)} saltate, "
          f"{len(outcome.errors)} in errore "
          f"(lead lunghi {len(outcome.long_leads)})")
    if outcome.errors:
        print("nessuna scheda scritta: correggi gli errori e rilancia", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--blocco", required=True, type=Path, help="blocco-<n>.json della direzione")
    parser.add_argument("--dry-run", action="store_true", help="stampa il diff per scheda, non scrive")
    parser.add_argument("--guardia", action="store_true",
                        help="lancia scripts.editoriale.guardia su ogni scheda scritta")
    parser.add_argument("--root", type=Path, default=None,
                        help="radice dello store (default: content/indicators)")
    args = parser.parse_args(argv)

    if not args.blocco.is_file():
        parser.error(f"il blocco {args.blocco} non esiste")
    block = json.loads(args.blocco.read_text(encoding="utf-8"))
    if not isinstance(block, dict):
        parser.error("il blocco deve essere un oggetto JSON")

    outcome = import_block(block, root=args.root, dry_run=args.dry_run, guard=args.guardia)
    report(outcome, args.dry_run, len(block))
    if outcome.errors or any(code != 0 for code, _ in outcome.guard.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
