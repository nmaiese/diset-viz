"""Quali articoli si somigliano troppo: la coda anti-serialita'.

`review_queue` chiede se un articolo e' probabilmente sbagliato, `reading_queue`
se si legge. Questa chiede una cosa che si vede solo guardando il catalogo tutto
insieme: **quali articoli sono quasi intercambiabili con un altro?** Un catalogo
di seicento pagine costruite sullo stesso stampo (stesso attacco, stessa sequenza
di H2, stesso giro di frasi con i nomi cambiati) e' seriale per costruzione, e la
serialita' e' un difetto di lettura prima ancora che di SEO: due pagine che si
leggono uguali non danno al lettore un motivo per distinguerle.

Non giudica un articolo da solo: nessun testo e' seriale in isolamento, lo e'
**rispetto a un altro**. Quindi il prodotto e' una coda di coppie, ordinata per
quanto si somigliano, e ogni riga porta il suo vicino piu' prossimo e su quale
asse (l'attacco, il corpo, la sequenza degli H2). Read-only, come le altre code:
non tocca nessun articolo, alimenta la revisione.

    python3 scripts/seriality_queue.py            # le coppie piu' seriali
    python3 scripts/seriality_queue.py --json      # per un altro programma
    python3 scripts/seriality_queue.py --all       # tutte, anche sotto soglia

Pure stdlib, come il resto della catena.
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import indicator_store  # noqa: E402  (path bootstrap above)
from scripts import verification_queue  # noqa: E402

_WORD = re.compile(r"[a-zA-Zàèéìòùç]+")
# Parole troppo corte non discriminano: sono le funzionali (di, che, la, per) che
# ogni articolo condivide, e gonfiano ogni somiglianza della stessa costante.
_MIN_WORD = 4

# Sopra queste soglie una coppia entra in coda. Larghe di proposito: la coda e'
# consultiva, e un falso positivo costa una lettura, non una riscrittura. Il
# lead e' l'asse piu' stretto perche' e' la prima cosa che il lettore legge e la
# descrizione SERP: due attacchi uguali sono il difetto piu' visibile.
LEAD_SIM = 0.45
BODY_SIM = 0.40


def _tokens(text: str) -> set:
    return {w for w in _WORD.findall((text or "").lower()) if len(w) >= _MIN_WORD}


def _jaccard(a: set, b: set) -> float:
    """L'indice di Jaccard, come `discovery._jaccard`: intersezione su unione."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _profile(entry: dict) -> dict | None:
    """L'impronta di stile di un articolo scritto: attacco, corpo, sequenza H2.

    None se non c'e' prosa scritta a mano (un articolo tutto composto dai dati non
    ha uno stile d'autore da confrontare: e' lo scheletro uguale per tutti apposta).
    """
    lead = (entry.get("lead") or "").strip()
    sections = [s for s in (entry.get("sections") or []) if (s.get("body") or "").strip()]
    if not lead and not sections:
        return None
    headings = tuple((s.get("h") or s.get("role") or "").strip().lower() for s in sections)
    body = " ".join(s.get("body") or "" for s in sections)
    return {
        "lead_tokens": _tokens(lead),
        "body_tokens": _tokens(body),
        "headings": headings,
    }


def _heading_overlap(a: tuple, b: tuple) -> float:
    """Quanto due sequenze di H2 si somigliano, come insiemi di titoli."""
    return _jaccard(set(a) - {""}, set(b) - {""})


def _pressure(lead_sim: float, body_sim: float) -> float:
    """Quanto una coppia preme sulle soglie, in un numero solo.

    Le due soglie sono diverse (0,45 sull'attacco, 0,40 sul corpo) perche' misurano
    cose diverse, quindi confrontare i due valori grezzi fra loro non vuol dire
    niente: 0,44 di attacco e' **sotto** la sua soglia, 0,42 di corpo e' **sopra**
    la sua, e la coppia da guardare e' la seconda. Tenere il vicino col numero piu'
    alto sceglieva la prima e buttava la seconda, che poi il filtro `serial()`
    scartava perche' sotto soglia: la coppia seriale vera spariva dalla coda.
    Rapportare ogni asse alla propria soglia rende i due confrontabili, e sopra
    soglia vuol dire semplicemente `>= 1`.
    """
    return max(lead_sim / LEAD_SIM, body_sim / BODY_SIM)


def build_queue(texts=None) -> list[dict]:
    """Una riga per articolo che ha un vicino troppo prossimo, ordinata per
    somiglianza decrescente. Ogni riga porta il codice, il vicino, e i tre assi."""
    texts = texts if texts is not None else indicator_store.load_all()
    profiles = {}
    for key, entry in texts.items():
        prof = _profile(entry)
        if prof is not None:
            profiles[key] = prof

    best = {}  # key -> (pressure, score, peer, lead_sim, body_sim, head_sim)
    for (key_a, pa), (key_b, pb) in itertools.combinations(profiles.items(), 2):
        lead_sim = _jaccard(pa["lead_tokens"], pb["lead_tokens"])
        body_sim = _jaccard(pa["body_tokens"], pb["body_tokens"])
        head_sim = _heading_overlap(pa["headings"], pb["headings"])
        pressure = _pressure(lead_sim, body_sim)
        score = max(lead_sim, body_sim)
        for key, peer in ((key_a, key_b), (key_b, key_a)):
            if key not in best or pressure > best[key][0]:
                best[key] = (pressure, score, peer, lead_sim, body_sim, head_sim)

    rows = []
    for key, (pressure, score, peer, lead_sim, body_sim, head_sim) in best.items():
        rows.append({
            "code": verification_queue.code_of(key),
            "key": key,
            "peer": verification_queue.code_of(peer),
            "score": round(score, 3),
            "lead_sim": round(lead_sim, 3),
            "body_sim": round(body_sim, 3),
            "headings_sim": round(head_sim, 3),
            "serial": pressure >= 1.0,
        })
    return sorted(rows, key=lambda r: -_pressure(r["lead_sim"], r["body_sim"]))


def serial(rows) -> list[dict]:
    """Le sole coppie sopra soglia: la coda vera di revisione."""
    return [r for r in rows if r["serial"]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="uscita per un altro programma")
    parser.add_argument("--all", action="store_true", help="tutte le coppie, anche sotto soglia")
    args = parser.parse_args(argv)

    rows = build_queue()
    if not args.all:
        rows = serial(rows)

    if args.json:
        import json
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    if not rows:
        print("Niente di seriale sopra soglia.")
        return 0
    for row in rows:
        print(f"{row['score']:.2f}  {row['code']:28.28} ~ {row['peer']:28.28}  "
              f"(lead {row['lead_sim']:.2f}  corpo {row['body_sim']:.2f}  h2 {row['headings_sim']:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
