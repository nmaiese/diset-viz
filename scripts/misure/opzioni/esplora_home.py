"""Ispezione home: blocchi, link per blocco, link di testata. Sola lettura."""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ux_lettura import BASE, UA
from ux_immagini import CHIUDI_BANNER
JS = r"""
() => {
  const main = document.querySelector('main');
  const hdr = [...document.querySelectorAll('header a, nav a')].filter(a => !main.contains(a)).map(a => a.getAttribute('href'));
  const blocchi = [...main.children].filter(c => c.getBoundingClientRect().height > 0).map(c => ({
    d: c.tagName.toLowerCase()+'#'+c.id+'.'+String(c.className).replace(/\s+/g,'.'),
    h: Math.round(c.getBoundingClientRect().height),
    h2: [...c.querySelectorAll('h2')].map(h => h.textContent.trim().slice(0,60)),
    parole: c.innerText.split(/\s+/).filter(Boolean).length,
    link: [...c.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(Boolean),
  }));
  return {hdr: [...new Set(hdr)], blocchi};
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width":1440,"height":900}, user_agent=UA, color_scheme="light")
    pg = ctx.new_page(); pg.goto(BASE+"/", wait_until="networkidle"); pg.wait_for_timeout(1000); pg.evaluate(CHIUDI_BANNER)
    r = pg.evaluate(JS)
    print("HEADER/NAV (fuori main):", r["hdr"])
    for x in r["blocchi"]:
        print("\n==", x["d"], x["h"], "px", x["parole"], "parole", len(x["link"]), "link; h2:", x["h2"])
        print("  link:", sorted(set(x["link"]))[:40])
    b.close()
