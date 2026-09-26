"""Rasterizza in PNG le immagini di anteprima sociale.

Perche' serve. Le `og:image` del sito erano tutte SVG, e **nessun social
disegna un SVG**: Facebook, LinkedIn, X, WhatsApp, Slack e iMessage scartano
l'immagine e mostrano il link nudo. Il sito dichiarava anche
`twitter:card=summary_large_image`, cioe' il formato che esiste apposta per
mostrare un'immagine grande, sopra un file che quel lettore non apre. Ogni
condivisione di ogni pagina usciva senza figura.

Perche' un PNG committato e non una conversione a runtime. L'immagine cambia
quando cambia il disegno, cioe' quasi mai, e un convertitore nel processo web
sarebbe una dipendenza in piu' sul percorso della richiesta per un file che e'
sempre lo stesso. Qui la conversione e' un passo di manutenzione: si rilancia
quando si tocca una copertina, e il risultato si committa accanto al sorgente.

I font. Dal 26 settembre 2026 le copertine nominano Sofia Sans, nella rampa
blu e coi colori delle ripartizioni. Dentro un <img> un SVG non carica i font
del sito, quindi in pagina ripiegano sul sans-serif di sistema, e il PNG fa lo
stesso: la figura condivisa e' identica a quella che si vede sul sito, che e'
la cosa che conta.

    bin/py scripts/rasterize_og_images.py            # converte cio' che manca
    bin/py scripts/rasterize_og_images.py --forza    # riconverte tutto
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
IMMAGINI = RADICE / "app" / "static" / "img"

# La misura che ogni lettore di anteprime si aspetta, e quella che i sorgenti
# gia' dichiarano nel loro viewBox: 1200x630, rapporto 1.91:1.
LARGHEZZA = 1200
ALTEZZA = 630


def sorgenti():
    """Gli SVG che finiscono in `og:image`: la figura del sito e le copertine."""
    trovati = [IMMAGINI / "og-divario-italia.svg"]
    trovati += sorted((IMMAGINI / "blog").glob("*.svg"))
    return [percorso for percorso in trovati if percorso.exists()]


def converti(sorgente: Path, forza: bool = False) -> str:
    destinazione = sorgente.with_suffix(".png")
    if destinazione.exists() and not forza:
        return f"salto  {destinazione.relative_to(RADICE)} (c'e' gia')"
    import cairosvg

    cairosvg.svg2png(
        url=str(sorgente),
        write_to=str(destinazione),
        output_width=LARGHEZZA,
        output_height=ALTEZZA,
    )
    peso = destinazione.stat().st_size / 1024
    return f"scritto {destinazione.relative_to(RADICE)} ({peso:.0f} KB)"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forza", action="store_true",
                        help="riconverte anche i PNG che esistono gia'")
    argomenti = parser.parse_args(argv)

    trovati = sorgenti()
    if not trovati:
        print("nessun SVG da convertire", file=sys.stderr)
        return 1
    for sorgente in trovati:
        print(converti(sorgente, forza=argomenti.forza))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
