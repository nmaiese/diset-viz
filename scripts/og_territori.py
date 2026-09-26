"""Disegna le immagini da condividere delle 20 regioni e delle 107 province.

Che cosa sono. Una figura 1200x630 per territorio, quella che WhatsApp,
LinkedIn, X o Slack mostrano quando qualcuno incolla il link della sua pagina:
il nome, la posizione nella qualita' della vita come cifra grande ("79ª su
107"), il profilo e da dove vengono i dati, dove va meglio e dove va peggio, e
a destra la regione ingrandita con le sue province nei colori della qualita'
della vita. La versione civica di un riepilogo di fine anno: una cosa sola,
detta in grande, che chi la riceve capisce senza aprire il link.

Da dove vengono i numeri. Dagli stessi punti da cui li prende la pagina, cosi'
la figura non dice mai una cosa diversa dalla pagina a cui porta:

- regione: posizione e totale da `regione._region_quality()`, il tema dove
  va meglio e quello dove va peggio da `regione._answer(region_profile(key))`
  (per posizione fra le regioni, come la frase-risposta della pagina);
- provincia: posizione, totale e dimensioni da `province_profile.profilo(key)`,
  la migliore e la peggiore come le sceglie `provincia.derive` (`d.best`,
  `d.worst`: la prima e l'ultima dimensione per punteggio);
- la mappa: `common.region_map(regione)`, gradini sulle 107 province; se la
  regione non ha province misurate, la sagoma della regione da
  `maps.REGION_PATHS` nel gradino del suo punteggio fra le regioni.

Il nome della fonte lo dice `app/sources.py` (`institutions_label` sulle
famiglie che il metodo della classifica dichiara), non questo file.

Colori. Sono i valori chiari dei token di `app/static/css/ds/system.css`,
cotti qui perche' un PNG non legge le variabili CSS: carta bianca, inchiostro,
la rampa `--seq-1..6` per i dati, l'arancio solo nel filetto del marchio, mai
su un dato. Il territorio della pagina e' contornato in inchiostro, come la
selezione sulle mappe del sito.

Font. cairosvg prende solo la prima famiglia di `font-family` e la chiede a
fontconfig. Lo script prepara un fontconfig che vede anche i woff2 latin di
Sofia Sans e Sofia Sans Semi Condensed in `app/static/fonts/` (FreeType li apre
se e' compilato con brotli, come sulle distribuzioni correnti). Dove non ci
riesce, fontconfig ripiega sul sans-serif di sistema, come fanno le copertine
del blog: il disegno resta lo stesso, cambia il carattere. Lo script dice
quale ha trovato.

Perche' PNG committati e non una conversione a runtime: le ragioni di
`scripts/rasterize_og_images.py`. Si rilancia quando cambia la classifica o
il disegno, e il risultato si committa. I PNG escono a tavolozza (Pillow,
dipendenza di cairosvg, solo in `requirements-dev.txt`): immagini a tinte
piatte, e un terzo del peso.

    bin/py -m pip install -r requirements-dev.txt
    bin/py scripts/og_territori.py                  # disegna cio' che manca
    bin/py scripts/og_territori.py --forza          # ridisegna tutto
    bin/py scripts/og_territori.py --solo isernia   # un territorio solo
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.design import og  # noqa: E402

FONT_DIR = ROOT / "app" / "static" / "fonts"
# Solo il sottoinsieme latin: latin-ext porta lo stesso nome di famiglia, e
# fontconfig potrebbe scegliere il file che non ha le lettere accentate.
# Latin copre tutto il Latin-1, quindi "ª", "à", "é", "ü" e l'apostrofo.
FONT_FILES = ("sofia-sans-latin-wght-normal.woff2", "sofia-sans-semi-condensed-latin-wght-normal.woff2")

WIDTH, HEIGHT = og.WIDTH, og.HEIGHT

# I valori chiari di app/static/css/ds/system.css.
INK = "#121519"
MUTED = "#5e646a"
PAPER = "#ffffff"
ACCENT = "#a75001"
RULE = "#e3e6ea"
SURFACE_2 = "#eceef1"
CONTROL_BORDER = "#767b80"
SEQ = ("#d8e8fa", "#a9cbf1", "#76a9e2", "#4383c8", "#1c5fa1", "#093e6f")

TEXT_FONT = "Sofia Sans"
DISPLAY_FONT = "Sofia Sans Semi Condensed"
# La prima famiglia e' quella che cairosvg chiede, le altre valgono per chi
# apre l'SVG in un browser.
FALLBACK = "Arial, Helvetica, sans-serif"

LEFT = 72
TEXT_RIGHT = 648
MAP_BOX = (700, 118, 444, 408)
FORBIDDEN = ("—", "–", ";", "…")
PALETTE_COLORS = 96


def prepare_fonts(workdir: Path) -> None:
    """Un fontconfig che vede anche Sofia Sans, da impostare prima che cairo parta."""
    fonts = workdir / "fonts"
    fonts.mkdir()
    for name in FONT_FILES:
        source = FONT_DIR / name
        if not source.is_file():
            raise FileNotFoundError(f"manca il font {source}")
        shutil.copy(source, fonts / name)
    conf = workdir / "fonts.conf"
    conf.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
        '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
        f"  <dir>{escape(str(fonts))}</dir>\n"
        f"  <cachedir>{escape(str(workdir / 'cache'))}</cachedir>\n"
        "</fontconfig>\n",
        encoding="utf-8",
    )
    os.environ["FONTCONFIG_FILE"] = str(conf)


def resolved_font(family: str) -> str:
    """Il file che fontconfig da' per una famiglia, per dire se e' Sofia o un ripiego."""
    if not shutil.which("fc-match"):
        return "sconosciuto (fc-match non c'e')"
    out = subprocess.run(["fc-match", family, "-f", "%{family[0]} (%{file})"],
                         capture_output=True, text=True, check=True, env=os.environ)
    return out.stdout.strip()


class Measurer:
    """Misura il testo con lo stesso motore che poi lo disegna (cairo, API toy)."""

    def __init__(self):
        import cairocffi as cairo

        self._cairo = cairo
        self._ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, 4))

    def width(self, text: str, size: float, family: str = TEXT_FONT, bold: bool = False) -> float:
        weight = self._cairo.FONT_WEIGHT_BOLD if bold else self._cairo.FONT_WEIGHT_NORMAL
        self._ctx.select_font_face(family, self._cairo.FONT_SLANT_NORMAL, weight)
        self._ctx.set_font_size(size)
        return self._ctx.text_extents(text)[4]

    def fit(self, text: str, width: float, sizes, family: str = TEXT_FONT, bold: bool = False) -> float | None:
        for size in sizes:
            if self.width(text, size, family, bold) <= width:
                return size
        return None

    def wrap(self, text: str, width: float, size: float, family: str = TEXT_FONT, bold: bool = False) -> list[str]:
        lines, line = [], ""
        for word in text.split():
            candidate = f"{line} {word}".strip()
            if line and self.width(candidate, size, family, bold) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        return lines


# -- i dati --------------------------------------------------------------------


def _check_text(card: dict) -> None:
    """I testi della figura seguono le regole dei testi pubblicati."""
    for field in ("name", "source_line", "best", "worst", "map_caption"):
        value = card.get(field) or ""
        if isinstance(value, tuple):
            value = " ".join(value)
        for ch in FORBIDDEN:
            if ch in value:
                raise ValueError(f"{card['level']} {card['key']}: carattere vietato {ch!r} in {field}: {value!r}")
        wide = [c for c in value if ord(c) > 0xFF and c not in "’−"]
        if wide:
            raise ValueError(f"{card['level']} {card['key']}: {wide!r} fuori dal sottoinsieme latin del font")


def _institutions(methodology: dict) -> str:
    from app import sources

    families = [f for f in (methodology.get("source_counts") or {}) if f in sources.SOURCES]
    label = sources.institutions_label(families)
    if not label:
        raise ValueError(f"la classifica non dichiara fonti note: {methodology.get('source_counts')!r}")
    return label


def _source_line(profile_name: str | None, institutions: str) -> str:
    line = f"Qualità della vita su dati {institutions}"
    return f"{line}, profilo {profile_name}" if profile_name else line


def region_cards() -> list[dict]:
    from app import profiles
    from app import quality_life_bes as qb
    from app.data import REGION_GEO_AREA
    from app.design import common
    from app.design.pages import regione

    quality = regione._region_quality()
    if not quality:
        raise RuntimeError("la classifica regionale della qualita' della vita non c'e'")
    payload = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    institutions = _institutions(payload.get("methodology") or {})
    total = len(quality["rows"])
    region_steps = common.map_steps({r["key"]: r["score"] for r in quality["rows"]})
    cards = []
    for key in sorted(REGION_GEO_AREA):
        profile = profiles.region_profile(key)
        if not profile:
            raise RuntimeError(f"regione {key}: nessun profilo")
        rank = quality["ranks"].get(key)
        if rank is None:
            raise RuntimeError(f"regione {key}: non sta nella classifica della qualita' della vita")
        answer = regione._answer(profile)
        cards.append({
            "level": "regione", "level_label": "Regione", "key": key,
            "name": profile["region"], "rank": rank, "total": total,
            "source_line": _source_line(quality.get("profile"), institutions),
            "best": _theme_line(answer.get("strong")),
            "worst": _theme_line(answer.get("weak")),
            "region_key": key, "selected_region": True,
            "region_step": region_steps.get(key), "region_total": total,
        })
    return cards


def _theme_line(item: dict | None) -> tuple[str, str] | None:
    if not item:
        return None
    return item["theme"], f"{item['rank']}ª su {item['total']}"


def province_cards() -> list[dict]:
    from app import province_profile
    from app.design import common, numfmt
    from app.design.pages import regione

    quality = regione._region_quality() or {"rows": ()}
    region_steps = common.map_steps({r["key"]: r["score"] for r in quality["rows"]})
    cards = []
    for key in province_profile.chiavi():
        profile = province_profile.profilo(key)
        if not profile or profile.get("rank") is None:
            raise RuntimeError(f"provincia {key}: nessun profilo o nessuna posizione")
        # Come `provincia.derive`: la prima e l'ultima dimensione per punteggio.
        categories = [c for c in profile.get("categories") or [] if c.get("score") is not None]
        best = categories[0] if categories else None
        worst = categories[-1] if len(categories) > 1 else None
        region_path = profile.get("region_path")
        region_key = region_path.rstrip("/").rsplit("/", 1)[-1] if region_path else None
        profile_name = ((profile.get("profile") or {}).get("name") or "").lower() or None
        cards.append({
            "level": "provincia", "level_label": "Provincia", "key": key,
            "name": profile["name"], "rank": profile["rank"], "total": profile["total"],
            "source_line": _source_line(profile_name, _institutions(profile.get("methodology") or {})),
            "best": (best["name"], f"{numfmt.text(best['score'], 1)} su 100") if best else None,
            "worst": (worst["name"], f"{numfmt.text(worst['score'], 1)} su 100") if worst else None,
            "region_key": region_key, "selected_region": False,
            "region_step": region_steps.get(region_key), "region_total": len(quality["rows"]),
        })
    return cards


# -- il disegno ----------------------------------------------------------------


def _text(x, y, text, size, fill=INK, family=TEXT_FONT, bold=False, anchor=None, spacing=None) -> str:
    attrs = [f'x="{x:g}"', f'y="{y:g}"', f'font-family="{family}, {DISPLAY_FONT if family == TEXT_FONT else TEXT_FONT}, {FALLBACK}"',
             f'font-size="{size:g}"', f'fill="{fill}"']
    if bold:
        attrs.append('font-weight="700"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if spacing:
        attrs.append(f'letter-spacing="{spacing:g}"')
    return f"<text {' '.join(attrs)}>{escape(text)}</text>"


def _map(card: dict) -> tuple[str, str]:
    """La mappa a destra, e la didascalia della sua legenda."""
    from app.design import common, maps

    bx, by, bw, bh = MAP_BOX
    region_key = card["region_key"]
    data = common.region_map(region_key) if region_key else None
    if data:
        viewbox = data["viewbox"]
        borders = data["borders"]
    elif region_key:
        view = maps.zoom(region_key)
        viewbox, borders = view["viewbox"], list(view["borders"].values())
    else:
        raise RuntimeError(f"{card['level']} {card['key']}: nessuna regione da disegnare")
    vx, vy, vw, vh = (float(v) for v in viewbox.split())
    scale = min(bw / vw, bh / vh)
    tx = bx + (bw - vw * scale) / 2 - vx * scale
    ty = by + (bh - vh * scale) / 2 - vy * scale

    def px(width: float) -> str:
        return f"{width / scale:.3f}"

    parts = [f'<clipPath id="box"><rect x="{vx:g}" y="{vy:g}" width="{vw:g}" height="{vh:g}"/></clipPath>',
             f'<g transform="translate({tx:.2f} {ty:.2f}) scale({scale:.5f})"><g clip-path="url(#box)">']
    selected = None
    if data:
        for shape in data["shapes"]:
            if shape["own"]:
                fill = SEQ[shape["step"] - 1] if shape.get("step") else SURFACE_2
                parts.append(f'<path d="{shape["d"]}" fill="{fill}" stroke="{PAPER}" stroke-width="{px(1.4)}" stroke-linejoin="round"/>')
                if not card["selected_region"] and shape["key"] == card["key"]:
                    selected = shape["d"]
            else:
                parts.append(f'<path d="{shape["d"]}" fill="{SURFACE_2}" stroke="{PAPER}" stroke-width="{px(1)}"/>')
        caption = f"Qualità della vita delle {data['total']} province"
        legend = data["legend"]
    else:
        for key, d in maps.REGION_PATHS.items():
            if key == region_key:
                continue
            parts.append(f'<path d="{d}" fill="{SURFACE_2}" stroke="{PAPER}" stroke-width="{px(1)}"/>')
        step = card.get("region_step")
        fill = SEQ[step - 1] if step else SURFACE_2
        parts.append(f'<path d="{maps.REGION_PATHS[region_key]}" fill="{fill}"/>')
        caption = f"Qualità della vita delle {card['region_total']} regioni"
        legend = None
    parts.append(f'<g fill="none" stroke="{CONTROL_BORDER}" stroke-width="{px(1.6)}" stroke-linejoin="round">'
                 + "".join(f'<path d="{d}"/>' for d in borders) + "</g>")
    if card["selected_region"]:
        selected = maps.REGION_PATHS[region_key]
    if selected:
        # Inchiostro con un filo bianco dentro: su una provincia al gradino 6
        # l'inchiostro da solo sparirebbe nel blu, il filo si vede su ogni
        # gradino e sul grigio delle vicine.
        parts.append(f'<path d="{selected}" fill="none" stroke="{INK}" stroke-width="{px(5)}" stroke-linejoin="round"/>')
        parts.append(f'<path d="{selected}" fill="none" stroke="{PAPER}" stroke-width="{px(1.4)}" stroke-linejoin="round"/>')
    parts.append("</g></g>")

    # La legenda: sei gradini, da chiaro a intenso, con gli estremi.
    lx, ly, sw, sh = bx + bw - 6 * 34, by + bh + 30, 34, 12
    parts.append(_text(lx - 14, ly + 11, caption, 17, MUTED, anchor="end"))
    for i, color in enumerate(SEQ):
        parts.append(f'<rect x="{lx + i * sw}" y="{ly}" width="{sw}" height="{sh}" fill="{color}"/>')
    if legend:
        parts.append(_text(lx, ly + sh + 22, legend["min"], 16, MUTED))
        parts.append(_text(lx + 6 * sw, ly + sh + 22, legend["max"], 16, MUTED, anchor="end"))
    else:
        parts.append(_text(lx, ly + sh + 22, "più bassa", 16, MUTED))
        parts.append(_text(lx + 6 * sw, ly + sh + 22, "più alta", 16, MUTED, anchor="end"))
    return "".join(parts), caption


def render_svg(card: dict, measure: Measurer) -> str:
    _check_text(card)
    width = TEXT_RIGHT - LEFT
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
             f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{PAPER}"/>']

    # Il marchio e il livello, col filetto d'accento.
    parts.append(f'<rect x="{LEFT}" y="58" width="44" height="6" fill="{ACCENT}"/>')
    parts.append(_text(LEFT, 100, "Divario Italia", 28, INK, DISPLAY_FONT, bold=True))
    brand_w = measure.width("Divario Italia", 28, DISPLAY_FONT, bold=True)
    parts.append(f'<rect x="{LEFT + brand_w + 16:.1f}" y="78" width="2" height="26" fill="{RULE}"/>')
    parts.append(_text(LEFT + brand_w + 34, 100, card["level_label"], 24, MUTED))
    parts.append(_text(WIDTH - 56, 100, "divarioitalia.it", 20, MUTED, anchor="end"))

    # Il nome: una riga, a costo di rimpicciolire, poi due.
    name = card["name"]
    size = measure.fit(name, width, (80, 76, 72, 68, 64, 60), DISPLAY_FONT, bold=True)
    if size:
        name_lines, y = [name], 196
    else:
        size = 58
        name_lines = measure.wrap(name, width, size, DISPLAY_FONT, bold=True)
        if len(name_lines) > 2:
            raise ValueError(f"{card['key']}: il nome non sta in due righe: {name_lines!r}")
        y = 170
    for i, line in enumerate(name_lines):
        parts.append(_text(LEFT, y + i * (size * 0.98), line, size, INK, DISPLAY_FONT, bold=True))
    bottom = y + (len(name_lines) - 1) * size * 0.98

    # La posizione, in grande.
    rank_text = f"{card['rank']}ª"
    rank_y = bottom + 176
    parts.append(_text(LEFT - 4, rank_y, rank_text, 168, INK, DISPLAY_FONT, bold=True))
    rank_w = measure.width(rank_text, 168, DISPLAY_FONT, bold=True)
    parts.append(_text(LEFT + rank_w + 14, rank_y, f"su {card['total']}", 52, INK, DISPLAY_FONT))

    source_lines = measure.wrap(card["source_line"], width, 22)
    y = rank_y + 40
    for line in source_lines:
        parts.append(_text(LEFT, y, line, 22, MUTED))
        y += 28

    # Dove va meglio e dove va peggio.
    y = max(y + 8, 520)
    parts.append(f'<rect x="{LEFT}" y="{y - 30}" width="{width}" height="1.5" fill="{RULE}"/>')
    for label, item in (("Va meglio in", card["best"]), ("Va peggio in", card["worst"])):
        if not item:
            continue
        theme, detail = item
        label_text = f"{label}:"
        label_w = measure.width(label_text + " ", 24)
        room = width - label_w
        value = f"{theme}, {detail}"
        value_size = measure.fit(value, room, (24, 23, 22, 21, 20, 19, 18), bold=True)
        if value_size is None:
            raise ValueError(f"{card['key']}: {value!r} non sta nella riga")
        parts.append(_text(LEFT, y, label_text, 24, MUTED))
        theme_w = measure.width(f"{theme}, ", value_size, bold=True)
        parts.append(_text(LEFT + label_w, y, f"{theme},", value_size, INK, bold=True))
        parts.append(_text(LEFT + label_w + theme_w, y, detail, value_size, INK))
        y += 42

    figure, _caption = _map(card)
    parts.append(figure)
    parts.append("</svg>")
    return "".join(parts)


def rasterize(svg: str, destination: Path) -> int:
    """SVG in PNG con cairosvg, poi a tavolozza. Restituisce il peso in byte."""
    import cairosvg
    from PIL import Image

    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=WIDTH, output_height=HEIGHT)
    image = Image.open(io.BytesIO(png)).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"{destination.name}: {image.size} invece di {WIDTH}x{HEIGHT}")
    paletted = image.quantize(colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paletted.save(destination, format="PNG", optimize=True)
    return destination.stat().st_size


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forza", action="store_true", help="ridisegna anche le immagini che esistono gia'")
    parser.add_argument("--solo", metavar="CHIAVE", help="disegna solo il territorio con questa chiave")
    parser.add_argument("--svg", action="store_true", help="scrive anche l'SVG accanto al PNG, per rivederlo")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="og-territori-") as workdir:
        prepare_fonts(Path(workdir))
        print(f"font del testo: {resolved_font(TEXT_FONT)}")
        print(f"font dei titoli: {resolved_font(DISPLAY_FONT)}")
        measure = Measurer()

        cards = region_cards() + province_cards()
        if args.solo:
            cards = [c for c in cards if c["key"] == args.solo]
            if not cards:
                print(f"nessuna regione o provincia con chiave {args.solo!r}", file=sys.stderr)
                return 1
        written = skipped = 0
        for card in cards:
            destination = og.DIRECTORY / og.filename(card["level"], card["key"])
            if destination.exists() and not (args.forza or args.solo):
                skipped += 1
                continue
            svg = render_svg(card, measure)
            if args.svg:
                destination.with_suffix(".svg").write_text(svg, encoding="utf-8")
            size = rasterize(svg, destination)
            written += 1
            print(f"scritto {destination.relative_to(ROOT)} ({size / 1024:.0f} KB)")

    total = sum(p.stat().st_size for p in og.DIRECTORY.glob("*.png")) if og.DIRECTORY.exists() else 0
    print(f"{written} scritte, {skipped} gia' presenti, {total / 1024 / 1024:.2f} MB in {og.DIRECTORY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
