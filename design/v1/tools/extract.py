"""Cattura il contesto vero dei template per le pagine di esempio della 1.0.

Ogni pagina si chiede all'app col test client Flask, e il segnale
`template_rendered` consegna il contesto con cui il template vero e' stato reso.
Da li' escono tre file per pagina in `design/v1/data/`:

- `<pagina>.context.json`: il contesto, serializzato;
- `<pagina>.head.json`: title, description, canonical, robots, JSON-LD e H1
  della pagina di oggi, cioe' il contratto SEO da portarsi dietro;
- `<pagina>.md`: il gemello Markdown, dove esiste.

Nessuna cifra dei prototipi si scrive a mano: arriva da qui o da `derive.py`.

    bin/py design/v1/tools/extract.py
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V1 = ROOT / "design" / "v1"
DATA = V1 / "data"
sys.path.insert(0, str(ROOT))

# Le pagine di esempio e le varianti che i prototipi devono reggere.
SAMPLES = {
    "home": "/",
    "indicatore": "/indicatore/pil-pro-capite/ter-901",
    "indicatore-senza-prosa": "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001",
    "indicatore-due-livelli": "/indicatore/tasso-di-infortuni-sul-lavoro-mortali-e-con-inabilita-permanente/bes-03LAV007",
    "indicatore-province": "/indicatore/retribuzione-media-annua-dei-lavoratori-dipendenti/bes-04BEC002P",
    "regione": "/regione/puglia",
    "provincia": "/provincia/lecce",
    "articolo": "/blog/infortuni-lavoro-province",
    "articolo-giugno": "/blog/italia-che-invecchia-indice-vecchiaia-2026",
    "classifica": "/qualita-della-vita/classifica/regioni",
    "classifica-province": "/qualita-della-vita/classifica/province",
    "qualita-della-vita": "/qualita-della-vita",
}

# Chiavi del contesto che non servono ai prototipi: configurazione, tracciamento,
# oggetti della richiesta.
DROP = re.compile(
    r"^(ADSENSE_|GA_|GOOGLE_|BING_|SUPABASE_|STAGING|GTM|IUBENDA|FUNDING|config$|request$|session$|g$|"
    r"url_for$|get_flashed_messages$|asset_url$|nav$|self$|range$|loop$)"
)


def _default(obj):
    """Converte in JSON cio' che json non sa scrivere."""
    if isinstance(obj, (dt.date, dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if hasattr(obj, "__html__"):
        return str(obj)
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    if hasattr(obj, "__dict__") and not callable(obj):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return None


def _clean(context: dict) -> dict:
    out = {}
    for key, value in context.items():
        if DROP.match(key) or callable(value) or key.startswith("_"):
            continue
        if type(value).__name__ == "module":
            continue
        out[key] = value
    return out


def _head(html: str, headers) -> dict:
    """Il contratto SEO della pagina di oggi."""

    def first(pattern):
        m = re.search(pattern, html, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else None

    jsonld = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.DOTALL):
        try:
            jsonld.append(json.loads(block))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON-LD non valido: {exc}") from exc
    h1 = first(r"<h1[^>]*>(.*?)</h1>")
    return {
        "title": first(r"<title>(.*?)</title>"),
        "description": first(r'<meta name="description" content="([^"]*)"'),
        "canonical": first(r'<link rel="canonical" href="([^"]*)"'),
        "robots": first(r'<meta name="robots" content="([^"]*)"'),
        "x_robots_tag": headers.get("X-Robots-Tag"),
        "h1": re.sub(r"<[^>]+>", "", h1).strip() if h1 else None,
        "jsonld": jsonld,
        "html_bytes": len(html.encode()),
    }


def main() -> None:
    from flask import template_rendered

    import app.views  # noqa: F401  registra rotte e filtri
    from app import app as flask_app  # non `import app`: app.views ribalta il nome
    from app import nav
    from app.cache import cache

    DATA.mkdir(parents=True, exist_ok=True)
    captured: list[tuple[str, dict]] = []

    def on_render(sender, template, context, **extra):
        captured.append((template.name, dict(context)))

    # weak=False: blinker tiene riferimenti deboli, e un ricevitore locale
    # sparirebbe lasciando la cattura vuota.
    template_rendered.connect(on_render, flask_app, weak=False)
    client = flask_app.test_client()
    manifest = {
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip(),
        "pages": {},
    }

    for name, route in SAMPLES.items():
        # La home ha @cache.cached: senza svuotare la cache la seconda richiesta
        # non renderizza e il segnale non parte.
        cache.clear()
        captured.clear()
        resp = client.get(route, follow_redirects=True)
        if resp.status_code != 200:
            raise RuntimeError(f"{name}: {route} risponde {resp.status_code}")
        if not captured:
            raise RuntimeError(f"{name}: nessun template catturato per {route}")
        html = resp.get_data(as_text=True)
        # Il template della pagina e' il primo reso, gli altri sono inclusioni.
        template, context = captured[0]
        payload = {"template": template, "route": route, "context": _clean(context)}
        (DATA / f"{name}.context.json").write_text(
            json.dumps(payload, default=_default, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        (DATA / f"{name}.head.json").write_text(
            json.dumps(_head(html, resp.headers), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        cache.clear()
        md = client.get(route, headers={"Accept": "text/markdown"}, follow_redirects=True)
        has_md = md.status_code == 200 and md.mimetype == "text/markdown"
        if has_md:
            (DATA / f"{name}.md").write_text(md.get_data(as_text=True), encoding="utf-8")
        manifest["pages"][name] = {
            "route": route,
            "final_url": resp.request.path,
            "template": template,
            "markdown": has_md,
            "html_bytes": len(html.encode()),
        }
        print(f"{name}: {template}, {len(html.encode())} B, markdown {'si' if has_md else 'no'}")

    chrome = {
        "primary": nav.PRIMARY,
        "footer_groups": nav.FOOTER_GROUPS,
        "drawer_other": nav.drawer_other() if callable(getattr(nav, "drawer_other", None)) else None,
        "short": getattr(nav, "SHORT", None),
    }
    (DATA / "chrome.json").write_text(json.dumps(chrome, default=_default, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
