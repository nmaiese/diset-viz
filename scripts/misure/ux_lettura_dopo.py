"""UX di lettura, fase 3: prima e dopo di 3 pagine, con un foglio di prova iniettato.

Sola raccolta: non modifica il sito. Apre le pagine vere di produzione, chiude il
banner del consenso, fotografa lo stato "prima"; poi inietta `proposta.css`, esegue
`trasforma.js` e fotografa lo stato "dopo". Riusa le misure di `ux_lettura.py`
(stesso JS, stessi parametri della fase 1) e aggiunge i controlli di rottura
(scroll orizzontale, elementi che escono dalla colonna, testi sotto 12 px).

    uv run --with playwright python scripts/misure/ux_lettura_dopo.py

Rete: solo https://divarioitalia.it. Una sola istanza di Chromium, un contesto
alla volta, pausa di 1 s fra una pagina e la successiva.
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux_lettura import BASE, JS_MISURE, UA, block_tracking, fmt  # noqa: E402

OUT = Path("/mnt/c/Users/Nilo/orca/direzione/ux-lettura/fase3")
PAGINE = {
    "articolo": "/blog/reddito-pro-capite-regioni-non-e-il-pil",
    "regione": "/regione/molise",
    "scheda": "/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600",
}
LARGHEZZE = [(375, 812), (1024, 768)]
TEMI = ["chiaro", "scuro"]

# Stesso JS della fase 1, ma limitato al testo corrente (prosa e paragrafi introduttivi):
# la misura sull'intero <main> mescola prosa, schede, tabelle e didascalie.
PROSA = ".prose p, .prose li, .indicator-article p, .indicator-article li, .art-brief p.answer, .regione-intro, .regione-stacca__lead"
JS_PROSA = (
    JS_MISURE.replace("main.querySelectorAll('p')", f"main.querySelectorAll('{PROSA}')", 1)
    .replace("main.querySelectorAll('p, li')", f"main.querySelectorAll('{PROSA}')", 1)
)

# Eseguito nella pagina dopo le trasformazioni: difetti che la proposta non deve introdurre.
JS_CONTROLLI = r"""
() => {
  const de = document.documentElement;
  const out = {scroll_orizzontale: de.scrollWidth > window.innerWidth,
               scrollWidth: de.scrollWidth, innerWidth: window.innerWidth};
  // Testi sotto 12 px (elementi con testo diretto visibile, svg esclusi).
  let sotto12 = 0, testuali = 0;
  const esempi = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let e;
  while ((e = w.nextNode())) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(e.tagName.toUpperCase()) || e.closest('svg')) continue;
    let diretto = false;
    for (const c of e.childNodes) if (c.nodeType === 3 && c.nodeValue.trim()) { diretto = true; break; }
    if (!diretto || !e.getClientRects().length) continue;
    testuali++;
    const f = parseFloat(getComputedStyle(e).fontSize);
    if (f < 12) { sotto12++; if (esempi.length < 5) esempi.push(e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0] + ' ' + f + 'px'); }
  }
  out.sotto_12 = {testuali, sotto12, esempi};
  // Elementi che sporgono oltre il viewport a destra (causa tipica di scroll orizzontale).
  const sporgono = [];
  for (const el of document.querySelectorAll('main *')) {
    if (el.closest('svg') || !el.getClientRects().length) continue;
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > window.innerWidth + 1) {
      sporgono.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]);
      if (sporgono.length >= 5) break;
    }
  }
  out.sporgono = sporgono;
  return out;
}
"""

CHIUDI_BANNER = r"""
() => {
  const b = document.querySelector('#iubenda-cs-banner, .iubenda-cs-container');
  const btn = document.querySelector('.iubenda-cs-accept-btn, .iubenda-cs-reject-btn, #iubenda-cs-banner button');
  if (btn) btn.click();
  document.querySelectorAll('#iubenda-cs-banner, .iubenda-cs-overlay').forEach(x => x.remove());
  return !!b;
}
"""


def prepara(page, url, tema):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    page.evaluate(CHIUDI_BANNER)
    page.wait_for_timeout(300)
    if tema == "scuro":
        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        page.wait_for_timeout(300)


def scatta(page, nome):
    page.screenshot(path=str(OUT / nome), full_page=True)


def misura(page, w):
    m = page.evaluate(JS_MISURE)
    m["controlli"] = page.evaluate(JS_CONTROLLI)
    m["prosa"] = page.evaluate(JS_PROSA)
    # Larghezza della colonna di prosa: primo paragrafo lungo dentro main.
    m["colonna_px"] = page.evaluate(
        "(() => { const p=[...document.querySelectorAll('main p')].find(p=>p.textContent.trim().length>80 && p.getClientRects().length);"
        " return p ? Math.round(p.getBoundingClientRect().width) : null; })()"
    )
    return m


def main():
    css = (OUT / "proposta.css").read_text(encoding="utf-8")
    js = (OUT / "trasforma.js").read_text(encoding="utf-8")
    risultati = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for chiave, path in PAGINE.items():
                url = BASE + path
                for w, h in LARGHEZZE:
                    for tema in TEMI:
                        ctx = browser.new_context(
                            viewport={"width": w, "height": h},
                            user_agent=UA,
                            color_scheme="dark" if tema == "scuro" else "light",
                        )
                        block_tracking(ctx)
                        try:
                            page = ctx.new_page()
                            prepara(page, url, tema)
                            voce = {"pagina": chiave, "larghezza": w, "tema": tema}
                            voce["prima"] = misura(page, w)
                            scatta(page, f"prima_{chiave}_{w}_{tema}.png")
                            page.add_style_tag(content=css)
                            voce["trasformazioni"] = page.evaluate(js)
                            page.wait_for_timeout(500)
                            voce["dopo"] = misura(page, w)
                            scatta(page, f"dopo_{chiave}_{w}_{tema}.png")
                            risultati.append(voce)
                            print(f"ok {chiave} {w} {tema}", flush=True)
                        except Exception as e:  # non inventare numeri: registra il guasto
                            risultati.append({"pagina": chiave, "larghezza": w, "tema": tema,
                                              "errore": f"{type(e).__name__}: {e}"[:300]})
                            print(f"ERRORE {chiave} {w} {tema}: {e}", file=sys.stderr)
                        finally:
                            ctx.close()
                time.sleep(1)
        finally:
            browser.close()
    (OUT / "misure_dopo.json").write_text(json.dumps(risultati, ensure_ascii=False, indent=2), encoding="utf-8")
    scrivi_md(risultati)
    print(f"Scritto in {OUT}")


def riga_prosa(v, quando):
    p = v[quando]["prosa"]
    if "riga_cpl" not in p:
        return None
    r, t = p["riga_cpl"], p["testo_corrente"]
    return (f"| {v['pagina']} | {v['larghezza']} | {quando} | {fmt(r['mediana'])} ({fmt(r['min'])}-{fmt(r['max'])}) "
            f"| {r['fuori_45_80']}/{r['n']} | {fmt(t['font_px_mediana'])} | {fmt(t['interlinea_px_mediana'])} "
            f"| {fmt(t['interlinea_rapporto_mediana'])} | {p['paragrafo_piu_lungo_parole']} |")


def riga(v, quando):
    m = v[quando]
    if "riga_cpl" not in m:
        return None
    r, t, c = m["riga_cpl"], m["testo_corrente"], m["controlli"]
    return (f"| {v['pagina']} | {v['larghezza']} | {quando} | {fmt(r['mediana'])} ({fmt(r['min'])}-{fmt(r['max'])}) "
            f"| {r['fuori_45_80']}/{r['n']} | {fmt(m['altezza_schermi'])} | {fmt(t['font_px_mediana'])} / {fmt(t['interlinea_px_mediana'])} "
            f"| {m['font_sotto_11']['sotto_11px']} | {c['sotto_12']['sotto12']}/{c['sotto_12']['testuali']} "
            f"| {m['paragrafo_piu_lungo_parole']} | {fmt(m['colonna_px'])} | {'sì' if c['scroll_orizzontale'] else 'no'} |")


def scrivi_md(risultati):
    righe = ["# Misure prima/dopo, fase 3 (tema chiaro)", "",
             "| pagina | larg. | stato | riga cpl med (min-max) | fuori 45-80 / par. | schermi | font / interl. px | testi <11px | testi <12px | par. più lungo (parole) | colonna px | scroll orizz. |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    note = []
    for v in risultati:
        if "errore" in v:
            note.append(f"{v['pagina']} {v['larghezza']} {v['tema']}: {v['errore']}")
            continue
        if v["tema"] != "chiaro":
            for q in ("prima", "dopo"):
                c = v[q]["controlli"]
                if c["scroll_orizzontale"] or c["sporgono"]:
                    note.append(f"{v['pagina']} {v['larghezza']} scuro {q}: scroll orizzontale {c['scroll_orizzontale']}, sporgono {c['sporgono']}")
            continue
        for q in ("prima", "dopo"):
            r = riga(v, q)
            if r:
                righe.append(r)
            c = v[q]["controlli"]
            if c["sporgono"]:
                note.append(f"{v['pagina']} {v['larghezza']} {q}: sporgono oltre il viewport {c['sporgono']}")
        note.append(f"{v['pagina']} {v['larghezza']} trasformazioni: {json.dumps(v.get('trasformazioni'), ensure_ascii=False)}")
    righe += ["", "## Solo testo corrente (prosa e paragrafi introduttivi, tema chiaro)", "",
              "| pagina | larg. | stato | riga cpl med (min-max) | fuori 45-80 / par. | font px | interl. px | interl./font | par. più lungo (parole) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for v in risultati:
        if "errore" in v or v["tema"] != "chiaro":
            continue
        for q in ("prima", "dopo"):
            r = riga_prosa(v, q)
            if r:
                righe.append(r)
    if note:
        righe += ["", "## Note", ""] + [f"- {n}" for n in note]
    (OUT / "misure_dopo.md").write_text("\n".join(righe) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
