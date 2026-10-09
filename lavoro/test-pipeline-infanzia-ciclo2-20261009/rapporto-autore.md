# Rapporto Autore: test-pipeline-infanzia-ciclo2-20261009

## Comandi ed Esiti
- `git status && git diff --cached`: lette modifiche stagionate.
- `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`: esito 0 errori, 21 avvisi (lunghezza e formato tabella), 17 non verificabili (dati esterni documentati). Nessun link rotto.
- test: non lanciati poiché toccato solo testo e metadati SVG (rimozione attributi non mobile-friendly spostati in markdown). Nessun HTML/indice generato; test mirati eseguiti da C-DIV dopo il commit autore, con output riportato nel rapporto di pipeline.

## Lista Modifiche
- `seo_title` riportato sotto 60 caratteri.
- Rese esplicite le unità "ogni 100 bambini residenti di 0-2 anni" per le 4 cifre territoriali (39,1/36,6/19,0/19,5).
- Link a figura 3.6 sul PDF Istat/Ca’ Foscari inserito direttamente nel paragrafo del 28,9%.
- Rimosse le diciture fisse SVG da `posti-autorizzati.svg` e `domande-non-accolte.svg` (titoli e sottotitoli) trasportandole in markdown `###` nel corpo del testo, e ridotti i viewBox SVG verticali; la resa a 375px richiede verifica visiva indipendente; questa dichiarazione non è una prova.
- Ripristinato `app/static/img/blog/posti-autorizzati-2023.svg` per mantenere allineamento esatto con PNG cover preesistente come richiesto (PNG non rigenerato per assenza strumenti).

## Limiti
- Le avvertenze di `guardia_articolo` rimangono in quanto i dati si riferiscono al rapporto PDF esterno non incluso nel CSV principale.

## Verifica mobile pre-Gate B
- CSS mirato aggiunto in `<style>` all'interno del file markdown `2026-06-30-servizi-infanzia-regioni-2023.md`.
  - La caption della tabella è stata nascosta visivamente a max-width 719px mantenendola accessibile per gli screen reader (`clip: rect(0 0 0 0)` ecc).
  - Aggiunto scroll orizzontale nativo (`overflow-x: auto`) con istruzione testuale in `::before` per il contenitore `.article-figure` SVG a max-width 719px, imponendo all'SVG originario `min-width: 720px`.
- Comandi: script Node Playwright su 375 e 1100 viewport (temi chiaro/scuro). Controllo scroll `document.documentElement.scrollWidth > clientWidth` negativo a 375px.
- Esito test screenshot mobile salvato in `lavoro/test-pipeline-infanzia-ciclo2-20261009/prove-mobile/`. Nomi leggibili senza schiacciamenti.
- `updated` nel frontmatter visibile come 2026-10-09.

## Verifica C-DIV successiva al commit mobile
Lo screenshot dell'autore `test-table1-375-light.png` mostrava ancora la caption automatica. Il selettore `.art-body > .tablewrap:first-of-type caption` non corrispondeva al DOM renderizzato. C-DIV lo ha corretto in `.tablewrap .table--stack caption` nel CSS locale dell'articolo e ha verificato la pagina Flask con Playwright a viewport reale 375×812: caption presente nel DOM, `position:absolute`, larghezza resa 1 px; screenshot `prove-mobile/cdiv-table-375-light-fixed.png` senza caption visibile e con etichette delle card. Il documento misura 375/375 px (scrollWidth/clientWidth); la prima figura 720/343 px, quindi il grafico si scorre entro il proprio contenitore. Test indipendente eseguito sul render locale, senza pubblicazione.

### Correzione del preflight C-DIV
Il primo screenshot dell'autore non provava l'assenza della caption: `test-table1-375-light.png` la mostrava ancora. Inoltre il CSS in coda al Markdown faceva fallire `guardia_articolo` (16 errori tipografici). C-DIV ha rimosso lo `<style>` dal testo e spostato le stesse regole in `app/static/css/ds/pages/articolo.css`, con selettori limitati al `data-post-slug` del template v1; ha corretto anche il selettore della caption. Prova Playwright su Flask locale: a 375 px, temi chiaro e scuro, caption nel DOM ma `position:absolute` e larghezza 1 px, pagina 375/375 px, figura scorrevole 720/343 px, istruzione visibile. A 1100 px, nei due temi, caption normale e figura 545/545 px senza istruzione. Screenshot corretti: `prove-mobile/cdiv-table-375-light-fixed.png` e `prove-mobile/cdiv-table-375-dark-fixed.png`. `guardia_articolo`: 0 errori, 21 avvisi, 17 non verificabili; test mirati: 23 OK. Le immagini `test-table1-375-*.png` restano prova del difetto riscontrato, non dell'esito corretto.
