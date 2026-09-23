"""Rende i prototipi della 1.0 con l'ambiente Jinja dell'app e i dati catturati.

    bin/py design/v1/tools/build.py            documenti completi in dist/pagine/
    bin/py design/v1/tools/build.py pagine home,regione   solo alcune pagine
    bin/py design/v1/tools/build.py artifact   un file solo per l'Artifact, in dist/artifact/

I template stanno in `src/` e si rendono con gli stessi filtri del sito (`it_num`,
`analyst_html`, `prose_html`, `figures`, `sparkline`) e con le macro dei template
veri, grazie a un ambiente in sovrapposizione su quello dell'app. Il contesto
viene da `data/<pagina>.context.json`, le frasi nuove da `derive.py`.

Le pagine si collegano fra loro: una rotta campionata porta al prototipo, ogni
altra a divarioitalia.it.
"""

from __future__ import annotations

import base64
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V1 = ROOT / "design" / "v1"
SRC = V1 / "src"
DATA = V1 / "data"
DIST = V1 / "dist"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import derive

SITE = "https://divarioitalia.it"

# Le pagine del prototipo, nell'ordine della barra. La chiave e' il nome del
# file in dist/pagine e del template in src/pages.
PAGES = {
    "indicatore": {"label": "Scheda indicatore", "active": "temi"},
    "home": {"label": "Home", "active": None},
    "regione": {"label": "Regione", "active": "territori"},
    "provincia": {"label": "Provincia", "active": "territori"},
    "articolo": {"label": "Articolo", "active": "storie"},
    "classifica": {"label": "Classifica", "active": "qualita"},
    "qualita-della-vita": {"label": "Qualità della vita", "active": "qualita"},
}

NAV = [
    {"key": "territori", "label": "Territori", "group": [
        {"label": "Le 20 regioni", "path": "/regioni"},
        {"label": "Le 107 province", "path": "/province"},
        {"label": "Confronta i territori", "path": "/confronto"},
    ]},
    {"key": "temi", "label": "Temi", "path": "/temi"},
    {"key": "qualita", "label": "Qualità della vita", "group": [
        {"label": "Dove si vive meglio", "path": "/qualita-della-vita"},
        {"label": "Classifica delle regioni", "path": "/qualita-della-vita/classifica/regioni"},
        {"label": "Classifica delle province", "path": "/qualita-della-vita/classifica/province"},
    ]},
    {"key": "atlante", "label": "Atlante e dati", "group": [
        {"label": "Atlante", "path": "/atlante"},
        {"label": "Divari regionali", "path": "/divari-regionali"},
        {"label": "Catalogo dati", "path": "/catalogo-dati"},
        {"label": "Metodologia", "path": "/metodologia"},
    ]},
    {"key": "storie", "label": "Storie", "path": "/blog"},
    {"key": "quiz", "label": "Quiz", "path": "/quiz"},
]

FOOTER = {
    "trust": ("Divario Italia ripubblica i dati di Istat ed Eurostat per regioni e province, senza correzioni, "
              "e ricalcola ogni sintesi a ogni caricamento. <a href=\"{metodologia}\">Come lavoriamo</a>, "
              "<a href=\"{correzioni}\">correzioni</a> e <a href=\"{chi}\">come citarci</a>."),
    "cols": [
        {"label": "Territori", "links": [{"label": "Regioni", "path": "/regioni"}, {"label": "Province", "path": "/province"},
                                          {"label": "Confronta", "path": "/confronto"}, {"label": "Divari regionali", "path": "/divari-regionali"}]},
        {"label": "Qualità della vita", "links": [{"label": "Dove si vive meglio", "path": "/qualita-della-vita"},
                                                   {"label": "Classifica delle regioni", "path": "/qualita-della-vita/classifica/regioni"},
                                                   {"label": "Classifica delle province", "path": "/qualita-della-vita/classifica/province"}]},
        {"label": "Atlante e dati", "links": [{"label": "Temi", "path": "/temi"}, {"label": "Atlante", "path": "/atlante"},
                                              {"label": "Catalogo dati", "path": "/catalogo-dati"}, {"label": "Metodologia", "path": "/metodologia"}]},
        {"label": "Progetto", "links": [{"label": "Storie", "path": "/blog"}, {"label": "Quiz", "path": "/quiz"},
                                        {"label": "Chi siamo", "path": "/chi-siamo"}, {"label": "Contatti", "path": "/contatti"}]},
    ],
}


def load_context(name: str) -> dict:
    payload = json.loads((DATA / f"{name}.context.json").read_text(encoding="utf-8"))
    return payload


def logo_data_uri() -> str:
    from PIL import Image

    img = Image.open(ROOT / "app" / "static" / "img" / "logo-mark.png").convert("RGBA")
    # Il PNG di oggi ha sul bordo destro un residuo della vecchia scritta: si
    # ritaglia la colonna scura prima di ridurre.
    w, h = img.size
    img = img.crop((0, 0, int(w * 0.9), h))
    img.thumbnail((96, 96))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def make_env(mode: str):
    from jinja2 import ChoiceLoader, FileSystemLoader

    import app.views  # noqa: F401  registra rotte e filtri
    from app import app as flask_app

    env = flask_app.jinja_env.overlay(loader=ChoiceLoader([FileSystemLoader(str(SRC)), flask_app.jinja_loader]))
    routes = {json.loads((DATA / "manifest.json").read_text())["pages"][k]["final_url"]: k
              for k in PAGES if (DATA / f"{k}.context.json").exists()}
    state = {"page": None}

    def href(path: str) -> str:
        if not path:
            return "#"
        if path.startswith(("http://", "https://", "#", "mailto:")):
            return path
        base = path.split("#")[0].split("?")[0]
        if base in routes and "?" not in path:
            key = routes[base]
            return f"#{key}" if mode == "artifact" else f"{key}.html"
        return SITE + path

    def aid(ident: str) -> str:
        """Nell'Artifact tutte le pagine stanno in un file: gli id si prefissano."""
        return f"{state['page']}-{ident}" if mode == "artifact" else ident

    env.globals.update(href=href, aid=aid, nav=NAV, logo_src=logo_data_uri(),
                       paths=json.loads((SRC / "partials" / "italy_paths.json").read_text()))
    return env, flask_app, state, href


def footer(href) -> dict:
    return {
        "trust": FOOTER["trust"].format(metodologia=href("/metodologia"), correzioni="https://github.com/nmaiese/diset-viz/issues/new",
                                        chi=href("/chi-siamo")),
        "cols": FOOTER["cols"], "license": "Creative Commons BY 4.0", "email": "divarioitalia@protonmail.com",
    }


def derive_for(name: str, ctx: dict) -> dict:
    """Le frasi nuove della pagina: `tools/pages/<pagina>.py` se c'e', con una
    funzione `derive(ctx)`, altrimenti la funzione omonima di derive.py."""
    module_path = Path(__file__).parent / "pages" / f"{name.replace('-', '_')}.py"
    if module_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"proto_pages_{name.replace('-', '_')}", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.derive(ctx)
    if name == "indicatore":
        return derive.indicator(ctx)
    fn = getattr(derive, name.replace("-", "_"), None)
    return fn(ctx) if fn else {}


def render_page(env, flask_app, state, href, name: str) -> str:
    payload = load_context(name)
    ctx = payload["context"]
    d = derive_for(name, ctx)
    state["page"] = name
    template = env.get_template(f"pages/{name}.html.j2")
    with flask_app.test_request_context(payload["route"]):
        html = template.render(**ctx, d=d, active=PAGES[name]["active"], footer=footer(href), page_key=name)
    # I link scritti nella prosa arrivano gia' in HTML: si portano al prototipo
    # o al sito vero come quelli dei template.
    return re.sub(r'href="(/[^"]*)"', lambda m: f'href="{href(m.group(1))}"', html)


def proto_bar(mode: str, current: str | None) -> str:
    links = []
    if mode == "artifact":
        links.append(f'<a href="#copertina"{" aria-current=\"page\"" if current == "copertina" else ""}>Copertina</a>')
    for key, spec in PAGES.items():
        if not (SRC / "pages" / f"{key}.html.j2").exists():
            continue
        target = f"#{key}" if mode == "artifact" else f"{key}.html"
        cur = ' aria-current="page"' if key == current else ""
        links.append(f'<a href="{target}"{cur} data-page-link="{key}">{spec["label"]}</a>')
    return (
        '<div class="proto-bar" role="region" aria-label="Prototipo">'
        '<b>Divario Italia 1.0, prototipo</b>'
        f'<nav class="proto-bar__pages" aria-label="Pagine del prototipo">{"".join(links)}</nav>'
        '<div class="proto-bar__theme" role="group" aria-label="Tema">'
        '<button type="button" data-set-theme="" aria-pressed="true">Sistema</button>'
        '<button type="button" data-set-theme="light" aria-pressed="false">Chiaro</button>'
        '<button type="button" data-set-theme="dark" aria-pressed="false">Scuro</button>'
        "</div></div>"
    )


def assets() -> tuple[str, str, str, str]:
    tokens = json.loads((V1 / "tokens" / "tokens.json").read_text(encoding="utf-8"))
    css = (SRC / "css" / "tokens.css").read_text(encoding="utf-8") + "\n" + (SRC / "css" / "components.css").read_text(encoding="utf-8")
    js = (SRC / "js" / "proto.js").read_text(encoding="utf-8")
    return tokens["fonts"]["google_css2"], css, js, tokens["direction"]


def page_css(name: str) -> str:
    """Il CSS di una sola pagina, se la pagina ne ha uno: src/css/pages/<pagina>.css."""
    path = SRC / "css" / "pages" / f"{name}.css"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_pages(only: list[str] | None = None) -> list[Path]:
    env, flask_app, state, href = make_env("pagine")
    fonts, css, js, _ = assets()
    out = DIST / "pagine"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, spec in PAGES.items():
        if only and name not in only:
            continue
        if not (SRC / "pages" / f"{name}.html.j2").exists():
            continue
        body = render_page(env, flask_app, state, href, name)
        head = json.loads((DATA / f"{name}.head.json").read_text(encoding="utf-8"))
        jsonld = "".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in head["jsonld"])
        doc = (
            '<!doctype html>\n<html lang="it">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"<title>{head['title'] or spec['label']}</title>\n"
            '<meta name="robots" content="noindex">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{fonts}">\n'
            f"<script>{THEME_BOOT}</script>\n<style>\n{css}\n{page_css(name)}\n</style>\n{jsonld}\n</head>\n"
            f'<body class="has-proto" data-page="{name}">\n{body}\n{proto_bar("pagine", name)}\n<script>\n{js}\n</script>\n</body>\n</html>\n'
        )
        target = out / f"{name}.html"
        target.write_text(doc, encoding="utf-8")
        written.append(target)
        print(f"{target.relative_to(V1)}: {len(doc.encode()) // 1024} KB")
    return written


# Prima del primo disegno: il tema scelto nel prototipo, se c'e'. Senza scelta
# decide prefers-color-scheme, come sul sito.
THEME_BOOT = ("try{var t=localStorage.getItem('proto-theme');if(t==='light'||t==='dark')"
              "document.documentElement.dataset.theme=t}catch(e){}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pagine"
    if mode == "pagine":
        build_pages(sys.argv[2].split(",") if len(sys.argv) > 2 else None)
    else:
        import build_artifact

        build_artifact.main()
