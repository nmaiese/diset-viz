"""Verifica che ogni citazione del corpus esista davvero, parola per parola.

Il corpus da' agli articoli la licenza di spiegare perche' i numeri si muovono,
citando l'istituzione invece di dedurre la causa dai dati. Quella licenza vale
solo se le citazioni sono vere: una parafrasi salvata come verbatim e' gia'
un'invenzione a meta', e finirebbe su una pagina pubblica sotto il nome del
progetto.

Il rischio e' concreto e vale la pena scriverlo: le citazioni si raccolgono con
strumenti che passano per un modello, e un modello che riassume mentre copia
non lo dichiara. Quindi questo script non si fida di chi ha raccolto. Scarica
la pagina con la sola libreria standard, la riduce a testo, e cerca la
citazione **come stringa**. Nessun modello nel giro di verifica.

    python3 -m scripts.fetch_corpus --verify
    python3 -m scripts.fetch_corpus --verify --id snpa-bacino-padano

Uscita diversa da zero se una citazione non si trova: e' pensato per il
cancello, non solo per l'occhio.

Sui blocchi: un 403 o un 503 e' "bloccato", non "inesistente", e lo script lo
dice cosi'. Non aggira niente e si presenta con uno user agent che dice chi e'.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

from packs import context

# Ci presentiamo per quello che siamo. Fingersi un browser sarebbe aggirare un
# blocco, e il blocco di una fonte istituzionale e' una sua decisione.
USER_AGENT = ("DivarioItalia-corpus/1.0 (verifica citazioni; "
              "https://divarioitalia.it)")
TIMEOUT = 30

_TAGS = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_ANY_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def page_text(url):
    """(testo, errore). Il testo e' normalizzato negli spazi, non nel resto."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as error:
        return None, f"HTTP {error.code}: bloccato o spostato, non inesistente"
    except Exception as error:  # rete, DNS, TLS
        return None, f"irraggiungibile: {type(error).__name__}"

    if url.lower().endswith(".pdf") or raw[:4] == b"%PDF":
        return None, "PDF: questa verifica legge solo HTML"

    body = raw.decode(charset, errors="replace")
    body = _TAGS.sub(" ", body)
    body = _ANY_TAG.sub(" ", body)
    return _SPACE.sub(" ", html.unescape(body)).strip(), None


def normalise(text):
    """Spazi e apostrofi tipografici uniformati. Le parole restano intatte.

    Solo cio' che un sito puo' cambiare senza cambiare il testo: un apostrofo
    curvo al posto di uno dritto non e' una citazione diversa. Tutto il resto
    deve combaciare, altrimenti non e' un verbatim.
    """
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"')
                .replace(" ", " ").replace("–", "-").replace("—", "-"))
    return _SPACE.sub(" ", text).strip().lower()


def verify(claim):
    """(esito, dettaglio) per una singola affermazione."""
    broken = context.problems(claim)
    if broken:
        return "malformata", "; ".join(broken)

    text, error = page_text(claim["url"])
    if text is None:
        return "bloccata", error

    if normalise(claim["quote"]) in normalise(text):
        return "verificata", f"{len(claim['quote'])} caratteri trovati"

    # Dove si rompe: aiuta a capire se e' una parafrasi o solo un troncamento.
    words = claim["quote"].split()
    longest = 0
    for size in range(len(words), 3, -1):
        if normalise(" ".join(words[:size])) in normalise(text):
            longest = size
            break
    return "non trovata", (f"combaciano le prime {longest} parole su {len(words)}"
                           if longest else "nemmeno l'inizio combacia")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--id", default=None, help="verifica una sola affermazione")
    args = parser.parse_args(argv)

    if not args.verify:
        parser.print_help()
        return 0

    claims = context.reload_corpus()
    if args.id:
        claims = [claim for claim in claims if claim.get("id") == args.id]
    if not claims:
        print("nessuna affermazione nel corpus", file=sys.stderr)
        return 1

    counts = {}
    failed = 0
    for claim in claims:
        outcome, detail = verify(claim)
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"[{outcome:12}] {claim.get('id', '?'):34} {detail}")
        if outcome in ("non trovata", "malformata"):
            failed += 1
            print(f"               {claim.get('url', '')}")

    print("\n" + "  ".join(f"{name}: {count}" for name, count in sorted(counts.items())))
    if failed:
        print(f"\n{failed} citazioni non reggono: vanno corrette o tolte.",
              file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
