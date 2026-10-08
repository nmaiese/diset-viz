# Fonti esterne aperte e verificate: Infortuni mortali e inabilità permanente (`bes:03LAV007`), 08/10/2026

Tutte aperte con `curl -A "DivarioCheck/1.0"` (HTTP 200) e lette in locale con pypdf/openpyxl l'08/10/2026. Citazioni letterali dal testo estratto. Gli URL INAIL sono quelli dei file `.pdf` linkati dalle pagine di dettaglio sotto `inail.it/portale/it/inail-comunica/pubblicazioni/rapporti-e-relazioni-inail/`.

## 1. Istat, Bes dei territori 2025, appendice statistica (fogli Glossario e Dominio 03)
- URL: https://www.istat.it/wp-content/uploads/2025/12/Appendice_Sicilia_2025.xlsx (HTTP 200, 244.579 byte)
- Data: dicembre 2025 (edizione 2025). Anno del dato: 2019 e 2022. Ruolo: **definizione e dato primario**.
- Glossario, riga `03-03`: «Tasso di infortuni sul lavoro mortali e con inabilità permanente | Numero di infortuni sul lavoro mortali e con inabilità permanente sul totale degli occupati (al netto delle forze armate) per 10.000. | Per 10.000 occupati | Inail».
- Foglio Dominio 03, riga Italia: 2019 = 11,7, 2022(*) = 11,0, differenza -0,7. Mezzogiorno 14,3 (2019) e 13,0 (2022). Nota del foglio: «(*) Dati provvisori». Sicilia 13,4 (2022), uguale al nostro CSV regionale.
- Limite d'uso: l'appendice dà la definizione in una riga e **non** dice quali gestioni, quali infortuni (in occasione di lavoro, in itinere), quale soglia di menomazione né se il numeratore sia per anno di accadimento. Il 2022 è provvisorio per Istat. Il foglio ha il nome «Sicilia» ma contiene Italia, Mezzogiorno e la regione.

## 2. Istat, Bes dei territori 2025, report regionale Calabria
- URL: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf (HTTP 200, `last-modified` 04/12/2025, 18 pagine)
- Anno del dato: 2022. Ruolo: **conferma indipendente del dato regionale e provinciale**, unica fonte aperta per un contrasto interno a una regione.
- Citazione: «A livello regionale il tasso di infortuni mortali e inabilità permanente nel 2022 raggiunge i 13,5 infortunati per 10 mila occupati (+2,5 punti rispetto all'Italia), con ampie differenze tra la provincia di Catanzaro, dove scende a 8,0 per 10 mila e la città metropolitana di Reggio di Calabria (17,3)».
- Citazione sul confronto 2019: «il tasso di infortuni mortali e inabilità permanente si riduce più che in Italia (-3,1 punti a fronte di -0,7)».
- Il CSV del sito concorda: Calabria 13,5, Catanzaro 8,0 (2022). Ricalcolo: 16,6 (2019) - 13,5 (2022) = -3,1.
- Limite d'uso: Istat dice «infortunati per 10 mila occupati», il glossario «infortuni». Il report non spiega le cause dei divari. Italia 11,0 è ricavato (13,5 - 2,5) e coincide con la fonte 1.

## 3. INAIL, Rapporto annuale regionale 2024, Umbria
- URL: https://www.inail.it/content/dam/inail-hub-site/documenti/rapporti-e-relazioni-inail/2025/10/UMBRIA.pdf (HTTP 200, `last-modified` 23/10/2025, 43 pagine, creato il 22/10/2025). Dati rilevati al 30 aprile 2025.
- Anno del dato: 2022, 2023, 2024. Ruolo: **cosa conta INAIL, e con quali numeri assoluti**, per la regione prima nel 2022.
- Citazione: «Gli infortuni accertati positivi in assenza di menomazioni sono stati 6.254, in incremento del 3,47% rispetto al 2022 e del 6,20% rispetto al 2023. Gli infortuni accertati positivi con menomazioni sono stati 1.048 (-20,18%, -23,11%). Gli accertati positivi con esito mortale sono stati 16, a fronte dei 14 del 2022 e dei 12 del 2023.»
- Tabella 2.4: Umbria con menomazioni 1.313 (2022), 1.363 (2023), 1.048 (2024); Italia esito mortale 716 (2022), 637 (2023), 572 (2024); Italia con menomazioni 68.538, 71.122, 59.801. Tabella 2.2 (denunce con esito mortale): Umbria 24 (2022), 26 (2023), 25 (2024); Italia 1.293, 1.201, 1.202.
- Citazione sulla denuncia (nota metodologica): «comunicazioni obbligatorie effettuate, ai soli fini statistici e informativi da tutti i datori di lavoro e i loro intermediari [...] degli infortuni che comportano un'assenza dal lavoro di almeno un giorno, escluso quello dell'evento». Definizione amministrativa: «situazione amministrativa prevalente, alla data di rilevazione [...] può cambiare nel tempo a seguito dell'evoluzione del caso.»
- Limite d'uso: INAIL pubblica **conteggi** per anno di accadimento e stato amministrativo (denunce, accertati positivi), non il tasso per 10.000 occupati del Bes. I conteggi INAIL non si dividono per gli occupati per rifare l'indicatore: il perimetro del numeratore Bes non è documentato (vedi «Non trovato»). I numeri INAIL sono contesto, mai conferma del 17,8.

## 4. INAIL, Rapporto annuale regionale 2024, Basilicata
- URL: https://www.inail.it/content/dam/inail-hub-site/documenti/rapporti-e-relazioni-inail/2025/10/BASILICATA.pdf (HTTP 200, `last-modified` 23/10/2025, 36 pagine). Dati rilevati al 30 aprile 2025.
- Anno del dato: 2022, 2023, 2024. Ruolo: la regione che cala di più nel nostro indicatore (24,1 nel 2018, 16,8 nel 2022).
- Citazione: «Gli accertati positivi con esito mortale sono stati 13, 6 in più rispetto al 2022 (7) e 4 in più rispetto al 2023 (9).»
- Tabella 2.4: Basilicata con menomazioni 662 (2022), 856 (2023), 710 (2024); mortali 7, 9, 13.
- Limite d'uso: numeri piccoli (7 mortali nel 2022): un caso in più sposta molto la serie. È un motivo per non leggere variazioni da un anno all'altro in una regione piccola come tendenza. Le cifre di occupati NON sono in questa fonte.

## 5. INAIL, Relazione annuale 2025
- URL: https://www.inail.it/content/dam/inail-hub-site/documenti/rapporti-e-relazioni-inail/2026/09/relazione-annuale-inail-2025.pdf (HTTP 200, `last-modified` 21/09/2026, 84 pagine, creato il 14/07/2026).
- Anno del dato: 2025 (con 2024). Ruolo: **il dato più recente sulle morti sul lavoro**, per dire con onestà che «morti sul lavoro» è un'altra misura e un anno più avanti.
- Citazione: «Sono state 1.198 le denunce di infortunio con esito mortale, in diminuzione del 3,3% (41 casi in meno) rispetto alle 1.239 del 2024, così ripartite: 1.189 denunce per lavoratori, 37 in meno rispetto alle 1.226 dell'anno precedente; 9 denunce per studenti».
- Citazione sul perimetro: «L'analisi dei dati sugli infortuni sul lavoro riguarda i soli casi occorsi ai lavoratori in senso stretto, esclusi quelli occorsi agli studenti».
- Limite d'uso: sono **denunce** (comunicazioni dei datori di lavoro, ancora da accertare), non infortuni riconosciuti; il testo letto non dice quante siano in itinere. 1.189 denunce di lavoratori nel 2025 non sono confrontabili con il tasso Bes 2022 né con gli accertati positivi (572 nel 2024).

## Non trovato / non aperto
- **Nessun dato Bes più recente del 2022** per `03LAV007`: il nostro CSV (archivio «aggiornamento intermedio 2026») e l'appendice dell'edizione 2025 si fermano al 2022 (Dominio 03: «2022(*)», provvisorio). Non ho trovato una serie 2023 o 2024 dello stesso tasso.
- **Nessuna pagina INAIL che pubblichi il tasso per 10.000 occupati per regione.** Cercato in: rapporti regionali 2024 (Umbria, Basilicata), Relazione annuale 2025, portale open data (`dati.inail.it`, HTTP 200, non esplorato). Quindi non riesco a dire quale sia esattamente il numeratore del Bes (accertati positivi con menomazioni + mortali? solo in occasione di lavoro? quali gestioni?).
- **Il numeratore non si riconcilia.** Come controllo d'ordine di grandezza, i conteggi INAIL 2022 (Umbria 1.313 con menomazioni + 14 mortali; Basilicata 662 + 7) divisi per un ordine di grandezza di occupati regionali danno un tasso grosso modo doppio del Bes. Occupati regionali NON presi da una fonte aperta da me: stima non verificata, **da non scrivere** nella scheda. Serve solo a dire che il Bes usa un perimetro più stretto di «tutti gli accertati».
- Cause dei divari regionali (settori, dimensione d'impresa, lavoro irregolare, denuncia): nessuna fonte aperta tra quelle lette le attribuisce ai valori regionali del Bes.
- Rapporto Bes regionale 2025 per Umbria, Basilicata, Abruzzo: gli URL `BesT2025_Umbria.pdf` e `BesT2025_Basilicata.pdf` danno 404 (nome file diverso, non trovato). Per questo la fonte 2 è la Calabria.
- Pagine INAIL `.../statistiche-infortuni.html` indicata nel `note.md` del worker precedente: HTTP 200, ma nel testo estratto ho trovato solo la cornice del portale (menu «Dati e statistiche», «Open Data»), nessun dato né data di pubblicazione. **Non elencata come fonte.**
- `note.md` citava anche «ISTAT Occupazione e struttura produttiva (contesto): https://www.istat.it/it/archivio/200359»: non aperta, non elencata.
