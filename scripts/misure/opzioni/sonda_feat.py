"""Sonda: nella home, elementi che escono dal riquadro dell'indicatore in evidenza (#dato article.feat) per stato."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, UA
from ux_immagini import CHIUDI_BANNER
from misura_opzioni import CSS_A, CSS_B
JS = r"""() => { const f = document.querySelector('#dato article.feat'); const fr = f.getBoundingClientRect(); const out = [];
 for (const el of f.querySelectorAll('*')) { const r = el.getBoundingClientRect(); if (r.width && r.right > fr.right + 1) out.push(el.tagName.toLowerCase()+'.'+String(el.className).split(' ')[0]+' right+'+Math.round(r.right-fr.right)); }
 return {feat_w: Math.round(fr.width), fuori: [...new Set(out)].slice(0,8), n: out.length}; }"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (1440, 1920):
        ctx = b.new_context(viewport={"width": w, "height": 900}, user_agent=UA, color_scheme="light"); pg = ctx.new_page()
        pg.goto(BASE + "/", wait_until="networkidle"); pg.wait_for_timeout(1000); pg.evaluate(CHIUDI_BANNER)
        for st, css in (("prima", None), ("A", CSS_A), ("B", CSS_B)):
            pg.evaluate("document.querySelectorAll('style[data-prova]').forEach(s=>s.remove())")
            if css: pg.evaluate("(c)=>{const s=document.createElement('style');s.dataset.prova='1';s.textContent=c;document.head.appendChild(s)}", css)
            pg.wait_for_timeout(400); print(w, st, pg.evaluate(JS))
        ctx.close(); time.sleep(1)
    b.close()
