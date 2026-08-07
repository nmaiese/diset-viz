"""Il lettore di `data/pipeline/tool_failures.jsonl`. Esisteva solo chi scriveva.

Il file lo riempie l'hook `PostToolUseFailure` da mesi, una riga per strumento
inciampato. Nessuno lo apriva mai, e si e' visto quanto costa: l'errore
`.venv/bin/python: exit 127` era registrato li' **tre ore prima** della prima
run del workflow, su `ter-178`. In quella run tutti e quattro gli scrittori
hanno speso quattro turni a testa a ricercarlo da capo, e un pubblicatore ha
finito per eseguire il lint con l'interprete di un altro worktree. Un canale
che nessuno legge non e' un canale: e' un costo di scrittura senza il ricavo.

Quello che serve non e' l'elenco dei fallimenti, che sono quasi tutti unici e
innocui: e' **cio' che si ripete**. Un gesto che fallisce una volta e' un
incidente, lo stesso gesto che fallisce cinque volte in due giorni e' un pezzo
di ambiente rotto che ogni agente ripaga da solo.

    bin/py scripts/tool_failures.py              # cio' che si ripete, ultime 48h
    bin/py scripts/tool_failures.py --ore 168 --min 3
    bin/py scripts/tool_failures.py --breve      # una riga, per gli hook

Stdlib pura. Non fallisce mai in modo rumoroso: se il file non c'e', non c'e'
niente da dire, ed esce zero.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG = PROJECT_ROOT / "data" / "pipeline" / "tool_failures.jsonl"

ORE = 48
MINIMO = 2
SPAZI = re.compile(r"\s+")
# I numeri variabili di un messaggio (pid, righe, byte, timestamp) fanno
# sembrare unico lo stesso guasto ripetuto. La firma li appiattisce, cosi'
# "exit code 127" ripetuto cinque volte si conta cinque volte.
CIFRE = re.compile(r"\d+")
USCITA = re.compile(r"(?i)exit code \d+\.?")


def firma(riga: dict) -> str:
    """Il guasto, non l'occorrenza: la prima riga che dice qualcosa, senza i numeri.

    Non la prima riga e basta: quasi tutti i fallimenti di `Bash` cominciano
    con "Exit code 1", quindi raggrupparli per quella riga risponde "trentuno
    volte lo stesso guasto" a trentuno guasti diversi, che e' peggio del
    silenzio. La riga utile e' la prima che non sia solo il codice di uscita.
    """
    errore = str(riga.get("error") or "").strip()
    for linea in errore.splitlines():
        pulita = SPAZI.sub(" ", linea).strip()
        if not pulita or USCITA.fullmatch(pulita):
            continue
        return CIFRE.sub("N", pulita)[:120]
    return CIFRE.sub("N", SPAZI.sub(" ", errore))[:120]


def leggi(path: Path = LOG) -> list[dict]:
    if not path.exists():
        return []
    righe = []
    with path.open(encoding="utf-8") as handle:
        for linea in handle:
            linea = linea.strip()
            if not linea:
                continue
            try:
                riga = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if isinstance(riga, dict):
                righe.append(riga)
    return righe


def _quando(riga: dict):
    try:
        return datetime.fromisoformat(str(riga.get("at")))
    except (TypeError, ValueError):
        return None


def recenti(righe: list[dict], ore: int = ORE, adesso=None) -> list[dict]:
    adesso = adesso or datetime.now(timezone.utc)
    soglia = adesso - timedelta(hours=ore)
    fuori = []
    for riga in righe:
        quando = _quando(riga)
        if quando is None or quando >= soglia:
            fuori.append(riga)
    return fuori


def ripetuti(righe: list[dict], minimo: int = MINIMO) -> list[tuple[str, int, dict]]:
    """[(firma, quante volte, un esempio)], dal piu' ripetuto, sopra `minimo`."""
    conteggio = Counter(firma(riga) for riga in righe if firma(riga))
    esempi = {}
    for riga in righe:
        esempi.setdefault(firma(riga), riga)
    return [(chiave, quante, esempi[chiave])
            for chiave, quante in conteggio.most_common() if quante >= minimo]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ore", type=int, default=ORE)
    parser.add_argument("--min", dest="minimo", type=int, default=MINIMO)
    parser.add_argument("--breve", action="store_true",
                        help="al massimo tre righe, niente se non c'e' niente")
    args = parser.parse_args(argv)

    gruppi = ripetuti(recenti(leggi(), args.ore), args.minimo)
    if not gruppi:
        if not args.breve:
            print(f"nessun guasto ripetuto nelle ultime {args.ore} ore.")
        return 0

    if args.breve:
        for chiave, quante, esempio in gruppi[:3]:
            print(f"guasto ripetuto ({quante}x, {args.ore}h): {esempio.get('tool')}: {chiave}")
        return 0

    print(f"{len(gruppi)} guasti ripetuti nelle ultime {args.ore} ore "
          f"(almeno {args.minimo} volte ciascuno):\n")
    for chiave, quante, esempio in gruppi:
        print(f"{quante}x  {esempio.get('tool') or '?'}  {chiave}")
        comando = str(esempio.get("input") or "").strip()
        if comando:
            print(f"      es. {comando[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
