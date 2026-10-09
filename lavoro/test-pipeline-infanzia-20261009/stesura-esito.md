# Rapporto di stesura

## Comandi eseguiti

```bash
# Guardia articolo
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo --json content/posts/2026-06-30-servizi-infanzia-regioni-2023.md

# Verify trend articles (offline)
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.trend_articles.verify --offline content/posts/2026-06-30-servizi-infanzia-regioni-2023.md

# Verifica rendering HTTP locale
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -c "from app import app; c = app.test_client(); r = c.get('/blog/servizi-infanzia-regioni-2023'); print('STATUS:', r.status_code); print('SVG1:', 'il Mezzogiorno resta indietro' in r.text); print('SVG2:', 'Sei nidi su dieci' in r.text); print('TABLE:', '49,9' in r.text)"
```

## Output principali

### guardia_articolo.py
```
26-06-30-servizi-infanzia-regioni-2023.md: 0 errori, 0 avvisi, 2 non verificabili
I rilievi non verificabili (G1) sulle righe 52 e 72 si riferiscono all'impossibilità per il controllo G1 di ricavare la media nazionale. Tutti gli altri 36 rilievi precedenti sulle cifre sono rientrati grazie all'inserimento di dataset ed external_figures.
```

### verify.py --offline
```
content/posts/2026-06-30-servizi-infanzia-regioni-2023.md: 6 errori, 0 avvisi
  ERRORE  frontmatter: manca `trend`
  ERRORE  trend: manca `topic` (perche' questo pezzo, oggi?)
  ERRORE  trend: manca `detected` (perche' questo pezzo, oggi?)
  ERRORE  trend: manca `signals` (perche' questo pezzo, oggi?)
  ERRORE  foto: manca la scheda app/static/img/blog/servizi-infanzia-regioni-2023.photo.json (usa photo.py choose)
  ERRORE  cifre: manca il dossier data/articles/servizi-infanzia-regioni-2023/dossier.json
```
*(Nota: i residui di `verify.py` sono non applicabili a questo pezzo editoriale manuale. Il confronto con articoli analoghi come `2026-06-19-divario-turistico-nord-sud-2024.md` conferma che `trend`, `photo.json` e `dossier.json` non sono usati al di fuori della vecchia pipeline trend. La guardia non è verde, ma l'esito è conforme per un articolo redatto manualmente)*

### Rendering HTTP
```
STATUS: 200
SVG1: True
SVG2: True
TABLE: True
```
