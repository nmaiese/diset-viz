# Verifica indipendente, secondo Gate B: medici di famiglia v2

Bozza: `content/posts/2026-10-07-medici-di-famiglia-regioni.md`, HEAD esaminato `f1eaf08563fcc3a0995500a49d0e89bb1c855355`, SHA-256 `ee6ddf9166bdcb538d50608d3184ee07d682b383dbf8efb36e3bdf307653acea`. Ho letto il primo Gate B (`b8b1cdc5`), il diff da `4c01ebae`, il rapporto dell'autore, brief, Gate A ter, numeri, fonti, bozza, SVG e i PNG a 375 e 1100 px. Il rapporto dell'autore non è prova dei numeri.

## Ricalcolo indipendente

Ho letto direttamente `app/static/data/Assoluti_BES_Regione.csv` e `app/static/data/Assoluti_Multiscopo_Regione.csv`: `Anno=2023`, `Area=Regione`, `Livello/Variazione=Livello`, separatore `;`, virgole decimali convertite. Venti regioni, incluso Trentino-Alto Adige aggregato. Rho di Spearman = correlazione dei ranghi medi in caso di parità, senza pesi; nessun import degli script `calcola*.py` o del CSV dell'articolo.

| Cella o primato della bozza | Sorgente 2023 | Verifica |
| --- | ---: | --- |
| Lombardia, medici oltre 1500 (r. 112) | 74,0% | massimo |
| Molise, medici oltre 1500 (r. 112) | 21,6% | minimo |
| Molise, dimissioni fuori regione (r. 116) | 32,6% | massimo, quota di dimissioni ordinarie per acuti |
| Lombardia, dimissioni fuori regione (r. 116) | 5,1% | minimo |
| Lombardia e Molise, utenti ASL con fila oltre 20 minuti (r. 118) | 47,1% e 67,6% | quote di utenti, non durata o attesa clinica |
| Sardegna, medici oltre soglia e dimissioni (r. 134) | 60,6% e 7,1% | primo valore massimo nel Mezzogiorno |
| Sardegna, rinunce (r. 136) | 13,7% | massimo regionale |
| Lombardia e Molise, uso del pronto soccorso (r. 142) | 64,8 e 39,8 per mille | stessa unità nel testo e nel CSV |

| Coppia con medici oltre soglia | Rho N=20 | Rho N=18, senza Lombardia e Molise | Valori nel testo |
| --- | ---: | ---: | --- |
| Dimissioni fuori regione | -0,503197 | -0,318018 | -0,50; -0,32: corretti |
| Fila ASL oltre 20 minuti | -0,547368 | -0,514964 | -0,55; -0,51: corretti |
| Uso pronto soccorso | +0,422556 | +0,360165 | +0,42; +0,36: corretti |
| Rinunce, controllo aggiuntivo | -0,217375 | -0,161074 | «nessun ordinamento comune evidente» è prudente |

Il rapporto nazionale 51,7/15,8 = 3,27 conferma «più che triplicata» (r. 148); i due valori Italia 2004 e 2023 sono in `data/derived/bes_areas_12SER027.csv`, non sono medie aritmetiche regionali. Il CSV scaricabile ora include tutte le 20 celle regionali di pronto soccorso: rilievo precedente chiuso. Confronto completo con i CSV sorgente: nessuna discrepanza non spiegata; il 20,5 della fila ASL in Trentino-Alto Adige arrotonda il valore grezzo 20,464645.

## Rilievi del primo Gate B e limiti del Gate A ter

- **R1 chiuso**, r. 110: «Se il tuo medico...» formula un'ipotesi, non deduce un individuo dalla quota regionale. R. 152 non ripete più la deduzione.
- **R2 chiuso**, r. 148 e 150: la misura è percentuale di medici oltre soglia, quella ospedaliera è quota di dimissioni; non diventano conteggi di liste o persone.
- **R3 chiuso**, r. 126 e titolo SVG: «tende a essere più bassa», con -0,32 vicino nel paragrafo successivo. Anche fila e pronto soccorso sono descritti come tendenze, con rho e unità coerenti.
- **R4 parzialmente chiuso**, SVG e PNG: le etichette sono ridotte a sei; il groviglio di nomi del primo giro è risolto. A 1100 px nomi, estremi e assi sono distinguibili. A 375 px la nota sulla legenda e la fonte sono ancora microscopiche: nel CSS hanno `font-size: 10.5px` in coordinate SVG su `viewBox` largo 680, cioè circa 5,8 px alla larghezza 375. La regola mobile dell'SVG aumenta titolo, sottotitolo, assi e nomi, ma omette `.fig__note` e `.fig__source`. Il PNG conferma che non si leggono. Fonte e distinzione cerchi/quadrati sono essenziali per interpretare il grafico; resta un bloccante visivo.
- **Altri rilievi**: r. 134 limita il caso Sardegna senza inferire una regola Nord-Sud; r. 142 mantiene «persone ogni mille»; r. 150 nomina la quota di dimissioni. R. 136 ripete «circa una persona su sette, il 13,7%»: duplicazione stilistica residua, non errore numerico.

I cinque limiti del Gate A ter sono sostanzialmente presenti: (1) quote e unità corrette; (2) dimissioni, fila e rinunce con denominatori e significato distinti; (3) r. 124 dichiara 78 coppie esplorate, scelta successiva, cronologia dei controlli non provata e anni non indipendenti; (4) r. 130 e 142 portano N=18 e segno opposto del pronto soccorso; (5) r. 148 e 152 dicono che il singolo dato non misura come si cura una regione. Le frasi su verso e primati alle righe 112, 116, 118, 126, 130, 134, 136, 138, 142 e 148 reggono al controllo delle serie. Le frasi «Perché sia così...» (r. 120 e 136) e «Perché le due misure...» (r. 144) dichiarano ignoto il meccanismo. Nessuna persona reale inventata, nessuna causa o significatività attribuita ai rho.

T/R/L/N: **sì/sì/sì/sì**. T, r. 110 e 148: il numero isolato non basta. R, r. 116: Molise 32,6% contro Lombardia 5,1% sposta il racconto. L, r. 110: domanda pratica nel lead. N, r. 130 e 142: fragilità senza estremi e pronto soccorso con segno opposto. La prosa resta più informativa che elegante, ma non è una lista di soli coefficienti.

## Fonti, collegamenti, ulteriori rilievi

Il 7 ottobre 2026 `curl -L` ha restituito HTTP 200 per [appendice Istat](https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip), [Data Browser Istat](https://esploradati.istat.it/databrowser/#/it), [foto su Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Ambulatorio_medico_Albonese_01.jpg) e i sei link interni alle tre schede e a Lombardia, Molise e Sardegna. La pagina Commons contiene Fabiocrotti67 e CC0 1.0. HTTP 200 non verifica i dati della pagina; il browser Istat richiede JavaScript e lo ZIP non è stato aperto. Le definizioni e le unità sono state confrontate con `fonti.md` e le intestazioni/righe dei CSV sorgente.

Righe 84-99 del frontmatter: i rho che usano fila ASL e pronto soccorso hanno anche dati Multiscopo, ma `source` e `url` indicano solo l'appendice BES. Anche `dataset.source_url` (r. 29) indica solo BES benché il download contenga due serie Multiscopo. Aggiungere una citazione alla fonte Multiscopo per tracciabilità. Riga 7: `draft: false`, mentre la regola della skill redazionale chiede di lasciare la bozza in draft e la PR è ancora draft; correggere prima di qualsiasi merge.

## Controlli automatici e non verificato

`DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-10-07-medici-di-famiglia-regioni.md` si interrompe prima della guardia con `ModuleNotFoundError: No module named 'PIL'` importando `scripts/trend_articles/photo.py`; nessun esito verde riprodotto in questo worktree. `git diff --check` esce 0, con solo avviso CRLF sul file estraneo `data/derived/casa_titolo_godimento.csv`, lasciato intatto. Non ho verificato la bozza HTML in browser, i microdati o i pesi Multiscopo, l'incertezza campionaria, le cause regionali, la cronologia dei controlli né la riconciliazione delle celle locali con lo ZIP primario.
