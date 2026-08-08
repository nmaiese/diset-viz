#!/usr/bin/env python3
"""Hook PreCompact: quello che sta su disco, ridetto prima che il contesto si accorci.

Quando la conversazione viene compattata, quello che sta solo nella
conversazione può perdersi. Quello che sta in un file no: questo hook lo rilegge
da lì e lo ristampa, così il riassunto che entra nel nuovo contesto se lo porta
dietro. Non inventa stato, lo cita.

Leggeva le schede di run sotto `data/pipeline/runs/`, che erano lo stato della
catena editoriale autonoma. Quella catena non esiste più, e le schede sono
ferme a luglio: l'hook continuava a stampare "stadio writer, esito merged" a
ogni compattazione, cioè a insegnare a chi legge il vocabolario di una macchina
spenta, con in fondo il rimando a due file cancellati. È esattamente il guasto
contro cui `CLAUDE.md` apre: un prompt che ripete un contratto invece di
puntarlo.

Adesso cita quello che la catena minima lascia davvero su disco: i dossier
montati, le bozze congelate da `lab.controlla --salva` e gli articoli scritti.
Sono le tre cose il cui percorso serve per riprendere un giro a metà.

Best effort: stampare meno è sempre meglio che fallire.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Che cosa la catena minima lascia dietro di sé, nell'ordine in cui la si
# attraversa. `content/indicators/` non è qui apposta: sono 300 file e solo gli
# ultimi due o tre vengono da una run: i suoi cambiamenti si leggono in git,
# che è la fonte giusta per un file versionato.
TRACCE = (
    ("dossier montati", Path("data") / "lab" / "dossier"),
    ("bozze congelate", Path("data") / "lab" / "bozze"),
    ("articoli di prova", Path("data") / "lab" / "articoli"),
)


def _recenti(cartella, quanti=3):
    try:
        file = [percorso for percorso in cartella.glob("*.json") if percorso.is_file()]
    except OSError:
        return []
    file.sort(key=lambda percorso: percorso.stat().st_mtime, reverse=True)
    return file[:quanti]


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    lines = ["Promemoria per la compattazione (stato letto dai file, non dalla chat):"]
    try:
        branch = subprocess.run(
            ("git", "rev-parse", "--abbrev-ref", "HEAD"),
            cwd=str(ROOT), capture_output=True, text=True,
        ).stdout.strip()
        if branch:
            lines.append(f"- branch corrente: {branch}")
    except OSError:
        pass
    for etichetta, relativo in TRACCE:
        recenti = _recenti(ROOT / relativo)
        if recenti:
            nomi = ", ".join(percorso.name for percorso in recenti)
            lines.append(f"- {etichetta} più di recente ({relativo}): {nomi}")
    lines.append("- la catena e i suoi comandi: lab/README.md; "
                 "che cosa conviene scrivere adesso: "
                 "bin/py -m lab.dossier --coda 5 --freschi 2025")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
