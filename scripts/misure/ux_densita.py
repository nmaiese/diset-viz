"""Measure density metrics for home, regioni, blog, atlante at 1440px and 1920px."""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, UA

OUT = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini")

PAGINE_DENSITA = {
    "home": "/",
    "regioni": "/regioni",
    "blog": "/blog",
    "atlante": "/atlante",
}

LARGHEZZE = {
    "desktop1440": (1440, 900),
    "desktop1920": (1920, 1080),
}

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

JS_DENSITA = r"""
() => {
  const main = document.querySelector('main');
  const de = document.documentElement;
  if (!main) return {error: 'no main'};
  
  const viewportHeight = window.innerHeight;
  const pageHeight = Math.max(de.scrollHeight, document.body.scrollHeight);
  const altezzaSchermi = +(pageHeight / viewportHeight).toFixed(2);
  
  // Figli diretti di main visibili (blocchi principali)
  const children = [...main.children].filter(c => c.getClientRects().length);
  const blocchiPrincipali = children.length;
  
  // Parole visibili e link unici nel primo schermo e ogni 3 schermi
  const parolePerSchermo = [];
  const linksPerSchermo = [];
  
  for (let schermo = 0; schermo < altezzaSchermi; schermo += 3) {
    const top = schermo * viewportHeight;
    const bottom = Math.min(top + viewportHeight, pageHeight);
    
    let parole = 0;
    const linkUrls = new Set();
    
    // Trova tutti gli elementi visibili in questo schermo
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
      if (!el.getClientRects().length) continue;
      const rect = el.getBoundingClientRect();
      if (rect.bottom < top || rect.top > bottom) continue;
      if (rect.width === 0 || rect.height === 0) continue;
      
      // Solo elementi foglia con testo diretto
      let hasDirectText = false;
      for (const child of el.childNodes) {
        if (child.nodeType === Node.TEXT_NODE && child.nodeValue.trim()) {
          hasDirectText = true;
          break;
        }
      }
      if (!hasDirectText) continue;
      
      // Parole
      const text = el.textContent.trim();
      if (text) {
        parole += text.split(/\s+/).filter(Boolean).length;
      }
      
      // Link in questo elemento
      const links = el.querySelectorAll('a');
      for (const link of links) {
        if (link.href && link.getClientRects().length) {
          const linkRect = link.getBoundingClientRect();
          if (linkRect.bottom >= top && linkRect.top <= bottom && linkRect.width > 0 && linkRect.height > 0) {
            linkUrls.add(link.href);
          }
        }
      }
    }
    
    parolePerSchermo.push({schermo: schermo + 1, parole: parole, links: linkUrls.size});
  }
  
  // Primo schermo (schermo 0)
  const primoSchermo = parolePerSchermo[0] || {schermo: 1, parole: 0, links: 0};
  
  // Link medi per schermo
  const totLinks = parolePerSchermo.reduce((a, b) => a + b.links, 0);
  const linksPerSchermoMedio = parolePerSchermo.length ? +(totLinks / parolePerSchermo.length).toFixed(1) : 0;
  
  return {
    altezza_schermi: altezzaSchermi,
    blocchi_principali: blocchiPrincipali,
    primo_schermo_parole: primoSchermo.parole,
    primo_schermo_links: primoSchermo.links,
    parole_per_schermo: parolePerSchermo,
    links_per_schermo_medio: linksPerSchermoMedio,
  };
}
"""

def prepara(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)
    page.evaluate(CHIUDI_BANNER)
    page.wait_for_timeout(300)

def main():
    risultati = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for chiave, path in PAGINE_DENSITA.items():
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
                        misure_prima = page.evaluate(JS_DENSITA)
                        print(f"prima {chiave} {device}: schermi={misure_prima.get('altezza_schermi')} blocchi={misure_prima.get('blocchi_principali')} parole1={misure_prima.get('primo_schermo_parole')} links1={misure_prima.get('primo_schermo_links')} links/schermo={misure_prima.get('links_per_schermo_medio')}")
                        
                        # STATO DOPO
                        page.add_style_tag(content=LAYOUT_CSS)
                        page.add_style_tag(content=PROPOSTA_CSS)
                        page.evaluate(TRASFORMA_JS)
                        page.wait_for_timeout(500)
                        
                        misure_dopo = page.evaluate(JS_DENSITA)
                        print(f"dopo  {chiave} {device}: schermi={misure_dopo.get('altezza_schermi')} blocchi={misure_dopo.get('blocchi_principali')} parole1={misure_dopo.get('primo_schermo_parole')} links1={misure_dopo.get('primo_schermo_links')} links/schermo={misure_dopo.get('links_per_schermo_medio')}")
                        
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
    
    # Salva
    (OUT / "densita.json").write_text(json.dumps(risultati, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nScritto in {OUT}/densita.json")
    
    # Stampa tabella riassuntiva
    print("\n=== TABELLA DENSITÀ ===")
    print(f"{'Pagina':<12} {'Device':<14} {'Stato':<6} {'Schermi':<8} {'Blocchi':<8} {'Parole 1°':<10} {'Link 1°':<8} {'Links/schermo':<12}")
    for r in risultati:
        if "errore" in r:
            continue
        for stato in ["prima", "dopo"]:
            m = r[stato]
            print(f"{r['pagina']:<12} {r['device']:<14} {stato:<6} {m.get('altezza_schermi', 'n/d'):<8} {m.get('blocchi_principali', 'n/d'):<8} {m.get('primo_schermo_parole', 'n/d'):<10} {m.get('primo_schermo_links', 'n/d'):<8} {m.get('links_per_schermo_medio', 'n/d'):<12}")

if __name__ == "__main__":
    main()