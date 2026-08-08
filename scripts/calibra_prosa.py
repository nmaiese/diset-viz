#!/usr/bin/env python3
"""Che cosa separa davvero il giornalismo vero dai nostri articoli, misurato.

## L'ipotesi di partenza, e perché non ha retto

Thäsler-Kordonouri, Thurman, Schwertberger e Stalph, *Journalism* 26(9) 2025,
esperimento su **3.135 lettori** e 24 articoli data-driven, metà scritti a mano
e metà automatizzati: comprensibilità 76,79 contro 73,10, sulla parte numerica
74,07 contro 69,38, e **nessuna differenza significativa su stile e struttura
delle frasi**. I due mediatori del divario sono la **densità numerica** e la
**scelta delle parole**.

Sembrava la spiegazione del freddo, e su questo corpus **non è così**.
Misurata la densità numerica, numeri ogni cento parole:

    per articolo      q10    q25    q50    q75    q90
    esempi (10)      1.63   2.00   3.54   6.80  11.54
    pubblicati (376) 2.03   2.44   2.91   3.62   4.78

I nostri articoli **non sono più densi**: la mediana è più bassa. Lo studio
misurava NLG post-editato in inglese, noi abbiamo prosa di modello in italiano,
e la soglia non si trasferisce. Sta scritto qui perché un'ipotesi provata e
caduta vale quanto una confermata, e perché senza questo paragrafo qualcuno
la riproverebbe.

## Quello che invece separa i due corpora

**La quota di paragrafi sostanziali senza nemmeno una cifra.**

    esempi (7 con almeno tre paragrafi)   mediana 0.25   massimo 0.33
    pubblicati (376)                      mediana 0.67   massimo 0.67

**313 articoli su 376, l'83%, stanno sopra il massimo degli esempi.** Le due
distribuzioni quasi non si toccano.

Che cosa dice questo numero: nei nostri articoli due paragrafi su tre affermano
qualcosa senza portare niente. Non è densità sbagliata, è **separazione**:
un paragrafo che ammucchia le cifre e due che commentano a vuoto. Il
giornalismo vero intreccia, e infatti lascia scoperto un paragrafo su quattro,
non due su tre.

Ed è lo stesso difetto che il lint aveva già trovato da un'altra porta, con
`dinamica-senza-fonte` su 52 articoli su 52: un paragrafo senza una cifra e
senza un identificatore di corpus non è sobrio, è **vuoto**. È il freddo,
contato.

## Perché sugli esempi e non sui 52 riscritti

I 52 sono i freddi. Calibrarci sopra consacrerebbe il difetto invece di
misurarlo. `content/esempi/` è un campione piccolo ma della popolazione
giusta: testi che un italiano ha scritto e che qualcuno ha letto volentieri.
Stesso principio di `packs/calibration.py`: è una misura, e ritoccarla a mano
la rende un'opinione.

    bin/py -m scripts.calibra_prosa              # scrive la calibrazione
    bin/py -m scripts.calibra_prosa --confronto  # esempi contro pubblicati

Stdlib pura.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESEMPI = os.path.join(ROOT, "content", "esempi", "*.md")
ARTICOLI = os.path.join(ROOT, "content", "indicators", "*.json")
OUT = os.path.join(ROOT, "officina", "calibrazione_prosa.json")

# Un numero è una cifra con la sua eventuale parte decimale, virgola o punto.
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

# Sotto le venticinque parole un blocco è una didascalia, non un paragrafo che
# deve reggersi: chiederle una cifra sarebbe pedanteria.
MIN_WORDS_PARAGRAPH = 25
# Sotto i tre paragrafi la quota è 0, 1/2 o 1, e non misura niente.
MIN_PARAGRAPHS = 3

QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)


def numeric_density(text: str) -> float:
    """Numeri ogni cento parole. Misurata, riportata, non usata come soglia."""
    words = len(WORD.findall(text))
    if not words:
        return 0.0
    return len(NUMBER.findall(text)) * 100.0 / words


def paragraphs(text: str) -> list[str]:
    return [block for block in re.split(r"\n\s*\n", text)
            if len(WORD.findall(block)) >= MIN_WORDS_PARAGRAPH]


def unsupported_share(text: str) -> float | None:
    """Quota di paragrafi sostanziali senza nemmeno una cifra. None se troppo corto."""
    blocks = paragraphs(text)
    if len(blocks) < MIN_PARAGRAPHS:
        return None
    return sum(1 for block in blocks if not NUMBER.search(block)) / len(blocks)


def read_exemplar(path: str) -> str:
    """Il solo testo citato, senza la scheda che lo introduce.

    Gli estratti sono in blockquote sotto `## Il testo`: la scheda sopra ha
    date e URL, cioè numeri che non sono prosa e falserebbero la misura verso
    l'alto proprio nel campione che deve fare da metro.
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    quoted, inside = [], False
    for line in lines:
        if line.strip().startswith("## "):
            inside = "testo" in line.lower()
            continue
        if inside and line.lstrip().startswith(">"):
            quoted.append(line.lstrip()[1:].strip())
        elif inside and not line.strip():
            quoted.append("")
    return "\n".join(quoted).strip()


def read_article(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        entry = json.load(handle)
    parts = [entry.get("lead") or ""]
    for section in entry.get("sections") or []:
        parts.append(section.get("body") or "")
    return "\n\n".join(part for part in parts if part.strip())


def quantiles(values) -> dict:
    values = [value for value in values if value is not None]
    if not values:
        return {}
    ordered = sorted(values)
    out = {}
    for share in QUANTILES:
        position = share * (len(ordered) - 1)
        low, high = int(position), min(int(position) + 1, len(ordered) - 1)
        weight = position - low
        out[f"q{int(share * 100)}"] = round(
            ordered[low] * (1 - weight) + ordered[high] * weight, 3)
    return out


def sample(paths, reader) -> dict:
    density, unsupported = [], []
    for path in sorted(paths):
        text = reader(path)
        if len(WORD.findall(text)) < 100:
            continue
        density.append(numeric_density(text))
        share = unsupported_share(text)
        if share is not None:
            unsupported.append(share)
    return {"testi": len(density), "misurabili": len(unsupported),
            "densita_numerica": quantiles(density),
            "paragrafi_scoperti": quantiles(unsupported),
            "paragrafi_scoperti_max": round(max(unsupported), 3) if unsupported else None}


def build() -> dict:
    esempi = sample(glob.glob(ESEMPI), read_exemplar)
    scoperti = esempi["paragrafi_scoperti"]
    return {
        "fonte": "content/esempi/",
        "metodo": ("quota di paragrafi sostanziali (>=25 parole) senza nemmeno "
                   "una cifra; quantili del campione"),
        "perche": (
            "Ipotesi provata e caduta: la densità numerica di "
            "Thäsler-Kordonouri et al. (Journalism 26(9) 2025, n=3135) non "
            "separa i due corpora, i nostri articoli non sono più densi. "
            "Separa invece la quota di paragrafi senza cifre: esempi 0.25 di "
            "mediana e 0.33 di massimo, pubblicati 0.67 di mediana, con 313 "
            "articoli su 376 sopra il massimo degli esempi."),
        # La soglia è il q90 del campione buono: sopra, il paragrafo che
        # afferma senza portare niente è la regola invece dell'eccezione.
        "soglia_paragrafi_scoperti": scoperti.get("q90"),
        "esempi": esempi,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--confronto", action="store_true",
                        help="stampa esempi contro pubblicati, senza scrivere")
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args(argv)

    esempi = sample(glob.glob(ESEMPI), read_exemplar)
    if not esempi["testi"]:
        print(f"nessun esempio leggibile in {ESEMPI}", file=sys.stderr)
        return 1

    if args.confronto:
        pubblicati = sample(glob.glob(ARTICOLI), read_article)
        header = " ".join(f"{f'q{int(q * 100)}':>7}" for q in QUANTILES)
        for measure in ("densita_numerica", "paragrafi_scoperti"):
            print(f"\n{measure.replace('_', ' ').upper()}")
            print(f"{'':14} {'testi':>6} {header}")
            for label, data in (("esempi", esempi), ("pubblicati", pubblicati)):
                row = data[measure]
                print(f"{label:14} {data['misurabili']:6} "
                      + " ".join(f"{row.get(f'q{int(q * 100)}', 0):7.2f}"
                                 for q in QUANTILES))
        soglia = esempi["paragrafi_scoperti"].get("q90") or 0
        oltre = [share for share in
                 (unsupported_share(read_article(p)) for p in glob.glob(ARTICOLI))
                 if share is not None and share > soglia]
        print(f"\npubblicati sopra il q90 degli esempi ({soglia:.2f}): "
              f"{len(oltre)} su {pubblicati['misurabili']}")
        return 0

    payload = build()
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"scritto {args.out}")
    print(f"  {esempi['testi']} esempi, {esempi['misurabili']} misurabili")
    print(f"  paragrafi scoperti  {esempi['paragrafi_scoperti']}")
    print(f"  soglia (q90)        {payload['soglia_paragrafi_scoperti']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
