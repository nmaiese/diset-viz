# Gate B indipendente, secondo e ultimo giro: cure fuori regione v3

Data: 2026-10-07  
Worktree: `/home/nilo/dev/sites/divarioitalia/.orca/worktrees/divarioitalia/divario-medici-gate-b`  
Ramo: `divario/medici-gate-b`  
HEAD: `a770e9ea0b6de97fb0b63697c84292459f12cf82` (atteso)  
SHA-256 articolo: `986e5b7d6bd2ddf7bd71c5e2f59333c96dc52638dac1cbf01b626f9e993ca87b`  
SHA-256 HTML: `56d70b40198dd32534158600480411a0b14afe56dffa9142c0f7283483e30a8c`  
Autrice: Claude Sonnet 5.5. Revisore: Codex GPT-6 Luna. Giro: 2 di 2.

## Decisione

**PASSA, voto 4/5, zero bloccanti.** R1, R2 e R3 sono chiusi sul significato delle misure e sui limiti. T/R/L/N passano; restano solo rilievi di stile e una piccola lacuna di copertura del CSV, descritti sotto. L'articolo resta `draft: true`; nessuna pubblicazione o promozione.

## T/R/L/N

- **T — sì.** AGENAS sostiene la prevalenza nazionale del privato accreditato nella coorte 2024 di mobilità effettiva. GIMBE documenta differenze fra destinazioni e settori nel 2023, sempre come quote del valore. Il testo non trasforma queste composizioni in cause o giudizi di qualità.
- **R — sì.** Lombardia ed Emilia-Romagna sono confrontate nello stesso anno e nello stesso perimetro GIMBE, con i due settori separati. Le differenze di 14,1 e 36,4 punti percentuali sono ricalcolate sulle quote pubblicate. Istat sui residenti in uscita resta distinto dai dati GIMBE sui poli che ricevono.
- **L — sì.** I primi due paragrafi spiegano la posta in gioco in parole comuni: il SSN paga cure erogate altrove, e il lettore vede come varia la ripartizione fra strutture pubbliche e private.
- **N — sì.** In Emilia-Romagna il privato supera metà del valore dei ricoveri ma resta al 25,5% della specialistica; Toscana, con 34,0% e 5,5%, è un controllo contrario esplicito. Il confronto non pretende di rappresentare tutte le destinazioni.

## Rilievi R1-R3

- **R1 — chiuso.** Ho verificato la description Markdown e quella effettiva nell'HTML, inclusi i metadati SEO/Open Graph. Le quote GIMBE sono esplicitamente quote del valore per entrambe le regioni e per entrambi i settori. Il lead e i passaggi dopo la figura ripetono la stessa unità; 14,1 e 36,4 sono indicati come punti percentuali fra quote del valore, non come differenze di volumi.
- **R2 — chiuso.** AGENAS conta ricoveri, non persone uniche. La bozza parla della quota dei ricoveri di mobilità effettiva e della quota della spesa, senza dedurre dove finiscano individui. Il riferimento ai ricoveri dei residenti Istat non viene trasformato in una matrice di destinazione.
- **R3 — chiuso sul contenuto e sulla posizione.** Alla prima menzione GIMBE, prima della figura, il testo specifica Modelli M al primo addebito, prima di contestazioni e compensazione, con possibile variazione e assenza di saldo definitivo. La nota successiva chiarisce che il valore contabilizzato non è costo reale né margine. Resta una coordinazione un po' ambigua in «Usa i valori ... e possono quindi cambiare»: il soggetto passa da GIMBE ai valori senza ripeterli. È rilievo grammaticale/stilistico non bloccante; una frase separata renderebbe il passaggio più netto.

## Claim table

| Claim dell'articolo | Fonte | Periodo | Territorio | Unità | Trasformazione | Limite dichiarato |
|---|---|---|---|---|---|---|
| 544.316 ricoveri di mobilità effettiva, circa 2,4 miliardi di euro | [AGENAS, terzo rapporto, PDF p. 18 (stampata 17)](https://www.agenas.gov.it/images/Terzo_Rapporto_mobilita.pdf?download=1) | 2024 | Italia | ricoveri; euro | Nessuna; “circa” riprende l'arrotondamento AGENAS | Ricoveri finanziati dalle regioni nella sola mobilità effettiva; non persone uniche, esclusi casi casuali e apparenti |
| Privato accreditato: 62,62% dei ricoveri e 69,23% della spesa | AGENAS, stesso PDF p. 18 | 2024 | Italia | percentuale dei ricoveri; percentuale della spesa | Quote riportate dalla fonte | Coorte effettiva soltanto; perimetro e anno diversi da GIMBE |
| Lombardia: 73,2% ricoveri e 61,9% specialistica; Emilia-Romagna: 59,1% e 25,5%; Toscana: 34,0% e 5,5% | [Fondazione GIMBE, rapporto 1/2026, tabella 4.5, PDF p. 26 (stampata 23)](https://salviamo-ssn.it/var/contenuti/Report_mobilita_sanitaria_2023.pdf) | 2023 | Regioni di destinazione | percentuale del valore economico | Quote riportate dalla fonte, non conteggi di attività | Mobilità attiva; denominatore è valore pubblico più privato nello stesso settore e nella stessa destinazione. Modelli M al primo addebito, non saldo definitivo, costo reale o margine |
| Lombardia meno Emilia-Romagna: 14,1 punti nei ricoveri e 36,4 nella specialistica | Calcolo sulle sei quote GIMBE sopra | 2023 | Lombardia ed Emilia-Romagna | punti percentuali | 73,2 − 59,1 = 14,1; 61,9 − 25,5 = 36,4 | Differenza descrittiva fra quote economiche, non differenza fra pazienti né effetto causale |
| Ricoveri fuori regione: Lombardia 5,3%, Emilia-Romagna 5,7%, Calabria 22,8% | [Istat, audizione LEA, PDF p. 18](https://www.istat.it/wp-content/uploads/2026/07/Istat-Audizione-Commissione-Affari-Sociali_07-luglio-2026.pdf) | 2024 | Regioni di residenza | percentuale dei ricoveri dei residenti | Quote riportate dalla fonte | Ricoveri per acuti in regime ordinario; descrive chi esce, non gli erogatori di destinazione né la traiettoria individuale |
| Scheda correlata generata nell'HTML: media semplice 12,6% | `app/static/data/Assoluti_BES_Regione.csv`, indicatore `12SER025` | 2024 | 20 regioni | media di percentuali regionali | Media aritmetica delle 20 celle a un decimale: 12,580%, resa 12,6% | Non è una media nazionale; il riepilogo HTML la chiama correttamente media semplice delle regioni con dato |
| La mobilità di confine può riflettere anche la comodità degli spostamenti | [Ministero della Salute, Rapporto SDO 2024, PDF p. 34 (stampata 24)](https://www.epicentro.iss.it/sdo/pdf/RAPPORTO_SDO_2024.pdf) | Rapporto sui ricoveri 2024; caveat generale | Italia, mobilità di confine | affermazione qualitativa | Nessuna | Il rapporto non misura tale fattore specificamente per Lombardia o Emilia-Romagna; l'articolo lo dichiara |

### Ricalcolo e allineamento degli artefatti

Ho scaricato e letto direttamente le fonti primarie/di fonte. Il PDF GIMBE scaricato ha SHA-256 `a2beff6f59f72cc68d63d8999196f0c9f4b7b98f2b7979acfc6a15525ecedcf4`, uguale all'hash già registrato nel brief. La tabella GIMBE, il CSV, l'SVG e la prosa concordano su tutte e sei le quote. Ricalcolo: 73,2 − 59,1 = 14,1; 61,9 − 25,5 = 36,4.

Il PDF AGENAS p. 18 mostra 544.316 ricoveri, circa 2.400 milioni di euro, 62,62% dei volumi e 69,23% della spesa. Ho controllato anche il PDF Istat citato, che conferma 5,3%, 5,7% e 22,8%, e il Rapporto SDO, p. 34, che descrive la mobilità di confine e la comodità degli spostamenti.

Render Chrome dei PDF locali: `/tmp/medici-v3-agenas-p18-browser.png`, `/tmp/medici-v3-gimbe-p26-browser.png`, `/tmp/medici-v3-sdo2024-p34-browser.png`.

Ho ricontrollato anche le date riportate nelle fonti dell'articolo: il [feed Atom ufficiale AGENAS](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=atom) data la scheda al 15 aprile 2026, mentre la pagina mostra ultima modifica 16 aprile. La [pagina Istat ufficiale](https://www.istat.it/audizioni/indagine-conoscitiva-sullattuazione-dei-livelli-essenziali-di-assistenza-e-sullerogazione-delle-prestazioni-sanitarie-nelle-regioni/) indica pubblicazione 8 luglio 2026 e audizione 7 luglio.

Il CSV contiene 14 righe: sei quote GIMBE, tre valori AGENAS (544.316 e le due percentuali), tre quote Istat e le due differenze calcolate. Non contiene il valore AGENAS di circa 2,4 miliardi, benché l'ultima frase dell'articolo dica in generale che «i numeri di questo pezzo si scaricano in CSV». Il dataset è descritto come selezione di quote, quindi non blocca il Gate B; conviene aggiungere il valore o restringere la promessa di completezza del link CSV.

## HTML e prova visuale

Ho ricontrollato l'hash dell'HTML prima della navigazione. Ho aperto il file locale con Google Chrome 146 / Playwright. Prima di `goto` ho installato un route handler che consente soltanto risorse `file:`, `data:`, `blob:` e `about:`, abortendo ogni altra richiesta; non sono state tentate richieste esterne (`blockedExternalRequests: []`). Il file si è caricato con assets incorporati.

- Viewport 375×1000, temi chiaro e scuro: documento 375 px, nessun overflow orizzontale. Figura 343 px; fonte e note a 11,59 px effettivi, leggibili, senza testo fuori dal viewBox, sovrapposizioni o tagli.
- Viewport 1440×1000, temi chiaro e scuro: documento 1440 px, nessun overflow. Figura 480 px; fonte e note a 16,22 px effettivi. Quote, legenda, denominatore, caveat, fonte e data restano leggibili in entrambi i temi.
- Copertina: foto 1200×630 caricata, ritaglio coerente con il padiglione Francesco Ponti del Policlinico di Milano; nessuna persona visibile. Alt descrive la facciata, la pensilina e il cielo. Credito HTML/frontmatter e scheda foto concordano. La [pagina Commons](https://commons.wikimedia.org/wiki/File:Pavillon_Francesco_Ponti_Polyclinique_Milan_-_Milan_(IT25)_-_2022-09-02_-_2.jpg) attribuisce l'opera a Chabe01 e conferma CC BY-SA 4.0. La foto raffigura un ospedale lombardo pubblico e non prova la quota del privato.

Screenshot di verifica, temporanei e fuori dal worktree: `/tmp/medici-v3-gate-b-375-light-figure.png`, `/tmp/medici-v3-gate-b-375-dark-figure.png`, `/tmp/medici-v3-gate-b-1440-light-figure.png`, `/tmp/medici-v3-gate-b-1440-dark-figure.png`, `/tmp/medici-v3-gate-b-375-light-cover.png`, `/tmp/medici-v3-gate-b-1440-light-cover.png`.

## Guardia, stile e stato

Comando: `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md`. Esito: 0 errori, 0 avvisi, 0 non verificabili; 817 parole su tetto 1.100. `draft: true` presente. Il controllo dei caratteri vietati `[—–;…]` sul testo ha restituito nessuna corrispondenza.

Rilievi non bloccanti:
1. La description effettiva HTML è lunga 243 caratteri, sopra i 150–160 indicati in `content/STYLE.md`.
2. La coordinazione grammaticale del caveat R3 lascia implicito il passaggio dal soggetto GIMBE ai valori.
3. CSV e formula «i numeri di questo pezzo» hanno copertura non perfettamente allineata per i circa 2,4 miliardi AGENAS.

Non ho ripetuto la suite completa, già riportata a 2.314 test OK sull'immediato commit precedente `3c61c3c1`; il delta di HEAD è la description e una nota di tracciamento in `riscrittura-gate-b-r1.md`. La guardia corrente è stata eseguita. `git status` è pulito, sul ramo atteso. Nessun file del worktree è stato creato, modificato o cancellato. Nessun commit, push, PR, merge o deploy.

## Fonti

- [AGENAS, rapporto ufficiale](https://www.agenas.gov.it/images/Terzo_Rapporto_mobilita.pdf?download=1), pagina ufficiale [dell'edizione 2025](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista/2743-la-mobilit%C3%A0-sanitaria-in-italia-edizione-2025).
- [Fondazione GIMBE, rapporto Osservatorio 1/2026](https://salviamo-ssn.it/var/contenuti/Report_mobilita_sanitaria_2023.pdf).
- [Istat, audizione sui LEA](https://www.istat.it/wp-content/uploads/2026/07/Istat-Audizione-Commissione-Affari-Sociali_07-luglio-2026.pdf).
- [Ministero della Salute, Rapporto SDO 2024, copia ISS](https://www.epicentro.iss.it/sdo/pdf/RAPPORTO_SDO_2024.pdf).
- [Wikimedia Commons, copertina e licenza](https://commons.wikimedia.org/wiki/File:Pavillon_Francesco_Ponti_Polyclinique_Milan_-_Milan_(IT25)_-_2022-09-02_-_2.jpg).
