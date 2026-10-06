#!/usr/bin/env python3
"""Controlla issue e label richieste per le PR che modificano contenuti."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Iterable


RIFERIMENTO_ISSUE = re.compile(r"\b(?:closes|fixes|resolves|refs)\s+#\d+\b", re.IGNORECASE)


def _name_status_paths(changed_files: Iterable[str]) -> list[tuple[str, str]]:
    """Restituisce coppie (stato, percorso) dal formato git --name-status."""
    result: list[tuple[str, str]] = []
    for line in changed_files:
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        # Rename/copy hanno percorso sorgente e destinazione: entrambi contano.
        result.extend((status[0], path) for path in fields[1:])
    return result


def _tocca_contenuti(changed_files: Iterable[str]) -> bool:
    return any(
        status != "D" and path.startswith(("content/posts/", "content/indicators/"))
        for status, path in _name_status_paths(changed_files)
    )


def controlla_pr(body: str | None, labels: Iterable[str], changed_files: Iterable[str]) -> list[str]:
    """Restituisce messaggi di errore; lista vuota significa PR valida."""
    files = list(changed_files)
    if not _tocca_contenuti(files):
        return []

    errori = []
    if not body or not RIFERIMENTO_ISSUE.search(body):
        errori.append("manca `Closes #n` nel corpo: apri una issue per il pezzo e collegala con Closes, Fixes, Resolves o Refs #numero.")
    if not any(label.casefold().startswith("run:") for label in labels):
        errori.append("manca una label `run:`: aggiungi una label come `run:blog`, `run:team`, `run:lite` o `run:routine`.")
    return errori


def _event_details(event_path: str) -> tuple[str | None, list[str], str]:
    with open(event_path, encoding="utf-8") as event_file:
        event = json.load(event_file)
    pr = event["pull_request"]
    body = pr.get("body")
    labels = [label["name"] for label in pr.get("labels", [])]
    base = pr["base"]["ref"]
    return body, labels, base


def _changed_files(base: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-status", f"origin/{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-cambiati", nargs="*", help="righe git --name-status, per test")
    args = parser.parse_args(argv)

    try:
        body, labels, base = _event_details(os.environ["GITHUB_EVENT_PATH"])
        files = args.file_cambiati if args.file_cambiati is not None else _changed_files(base)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Impossibile leggere evento o file PR: {exc}", file=sys.stderr)
        return 1

    errori = controlla_pr(body, labels, files)
    if errori:
        for errore in errori:
            print(f"::error::{errore}")
        return 1
    print("Controllo contenuti superato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
