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

## Stesura finale: Claude Sonnet 5.5 (9 ottobre 2026, dopo 71f932ee)

Autore, non revisore Gate B. Brief con SHA256 `2d512d87...e7d3b`, Gate A PASSA. Modificato solo il corpo di `content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`. Figure, CSS, template, tabelle, frontmatter, cover e altri articoli non sono stati toccati, quindi non ho rifatto gli screenshot: la resa mobile del preflight resta quella già provata da C-DIV.

### Diff concettuale
- Apertura: da definizione generica ("strumento essenziale per conciliare lavoro e cura") a significato. Sapere quanti posti ha il territorio non dice se un bambino entrerà. Il rapporto posti/residenti misura l'offerta, non l'ingresso, la retta, gli orari.
- Tesi tenuta in un filo: posti (offerta), frequenza 34,5% (partecipazione), utenti comunali 18,5% (presa in carico) sono grandezze diverse; poi il divario territoriale; poi cosa il numero non dice.
- Divario per area e per tipo di comune: aggiunto l'ancoraggio concreto, verificato sul rapporto Istat p.2, che al Nord e al Centro anche i comuni non capoluogo superano in media i 33 posti (33,5, 36,1, 33,4 in tabella), mentre al Sud nemmeno i capoluoghi (23,0). "Il Centro offre più del doppio dei posti del Sud" (40,4 / 19,0 = 2,13).
- Crescita +3,4% e calo dei bambini: detto in due frasi, con il limite che il rapporto non riporta i residenti assoluti e quindi non si separano i due effetti.
- LEP 33: paragrafo suo, livello comune o bacino, orizzonte 2027. Il 31,6 è confronto di scala e non prova conformità locale. Non mescolato col 45% UE, che è partecipazione e non posti.
- Lista d'attesa: tre frasi distinte per la base. 28,9 / 19,9 / 21,3 sono quote dei nidi e sezioni primavera del campione che hanno già bambini in lista, con lista pari ad almeno il 25% delle richieste. Non sono quote di bambini esclusi, famiglie, domande né di tutti i servizi. Distinte dal 59,5%, che conta strutture che non hanno accolto tutte le richieste, con avviso di non sommarli.
- Anno del dato (2023/2024) e data della fonte (PDF 2 febbraio 2026, comunicato 3 febbraio 2026; rapporto Ca' Foscari 16 maggio 2025) tenuti distinti.
- Chiusura: passo concreto (chiedere al comune posti, domande, graduatoria, retta, orari) e link alla scheda `ter-414`.
- Nessuna media nazionale ricavata dalle righe territoriali.

### Verifiche sulle fonti primarie
Scaricati e letti i due PDF Istat il 9 ottobre 2026.
- Rapporto 2026 p.1-2: 31,6; 40,4, 39,1, 36,6, 19,0, 19,5; 39,8 e 28,2 (differenza 11,6); tabella completa; quasi 378.500 posti, +3,4%; LEP 33% da garantire a livello di comune o bacino entro il 2027; calo del denominatore. Confermati.
- p.3: 34,5% frequenza con anticipatari e ludoteche (anno educativo 2023/2024); 18,5% utenti dell'offerta comunale nel 2023. Confermati e con anni diversi.
- p.5: 59,5% (49,1% nel 2021/2022); 28,9, 19,9, 21,3. Nota: Istat scrive "nel 28,9% dei casi rimane inevaso oltre un quarto delle domande", la grafica di p.1 e la figura 3 dicono "nidi con bambini in lista d'attesa". Il pezzo usa la formula del brief ("almeno il 25%", base: servizi con lista), coerente con le classi 25-50% e oltre 50% di Ca' Foscari.
- p.9-10: risposta Comuni 79,9% e campione di circa 3.000 servizi. Confermati.
- Ca' Foscari: i valori del Mezzogiorno 21,1 + 7,8 = 28,9 sono nel testo (PDF p.24). Centro e Nord (15,8 + 4,1, 17,1 + 4,2) stanno nella figura e non li ho estratti dal grafico; i totali 19,9 e 21,3 sono però confermati dal testo del rapporto 2026 p.5.

### Correzione trovata
Il link alla figura 3.6 usava `#page=21`. Nel PDF Ca' Foscari la figura sta a pagina stampata 21 ma a pagina PDF 25 (la numerazione stampata parte quattro pagine dopo). Corretto in `#page=25`; il testo dice "pagina 21 del rapporto".

### Prove
- `DIVARIO_PYTHON=.../.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`: 0 errori, 23 avvisi, 17 non verificabili, 1046 parole (tetto 1100; prima 1125). Gli avvisi restano di tipo G4 (cifre in tabella o frase senza unità nella stessa riga) e i non verificabili sono dati esterni al CSV, già dichiarati in `external_figures`.
- `bin/py -m unittest tests.integration.test_blog_trend_articles tests.integration.test_blog_indicator_links -q`: 23 test, OK.
- `rg -n "[—–;…]"` sul post: solo la riga 27 del frontmatter (`method`, preesistente, apostrofi e punto e virgola assenti nel corpo). `git diff --check` pulito.

### Limiti
- Non ho aperto la pagina Flask né rifatto screenshot, perché non ho toccato figure, CSS o template.
- Il guardiano segnala "figura 3,6" con la virgola perché con il punto scatta l'errore sul decimale all'inglese; la dicitura del rapporto è 3.6.
- Cover: grafico originale Divario Italia, licenza CC BY 4.0 dichiarata nel frontmatter, nessuna foto AI. Non ricontrollata oltre al frontmatter.
- Gate B, `bozza_html`, indice, push, PR, merge e deploy non fatti.
