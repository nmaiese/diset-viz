"""Mette tutti i prototipi in un file solo, per l'Artifact di claude.ai.

    bin/py design/v1/tools/build.py artifact

L'Artifact non naviga fra file HTML e non carica immagini da altri domini:
ogni pagina diventa una sezione dello stesso documento, gli id si prefissano
col nome della pagina, i link fra pagine diventano ancore (#home, #regione),
e le immagini si incorporano come data URI. Un piccolo router mostra la
sezione che l'ancora nomina. In testa c'e' una copertina con il prima e il
dopo di ogni pagina.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

import build
from jinja2 import TemplateError

V1 = build.V1
ROOT = build.ROOT
OUT = V1 / "dist" / "artifact" / "divario-italia-1-0.html"
PRIMA = V1 / "screens" / "prima" / "2026-09-23"
DOPO = V1 / "screens" / "dopo"

ROUTER = r"""
(function () {
  "use strict";
  var pages = Array.prototype.slice.call(document.querySelectorAll("[data-page-root]"));
  var bar = document.querySelectorAll(".proto-bar [data-page-link], .proto-bar a[href='#copertina']");
  function show(hash) {
    var id = (hash || "").replace(/^#/, "") || "copertina";
    var target = document.getElementById(id);
    var page = target ? target.closest("[data-page-root]") : null;
    if (!page) { page = document.getElementById("copertina"); target = null; }
    pages.forEach(function (p) { p.hidden = p !== page; });
    bar.forEach(function (a) {
      if (a.getAttribute("href") === "#" + page.id) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    if (target && target !== page) target.scrollIntoView(); else window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", function () { show(location.hash); });
  show(location.hash);
})();
"""

COVER_CSS = """
.cover { padding-block: var(--space-8) var(--space-16); }
.cover__intro { display: grid; gap: var(--space-4); max-width: 46rem; padding-bottom: var(--space-8); }
.cover__points { display: grid; gap: var(--space-2); padding-left: 1.2em; color: var(--ink); }
.cover__grid { display: grid; gap: var(--space-12); margin-top: var(--space-8); }
.cover__page { display: grid; gap: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--rule-strong); }
.cover__page h2 { font-size: var(--fs-section); line-height: var(--lh-section); }
.cover__pair { display: grid; gap: var(--space-6); }
@media (min-width: 960px) { .cover__pair { grid-template-columns: 1fr 1fr; } }
.cover__pair figure { display: grid; gap: var(--space-2); }
.cover__pair img { width: 100%; border: 1px solid var(--rule); }
.cover__pair figcaption { font-size: var(--fs-label); font-weight: 600; color: var(--text-2); }
.cover__open { margin-top: var(--space-12); max-width: 46rem; }
"""


def image_data_uri(path: Path, width: int = 900, quality: int = 70) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def inline_images(html: str) -> str:
    """Le immagini del sito vero diventano data URI: l'Artifact non le caricherebbe."""

    def repl(m):
        rel = m.group(2)
        local = ROOT / "app" / rel.lstrip("/")
        if local.exists() and local.suffix.lower() == ".svg":
            return f'{m.group(1)}"data:image/svg+xml;base64,{base64.b64encode(local.read_bytes()).decode()}"'
        if not local.exists() or local.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            return m.group(0)
        return f'{m.group(1)}"{image_data_uri(local, 1200, 72)}"'

    return re.sub(r'(src=)"https://divarioitalia\.it(/static/[^"]+)"', repl, html)


def cover(pages: list[str]) -> str:
    items = []
    variants = [n for n in pages if build.PAGES[n].get("variant")]
    for name in [n for n in pages if not build.PAGES[n].get("variant")]:
        label = build.PAGES[name]["label"]
        before = PRIMA / f"{name}-1440-chiaro-fold.webp"
        after = DOPO / f"{name}-1440-chiaro-fold.webp"
        pair = []
        if before.exists():
            pair.append(f'<figure><img src="{image_data_uri(before)}" alt="{label}, il sito di oggi a 1440 pixel" loading="lazy"><figcaption>Oggi</figcaption></figure>')
        if after.exists():
            pair.append(f'<figure><img src="{image_data_uri(after)}" alt="{label}, il prototipo 1.0 a 1440 pixel" loading="lazy"><figcaption>Versione 1.0</figcaption></figure>')
        items.append(
            f'<article class="cover__page"><h2><a href="#{name}">{label}</a></h2>'
            f'<div class="cover__pair">{"".join(pair)}</div>'
            f'<p><a class="linkarrow" href="#{name}">Apri il prototipo della pagina</a></p></article>'
        )
    return f"""
<section id="copertina" data-page-root data-page="copertina">
<main class="wrap cover">
  <div class="cover__intro">
    <p class="eyebrow">Prototipo, 23 settembre 2026</p>
    <h1 class="h-display">Divario Italia 1.0</h1>
    <p class="lede">Le pagine chiave del sito nella direzione Cronaca, con i dati veri catturati dall'app. Ogni cifra viene dal contesto con cui la pagina di oggi è resa, o si calcola con le funzioni del sito.</p>
    <ul class="cover__points">
      <li>Una griglia sola da 1200 pixel, dalla testata al piede, e tutto allineato a sinistra sotto il marchio.</li>
      <li>Una famiglia sola, Source Sans 3, e dieci ruoli tipografici al posto di 58 taglie.</li>
      <li>Un accento solo, arancio bruciato, per ciò che si clicca e per l'elemento in evidenza. I dati sono blu, e nessun colore dice meglio o peggio.</li>
      <li>Ogni pagina apre con la risposta, il numero e un grafico. Il metodo e la citazione stanno in fondo, fuori dal racconto.</li>
      <li>Tema scuro compreso: la barra in basso lo cambia, oppure segue il sistema.</li>
    </ul>
  </div>
  <div class="cover__grid">{"".join(items)}</div>
  <div class="cover__open">
    <h2 class="h-section">Gli stati difficili</h2>
    <p class="lede">Gli stessi template con i contesti che li mettono alla prova.</p>
    <ul class="cover__points">{"".join(f'<li><a href="#{v}">{build.PAGES[v]["label"]}</a></li>' for v in variants)}</ul>
  </div>
  <div class="cover__open prose">
    <h2>Da decidere guardando i prototipi</h2>
    <p>Il numero chiave della regione: oggi è la posizione media sugli indicatori, il prototipo mostra la posizione nella qualità della vita, come per le province. Cambia il titolo di venti pagine.</p>
    <p>Gli spazi pubblicitari sono segnaposto. Perché restino dove sono disegnati, gli annunci automatici di AdSense vanno spenti dalla console.</p>
  </div>
</main>
</section>"""


def main() -> None:
    env, flask_app, state, href = build.make_env("artifact")
    fonts, css, js, _ = build.assets()
    pages = [n for n in build.PAGES if (build.SRC / "pages" / f"{build.template_of(n)}.html.j2").exists()]
    sections, page_css = [], []
    rendered = []
    for name in pages:
        try:
            body = build.render_page(env, flask_app, state, href, name)
        except (TemplateError, KeyError, TypeError, ValueError, AttributeError, FileNotFoundError) as exc:
            # una pagina in lavorazione non ferma le altre
            print(f"salto {name}: {exc}")
            continue
        rendered.append(name)
        sections.append(f'<section id="{name}" data-page-root data-page="{name}" hidden>\n{inline_images(body)}\n</section>')
        css_name = build.template_of(name)
        if css_name == name:
            page_css.append(build.page_css(css_name))
    doc = (
        "<title>Divario Italia 1.0</title>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{fonts}">\n'
        f"<style>\n{css}\n{''.join(page_css)}\n{COVER_CSS}\nbody {{ padding-bottom: 96px; }}\n</style>\n"
        f"<script>{build.THEME_BOOT}</script>\n"
        f"{cover(rendered)}\n{''.join(sections)}\n{build.proto_bar('artifact', 'copertina')}\n"
        f"<script>\n{js}\n{ROUTER}\n</script>\n"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"{OUT.relative_to(V1)}: {len(doc.encode()) // 1024} KB, {len(rendered)} pagine")


if __name__ == "__main__":
    main()
