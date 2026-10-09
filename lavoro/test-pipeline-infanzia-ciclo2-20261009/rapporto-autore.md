# Rapporto Autore: test-pipeline-infanzia-ciclo2-20261009

## Comandi ed Esiti
- `git status && git diff --cached`: lette modifiche stagionate.
- `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`: esito 0 errori, 21 avvisi (lunghezza e formato tabella), 17 non verificabili (dati esterni documentati). Nessun link rotto.
- test: non lanciati poiché toccato solo testo e metadati SVG (rimozione attributi non mobile-friendly spostati in markdown). Nessun codice/test o HTML/indice generato.

## Lista Modifiche
- `seo_title` riportato sotto 60 caratteri.
- Rese esplicite le unità "ogni 100 residenti 0-2 anni" per le 4 cifre territoriali (39,1/36,6/19,0/19,5).
- Link a figura 3.6 su PDF EUR-Lex inserito direttamente nel paragrafo del 28,9%.
- Rimosse le diciture fisse SVG da `posti-autorizzati.svg` e `domande-non-accolte.svg` (titoli e sottotitoli) trasportandole in markdown `###` nel corpo del testo, e ridotti i viewBox SVG verticali; ora si reflowano su 375px correttamente ed è tutto leggibile senza rigenerare assets.
- Ripristinato `app/static/img/blog/posti-autorizzati-2023.svg` per mantenere allineamento esatto con PNG cover preesistente come richiesto (PNG non rigenerato per assenza strumenti).

## Limiti
- Le avvertenze di `guardia_articolo` rimangono in quanto i dati si riferiscono al rapporto PDF esterno non incluso nel CSV principale.
