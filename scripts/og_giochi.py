"""Disegna le cinque immagini da condividere dei giochi del Quiz.

Una figura 1200x630 per gioco in `app/static/img/og/gioco-<nome>.png`: il
marchio, il titolo del gioco in grande, una riga che dice che cosa si fa. Stessa
grafica, stessi font (Sofia Sans) e stessa quantizzazione delle figure dei
territori: si riusano da `scripts/og_territori.py`. I colori sono i valori chiari
dei token, cotti qui perche' un PNG non legge le variabili CSS.

Si lancia una volta e i PNG si committano, come le altre figure OG. Serve
cairosvg e Pillow, che non sono nel venv del sito:

    uv run --with cairosvg --with pillow python scripts/og_giochi.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import og_territori as t  # noqa: E402

DESTINAZIONE = ROOT / "app" / "static" / "img" / "og"

GIOCHI = {
    "indovina-regione": ("Indovina la Regione", "Una regione misteriosa, sei indizi Istat, sei tentativi."),
    "indovina-provincia": ("Indovina la Provincia", "Una provincia misteriosa, sei indizi di dato, sei tentativi."),
    "chi-e-maggiore": ("Chi è maggiore?", "Due territori, un indicatore: quale vale di più?"),
    "ordina": ("Ordina le regioni", "Dal valore più alto al più basso, con i dati veri."),
    "province-italiane": ("Dov'è la provincia?", "Dieci province da trovare sulla mappa muta, e ogni errore dice di quanto."),
}

# La riga in fondo dice di che cosa e' fatto il gioco: la mappa e' fatta di confini, non di indicatori.
PIEDE = {"province-italiane": "Confini delle province Istat, 2023"}
PIEDE_PREDEFINITO = "Dati Istat, con anno e fonte a ogni domanda"


def svg(titolo: str, riga: str, m: t.Measurer, piede: str = PIEDE_PREDEFINITO) -> str:
    for testo in (titolo, riga, piede):
        for ch in t.FORBIDDEN:
            assert ch not in testo, testo
    larghezza = t.WIDTH - 2 * t.LEFT
    size = m.fit(titolo, larghezza, (120, 112, 104, 96, 88, 80), t.DISPLAY_FONT, bold=True)
    assert size, titolo
    parti = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{t.WIDTH}" height="{t.HEIGHT}" viewBox="0 0 {t.WIDTH} {t.HEIGHT}">',
             f'<rect width="{t.WIDTH}" height="{t.HEIGHT}" fill="{t.PAPER}"/>',
             f'<rect x="{t.LEFT}" y="58" width="44" height="6" fill="{t.ACCENT}"/>',
             t._text(t.LEFT, 100, "Divario Italia", 28, t.INK, t.DISPLAY_FONT, bold=True)]
    brand = m.width("Divario Italia", 28, t.DISPLAY_FONT, bold=True)
    parti.append(f'<rect x="{t.LEFT + brand + 16:.1f}" y="78" width="2" height="26" fill="{t.RULE}"/>')
    parti.append(t._text(t.LEFT + brand + 34, 100, "Quiz", 24, t.MUTED))
    parti.append(t._text(t.WIDTH - 56, 100, "divarioitalia.it", 20, t.MUTED, anchor="end"))
    parti.append(t._text(t.LEFT - 4, 340, titolo, size, t.INK, t.DISPLAY_FONT, bold=True))
    for i, linea in enumerate(m.wrap(riga, larghezza, 36)):
        parti.append(t._text(t.LEFT, 410 + i * 46, linea, 36, t.MUTED))
    parti.append(f'<rect x="{t.LEFT}" y="540" width="{larghezza}" height="1.5" fill="{t.RULE}"/>')
    parti.append(t._text(t.LEFT, 584, piede, 24, t.MUTED))
    parti.append("</svg>")
    return "".join(parti)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="og-giochi-") as workdir:
        t.prepare_fonts(Path(workdir))
        print(f"font dei titoli: {t.resolved_font(t.DISPLAY_FONT)}")
        m = t.Measurer()
        for nome, (titolo, riga) in GIOCHI.items():
            peso = t.rasterize(svg(titolo, riga, m, PIEDE.get(nome, PIEDE_PREDEFINITO)), DESTINAZIONE / f"gioco-{nome}.png")
            print(f"gioco-{nome}.png {peso} byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
