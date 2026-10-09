# Esito test pipeline infanzia 20261009

I rilievi del preflight C-DIV sono stati corretti (il Gate B non è ancora stato eseguito):
1. Copertina: creato nuovo asset SVG `posti-autorizzati-2023.svg` con i dati aggiornati e aggiornati i tag `cover` e `cover_alt`. L'asset originario è stato conservato.
2. Definizione ter-414: modificata l'introduzione e il link finale, chiamando la misura "presa in carico di tutti gli utenti", senza restringere il perimetro ai soli servizi comunali.
3. Fonti esterne: aggiornato il link UE a Consilium, e aggiunta la sezione Fonti alla fine del testo con i link corretti separando la Commissione Europea dalle dinamiche italiane locali.

Il file CSV è stato corretto rinominando la colonna in `Totale posti per 100 residenti` e specificando la natura del calcolo in `dataset.method`.

`guardia_articolo --json` passa con 0 errori, 0 avvisi, e 2 non verificabili per le medie. `verify.py --offline` riporta sei errori (manca trend, photo.json, dossier.json) ma, da indicazioni, questi file non vanno fabbricati per questo test e verify.py viene dichiarato non verde.

Comando prova di rendering:
`PYTHONPATH=. DIVARIO_PYTHON=.../.venv/bin/python bin/py screenshot_test.py` (con server Flask locale e Google Chrome headless a 375x1100 px).
Output prova rendering e dimensioni raster:
- Nuova copertina rasterizzata: `app/static/img/blog/posti-autorizzati-2023.png` (48383 bytes)
- Screenshot mobile generato con successo.
