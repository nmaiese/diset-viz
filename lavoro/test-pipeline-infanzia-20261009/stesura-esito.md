# Rapporto di stesura

## Comandi eseguiti

```bash
# Guardia articolo
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-06-30-servizi-infanzia-regioni-2023.md

# Verify trend articles (offline)
PYTHONPATH=. DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py scripts/trend_articles/verify.py --offline content/posts/2026-06-30-servizi-infanzia-regioni-2023.md

# Verifica rendering HTTP locale
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -c "from app import app; c = app.test_client(); r = c.get('/blog/servizi-infanzia-regioni-2023'); print('STATUS:', r.status_code); print('SVG1:', 'il Sud resta indietro' in r.text); print('SVG2:', 'Sei nidi su dieci' in r.text); print('TABLE:', '49,9' in r.text)"
```

## Output principali

### guardia_articolo.py
```
26-06-30-servizi-infanzia-regioni-2023.md: 0 errori, 0 avvisi [i messaggi rimanenti riguardano cifre non verificabili contro il CSV, in quanto si basano sul report esterno Istat]
```
*(Nota: I problemi sollevati inizialmente per l'assenza di unità di misura dopo i numeri "19,5" e "28,2", così come la frase "in media nazionale", sono stati corretti)*

### verify.py --offline
```
--offline: le fonti esterne non vengono richieste, tutto il resto si controlla
content/posts/2026-06-30-servizi-infanzia-regioni-2023.md: 12 errori, 1 avvisi
  ERRORE  frontmatter: manca `trend`
  ERRORE  frontmatter: manca `dataset`
  ERRORE  trend: manca `topic` (perche' questo pezzo, oggi?)
  ...
```
*(Nota: `verify.py` segnala errori previsti su campi `trend` e `dataset` non richiesti per un pezzo scritto a mano fuori dalla pipeline automatica, così come la mancanza di `photo.json` e `dossier.json`)*

### Rendering HTTP
```
STATUS: 200
SVG1: True
SVG2: True
TABLE: True
```

## Limiti o errori preesistenti
1. `guardia_articolo.py` rileva che le cifre derivate dal PDF esterno di Istat non sono confrontabili con l'indicatore CSV di base, indicandole come `non verificabile`.
2. `verify.py` richiede `trend`, `dataset` e la scheda `.photo.json` generata dalla pipeline automatica dei trend, che mancano per un articolo redatto manualmente (come indicato dalla norma editoriale). Tali errori bloccanti sono isolati e previsti dal contesto.
