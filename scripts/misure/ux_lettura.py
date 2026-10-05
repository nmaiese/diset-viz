"""UX di lettura, fase 1: screenshot e misure di 7 pagine del sito vivo.

Sola raccolta: non modifica il sito. Si lancia con

    uv run --with playwright python scripts/misure/ux_lettura.py

Rete: solo https://divarioitalia.it. Una sola istanza di Chromium, un contesto
alla volta, pausa di 1 s fra una pagina e la successiva.
"""

import json
import statistics
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://divarioitalia.it"
OUT = Path("/mnt/c/Users/Nilo/orca/direzione/ux-lettura/fase1")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

PAGINE = {
    "home": "/",
    "scheda": "/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600",
    "regione": "/regione/piemonte",
    "provincia": "/provincia/monza-e-della-brianza",
    "atlante": "/atlante",
    "articolo": "/blog/reddito-pro-capite-regioni-non-e-il-pil",
    "tema": "/tema/reddito-inclusione-e-accessibilita",
}
LARGHEZZE = [(375, 812), (768, 1024), (1024, 768), (1440, 900)]
TEMI = ["chiaro", "scuro"]

# Eseguito nella pagina: restituisce tutte le misure di testo e di ritmo.
JS_MISURE = r"""
() => {
  const median = a => {
    if (!a.length) return null;
    const s = [...a].sort((x, y) => x - y), m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const px = v => { const n = parseFloat(v); return isNaN(n) ? null : n; };
  const out = {errori: []};
  const main = document.querySelector('main');
  const de = document.documentElement;
  out.altezza_px = Math.max(de.scrollHeight, document.body.scrollHeight);
  out.altezza_schermi = +(out.altezza_px / window.innerHeight).toFixed(2);
  out.scroll_orizzontale = de.scrollWidth > window.innerWidth;
  out.scrollWidth = de.scrollWidth;
  out.innerWidth = window.innerWidth;
  if (!main) { out.errori.push('nessun <main>'); return out; }

  // Lunghezza di riga: caratteri nella prima riga reale / caratteri totali.
  const cpl = [];
  let paragrafi = 0;
  for (const p of main.querySelectorAll('p')) {
    const t = p.textContent.replace(/\s+/g, ' ').trim();
    if (t.length <= 40) continue;
    if (!p.getClientRects().length) continue;   // nascosto
    paragrafi++;
    try {
      const tn = [];
      const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())) if (n.nodeValue.trim()) tn.push(n);
      if (!tn.length) continue;
      // Range carattere per carattere finche' la riga resta la stessa.
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
      if (!done) { // una sola riga: tutto il testo e' sulla prima
        // paragrafo su una riga: usa il conteggio totale, e' un limite inferiore
      }
      if (count > 0) cpl.push(count);
    } catch (e) { out.errori.push('riga: ' + e.message); }
  }
  out.paragrafi_misurati = paragrafi;
  out.riga_cpl = {
    n: cpl.length,
    mediana: median(cpl), min: cpl.length ? Math.min(...cpl) : null,
    max: cpl.length ? Math.max(...cpl) : null,
    fuori_45_80: cpl.filter(c => c < 45 || c > 80).length,
  };

  // Font e interlinea dei testi correnti (paragrafi e voci di lista nel main).
  const fs = [], lh = [];
  for (const el of main.querySelectorAll('p, li')) {
    if (!el.getClientRects().length || el.textContent.trim().length < 20) continue;
    const cs = getComputedStyle(el);
    const f = px(cs.fontSize);
    fs.push(f);
    const l = cs.lineHeight === 'normal' ? f * 1.2 : px(cs.lineHeight);
    if (l) lh.push(l);
  }
  out.testo_corrente = {
    n: fs.length, font_px_mediana: median(fs), interlinea_px_mediana: median(lh),
    interlinea_rapporto_mediana: fs.length && lh.length ? +(median(lh) / median(fs)).toFixed(3) : null,
  };
  // Elementi di testo con font < 11 px (tutta la pagina, solo elementi con testo diretto).
  let piccoli = 0, testuali = 0;
  const esempi = [];
  const w2 = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let e;
  while ((e = w2.nextNode())) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG'].includes(e.tagName.toUpperCase())) continue;
    if (e.closest('svg')) continue;
    let diretto = false;
    for (const c of e.childNodes) if (c.nodeType === 3 && c.nodeValue.trim()) { diretto = true; break; }
    if (!diretto || !e.getClientRects().length) continue;
    testuali++;
    const f = px(getComputedStyle(e).fontSize);
    if (f !== null && f < 11) {
      piccoli++;
      if (esempi.length < 5) esempi.push(e.tagName.toLowerCase() + '.' + (e.className && e.className.baseVal === undefined ? String(e.className).split(' ')[0] : '') + ' ' + f + 'px');
    }
  }
  out.font_sotto_11 = {elementi_testuali: testuali, sotto_11px: piccoli, esempi};

  // Blocchi continui: parole del paragrafo piu' lungo e serie di <p> consecutivi.
  let maxParole = 0;
  const parole = [];
  for (const p of main.querySelectorAll('p')) {
    const n = p.textContent.trim().split(/\s+/).filter(Boolean).length;
    if (p.getClientRects().length) { parole.push(n); if (n > maxParole) maxParole = n; }
  }
  out.paragrafo_piu_lungo_parole = maxParole;
  const serie = [];
  let corr = 0;
  const ROMPE = /^(H[1-6]|UL|OL|IMG|FIGURE|SVG|CANVAS|TABLE|PICTURE|VIDEO|IFRAME|BLOCKQUOTE|PRE|HR)$/;
  const visita = (root) => {
    for (const c of root.children) {
      const tag = c.tagName.toUpperCase();
      if (!c.getClientRects().length) continue;
      if (tag === 'P') {
        if (c.textContent.trim().length > 40) corr++;
      } else if (ROMPE.test(tag) || c.querySelector('svg, canvas, img, figure, table, ul, ol, h1, h2, h3, h4')) {
        // contenitore con elementi che rompono: scendi se non e' foglia di contenuto
        if (!ROMPE.test(tag) && c.children.length && !c.matches('section, article, div, main, aside')) {
          if (corr) { serie.push(corr); corr = 0; }
        } else if (!ROMPE.test(tag)) {
          visita(c);
          continue;
        }
        if (corr) { serie.push(corr); corr = 0; }
      } else if (c.querySelector('p')) {
        visita(c);
      } else {
        // blocco senza paragrafi (card, form, ecc.): rompe la serie
        if (corr) { serie.push(corr); corr = 0; }
      }
    }
  };
  visita(main);
  if (corr) serie.push(corr);
  out.paragrafi_consecutivi = {
    serie: serie.length, max: serie.length ? Math.max(...serie) : 0, mediana: median(serie),
  };

  // Scala dei titoli e margini titolo-paragrafo.
  out.titoli = {};
  for (const tag of ['h1', 'h2', 'h3']) {
    const els = [...document.querySelectorAll(tag)].filter(h => h.getClientRects().length);
    const sizes = els.map(h => px(getComputedStyle(h).fontSize));
    const mt = els.map(h => px(getComputedStyle(h).marginTop));
    const mb = els.map(h => px(getComputedStyle(h).marginBottom));
    const avg = a => a.length ? +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(1) : null;
    out.titoli[tag] = {n: els.length, font_px_mediana: median(sizes), margine_sup_medio: avg(mt), margine_inf_medio: avg(mb)};
  }
  // Spazio effettivo titolo -> paragrafo seguente (distanza fra i box).
  const gap = [];
  for (const h of main.querySelectorAll('h2, h3')) {
    const nx = h.nextElementSibling;
    if (nx && nx.tagName === 'P' && h.getClientRects().length) {
      const g = nx.getBoundingClientRect().top - h.getBoundingClientRect().bottom;
      if (g >= 0) gap.push(g);   // negativo = affiancati, non sovrapposti in colonna
    }
  }
  out.gap_titolo_paragrafo_px = {n: gap.length, medio: gap.length ? +(gap.reduce((a, b) => a + b, 0) / gap.length).toFixed(1) : null};

  // Ritmo verticale: distanza fra box di fratelli diretti di main.
  const dist = [];
  const kids = [...main.children].filter(c => c.getClientRects().length);
  for (let i = 1; i < kids.length; i++) {
    dist.push(kids[i].getBoundingClientRect().top - kids[i - 1].getBoundingClientRect().bottom);
  }
  const pad = kids.map(k => { const c = getComputedStyle(k);
    return px(c.marginTop) + px(c.paddingTop) + px(c.marginBottom) + px(c.paddingBottom); });
  out.ritmo_main = {figli: kids.length, distanza_px_mediana: median(dist),
    margine_padding_px_mediana: median(pad)};
  out.main_larghezza_px = Math.round(main.getBoundingClientRect().width);
  return out;
}
"""


def imposta_tema(page, tema, sfondo_chiaro=None):
    """Imposta il tema su <html>; per lo scuro confronta con lo sfondo chiaro.

    Il contesto scuro porta anche `prefers-color-scheme: dark`, quindi lo sfondo
    "prima" puo' essere gia' scuro: il confronto vero e' con il tema chiaro.
    """
    sfondo = lambda: page.evaluate(  # noqa: E731
        "getComputedStyle(document.body).backgroundColor"
    )
    if tema == "scuro":
        prima = sfondo()
        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        page.wait_for_timeout(300)
        dopo = sfondo()
        return {
            "sfondo_chiaro": sfondo_chiaro,
            "sfondo_prima_attributo": prima,
            "sfondo_dopo": dopo,
            "cambiato": sfondo_chiaro is not None and sfondo_chiaro != dopo,
        }
    return {"sfondo": sfondo()}


def carica(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)


def mediana(v):
    return statistics.median(v) if v else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    risultati = []
    immagini = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for chiave, path in PAGINE.items():
                url = BASE + path
                for w, h in LARGHEZZE:
                    sfondo_chiaro = None
                    for tema in TEMI:
                        voce = {"pagina": chiave, "url": url, "larghezza": w, "tema": tema}
                        ctx = browser.new_context(
                            viewport={"width": w, "height": h},
                            user_agent=UA,
                            color_scheme="dark" if tema == "scuro" else "light",
                        )
                        try:
                            page = ctx.new_page()
                            carica(page, url)
                            voce["tema_verifica"] = imposta_tema(page, tema, sfondo_chiaro)
                            if tema == "chiaro":
                                sfondo_chiaro = voce["tema_verifica"]["sfondo"]
                            if tema == "scuro" and not voce["tema_verifica"]["cambiato"]:
                                voce.setdefault("note", []).append(
                                    "sfondo del body invariato dopo data-theme=dark"
                                )
                            if tema == "chiaro":
                                voce["misure"] = page.evaluate(JS_MISURE)
                            nome = f"{chiave}_{w}_{tema}.png"
                            page.screenshot(path=str(OUT / nome), full_page=True)
                            immagini.append(nome)
                            voce["screenshot"] = nome
                        except Exception as e:  # non inventare numeri: registra il guasto
                            voce["errore"] = f"{type(e).__name__}: {e}"[:300]
                            print(f"ERRORE {chiave} {w} {tema}: {voce['errore']}", file=sys.stderr)
                        finally:
                            ctx.close()
                        risultati.append(voce)
                        print(f"ok {chiave} {w} {tema}", flush=True)
                time.sleep(1)
        finally:
            browser.close()

    (OUT / "misure.json").write_text(
        json.dumps(risultati, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scrivi_md(risultati)
    scrivi_indice(risultati, immagini)
    print(f"Scritto in {OUT}")


def fmt(v):
    return "n/d" if v is None else (f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


def scrivi_md(risultati):
    righe = [
        "# Misure di lettura, fase 1 (tema chiaro)",
        "",
        "Fonte: https://divarioitalia.it, misurato con Chromium. `n/d` = non misurabile.",
        "",
        "| pagina | larg. | altezza px | schermi | riga cpl med (min-max) | fuori 45-80 / par. | font med px | interl. med px | testi <11px | par. più lungo (parole) | par. consecutivi max/med | h1/h2/h3 px | gap titolo-par. px | ritmo main px (distanza / margine+padding) | scroll orizz. |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    note = []
    for v in risultati:
        if v["tema"] != "chiaro":
            continue
        if "errore" in v:
            righe.append(f"| {v['pagina']} | {v['larghezza']} | errore: {v['errore']} |" + " |" * 12)
            note.append(f"{v['pagina']} {v['larghezza']}: {v['errore']}")
            continue
        m = v["misure"]
        for e in m.get("errori", []):
            note.append(f"{v['pagina']} {v['larghezza']}: {e}")
        if "riga_cpl" not in m:
            righe.append(f"| {v['pagina']} | {v['larghezza']} | {fmt(m.get('altezza_px'))} | {fmt(m.get('altezza_schermi'))} |" + " n/d |" * 11 + f" {'sì' if m.get('scroll_orizzontale') else 'no'} |")
            continue
        r, t, f = m["riga_cpl"], m["testo_corrente"], m["font_sotto_11"]
        pc, ti = m["paragrafi_consecutivi"], m["titoli"]
        righe.append(
            f"| {v['pagina']} | {v['larghezza']} | {m['altezza_px']} | {m['altezza_schermi']} "
            f"| {fmt(r['mediana'])} ({fmt(r['min'])}-{fmt(r['max'])}) | {r['fuori_45_80']}/{r['n']} "
            f"| {fmt(t['font_px_mediana'])} | {fmt(t['interlinea_px_mediana'])} "
            f"| {f['sotto_11px']}/{f['elementi_testuali']} | {m['paragrafo_piu_lungo_parole']} "
            f"| {pc['max']}/{fmt(pc['mediana'])} "
            f"| {fmt(ti['h1']['font_px_mediana'])}/{fmt(ti['h2']['font_px_mediana'])}/{fmt(ti['h3']['font_px_mediana'])} "
            f"| {fmt(m['gap_titolo_paragrafo_px']['medio'])} | {fmt(m['ritmo_main']['distanza_px_mediana'])} / {fmt(m['ritmo_main']['margine_padding_px_mediana'])} "
            f"| {'sì' if m['scroll_orizzontale'] else 'no'} |"
        )
    righe += ["", "## Verifica tema scuro", ""]
    for v in risultati:
        if v["tema"] == "scuro":
            tv = v.get("tema_verifica")
            righe.append(
                f"- {v['pagina']} {v['larghezza']}: "
                + (f"sfondo chiaro {tv['sfondo_chiaro']} -> scuro {tv['sfondo_dopo']} ({'cambiato' if tv['cambiato'] else 'INVARIATO'})" if tv else f"non verificato ({v.get('errore')})")
            )
    if note:
        righe += ["", "## Note e misure fallite", ""] + [f"- {n}" for n in note]
    (OUT / "misure.md").write_text("\n".join(righe) + "\n", encoding="utf-8")


def scrivi_indice(risultati, immagini):
    righe = ["# Indice, UX di lettura fase 1", "", "## Immagini", ""]
    righe += [f"- {n}" for n in sorted(immagini)]
    righe += ["", "## Dove il testo si accumula (solo misure, tema chiaro)", ""]
    for chiave in PAGINE:
        vs = [v for v in risultati if v["pagina"] == chiave and v["tema"] == "chiaro" and "misure" in v and "riga_cpl" in v["misure"]]
        righe.append(f"### {chiave}")
        if not vs:
            righe += ["- misure non disponibili", "", ]
            continue
        a = max(vs, key=lambda v: v["misure"]["altezza_px"])
        d = min(vs, key=lambda v: v["larghezza"])
        w = max(vs, key=lambda v: v["larghezza"])
        ma, md, mw = a["misure"], d["misure"], w["misure"]
        righe.append(
            f"- Altezza: da {min(x['misure']['altezza_schermi'] for x in vs)} a {ma['altezza_schermi']} schermi "
            f"({ma['altezza_px']} px a {a['larghezza']} px)."
        )
        righe.append(
            f"- Righe: a {d['larghezza']} px mediana {fmt(md['riga_cpl']['mediana'])} caratteri, "
            f"a {w['larghezza']} px mediana {fmt(mw['riga_cpl']['mediana'])}; "
            f"fuori 45-80: {md['riga_cpl']['fuori_45_80']}/{md['riga_cpl']['n']} e {mw['riga_cpl']['fuori_45_80']}/{mw['riga_cpl']['n']}."
        )
        righe.append(
            f"- Blocchi: paragrafo più lungo {mw['paragrafo_piu_lungo_parole']} parole; "
            f"massimo {mw['paragrafi_consecutivi']['max']} paragrafi consecutivi senza titolo, lista o figura."
        )
        righe.append("")
    (OUT / "INDICE.md").write_text("\n".join(righe) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
