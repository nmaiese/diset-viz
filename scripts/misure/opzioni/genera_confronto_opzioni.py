"""Genera confronto.html (immagini prima/A/B/C affiancate + tabella di misure) da misure_opzioni.json."""
import html
import json
from pathlib import Path

OUT = Path("/mnt/c/Users/Nilo/orca/direzione/review/ux-opzioni")
dati = [r for r in json.loads((OUT / "misure_opzioni.json").read_text(encoding="utf-8")) if "errore" not in r]
idx = {(r["pagina"], r["device"], r["stato"]): r for r in dati}

PAGINE = [("home", "Home"), ("regione", "Regione (Molise)"), ("articolo", "Articolo"), ("scheda", "Scheda indicatore")]
DEVICE = {"desktop": "1440 px", "desktop1920": "1920 px", "mobile": "375 px"}
STATI = ["prima", "A", "B", "C"]
NOME = {"prima": "Prima", "A": "A solo larghezza", "B": "B larghezza e lettura", "C": "C = B + home meno densa"}


def stato_eff(pagina, s):
    return "B" if (s == "C" and pagina != "home") else s


def m(pagina, dev, s):
    return idx.get((pagina, dev, stato_eff(pagina, s)))


def cella(v):
    return "-" if v is None else html.escape(str(v))


def tabella(pagina):
    righe = [("Contenitore a 1440 px (px)", "desktop", "larghezza_contenitore"),
             ("Contenitore a 1920 px (px)", "desktop1920", "larghezza_contenitore"),
             ("Caratteri per riga della prosa (mediana, 1440)", "desktop", "cpl_mediana"),
             ("Altezza della pagina (schermi, 1440)", "desktop", "altezza_schermi"),
             ("Blocchi principali (figli di main)", "desktop", "blocchi"),
             ("Link ogni 3 schermi (grezzo)", "desktop", "link_per_3schermi"),
             ("Parole ogni 3 schermi", "desktop", "parole_per_3schermi"),
             ("Altezza della pagina (schermi, 375 mobile)", "mobile", "altezza_schermi")]
    out = ["<table><thead><tr><th>Misura</th>" + "".join(f"<th>{NOME[s]}</th>" for s in STATI) + "</tr></thead><tbody>"]
    for etichetta, dev, chiave in righe:
        celle = []
        for s in STATI:
            r = m(pagina, dev, s)
            celle.append(cella(r.get(chiave) if r else None))
        if all(c == "-" for c in celle):
            continue
        if chiave == "cpl_mediana" and pagina == "home":
            celle = ["n.a. (poca prosa)"] * 4
        out.append(f"<tr><th>{etichetta}</th>" + "".join(f"<td>{c}</td>" for c in celle) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def immagini(pagina, dev):
    figs = []
    for s in STATI:
        eff = stato_eff(pagina, s)
        f = f"{pagina}_{dev}_{eff}.png"
        if not (OUT / f).exists():
            continue
        nota = " (uguale a B: la C cambia solo la home)" if eff != s else ""
        figs.append(f'<figure><figcaption>{NOME[s]}{nota}</figcaption><img src="{f}" alt="{html.escape(pagina)} {dev} {NOME[s]}" loading="lazy"></figure>')
    return '<div class="riga">' + "".join(figs) + "</div>"


css = """
body{font:16px/1.5 system-ui,sans-serif;margin:0;padding:24px;color:#121519;background:#fff}
h1{font-size:28px}h2{margin-top:48px;border-top:2px solid #121519;padding-top:12px}h3{margin:24px 0 8px}
table{border-collapse:collapse;margin:12px 0;font-size:14px}th,td{border:1px solid #ccd;padding:4px 8px;text-align:left;vertical-align:top}
thead th{background:#eef}
.riga{display:flex;gap:12px;align-items:flex-start;overflow-x:auto}
figure{margin:0;flex:1 1 0;min-width:240px}figcaption{font-weight:600;font-size:14px;margin-bottom:4px}
img{max-width:100%;height:auto;border:1px solid #ccd}
.nota{background:#fff8e6;border:1px solid #e0c060;padding:8px 12px;max-width:80ch}
"""
h = ['<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Tre opzioni di impianto</title><style>' + css + "</style></head><body>",
     "<h1>Tre opzioni di impianto: prima, A, B, C</h1>",
     '<p class="nota">Pagine vere di produzione fotografate con un foglio di prova: il sito non è stato toccato. A = solo larghezza (1200 px). B = 1120 px, colonna di testo, ritmo unico. C = B e, solo in home, due blocchi nascosti per vedere come starebbe una home meno densa: è un\'anteprima, non una proposta di cancellazione. La home «a caso» cambia a ogni visita: le altezze fra dispositivi diversi non sono confrontabili, quelle fra Prima/A/B/C dello stesso dispositivo sì.</p>']
for pagina, titolo in PAGINE:
    h.append(f"<h2>{titolo}</h2>")
    h.append(tabella(pagina))
    for dev, lab in DEVICE.items():
        if not any((pagina, dev, s) in idx for s in STATI):
            continue
        h.append(f"<h3>{lab}</h3>")
        h.append(immagini(pagina, dev))
h.append("</body></html>")
(OUT / "confronto.html").write_text("\n".join(h), encoding="utf-8")
print("scritto", OUT / "confronto.html")
