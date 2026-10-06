"""Generate confronto.html from misure_immagini.json"""

import json
from pathlib import Path

# Read the JSON from external directory
json_path = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini/misure_immagini.json")
data = json.loads(json_path.read_text(encoding="utf-8"))

# Organize by pagina
pagine = {}
for r in data:
    if "errore" in r:
        continue
    chiave = r["pagina"]
    device = r["device"]
    if chiave not in pagine:
        pagine[chiave] = {}
    pagine[chiave][device] = r

# Page order
page_order = ["home", "regioni", "blog", "atlante", "articolo", "regione", "scheda"]
page_labels = {
    "home": "Home",
    "regioni": "Regioni",
    "blog": "Blog",
    "atlante": "Atlante",
    "articolo": "Articolo",
    "regione": "Regione",
    "scheda": "Scheda indicatore"
}

device_order = ["desktop1920", "desktop1440", "mobile"]
device_labels = {
    "desktop1920": "Desktop 1920px",
    "desktop1440": "Desktop 1440px",
    "mobile": "Mobile 375px"
}

html = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Confronto prima/dopo - UX lettura Divario Italia</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; padding: 2rem; background: #fafafa; color: #111; }
  h1 { text-align: center; margin-bottom: 0.5rem; }
  .subtitle { text-align: center; color: #666; margin-bottom: 2rem; }
  .page-section { margin-bottom: 4rem; }
  .page-title { font-size: 1.5rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #ddd; }
  .images-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
  @media (max-width: 1200px) { .images-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 800px) { .images-grid { grid-template-columns: 1fr; } }
  .img-wrap { background: white; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; }
  .img-wrap img { width: 100%; height: auto; display: block; }
  .img-label { padding: 0.5rem; background: #f5f5f5; font-size: 0.875rem; font-weight: 600; text-align: center; border-bottom: 1px solid #ddd; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 0.875rem; }
  th, td { padding: 0.5rem; border: 1px solid #ddd; text-align: center; }
  th { background: #f0f0f0; font-weight: 600; }
  tr:nth-child(even) { background: #fafafa; }
  .scroll-yes { color: #c00; font-weight: 600; }
  .scroll-no { color: #080; }
  .break { background: #fff3cd; }
  .legend { font-size: 0.8rem; color: #666; margin-top: 2rem; padding: 1rem; background: #f9f9f9; border-radius: 4px; }
  .viewport-badge { display: inline-block; padding: 0.1rem 0.4rem; font-size: 0.75rem; background: #e0e0e0; border-radius: 3px; margin-left: 0.5rem; }
</style>
</head>
<body>
<h1>Confronto prima / dopo — Impianto di pagina</h1>
<p class="subtitle">7 pagine × 3 viewport (desktop 1920px, desktop 1440px, mobile 375px) × 2 stati = 42 screenshot. Tema chiaro.</p>
"""

for chiave in page_order:
    if chiave not in pagine:
        continue
    p = pagine[chiave]
    html += f'<div class="page-section"><h2 class="page-title">{page_labels[chiave]}</h2>'
    html += '<div class="images-grid">'
    for device in device_order:
        if device not in p:
            continue
        for stato in ["prima", "dopo"]:
            label = f"{page_labels[chiave]} — {device_labels[device]} — {stato.capitalize()}"
            fname = f"{chiave}_{device}_{stato}.png"
            html += f'''
  <div class="img-wrap">
    <div class="img-label">{label}</div>
    <img src="{fname}" alt="{label}">
  </div>'''
    html += '</div>'

    # Table
    html += '<table><thead><tr>'
    html += '<th>Stato</th><th>Viewport</th><th>Larghezza main (px)</th><th>Caratteri/riga (mediana)</th>'
    html += '<th>Altezza (schermi)</th><th>Blocchi principali</th><th>Blocchi/schermo</th><th>Scroll orizz.</th>'
    html += '</tr></thead><tbody>'

    for device in device_order:
        if device not in p:
            continue
        for stato in ["prima", "dopo"]:
            m = p[device][stato]
            main_w = m.get("main_width", "n/d")
            cpl = m.get("cpl_mediana", "n/d")
            if cpl is None:
                cpl = "n/d"
            schermi = m.get("altezza_schermi", "n/d")
            blocchi = m.get("blocchi_principali", "n/d")
            bps = m.get("blocchi_per_schermo", "n/d")
            scroll = m.get("scroll_orizzontale", False)
            scroll_cls = "scroll-yes" if scroll else "scroll-no"
            scroll_txt = "SÌ" if scroll else "no"
            row_cls = "break" if scroll else ""
            html += f'<tr class="{row_cls}"><td>{stato.capitalize()}</td><td>{device_labels[device]}</td><td>{main_w}</td><td>{cpl}</td><td>{schermi}</td><td>{blocchi}</td><td>{bps}</td><td class="{scroll_cls}">{scroll_txt}</td></tr>'

    html += '</tbody></table></div>'

html += """
<div class="legend">
<p><strong>Legenda:</strong> "Larghezza main" = larghezza dell'elemento <main> (contenitore principale). "Caratteri/riga" = mediana caratteri per riga sui paragrafi di prosa (target 45–80). "Altezza (schermi)" = altezza pagina in unità viewport. "Blocchi principali" = figli diretti di <main> visibili. "Scroll orizz." = pagina più larga del viewport.</p>
<p>Righe evidenziate in giallo = scroll orizzontale presente (difetto).</p>
<p>Misure rilevate con Playwright/Chromium su https://divarioitalia.it, banner consenso chiuso, pausa 1s tra pagine.</p>
</div>
</body>
</html>
"""

out_path = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini/confronto.html")
out_path.write_text(html, encoding="utf-8")
print(f"Scritto {out_path}")