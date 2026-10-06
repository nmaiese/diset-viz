"""Verify footer and header font-size before/after."""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, UA

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

JS_FONT = r"""
() => {
  const results = {};
  
  // Footer h2
  const footerH2 = document.querySelectorAll('footer h2, .ftr h2, .ftr__cols h2');
  results.footer_h2 = [];
  footerH2.forEach(el => {
    const cs = getComputedStyle(el);
    results.footer_h2.push({fontSize: cs.fontSize, tag: el.tagName, class: el.className});
  });
  
  // Footer links
  const footerLinks = document.querySelectorAll('footer a, .ftr a, .ftr__cols a, .ftr__legal a');
  results.footer_links = [];
  footerLinks.forEach(el => {
    const cs = getComputedStyle(el);
    results.footer_links.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,30)});
  });
  
  // Footer p
  const footerP = document.querySelectorAll('footer p, .ftr p, .ftr__trust');
  results.footer_p = [];
  footerP.forEach(el => {
    const cs = getComputedStyle(el);
    results.footer_p.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,50)});
  });
  
  // Header brand
  const headerBrand = document.querySelectorAll('.hdr__brand, .hdr .brandword, header .brandword');
  results.header_brand = [];
  headerBrand.forEach(el => {
    const cs = getComputedStyle(el);
    results.header_brand.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,30)});
  });
  
  // Header nav links
  const headerNav = document.querySelectorAll('.hdr__nav a, .navlink a, header nav a');
  results.header_nav = [];
  headerNav.forEach(el => {
    const cs = getComputedStyle(el);
    results.header_nav.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,30)});
  });
  
  // Main h1/h2/h3 (content)
  const mainH1 = document.querySelectorAll('main h1, main .h-title, main .h-display');
  results.main_h1 = [];
  mainH1.forEach(el => {
    const cs = getComputedStyle(el);
    results.main_h1.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,50)});
  });
  
  const mainH2 = document.querySelectorAll('main h2, main .h-section, main .h-sub');
  results.main_h2 = [];
  mainH2.forEach(el => {
    const cs = getComputedStyle(el);
    results.main_h2.push({fontSize: cs.fontSize, text: el.textContent.trim().slice(0,50)});
  });
  
  return results;
}
"""

def prepara(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)
    page.evaluate(CHIUDI_BANNER)
    page.wait_for_timeout(300)

def main():
    url = BASE + "/"
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, user_agent=UA, color_scheme="light")
        page = ctx.new_page()
        prepara(page, url)
        
        # PRIMA
        prima = page.evaluate(JS_FONT)
        print("=== PRIMA (sito vivo) ===")
        for k, v in prima.items():
            if v:
                print(f"{k}: {[(x['fontSize'], x.get('text','')[:30]) for x in v]}")
        
        # DOPO
        page.add_style_tag(content=LAYOUT_CSS)
        page.add_style_tag(content=PROPOSTA_CSS)
        page.evaluate(TRASFORMA_JS)
        page.wait_for_timeout(500)
        
        dopo = page.evaluate(JS_FONT)
        print("\n=== DOPO (con CSS) ===")
        for k, v in dopo.items():
            if v:
                print(f"{k}: {[(x['fontSize'], x.get('text','')[:30]) for x in v]}")
        
        ctx.close()
        browser.close()

if __name__ == "__main__":
    main()