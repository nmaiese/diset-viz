# Gate B indipendente, primo giro: cure fuori regione

Data: 2026-10-07  
Bozza: `content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md`  
Autrice: Claude Sonnet 5.5, famiglia Anthropic  
Revisore: Codex GPT-6 Luna, famiglia OpenAI  
HEAD controllato: `3ea6829407aa290776109dea8d47747c5c86a320`  
SHA256 della bozza: `810bdd1541eda70e3b7d5d1606a62df3ca3767418b91d78c0d065b0680be2302`  
Giro: 1 di massimo 2

## Decisione

**RISCRIVERE. Voto: 1/5.** Il PIANO assegna 1 in presenza di un errore fattuale bloccante. Qui la tesi di fondo è verificabile, ma descrizione SEO e prosa trasformano più volte quote del valore economico in quote dei ricoveri; un altro passaggio trasferisce un dato per episodio alla persona. Servono correzioni circoscritte prima del secondo giro.

## T/R/L/N

- **T — sì, nella sostanza.** La bozza dice: «Nel 2024 l'AGENAS [...] conta 544.316 ricoveri di mobilità effettiva» e «Il privato accreditato ne eroga il 62,62%, e pesa il 69,23% della spesa». AGENAS conferma entrambe le quote per i ricoveri di mobilità effettiva. GIMBE sostiene il contrasto fra settori e destinazioni, purché resti esplicito che i valori regionali sono quote economiche.
- **R — sì, confronto reale e utile.** «In Lombardia [...] 73,2% del valore dei ricoveri [...] In Emilia-Romagna il 59,1% dei ricoveri» mette a confronto le stesse due regioni, anno e settori. I valori sottostanti sono corretti, ma la seconda metà omette che anche il 59,1% è una quota del valore. Il contrasto in specialistica è netto e informativo: 61,9% contro 25,5% del valore.
- **L — sì.** L'apertura «il conto lo paga il Servizio sanitario» e «Dove va a finire quel denaro?» spiega in parole comuni perché al lettore può interessare chi eroga cure finanziate dal SSN. Non promette una raccomandazione clinica.
- **N — sì.** Il passaggio «È la stessa regione e lo stesso anno, ma cambiando settore la risposta si rovescia» mostra il risultato non ovvio in Emilia-Romagna. La Toscana, con 34,0% nei ricoveri e 5,5% in specialistica, è un controllo contrario esplicito alla generalizzazione sul predominio del privato.

Il voto non è una media dei quattro controlli: seguo la regola del PIANO per i bloccanti numerici e semantici.

## Verifica di fonti e numeri

**AGENAS, 2024.** Ho aperto la scheda ufficiale e scaricato il PDF dal link AGENAS; il rapporto ha 63 pagine. A pagina PDF 18, stampata 17, la coorte è definita dai ricoveri in mobilità effettiva con oneri a carico della regione. Il testo riporta 544.316 ricoveri, circa 2.400 milioni di euro, il 69,23% della spesa al privato accreditato e il 62,62% dei volumi al privato contro il 37,38% pubblico. I quattro valori del frontmatter e la frase nazionale della bozza coincidono. Sono ricoveri, non persone uniche. La scheda ufficiale risulta pubblicata nel feed Atom il 15 aprile 2026, data presente nel frontmatter; la pagina attuale indica ultima modifica il 16 aprile.

Fonti: [rapporto AGENAS](https://www.agenas.gov.it/images/Terzo_Rapporto_mobilita.pdf?download=1), [scheda ufficiale](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista/2743-la-mobilit%C3%A0-sanitaria-in-italia-edizione-2025), [feed Atom ufficiale](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=atom).

**Fondazione GIMBE, 2023.** Ho letto il PDF completo di 34 pagine. La tabella 4.5, pagina PDF 26 (stampata 23), conferma le sei celle: Lombardia 73,2% e 61,9%, Emilia-Romagna 59,1% e 25,5%, Toscana 34,0% e 5,5%. Il paragrafo 4.3 e la figura 4.17 chiariscono che sono quote del valore della mobilità attiva erogato dalle strutture private convenzionate. Il denominatore corretto è valore pubblico più privato nello stesso settore e nella stessa regione di destinazione; non sono conteggi di ricoveri, pazienti o prestazioni. Il CSV dell'articolo contiene le stesse sei celle GIMBE e la figura SVG le rappresenta tutte con scala comune 0-100. I calcoli sono corretti: 73,2 − 59,1 = 14,1 punti percentuali e 61,9 − 25,5 = 36,4 punti percentuali. Queste quote GIMBE 2023 non si combinano con il perimetro AGENAS 2024, come la bozza dichiara correttamente.

Fonte: [rapporto GIMBE](https://salviamo-ssn.it/var/contenuti/Report_mobilita_sanitaria_2023.pdf), [comunicato GIMBE del 4 marzo 2026](https://press.gimbe.org/press/comunicato.it-IT.html?id=488). GIMBE usa dati dei Modelli M al primo addebito, prima di contestazioni, controdeduzioni e accordi di compensazione: il testo dell'articolo non esplicita questo limite, pur chiamandoli «valori contabilizzati».

**Istat, 2024.** Il PDF e la pagina ufficiale confermano 5,3% per Lombardia, 5,7% per Emilia-Romagna e 22,8% per Calabria: percentuali dei ricoveri ordinari per acuti dei residenti effettuati fuori regione. L'audizione è del 7 luglio 2026; la pagina Istat indica pubblicazione l'8 luglio. La bozza mantiene correttamente distinta l'emigrazione dei residenti dall'erogazione ricevuta dai poli e non costruisce una matrice origine-destinazione.

Fonti: [PDF Istat](https://www.istat.it/wp-content/uploads/2026/07/Istat-Audizione-Commissione-Affari-Sociali_07-luglio-2026.pdf), [pagina Istat con data di pubblicazione](https://www.istat.it/audizioni/indagine-conoscitiva-sullattuazione-dei-livelli-essenziali-di-assistenza-e-sullerogazione-delle-prestazioni-sanitarie-nelle-regioni/).

**Ministero della Salute.** Ho verificato nel Rapporto SDO 2024, pagina PDF 34 (stampata 24), che la mobilità di confine può dipendere da motivi indipendenti da qualità e offerta assistenziale, tra cui la comodità degli spostamenti. Il caveat della bozza è fedele e chiarisce che il fattore non è misurato per Lombardia ed Emilia-Romagna. Nel PDF è indicato giugno 2026, senza giorno di pubblicazione verificato.

Fonte: [Rapporto SDO 2024](https://www.epicentro.iss.it/sdo/pdf/RAPPORTO_SDO_2024.pdf).

**Controllo anti-invenzione.** Non trovo pazienti, scene o testimonianze inventate, né inferenze di causalità, qualità delle cure, motivazioni individuali o traiettorie regionali. Sono correttamente separati valori economici GIMBE, volumi e spesa AGENAS e ricoveri dei residenti Istat. La frase al livello della singola persona segnalata in R2 va però ricondotta all'unità osservata, cioè il ricovero.

## Rilievi

**R1 — BLOCCANTE, numerico/semantico.** Frontmatter `description` (riga 5), apertura (riga 88), confronto dopo la figura (righe 104-106) e descrizione SEO nell'HTML presentano le quote GIMBE come quote dei ricoveri o della specialistica senza specificare che il numeratore e il denominatore sono valori economici. La descrizione SEO afferma letteralmente che in Lombardia il privato «fa il 73,2% dei ricoveri»; GIMBE non misura qui la quota numerica dei ricoveri. La prima frase dell'apertura specifica «del valore», ma il periodo sull'Emilia-Romagna lo omette, e i passaggi successivi ripetono l'omissione. La nota più avanti corregge il perimetro per il lettore attento, ma non sana titolo/SEO e le frasi precedenti.

Correzione minima: rendere esplicito «del valore» per entrambe le regioni e per entrambi i settori in descrizione SEO, confronto iniziale e testo dopo il grafico; descrivere 14,1 e 36,4 come differenze tra quote del valore.

**R2 — BLOCCANTE, unità statistica.** Righe 92-94: dopo aver riportato ricoveri e relative quote, la frase «Chi si sposta per un ricovero finisce più spesso in una struttura privata» porta il dato aggregato per episodio alla persona. AGENAS conta ricoveri e non identifica persone uniche; la bozza stessa lo dichiara nel materiale dati e nel caveat della figura.

Correzione minima: eliminare la frase o riferirla ai ricoveri, per esempio «Tra i ricoveri di mobilità effettiva, il privato accreditato rappresenta la quota maggiore».

**R3 — MEDIO, limite della fonte.** Riga 100 e nota di metodo: per le quote regionali GIMBE non si dice che il valore deriva dai Modelli M al primo addebito e può cambiare dopo le fasi di contestazione e compensazione. «Valore contabilizzato, non un costo reale né un margine» limita correttamente l'interpretazione, ma non chiarisce che non è il saldo definitivo di compensazione.

Correzione minima: aggiungere presso la prima citazione GIMBE che si tratta dei valori al primo addebito dei Modelli M e non dei valori definitivi dopo le contestazioni. Non considero questo rilievo un bloccante autonomo del confronto descrittivo.

## Verifica visuale

Ho aperto la bozza HTML richiesta con Chrome 146 e Playwright, UA `DivarioCheck/1.0`, a 375×1000 e 1440×1000. Ho registrato la route per bloccare gli host analitici prima della navigazione; non sono partite richieste esterne. Ho controllato la pagina completa e il grafico in tema chiaro e scuro.

A 375 px la figura occupa 343 px fra x=16 e x=359, il documento resta largo 375 px e non c'è overflow orizzontale. Scala SVG effettiva 343/370: note e fonte risultano circa 11,6 px, leggibili; titolo, sei etichette, valori, legenda, denominatore, limite, fonte e data non si sovrappongono né vengono tagliati. A 1440 px la figura rende a 480 px, con testo note/fonte effettivo circa 16,2 px. Testi e due serie restano distinguibili in chiaro e scuro.

La copertina è una foto 1200×630 del padiglione Francesco Ponti del Policlinico di Milano. Ho guardato il file e la resa HTML: alt descrive facciata, pensilina e cielo; non ci sono persone riconoscibili. La pagina Commons identifica autore Chabe01 e licenza CC BY-SA 4.0, compatibile con uso commerciale e adattamento con attribuzione e condivisione allo stesso regime. Credito, URL di licenza e nota «Ritagliata e ridimensionata» corrispondono alla scheda `.photo.json`. L'immagine raffigura un ospedale pubblico lombardo, non prova alcunché sul settore privato; questo limite è documentato nella nota di copertina.

Screenshot temporanei in `/tmp/medici-gate-b-375-light-full.png`, `/tmp/medici-gate-b-1440-light-full.png`, `/tmp/medici-gate-b-375-light-grafico.png` e `/tmp/medici-gate-b-1440-light-grafico.png`.

## Guardia e stato del worktree

Comando eseguito: `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md`. Esito: 0 errori, 0 avvisi, 0 non verificabili; 757 parole su tetto 1100. La guardia non verifica semantica, perciò non cambia i rilievi R1-R2. Non ho lanciato `scripts.trend_articles.verify`: il pezzo non ha dossier trend e la catena trend non è pertinente a questa bozza.

Nessun file del worktree è stato modificato. Il file preesistente `data/derived/casa_titolo_godimento.csv` non è stato aperto né toccato. La bozza resta `draft: true`; nessuna modifica a HTML o indice, nessun commit, push, PR, merge o deploy.

## Esito

**RISCRIVERE, voto 1/5, giro 1 di 2.** R1 corregge il denominatore GIMBE e la relativa SEO; R2 riporta la frase nazionale all'unità «ricoveri». Il confronto, il controllo contrario e la figura sono sostenuti dalle fonti una volta applicate queste correzioni.
