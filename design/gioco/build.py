"""Genera il prototipo statico del sotto-marchio del gioco: design/gioco/index.html.

    bin/py design/gioco/build.py

Il prototipo si apre da file:// e usa i fogli veri: i token e la base della 1.0
(app/static/css/ds/system.css, fonts.css) e i fogli del gioco
(frontend/src/game/game.css, che raccoglie i quattro). Le icone arrivano da
app/static/img/gioco/, in linea perche' prendano currentColor e i --game-*.

Nessuna cifra e' scritta a mano: gli indizi della partita a livello Provincia
sono gli ultimi valori di Assoluti_Provincia.csv, con la posizione fra le
province, e i riscontri dei tentativi confrontano i valori veri. Cio' che
arriva dall'API del gioco (numero della sfida, orario, statistiche personali)
resta un segnaposto visibile.
"""

from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "app" / "static" / "data"
ICONS = ROOT / "app" / "static" / "img" / "gioco"

# Il primo dei nomi proposti, come segnaposto: la scelta e' di Nello.
SUB_BRAND = "Divario in gioco"
MYSTERY = "matera"
GUESSES = ("potenza", "bari")  # due tentativi sbagliati, poi tocca a chi gioca
CLUES = ("04BEC001P", "10AMB016", "03LAV001-N22", "09PAE008", "01SAL001", "10AMB017")
ATTEMPTS = 6


def icon(name: str, size: int, extra: str = "") -> str:
    svg = (ICONS / f"{name}.svg").read_text(encoding="utf-8").strip()
    return svg.replace('width="24" height="24"', f'width="{size}" height="{size}" class="gi gi-{size}{extra}"', 1)


def fmt(value: float, unit: str) -> str:
    decimals = 0 if abs(value) >= 1000 or unit == "euro" else 1
    text = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if unit == "%":
        return f"{text}%"
    if unit == "euro":
        return f"{text} euro"
    return text


def latest_values() -> tuple[dict, dict]:
    """{indicatore: {provincia: valore}} all'ultimo anno, e il nome e l'unita'."""
    rows: dict[str, dict[str, tuple[int, float]]] = {}
    meta: dict[str, tuple[str, str, str, int]] = {}
    with (DATA / "Assoluti_Provincia.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["idIndicatore"] not in CLUES or not r["Dato"]:
                continue
            year, value = int(r["Anno"]), float(r["Dato"].replace(",", "."))
            cur = rows.setdefault(r["idIndicatore"], {}).get(r["Territorio"])
            if cur is None or year > cur[0]:
                rows[r["idIndicatore"]][r["Territorio"]] = (year, value)
            meta[r["idIndicatore"]] = (r["Indicatore"], r["UDM"], r["Tema"], year)
    values = {}
    for ind, per in rows.items():
        last = max(y for y, _ in per.values())
        values[ind] = {name: v for name, (y, v) in per.items() if y == last}
        meta[ind] = (*meta[ind][:3], last)
    return values, meta


def main() -> None:
    codes = {r["province_key"]: r for r in csv.DictReader((DATA / "province_codes.csv").open(encoding="utf-8"), delimiter=";")}
    paths = json.loads((ROOT / "app" / "design" / "province_paths.json").read_text(encoding="utf-8"))
    regions = json.loads((ROOT / "app" / "design" / "italy_paths.json").read_text(encoding="utf-8"))
    values, meta = latest_values()
    name = {k: codes[k]["name"] for k in codes}
    mystery = name[MYSTERY]

    def rank(ind: str, prov: str) -> tuple[int, int]:
        ordered = sorted(values[ind].values(), reverse=True)
        return ordered.index(values[ind][prov]) + 1, len(ordered)

    revealed = CLUES[: len(GUESSES) + 1]

    # --- indizi
    clue_rows = []
    for i, ind in enumerate(CLUES):
        if ind in revealed:
            label, unit, theme, _ = meta[ind]
            latest = ind == revealed[-1]
            clue_rows.append(
                f'<tr class="{"latest" if latest else ""}"><td class="n">{i + 1}</td>'
                f"<td><strong>{html.escape(theme)}</strong> · {html.escape(label)}</td>"
                f'<td class="v">{fmt(values[ind][mystery], unit)}</td></tr>'
            )
        else:
            clue_rows.append(f'<tr class="locked"><td class="n">{i + 1}</td><td class="theme">Indizio da svelare</td><td class="v"><span class="visually-hidden">nessun valore</span></td></tr>')
    last = revealed[-1]
    label, unit, theme, year = meta[last]
    pos, count = rank(last, mystery)
    clue_desc = (
        f'<div class="qz-clue-desc"><p><strong>Indizio {len(revealed)}</strong> · {html.escape(label)}. '
        f'<span class="qz-clue-rank">{pos}ª su {count} province, dal valore più alto</span></p>'
        f'<div class="quiz-source"><span class="quiz-source-year">{year}</span>'
        f'<span class="quiz-source-link">Istat, BES dei territori</span></div></div>'
    )

    # --- tentativi sbagliati, con il riscontro sugli indizi gia' svelati
    history = []
    for n, guess in enumerate(GUESSES, 1):
        items = []
        for ind in CLUES[:n]:
            label, unit, _, _ = meta[ind]
            g, m = values[ind][name[guess]], values[ind][mystery]
            gpos, count = rank(ind, name[guess])
            mpos, _ = rank(ind, mystery)
            up = m > g
            direction = "più alto" if up else "più basso"
            items.append(
                f'<li><span class="guess-symbol" aria-hidden="true">{"↑" if up else "↓"}</span>'
                f'<span class="guess-feedback-body"><strong>{html.escape(label)}</strong>'
                f'<span class="guess-feedback-detail">{fmt(g, unit)} · {gpos}ª su {count} '
                f'(la misteriosa ha un valore {direction}, {mpos}ª)</span></span></li>'
            )
        history.append(
            f'<div class="guess-row is-wrong"><p class="gi-verdict gi-verdict--wrong">'
            f'{icon("stato-sbagliato", 24)}<span>Tentativo {n}, sbagliato</span></p>'
            f"<strong>{html.escape(name[guess])}</strong>"
            f'<ul class="guess-feedback">{"".join(items)}</ul></div>'
        )

    # --- mappa: le province, i confini regionali sopra
    prov_svg = []
    for key, d in paths.items():
        cls = "rmap-region is-guessed-wrong" if key in GUESSES else "rmap-region is-clickable"
        title = html.escape(name.get(key, key))
        extra = ', tentativo sbagliato' if key in GUESSES else ''
        prov_svg.append(f'<path class="{cls}" d="{d}" tabindex="-1"><title>{title}{extra}</title></path>')
    reg_svg = "".join(f'<path class="gi-region-edge" d="{d}"/>' for d in regions.values())
    map_svg = (
        '<svg class="regions-map" viewBox="0 0 560 660" role="img" aria-label="Mappa delle province: in tratteggio i tentativi sbagliati">'
        '<defs><pattern id="gi-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="6" height="6" style="fill: var(--game-wrong-wash)"/>'
        '<path d="M0 0v6" style="stroke: var(--game-wrong); stroke-width: 2.4"/></pattern></defs>'
        f'<g>{"".join(prov_svg)}</g><g aria-hidden="true">{reg_svg}</g></svg>'
    )

    # --- traguardi, dal catalogo dell'app
    src = (ROOT / "app" / "achievements.py").read_text(encoding="utf-8")
    achv = re.findall(r'\{"id": "([a-z0-9_]+)", "icon": "[^"]*", "title": "([^"]+)",\s*"description": "([^"]+)"', src)
    assert len(achv) == 9, achv
    unlocked = {"first_correct", "compare_10", "daily_solver"}
    achv_html = "".join(
        f'<div class="achv-card{"" if a in unlocked else " is-locked"}">'
        f'<span class="achv-card-ic">{icon("traguardi/" + a, 24)}</span>'
        f'<div><div class="achv-card-t">{html.escape(t)}</div><div class="achv-card-d">{html.escape(d)}</div>'
        f'<div class="gi-achv-state">{"Sbloccato" if a in unlocked else "Da sbloccare"}</div></div></div>'
        for a, t, d in achv
    )

    attempts = "".join(f'<span class="seg{" is-wrong" if i < len(GUESSES) else ""}"></span>' for i in range(ATTEMPTS))
    page = (HERE / "index.template.html").read_text(encoding="utf-8")
    for k, v in {
        "SUB_BRAND": html.escape(SUB_BRAND),
        "ICON_GUESS_34": icon("indovina", 34),
        "ICON_COMPARE_34": icon("maggiore", 34),
        "ICON_ORDER_34": icon("ordina", 34),
        "ICON_PROV_24": icon("provincia", 24),
        "ICON_GUESS_24": icon("indovina", 24),
        "ICON_PROV_34": icon("provincia", 34),
        "ICON_RIGHT": icon("stato-giusto", 24),
        "ICON_WRONG": icon("stato-sbagliato", 24),
        "ACHV": achv_html,
        "ACHV_COUNT": f"{len(unlocked)}/{len(achv)}",
        "ATTEMPTS": attempts,
        "ATTEMPT_N": str(len(GUESSES) + 1),
        "ATTEMPT_TOT": str(ATTEMPTS),
        "CLUE_ROWS": "".join(clue_rows),
        "CLUE_DESC": clue_desc,
        "HISTORY": "".join(history),
        "MAP": map_svg,
        "N_PROV": str(len(paths)),
    }.items():
        page = page.replace("{{" + k + "}}", v)
    assert "{{" not in page, re.findall(r"\{\{\w+\}\}", page)
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"design/gioco/index.html: {len(page) // 1024} KB")


if __name__ == "__main__":
    main()
