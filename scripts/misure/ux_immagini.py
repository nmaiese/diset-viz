"""UX immagini prima/dopo: 7 pagine, desktop 1440 e mobile 375, tema chiaro.
 * Stato 'prima': pagina viva. Stato 'dopo': con layout.css + proposta.css iniettati.
 * Output: /mnt/c/Users/Nilo/orca/direzione/review/ux-immagini/<pagina>_<desktop|mobile>_<prima|dopo>.png
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, UA

# Output directory
OUT = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini")

# 7 pagine da testare
PAGINE = {
    "home": "/",
    "regioni": "/regioni",
    "blog": "/blog",
    "atlante": "/atlante",
    "articolo": "/blog/reddito-pro-capite-regioni-non-e-il-pil",
    "regione": "/regione/molise",
    "scheda": "/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600",
}

# Desktop 1440, 1920 e mobile 375, tema chiaro
LARGHEZZE = {
    "desktop1440": (1440, 900),
    "desktop1920": (1920, 1080),
    "mobile": (375, 812),
}

# CSS da iniettare per stato "dopo"
LAYOUT_CSS = (Path(__file__).parent.parent.parent / "layout.css").read_text(encoding="utf-8")
PROPOSTA_CSS = (Path(__file__).parent.parent.parent / "proposta.css").read_text(encoding="utf-8")
TRASFORMA_JS = (Path(__file__).parent.parent.parent / "trasforma.js").read_text(encoding="utf-8")

CHIUDI_BANNER = r"""
() => {
  const btn = document.querySelector('.iubenda-cs-accept-btn, .iubenda-cs-reject-btn, #iubenda-cs-banner button');
  if (btn) btn.click();
  document.querySelectorAll('#iubenda-cs-banner, .iubenda-cs-overlay, .iubenda-cs-container').forEach(x => x.remove());
  return true;
}
"""

# JS per misure chiave prima/dopo
JS_MISURE_CHIAVE = r"""
() => {
  const main = document.querySelector('main');
  const de = document.documentElement;
  if (!main) return {error: 'no main'};
  const rect = main.getBoundingClientRect();
  const style = getComputedStyle(main);
  const children = [...main.children].filter(c => c.getClientRects().length);
  const childWidths = children.map(c => Math.round(c.getBoundingClientRect().width));
  const maxChild = childWidths.length ? Math.max(...childWidths) : 0;

  // Caratteri per riga (prosa)
  const proseEls = main.querySelectorAll('.prose p, .indicator-article p, .art-body p, .answer p, .regione-intro, .regione-stacca__lead');
  let cpl = [];
  for (const p of proseEls) {
    const t = p.textContent.replace(/\s+/g, ' ').trim();
    if (t.length <= 40 || !p.getClientRects().length) continue;
    try {
      const tn = [];
      const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())) if (n.nodeValue.trim()) tn.push(n);
      if (!tn.length) continue;
      const first = tn[0];
      const r = document.createRange();
      r.setStart(first, 0); r.setEnd(first, 1);
      const top0 = r.getClientRects()[0]?.top;
      if (top0 === undefined) continue;
      let count = 0, done = false;
      for (const node of tn) {
        const len = node.nodeValue.length;
        for (let i = 0; i < len; i++) {
          r.setStart(node, i); r.setEnd(node, i + 1);
          const rc = r.getClientRects()[0];
          if (!rc || rc.width === 0) { count++; continue; }
          if (Math.abs(rc.top - top0) > rc.height * 0.6) { done = true; break; }
          count++;
        }
        if (done) break;
      }
      if (count > 0) cpl.push(count);
    } catch (e) {}
  }
  const median = a => a.length ? a.sort((x,y)=>x-y)[a.length>>1] : null;
  const cplMed = median(cpl);

  // Altezza pagina in schermi
  const altezzaPx = Math.max(de.scrollHeight, document.body.scrollHeight);
  const altezzaSchermi = +(altezzaPx / window.innerHeight).toFixed(2);

  // Scroll orizzontale
  const scrollOrizzontale = de.scrollWidth > window.innerWidth;

  // Blocchi principali per schermo (figli diretti di main visibili)
  const blocchiPerSchermo = children.length / Math.max(1, altezzaSchermi);

  return {
    main_width: Math.round(rect.width),
    main_left: Math.round(rect.left),
    max_child_width: maxChild,
    viewport_width: window.innerWidth,
    scroll_width: de.scrollWidth,
    cpl_mediana: cplMed,
    cpl_campioni: cpl.length,
    altezza_px: altezzaPx,
    altezza_schermi: altezzaSchermi,
    scroll_orizzontale: scrollOrizzontale,
    blocchi_principali: children.length,
    blocchi_per_schermo: +blocchiPerSchermo.toFixed(2),
    main_class: main.className
  };
}
"""


def prepara(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)
    page.evaluate(CHIUDI_BANNER)
    page.wait_for_timeout(300)


def scatta(page, nome):
    page.screenshot(path=str(OUT / nome), full_page=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    risultati = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for chiave, path in PAGINE.items():
                url = BASE + path
                for device, (w, h) in LARGHEZZE.items():
                    ctx = browser.new_context(
                        viewport={"width": w, "height": h},
                        user_agent=UA,
                        color_scheme="light",
                    )
                    try:
                        page = ctx.new_page()
                        prepara(page, url)

                        # STATO PRIMA
                        misure_prima = page.evaluate(JS_MISURE_CHIAVE)
                        scatta(page, f"{chiave}_{device}_prima.png")
                        print(f"ok prima {chiave} {device}: main={misure_prima.get('main_width')}px cpl={misure_prima.get('cpl_mediana')} scrollX={misure_prima.get('scroll_orizzontale')}")

                        # STATO DOPO: inietta layout.css + proposta.css + esegui trasforma.js
                        page.add_style_tag(content=LAYOUT_CSS)
                        page.add_style_tag(content=PROPOSTA_CSS)
                        page.evaluate(TRASFORMA_JS)
                        page.wait_for_timeout(500)

                        misure_dopo = page.evaluate(JS_MISURE_CHIAVE)
                        scatta(page, f"{chiave}_{device}_dopo.png")
                        print(f"ok dopo  {chiave} {device}: main={misure_dopo.get('main_width')}px cpl={misure_dopo.get('cpl_mediana')} scrollX={misure_dopo.get('scroll_orizzontale')}")

                        risultati.append({
                            "pagina": chiave,
                            "device": device,
                            "larghezza": w,
                            "prima": misure_prima,
                            "dopo": misure_dopo
                        })

                    except Exception as e:
                        print(f"ERRORE {chiave} {device}: {e}", file=sys.stderr)
                        risultati.append({"pagina": chiave, "device": device, "larghezza": w, "errore": str(e)[:300]})
                    finally:
                        ctx.close()
                time.sleep(1)
        finally:
            browser.close()

    # Salva misure per il rapporto
    (OUT / "misure_immagini.json").write_text(json.dumps(risultati, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nScritto in {OUT}/misure_immagini.json")


if __name__ == "__main__":
    main()