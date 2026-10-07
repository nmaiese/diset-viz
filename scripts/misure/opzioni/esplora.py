"""Ispezione DOM: struttura di main, larghezza di p/li per contenitore. Sola lettura."""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ux_lettura import BASE, UA
from ux_immagini import PAGINE, CHIUDI_BANNER

JS = r"""
() => {
  const main = document.querySelector('main');
  const desc = el => el.tagName.toLowerCase() + (el.id ? '#'+el.id : '') + (el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\s+/).join('.') : '');
  const r = {main: desc(main), mainW: Math.round(main.getBoundingClientRect().width),
    figli: [...main.children].map(c => ({d: desc(c), w: Math.round(c.getBoundingClientRect().width), h: Math.round(c.getBoundingClientRect().height), txt: (c.querySelector('h1,h2,h3')||{}).textContent?.trim().slice(0,50)}))};
  // gruppi di p/li con testo lungo: per contenitore genitore
  const g = {};
  main.querySelectorAll('p, li').forEach(p => {
    const t = p.textContent.replace(/\s+/g,' ').trim();
    if (t.length < 80 || !p.getClientRects().length) return;
    // catena di antenati breve
    let chain = []; let a = p.parentElement;
    while (a && a !== main && chain.length < 3) { chain.push(desc(a).slice(0,60)); a = a.parentElement; }
    const k = p.tagName.toLowerCase() + ' < ' + chain.join(' < ');
    const w = Math.round(p.getBoundingClientRect().width);
    const fs = parseFloat(getComputedStyle(p).fontSize);
    (g[k] = g[k] || []).push({w, fs, len: t.length});
  });
  r.prosa = Object.entries(g).map(([k,v]) => ({k, n: v.length, w: v[0].w, fs: v[0].fs, medlen: v.map(x=>x.len).sort((a,b)=>a-b)[v.length>>1]}));
  return r;
}
"""
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for k in ["home","regione","articolo","scheda","atlante"]:
        ctx = b.new_context(viewport={"width":1440,"height":900}, user_agent=UA, color_scheme="light")
        pg = ctx.new_page()
        resp = pg.goto(BASE+PAGINE[k], wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1000); pg.evaluate(CHIUDI_BANNER)
        out[k] = {"status": resp.status, **pg.evaluate(JS)}
        ctx.close(); time.sleep(1)
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
