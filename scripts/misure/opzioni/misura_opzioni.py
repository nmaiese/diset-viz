"""Terzo giro UX: tre opzioni di impianto (A, B, C) fotografate sulle pagine vive.

Il sito non si tocca: si apre la pagina di produzione, si inietta un foglio di prova
(A.css, B.css, B.css + C_home.css) e si misura e fotografa. Un solo Chromium, tema chiaro,
banner del consenso chiuso, pausa di 1 s fra una pagina e la successiva. Si lancia con

    uv run --with playwright python scripts/misure/opzioni/misura_opzioni.py

Uscita: /mnt/c/Users/Nilo/orca/direzione/review/ux-opzioni/<pagina>_<device>_<stato>.png e misure_opzioni.json
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from ux_lettura import BASE, UA  # noqa: E402
from ux_immagini import CHIUDI_BANNER  # noqa: E402

OUT = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-opzioni")
PAGINE = {
    "home": "/",
    "regione": "/regione/molise",
    "articolo": "/blog/reddito-pro-capite-regioni-non-e-il-pil",
    "scheda": "/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600",
    "atlante": "/atlante",  # solo misure: è un'interfaccia
}
SOLO_MISURE = {"atlante"}
DEVICE = {"desktop": (1440, 900), "desktop1920": (1920, 1080), "mobile": (375, 812)}
DEVICE_PER_PAGINA = {"home": ["desktop", "desktop1920", "mobile"], "scheda": ["desktop", "desktop1920", "mobile"],
                     "regione": ["desktop", "mobile"], "articolo": ["desktop", "mobile"], "atlante": ["desktop", "desktop1920", "mobile"]}
FEAT = (QUI / "feat.css").read_text(encoding="utf-8")
CSS_A = (QUI / "A.css").read_text(encoding="utf-8") + "\n" + FEAT
CSS_B = (QUI / "B.css").read_text(encoding="utf-8") + "\n" + FEAT
CSS_C = CSS_B + "\n" + (QUI / "C_home.css").read_text(encoding="utf-8")

SELETTORE_PROSA = {
    "articolo": ".art-body > p",
    "regione": "main .prose p",
    "scheda": ".indicator-article p",
    "atlante": "main p",
    "home": "main p",
}

JS = r"""
(sel) => {
  const main = document.querySelector('main');
  const de = document.documentElement;
  const vh = window.innerHeight;
  const rect = el => el.getBoundingClientRect();
  const desc = el => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.') : '');

  // caratteri sulla prima riga dei paragrafi lunghi (mediana)
  const cpl = [];
  const larg = [];
  for (const p of main.querySelectorAll(sel)) {
    const t = p.textContent.replace(/\s+/g, ' ').trim();
    if (t.length < 150 || !p.getClientRects().length) continue;
    const tn = []; const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) if (n.nodeValue.trim()) tn.push(n);
    if (!tn.length) continue;
    const r = document.createRange(); r.setStart(tn[0], 0); r.setEnd(tn[0], 1);
    const top0 = r.getClientRects()[0]?.top; if (top0 === undefined) continue;
    let count = 0, done = false;
    for (const node of tn) {
      for (let i = 0; i < node.nodeValue.length; i++) {
        r.setStart(node, i); r.setEnd(node, i + 1);
        const rc = r.getClientRects()[0];
        if (!rc || rc.width === 0) { count++; continue; }
        if (Math.abs(rc.top - top0) > rc.height * 0.6) { done = true; break; }
        count++;
      }
      if (done) break;
    }
    if (done && count > 0) { cpl.push(count); larg.push(Math.round(rect(p).width)); }
  }
  const med = a => a.length ? [...a].sort((x, y) => x - y)[a.length >> 1] : null;

  // contenitore: larghezza del primo .wrap in main
  const wrap = main.querySelector('.wrap');
  // testata e piede
  const hdr = document.querySelector('header'); const ftr = document.querySelector('footer');
  const ftrw = document.querySelector('.ftr__wrap');
  const hw = document.querySelector('.sitechrome header, header.sitechrome') || hdr;
  const cs = el => { if (!el) return null; const c = getComputedStyle(el); return {w: Math.round(rect(el).width), h: Math.round(rect(el).height), fs: c.fontSize, pad: c.paddingTop + '/' + c.paddingBottom, width: c.width}; };

  // blocchi, link, parole
  const figli = [...main.children].filter(c => rect(c).height > 0 && c.tagName !== 'svg');
  const h2 = [...main.querySelectorAll('h2')].filter(h => h.getClientRects().length).length;
  const link = [...main.querySelectorAll('a[href]')].filter(a => a.getClientRects().length).length;
  const parole = main.innerText.split(/\s+/).filter(Boolean).length;
  const alt = Math.max(de.scrollHeight, document.body.scrollHeight);
  const schermi = alt / vh;
  const per3 = schermi / 3;

  // rotture: elementi che escono dal loro .wrap (non in contenitori con scroll proprio)
  const rotture = new Set();
  for (const el of main.querySelectorAll('*')) {
    const r = rect(el); if (r.width === 0 || r.height === 0) continue;
    const wr = el.closest('.wrap'); if (!wr || wr === el) continue;
    const wrr = rect(wr);
    if (r.right > wrr.right + 1.5 || r.left < wrr.left - 1.5) {
      let a = el.parentElement, scroll = false;
      while (a && a !== wr) { const o = getComputedStyle(a).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { scroll = true; break; } a = a.parentElement; }
      if (!scroll) rotture.add(desc(el) + ' (' + Math.round(r.width) + 'px in ' + Math.round(wrr.width) + ')');
    }
  }
  // contenuto tagliato o scorrevole: scrollWidth > clientWidth in un contenitore con overflow proprio
  const tagliati = new Set();
  for (const el of main.querySelectorAll('*')) {
    if (el.clientWidth < 40) continue;
    const o = getComputedStyle(el).overflowX;
    if ((o === 'auto' || o === 'scroll' || o === 'hidden') && el.scrollWidth > el.clientWidth + 2) tagliati.add(desc(el) + ' (' + el.scrollWidth + ' in ' + el.clientWidth + ', overflow ' + o + ')');
  }
  // elementi che escono dal riquadro (figura, scheda, tabella) che li contiene
  const fuori = new Set();
  for (const el of main.querySelectorAll('*')) {
    const r = rect(el); if (r.width === 0 || r.height === 0 || el.closest('svg') && el.tagName !== 'svg') continue;
    const box = el.parentElement && el.parentElement.closest('figure, article, .module, .card, .tablewrap, details');
    if (!box) continue;
    const bo = getComputedStyle(box).overflowX; if (bo === 'auto' || bo === 'scroll') continue;
    if (r.right > rect(box).right + 1.5) fuori.add(desc(el) + ' in ' + desc(box).slice(0, 40) + ' +' + Math.round(r.right - rect(box).right));
  }
  return {
    fuori_riquadro: [...fuori].slice(0, 12),
    tagliati: [...tagliati].slice(0, 12),
    larghezza_contenitore: wrap ? Math.round(rect(wrap).width) : null,
    main_w: Math.round(rect(main).width),
    cpl_mediana: med(cpl), cpl_campioni: cpl.length, larghezza_p: med(larg),
    altezza_schermi: +schermi.toFixed(2), altezza_px: alt,
    blocchi: figli.length, h2,
    link, parole,
    link_per_3schermi: +(link / per3).toFixed(1), parole_per_3schermi: Math.round(parole / per3),
    scroll_orizzontale: de.scrollWidth > window.innerWidth,
    header: cs(hdr), header_wrap: cs(hw), footer: cs(ftr), footer_wrap: cs(ftrw),
    rotture: [...rotture].slice(0, 12),
  };
}
"""

STATI = ["prima", "A", "B", "C"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ris = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for pagina, path in PAGINE.items():
                for dev in DEVICE_PER_PAGINA[pagina]:
                    w, h = DEVICE[dev]
                    ctx = browser.new_context(viewport={"width": w, "height": h}, user_agent=UA, color_scheme="light")
                    try:
                        pg = ctx.new_page()
                        resp = pg.goto(BASE + path, wait_until="networkidle", timeout=60000)
                        if resp.status != 200:
                            print(f"SALTO {pagina}: status {resp.status}")
                            ris.append({"pagina": pagina, "device": dev, "errore": f"status {resp.status}"})
                            continue
                        pg.wait_for_timeout(1000)
                        pg.evaluate(CHIUDI_BANNER)
                        pg.wait_for_timeout(300)
                        for stato in STATI:
                            if stato == "C" and pagina != "home":
                                continue
                            pg.evaluate("document.querySelectorAll('style[data-prova]').forEach(s => s.remove())")
                            css = {"A": CSS_A, "B": CSS_B, "C": CSS_C}.get(stato)
                            if css:
                                pg.evaluate("(c) => { const s = document.createElement('style'); s.dataset.prova = '1'; s.textContent = c; document.head.appendChild(s); }", css)
                            pg.wait_for_timeout(500)
                            m = pg.evaluate(JS, SELETTORE_PROSA[pagina])
                            m.update({"pagina": pagina, "device": dev, "stato": stato})
                            ris.append(m)
                            if pagina not in SOLO_MISURE:
                                pg.screenshot(path=str(OUT / f"{pagina}_{dev}_{stato}.png"), full_page=True)
                            print(f"{pagina:9} {dev:12} {stato:5} wrap={m['larghezza_contenitore']} cpl={m['cpl_mediana']} ({m['cpl_campioni']}) schermi={m['altezza_schermi']} blocchi={m['blocchi']} scrollX={m['scroll_orizzontale']} rotture={len(m['rotture'])} tagliati={len(m['tagliati'])} fuori={len(m['fuori_riquadro'])}")
                    except Exception as e:  # noqa: BLE001
                        print(f"ERRORE {pagina} {dev}: {e}", file=sys.stderr)
                        ris.append({"pagina": pagina, "device": dev, "errore": str(e)[:300]})
                    finally:
                        ctx.close()
                    time.sleep(1)
        finally:
            browser.close()
    (OUT / "misure_opzioni.json").write_text(json.dumps(ris, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"scritto {OUT}/misure_opzioni.json")


if __name__ == "__main__":
    main()
