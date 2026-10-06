"""Misura larghezza contenitori principali per 7 pagine a 1440, 1920, 375px."""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, UA

OUT = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini")
PAGINE = {
    "home": "/",
    "regioni": "/regioni",
    "blog": "/blog",
    "atlante": "/atlante",
    "articolo": "/blog/reddito-pro-capite-regioni-non-e-il-pil",
    "regione": "/regione/molise",
    "scheda": "/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600",
}
LARGHEZZE = [(375, 812), (1440, 900), (1920, 1080)]

JS_CONTAINER = r"""
() => {
  const main = document.querySelector('main');
  if (!main) return {error: 'no main'};
  const rect = main.getBoundingClientRect();
  const style = getComputedStyle(main);
  const children = [...main.children].filter(c => c.getClientRects().length);
  const childWidths = children.map(c => Math.round(c.getBoundingClientRect().width));
  const maxChild = childWidths.length ? Math.max(...childWidths) : 0;
  return {
    main_width: Math.round(rect.width),
    main_left: Math.round(rect.left),
    main_right: Math.round(rect.right),
    viewport_width: window.innerWidth,
    scroll_width: document.documentElement.scrollWidth,
    padding_left: parseFloat(style.paddingLeft) || 0,
    padding_right: parseFloat(style.paddingRight) || 0,
    margin_left: parseFloat(style.marginLeft) || 0,
    margin_right: parseFloat(style.marginRight) || 0,
    max_child_width: maxChild,
    child_widths: childWidths,
    main_class: main.className,
    main_id: main.id
  };
}
"""

CHIUDI_BANNER = r"""
() => {
  const btn = document.querySelector('.iubenda-cs-accept-btn, .iubenda-cs-reject-btn, #iubenda-cs-banner button');
  if (btn) btn.click();
  document.querySelectorAll('#iubenda-cs-banner, .iubenda-cs-overlay, .iubenda-cs-container').forEach(x => x.remove());
  return true;
}
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    risultati = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for chiave, path in PAGINE.items():
                url = BASE + path
                for w, h in LARGHEZZE:
                    ctx = browser.new_context(
                        viewport={"width": w, "height": h},
                        user_agent=UA,
                        color_scheme="light",
                    )
                    try:
                        page = ctx.new_page()
                        page.goto(url, wait_until="networkidle", timeout=60000)
                        page.wait_for_timeout(1000)
                        page.evaluate(CHIUDI_BANNER)
                        page.wait_for_timeout(300)
                        m = page.evaluate(JS_CONTAINER)
                        m["pagina"] = chiave
                        m["larghezza"] = w
                        m["url"] = url
                        risultati.append(m)
                        print(f"ok {chiave} {w}: main={m.get('main_width')}px viewport={m.get('viewport_width')}px scroll={m.get('scroll_width')}px class={m.get('main_class')}")
                    except Exception as e:
                        print(f"ERRORE {chiave} {w}: {e}", file=sys.stderr)
                        risultati.append({"pagina": chiave, "larghezza": w, "errore": str(e)[:300]})
                    finally:
                        ctx.close()
                time.sleep(1)
        finally:
            browser.close()
    (OUT / "misure_contenitori.json").write_text(json.dumps(risultati, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scritto in {OUT}/misure_contenitori.json")
    # Stampa tabella riassuntiva
    print("\n=== RIASSUNTO LARGHEZZE CONTENITORE MAIN ===")
    for w in [375, 1440, 1920]:
        print(f"\n--- {w}px ---")
        for r in risultati:
            if r.get("larghezza") == w and "main_width" in r:
                print(f"  {r['pagina']:10s} main={r['main_width']:4d}px left={r['main_left']:4d} right={r['main_right']:4d} maxChild={r['max_child_width']:4d} class={r.get('main_class','')}")


if __name__ == "__main__":
    main()