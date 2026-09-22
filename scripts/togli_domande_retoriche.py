#!/usr/bin/env python3
"""Toglie la domanda retorica in chiusura dalle pagine indicatore che ce l'hanno.

`content/STYLE.md` la vieta per nome ("Niente domanda retorica in chiusura") e il
18 settembre 2026 stava in **298 pagine su 382**. Non sono pezzi della catena di
oggi: sono gli stub della produzione in massa, tre blocchi senza titoli scritti
prima del 4 agosto 2026, quando l'unica istruzione sulla lingua era un elenco di
divieti. Sono l'83% di quello che il sito pubblica, e quindi sono quasi tutto
quello che un lettore trova.

**Questo script non rende buono un pezzo.** Toglie il tell piu' visibile da 298
pagine in un colpo, e il resto di quei pezzi resta da riscrivere passando dalla
coda. Serve perche' riscriverli tutti a mano non si fa, e perche' una pagina che
si chiude con "Si fanno pochi figli per scelta o per un contesto che non aiuta?"
dice al lettore che chi ha scritto non aveva una fine.

La forma e' uniforme e per questo la chirurgia e' sicura: in tutte e 298 la
domanda e' **l'ultima frase del blocco `quadro`**, e il paragrafo che la contiene
ne ha altre. Lo script rifiuta di toccare qualunque altro caso.

    bin/py scripts/togli_domande_retoriche.py            # dice che cosa farebbe
    bin/py scripts/togli_domande_retoriche.py --scrivi   # lo fa
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

RADICE = pathlib.Path(__file__).resolve().parent.parent
PAGINE = RADICE / "content" / "indicators"

FRASE = re.compile(r"[^.!?]+[.!?]")
SEZIONE = re.compile(r"<!-- sezione: (\w+) -->")


def _paragrafi(testo: str) -> list[str]:
    return [p for p in testo.split("\n\n") if p.strip()]


def togli(contenuto: str) -> tuple[str, str] | None:
    """Il contenuto senza la domanda finale del `quadro`, e la domanda tolta.

    `None` quando non c'e' niente da togliere, o quando il caso non e' quello
    previsto: un paragrafo fatto della sola domanda resterebbe vuoto, e un
    pezzo con i titoli di sezione non e' uno stub e va riscritto, non rattoppato.
    """
    if re.search(r"^## ", contenuto, re.M):
        return None
    pezzi = SEZIONE.split(contenuto)
    if len(pezzi) < 3:
        return None
    for indice in range(1, len(pezzi) - 1, 2):
        if pezzi[indice] != "quadro":
            continue
        corpo = pezzi[indice + 1]
        paragrafi = _paragrafi(corpo)
        if not paragrafi:
            return None
        ultimo = paragrafi[-1]
        frasi = FRASE.findall(ultimo)
        if len(frasi) < 2 or not frasi[-1].strip().endswith("?"):
            return None
        domanda = frasi[-1].strip()
        # Si taglia sull'ultima occorrenza, cosi' una domanda che comparisse
        # due volte non fa sparire quella sbagliata.
        taglio = ultimo.rstrip().rfind(domanda)
        if taglio <= 0:
            return None
        nuovo_ultimo = ultimo.rstrip()[:taglio].rstrip()
        if not nuovo_ultimo or not nuovo_ultimo.endswith((".", "!")):
            return None
        pezzi[indice + 1] = corpo.replace(ultimo.rstrip(), nuovo_ultimo, 1)
        return "".join(
            p if i % 2 == 0 else f"<!-- sezione: {p} -->"
            for i, p in enumerate(pezzi)
        ), domanda
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scrivi", action="store_true", help="scrive i file invece di dire che cosa farebbe")
    parser.add_argument("--quanti", type=int, default=6, help="quante domande stampare per esempio")
    args = parser.parse_args(argv)

    toccati, saltati = [], 0
    for file in sorted(PAGINE.glob("*.md")):
        contenuto = file.read_text(encoding="utf-8")
        esito = togli(contenuto)
        if esito is None:
            if "?" in contenuto:
                saltati += 1
            continue
        nuovo, domanda = esito
        toccati.append((file, domanda))
        if args.scrivi:
            file.write_text(nuovo, encoding="utf-8")

    print(f"{'tolte da' if args.scrivi else 'da togliere in'} {len(toccati)} pagine")
    print(f"{saltati} pagine hanno un punto di domanda che questo script non tocca")
    for file, domanda in toccati[: args.quanti]:
        print(f"  {file.name:16} {domanda}")
    if not args.scrivi and toccati:
        print("\n--scrivi per farlo")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
