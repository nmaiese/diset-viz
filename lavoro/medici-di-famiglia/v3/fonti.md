# Medici v3: registro delle fonti esterne

Integrazione della data F3: C-DIV, 2026-10-07; il resto del registro conserva attribuzione allo scout.
Scout: Claude Sonnet 5.5, 7 ottobre 2026. Dispatch task_4db37a6d0c7d. Tutte le fonti qui sotto sono state **aperte e lette davvero** (PDF scaricato e testo estratto, pagina letta, API interrogata), salvo dove scritto «non aperta». Nessun valore è stato copiato da un'immagine. Dove ho letto uno specchio e non la pagina ufficiale lo dico nella colonna URL.

Legenda tipo: **P** fonte primaria (ente che produce il dato), **S** analisi di terzi su dati primari, **Sec** articolo giornalistico (solo per orientarsi, mai come prova).

## 1. Registro delle fonti aperte

| ID | Titolo | Ente | Tipo | URL realmente aperto | Pubblicazione | Ultimo anno dati | Limiti |
|---|---|---|---|---|---|---|---|
| F1 | Audizione Istat sull'attuazione dei LEA (XII Commissione Affari sociali, Camera) con Allegato statistico | Istat, Direzione centrale statistiche sociali | P | https://storagehub.homnya.net/cmsimage/2026/07/leg19.com12.audizioni.memoria.pubblico.ideges.95227.07-07-2026-17-22-15.774.pdf (specchio dell'atto Camera. Il percorso `documenti.camera.it/.../COM12/Audizioni/` con lo stesso nome dà 404: pagina ufficiale non verificata) | 7 luglio 2026 (frontespizio, metadati PDF 7/07/2026) | MMG e mobilità 2024. Massimalisti regionali 2023. Conti della sanità 2025 (pubblicati maggio 2026). Posti letto e dimissioni 2023 | Memoria parlamentare: le figure regionali MMG sono grafici senza tabella (valori non estraibili, tranne quelli nel testo). Rinuncia regionale solo per Sardegna nel testo |
| F2 | Rapporto Osservatorio GIMBE 1/2026, La mobilità sanitaria interregionale nel 2023 | Fondazione GIMBE | S su Modelli M, Intesa Stato-Regioni, Agenas | https://salviamo-ssn.it/var/contenuti/Report_mobilita_sanitaria_2023.pdf (specchio. La pagina indicata nel PDF è `gimbe.org/mobilita2023`, risponde 200) | 4 marzo 2026 (citazione nel PDF) | 2023 | Prima fatturazione, rettifiche non stimabili. Non distingue pubblico/privato nell'Intesa. Solo ricoveri e specialistica: il valore è sottostimato. Gimbe è una fondazione non profit, non un ente pubblico |
| F3 | La Mobilità Sanitaria in Italia, Terzo rapporto, edizione 2025 | AGENAS | P | [PDF ufficiale](https://www.agenas.gov.it/images/Terzo_Rapporto_mobilita.pdf?download=1) collegato dalla [scheda ufficiale](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista/2743-la-mobilit%C3%A0-sanitaria-in-italia-edizione-2025); [feed Atom](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=atom) e [feed RSS](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=rss) aperti il 2026-10-07 | **2026-04-15** per la scheda: Atom published 2026-04-15T12:58:07+02:00, RSS pubDate Wed, 15 Apr 2026 12:58:07 +0200, entrambi con link/GUID della scheda. Il PDF non indica giorno proprio; pagina modificata 2026-04-16 e PDF Last-Modified 2026-04-15 sono date diverse da non sostituire alla pubblicazione | 2024 | Solo ricoveri e specialistica in mobilità passiva. Mobilità effettiva = totale meno casuale e apparente. Non ho estratto le tabelle regionali (figure) |
| F4 | Rapporto annuale sull'attività di ricovero ospedaliero, dati SDO 2024 | Ministero della Salute | P | https://www.epicentro.iss.it/sdo/pdf/RAPPORTO_SDO_2024.pdf (copia ISS Epicentro del PDF ministeriale, 256 pagine. Pagina ministeriale `salute.gov.it/new/it/tema/ricoveri-ospedalieri/` risponde 200 ma non ho verificato che linki lo stesso file) | giugno 2026 (frontespizio) | 2024 | Tassi standardizzati. Tavole con font codificato: le cifre della Tavola 5.6 sono state decodificate e verificate sulla riga Italia (77,71 + 7,63 = 85,34). Non è l'indice di fuga ufficiale |
| F5 | Quaderno n. 4, La Sanità in cammino per il cambiamento (Rapporto sul coordinamento della finanza pubblica) | Corte dei conti, Sezioni riunite in sede di controllo | P | https://www.corteconti.it/Download?id=6677f13f-bc0b-4295-9193-1dfacfd08c33 | settembre 2025 | MMG 2023 (Annuario SSN). Intramoenia e costi 2024. Mobilità 2023 | I dati MMG sono del Ministero della Salute. Sull'intramoenia: costi riconosciuti, non volumi. Gettonisti citati solo come tema, senza serie |
| F6 | Comunicato stampa GIMBE, Crisi dei medici di famiglia: ne mancano oltre 5.700, carenze in 18 Regioni | Fondazione GIMBE | S su SISAC, FIMMG, Agenas, Istat | https://gest.gimbe.org/comunicatistampa/cs_gimbe_carenza_medici_di_famiglia_0.docx (testo e Tabella 1 letti. Le 7 figure sono PNG e **non** ho trascritto i valori) | 17 marzo 2026 | 1° gennaio 2025 (SISAC). Pensionamenti 2025-2028 (FIMMG). Borse 2025 | La carenza è una **stima GIMBE** con rapporto ottimale 1/1.200, media regionale. 21 Accordi integrativi cambiano il massimale. Pensionamenti e candidati da FIMMG (sindacato) |
| F7 | Conti della sanità, tavole 1-4 nell'Allegato statistico di F1 | Istat, Sistema dei conti della sanità | P | stesso PDF di F1, pagine 22-25 | pubblicati maggio 2026 (nota 3 di F1) | 2025 (totali), 2024 (per funzione) | Solo nazionale. Dati provvisori e rivisti con i conti nazionali di marzo 2026 |
| F8 | Eurostat, `hlth_silc_08` e `hlth_silc_08b`: bisogni di visita medica non soddisfatti (EU-SILC) | Eurostat | P | API https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hlth_silc_08 e .../hlth_silc_08b, interrogate il 7/10/2026 | aggiornamento del 17/09/2026 (campo `updated`) | 2025 | Solo nazionale. Indagine campionaria, definizione diversa dalla rinuncia Istat. Italia 2020 mancante. Rottura di serie possibile nel 2025 |
| F9 | Relazione sull'esercizio dell'attività libero-professionale intramuraria, anno 2022 (Doc. CLXVIII n. 2) | Ministero della Salute, trasmessa alla Camera | P | https://documenti.camera.it/_dati/leg19/lavori/documentiparlamentari/indiceetesti/168/002/INTERO.pdf | trasmessa 9 agosto 2024 | **2022** | Non è doppio lavoro nel privato: è la libera professione dentro e fuori le mura aziendali dei dirigenti medici SSN. Ultimo anno vecchio. Non ho trovato una relazione più recente |
| F10 | I-Com, Pazienti in viaggio: cosa racconta la mobilità sanitaria sul SSN | I-Com | Sec | https://www.i-com.it/2026/08/28/mobilita-sanitaria-2026/ | 28 agosto 2026 | 2024 | Solo orientamento. Ogni cifra usata è stata riletta in F3 |

## 2. Fonti cercate e non usate

- **SISAC, medici al 1/1/2025** (primaria per F6): https://www.sisac.info/downloadFILE.do?doc_id=www.sisac.info/resources/pagine/201012220128505922&nomefile=medici_1_1_2025.pdf&serv=nws . **Non aperta**: il download restituisce 0 byte anche con user agent da browser. I valori regionali di F6 (carenza, assistiti per medico 1.153 Molise, 1.533 Lombardia) sono quindi di seconda mano.
- **OECD Health at a Glance 2025, profilo Italia**: risponde 403 a WebFetch. **Non aperta.** Non la cito per le cifre sui MMG.
- **Rapporto GIMBE «tagli invisibili» del 7/10/2026** (uscito sui giornali oggi): non aperto, non citato.
- **Articolo di Quotidiano Sanità sul rapporto GIMBE mobilità** con data «7 ottobre 2026» restituita dal fetch: la data è incoerente con il PDF (marzo 2026). Ignorato, vale F2.
- **Ragioneria generale dello Stato, Monitoraggio della spesa sanitaria**: citato dall'ANSA del 24/01/2026 (spesa pubblica 139,4 mld, privata 46,4 mld nel 2024). Non aperto il rapporto. Le cifre differiscono da F7 per definizione, quindi non le uso.
- **Annuario statistico SSN 2023 (Ministero)**: non aperto, ma F5 ne riporta la tavola 19.
- **Gettonisti**: nessuna serie aperta confrontabile trovata. F5 li cita solo come rischio qualitativo («stop ai gettonisti»). **Non trovato.**
- **Extramoenia (nel senso di medico pubblico che lavora nel privato) e doppio incarico**: nessun dato aperto confrontabile per regione. F9 copre solo la libera professione intramuraria al 2022. **Non trovato.**
- **Liste d'attesa regionali (PNLA Agenas)**: il portale esiste (stat.agenas.it), non l'ho interrogato. Nessuna serie estratta.

## 3. Cifre che sembrano in conflitto e non lo sono

| Tema | Valore A | Valore B | Perché differiscono |
|---|---|---|---|
| Medici di famiglia | 37.173 (Istat/Ministero, 2024) | 36.812 (SISAC, via GIMBE, 1/1/2025). 37.983 (Corte dei conti, Annuario SSN, 2023) | Tre fonti, tre date di riferimento, flussi diversi. Non vanno mescolate in un grafico |
| Massimalisti (MMG oltre 1.500 assistiti) | 54,5% nazionale 2024 (F1) | 51,7% (2023, F1 per il regionale), 47,7% in articoli sul 2022 | Il dettaglio regionale esiste **solo al 2023**. Il 2024 è solo nazionale |
| Indice di fuga Molise | 39,80% (AGENAS, mobilità effettiva) | 32,8% (Istat, acuti ordinari) | Il primo conta la sola mobilità effettiva (IFv), il secondo i ricoveri per acuti in regime ordinario |
| Valore della mobilità | circa 2,9 mld (AGENAS 2024, solo ricoveri) | 5,153 mld (GIMBE 2023, Modelli M ricoveri più specialistica) | Perimetro e anno diversi |
| Quota di mobilità al privato accreditato | 69,2% della **spesa** della mobilità effettiva, 62,6% dei volumi (AGENAS 2024) | 54,5% del valore totale (GIMBE 2023), 56,4% ricoveri, 46,1% specialistica | Mobilità effettiva contro totale, anno diverso |
| Rinuncia alle cure | 9,9% della popolazione (Istat, 2024) | 2,5% della popolazione e 4,5% di chi ha bisogno (Eurostat, 2025) | Indagini, definizioni e denominatori diversi. Non confrontabili tra loro |
| Spesa privata | 42,4 mld di spesa diretta delle famiglie 2025 (Istat) | 46,4 mld (RGS via ANSA, 2024) | Il secondo comprende altro: non aperto, non usato |
| Saldi di mobilità 2024 | Sicilia -138,2 mln (AGENAS) | -140 (I-Com) | Tengo AGENAS, fonte primaria |

## 4. Serie esterne pronte per un grafico

### S1. Mobilità e privato accreditato per regione di destinazione, 2023 (F2, tabelle 4.4 e 4.5)

Saldo pro capite = crediti meno debiti per cittadino residente, euro. Quota privato = quota del valore della mobilità **attiva** erogata da strutture private convenzionate.

| Regione | Saldo pro capite 2023 (€) | Quota privato, ricoveri (%) | Quota privato, specialistica (%) |
|---|---:|---:|---:|
| Emilia-Romagna | 127 | 59,1 | 25,5 |
| Lombardia | 65 | 73,2 | 61,9 |
| Molise | 64 | 89,0 | 92,2 |
| Veneto | 44 | 55,8 | 64,7 |
| P.A. Trento | 15 | 61,4 | 40,7 |
| Toscana | 13 | 34,0 | 5,5 |
| Piemonte | -5 | 52,9 | 30,0 |
| P.A. Bolzano | -7 | 8,8 | 10,1 |
| Friuli Venezia Giulia | -8 | 26,2 | 21,8 |
| Lazio | -34 | 68,1 | 46,7 |
| Marche | -37 | 48,2 | 32,2 |
| Liguria | -49 | 12,1 | 7,7 |
| Sicilia | -51 | 33,5 | 45,8 |
| Campania | -55 | 52,4 | 64,9 |
| Sardegna | -65 | 22,8 | 23,0 |
| Puglia | -65 | 70,0 | 63,2 |
| Umbria | -65 | 16,7 | 7,7 |
| Abruzzo | -68 | 44,5 | 30,6 |
| Valle d'Aosta | -104 | 20,2 | 0,2 |
| Basilicata | -146 | 0,4 | 23,8 |
| Calabria | -178 | 37,6 | 26,3 |
| Italia | | 56,4 | 46,1 |

Totale mobilità 2023: 5.152,5 milioni di euro. Saldi in milioni nella tabella 4.1 di F2 (Lombardia +645,8, Emilia-Romagna +564,9, Veneto +212,1, Calabria -326,9, Campania -306,3, Puglia -253,2, Sicilia -246,7, Lazio -191,7). Il saldo pro capite di Molise (+64) è un effetto di piccola popolazione e di mobilità di confine, vedi limiti.

### S2. Ricoveri per acuti in regime ordinario, entro e fuori regione, per 1.000 residenti, 2024 (F4, Tavola 5.6, tassi standardizzati per età e genere)

La colonna «fuori/totale» è un rapporto mio dei due tassi: **non coincide** con l'indice di fuga ufficiale. Per gli indici ufficiali citabili: F1 (Lombardia 5,3%, Emilia-Romagna 5,7%, Veneto 6,5%, Puglia 9,3%, Campania 9,6%, Abruzzo 16,2%, Trento 15,2%, Valle d'Aosta 19,6%, Calabria 22,8%, Basilicata 28,6%, Molise 32,8%, Italia 8,6%) e F3 (indice di fuga nazionale 8,72%, Molise 39,80% e Basilicata 33,53% sulla mobilità effettiva).

| Regione | Entro regione | Fuori regione | Totale | Fuori/totale (%) |
|---|---:|---:|---:|---:|
| Piemonte | 79,73 | 6,08 | 85,81 | 7,1 |
| Valle d'Aosta | 75,10 | 19,90 | 95,01 | 20,9 |
| Lombardia | 74,78 | 4,41 | 79,19 | 5,6 |
| P.A. Bolzano | 94,46 | 4,89 | 99,35 | 4,9 |
| P.A. Trento | 68,39 | 13,08 | 81,47 | 16,1 |
| Veneto | 78,69 | 5,81 | 84,49 | 6,9 |
| Friuli Venezia Giulia | 77,09 | 7,29 | 84,38 | 8,6 |
| Liguria | 78,67 | 13,99 | 92,67 | 15,1 |
| Emilia-Romagna | 87,38 | 5,71 | 93,09 | 6,1 |
| Toscana | 75,14 | 6,21 | 81,35 | 7,6 |
| Umbria | 79,17 | 15,10 | 94,27 | 16,0 |
| Marche | 75,72 | 12,76 | 88,48 | 14,4 |
| Lazio | 78,94 | 6,41 | 85,35 | 7,5 |
| Abruzzo | 75,40 | 15,59 | 90,99 | 17,1 |
| Molise | 55,52 | 30,90 | 86,42 | 35,8 |
| Campania | 77,34 | 8,12 | 85,47 | 9,5 |
| Puglia | 82,84 | 8,76 | 91,61 | 9,6 |
| Basilicata | 60,97 | 25,95 | 86,92 | 29,9 |
| Calabria | 61,15 | 17,89 | 79,04 | 22,6 |
| Sicilia | 78,57 | 6,10 | 84,68 | 7,2 |
| Sardegna | 76,50 | 5,60 | 82,10 | 6,8 |
| Italia | 77,71 | 7,63 | 85,34 | 8,9 |

Altri valori nazionali 2024 (F3): 675.879 ricoveri in mobilità, 544.316 di mobilità effettiva, circa 2,9 mld di spesa (2,4 mld la sola effettiva), 19,7 milioni di prestazioni ambulatoriali in mobilità per 650 milioni. DRG ad alta complessità: 20,4% dei volumi e 53% della spesa. Saldi 2024 in milioni: Emilia-Romagna +419,2, Lombardia +385,7, Veneto +111,8, Campania -210,5, Calabria -193,9, Sicilia -138,2, Puglia -131,8. Corte dei conti (F5, dati 2023): ricoveri ad alta complessità in mobilità effettiva 105.288, di cui 75% nel privato accreditato.

### S3. Medici di medicina generale in Italia per anzianità di laurea, 2009-2023 (F5, Tavola 19, fonte Annuario statistico SSN 2023, p. 110)

Numero di medici. Le colonne sono le classi di anzianità di laurea.

| Anno | 0-6 anni | 6-13 | 13-20 | 20-27 | oltre 27 | Totale |
|---|---:|---:|---:|---:|---:|---:|
| 2009 | 109 | 827 | 6.811 | 16.040 | 22.422 | 46.209 |
| 2012 | 69 | 554 | 4.231 | 12.120 | 28.463 | 45.437 |
| 2014 | 78 | 739 | 3.307 | 10.853 | 29.960 | 44.937 |
| 2016 | 95 | 881 | 2.331 | 9.282 | 31.681 | 44.270 |
| 2018 | 139 | 1.350 | 1.917 | 6.814 | 32.767 | 42.987 |
| 2019 | 150 | 1.683 | 1.833 | 5.750 | 33.012 | 42.428 |
| 2020 | 311 | 2.234 | 1.943 | 4.859 | 32.360 | 41.707 |
| 2021 | 666 | 3.196 | 2.091 | 3.994 | 30.303 | 40.250 |
| 2022 | 1.102 | 3.711 | 2.485 | 3.532 | 28.536 | 39.366 |
| 2023 | 1.695 | 4.291 | 2.891 | 3.096 | 26.010 | 37.983 |

Nel testo di F5 la riga 2018 ha un refuso di stampa («6..814») e la 2022 «3..711»: ho letto 6.814 e 3.711, i totali tornano. Il 2014 è confermato da F1: 37.173 + 7.764 = 44.937. Punto di riferimento: 2023, oltre il 68% dei MMG ha più di 27 anni di laurea e il 4,5% meno di 6.

Valori Istat (F1): MMG 2024 = 37.173 (6,3 per 10.000 residenti), 810 in meno del 2023, 7.764 in meno del 2014 (-17,3%). Il 32,7% ha 65-69 anni. Nel Mezzogiorno la quota va dal 33,9% della Sicilia al 46,1% della Campania. Nel Lazio la quota dei MMG che lasceranno entro cinque anni è 34,9%. Tasso per 10.000 residenti, 2024: Lombardia e P.A. Bolzano 5,3, Veneto 5,6, Friuli-Venezia Giulia 5,8, Emilia-Romagna, Campania e Sardegna 6,0. Massimalisti 2023: dal 52,4% del Friuli-Venezia Giulia al 74,0% della Lombardia, media nazionale 51,7%.

### S4. Candidati e borse del corso di formazione in medicina generale, 2025 (F6, Tabella 1, dati FIMMG)

Differenza = candidati meno borse finanziate. Nazionale: 2.810 candidati per 2.228 borse (+582, +26%). Borse: 4.362 nel 2021 (picco), circa 2.600 nel 2023 e 2024, 2.228 nel 2025 (-15,1%). Carenza stimata dal GIMBE (media regionale, rapporto 1/1.200): Lombardia -1.540, Veneto -747, Campania -643, Emilia-Romagna -502, Piemonte -463, Toscana -394, Lazio -358, nessuna carenza in Basilicata, Molise e Sicilia. Totale 5.716.

| Regione | Differenza | % |
|---|---:|---:|
| Valle d'Aosta | -6 | -60 |
| P.A. Bolzano | -18 | -60 |
| Marche | -78 | -49 |
| P.A. Trento | -15 | -38 |
| Piemonte | -50 | -29 |
| Lombardia | -84 | -22 |
| Liguria | -11 | -18 |
| Veneto | -12 | -6 |
| Sardegna | -3 | -5 |
| Toscana | 0 | 0 |
| Friuli Venezia Giulia | +4 | +10 |
| Puglia | +42 | +27 |
| Umbria | +11 | +32 |
| Emilia-Romagna | +74 | +42 |
| Basilicata | +8 | +67 |
| Molise | +7 | +70 |
| Sicilia | +149 | +79 |
| Abruzzo | +44 | +142 |
| Campania | +230 | +153 |
| Lazio | +181 | +221 |
| Calabria | +109 | +273 |

Altri valori di F6: MMG 42.009 nel 2019 e 36.812 nel 2024 (-5.197, -14,1%), calo più forte in Sardegna (-40,3%), P.A. Bolzano unica in crescita (+2,4%), 1.383 assistiti per medico in media al 1/1/2025 (Molise 1.153, Lombardia 1.533), 8.180 pensionamenti attesi 2025-2028 (Valle d'Aosta 10, Campania 1.147), gap oltre 2.700 al 2028 nell'ipotesi più ottimistica.

### S5. Spesa sanitaria in Italia per regime di finanziamento, 2019-2025 (F7, Tavola 1, milioni di euro)

| Voce | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pubblica amministrazione e assicurazioni obbligatorie | 113.840 | 121.113 | 127.450 | 130.345 | 130.890 | 137.108 | 140.789 |
| Regimi volontari (assicurazioni, imprese, no profit) | 4.479 | 4.297 | 4.550 | 5.250 | 5.882 | 6.329 | 6.971 |
| Spesa diretta delle famiglie | 37.108 | 34.315 | 39.015 | 41.239 | 42.480 | 42.791 | 42.356 |
| Totale | 155.427 | 159.725 | 171.015 | 176.834 | 179.252 | 186.228 | 190.116 |
| Spesa diretta delle famiglie, % del totale | 23,9 | 21,5 | 22,8 | 23,3 | 23,7 | 23,0 | 22,3 |

Spesa diretta delle famiglie per funzione, 2019 e 2024 (F7, Tavola 4, milioni): assistenza ambulatoriale per cura e riabilitazione 13.888 e 17.687 (+27%), ospedaliera in ricovero ordinario 1.531 e 1.437, day hospital 462 e 412, lunga durata 4.442 e 4.827, farmaceutica e presidi 14.075 e 15.261, servizi ausiliari 2.503 e 2.925. Pro capite 2025: 3.225 € di spesa totale, di cui 2.388 pubblica, 719 diretta delle famiglie, 118 volontaria.

Intramoenia, costi riconosciuti (F5): 894 milioni nel 2019, 1.048 milioni nel 2024, in termini reali nel 2024 vicini al 2019. Pro capite 2024 per area: regioni a statuto ordinario del Nord 23,9 €, speciale del Nord 19,6 €, ordinario del Centro 18,9 €, 8,5 € per le regioni a statuto ordinario meridionali (il testo dice «regioni meridionali» e poi «quelle a statuto ordinario», lettura da riconfermare sul PDF prima di citarla).

### S6. Bisogni di visita medica non soddisfatti, Italia e UE27 (F8, Eurostat, % persone di 16 anni e più, 2019-2025)

`hlth_silc_08`, motivo costo, distanza o lista di attesa, sul totale della popolazione:

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Italia, totale | 1,8 | n.d. | 1,8 | 1,8 | 1,8 | 1,9 | 2,5 |
| UE27, totale | 1,7 | 1,9 | 2,0 | 2,2 | 2,4 | 2,5 | 2,4 |
| Italia, primo quintile di reddito | 4,1 | n.d. | 3,5 | 3,3 | 3,8 | 4,3 | 4,4 |
| Italia, quinto quintile | 0,4 | n.d. | 0,9 | 0,7 | 0,4 | 0,6 | 0,8 |
| UE27, primo quintile | 3,2 | 3,8 | 3,5 | 3,8 | 3,8 | 3,9 | 3,7 |
| Italia, solo lista di attesa, totale | 0,4 | n.d. | 0,7 | 0,6 | 0,7 | 0,8 | 0,9 |
| UE27, solo lista di attesa, totale | 0,7 | 0,7 | 0,9 | 0,9 | 1,2 | 1,4 | 1,2 |
| Italia, solo costo, totale | 1,3 | n.d. | 1,1 | 1,2 | 1,2 | 1,0 | 1,6 |
| UE27, solo costo, totale | 0,9 | 1,1 | 1,0 | 1,1 | 1,0 | 1,0 | 1,0 |

`hlth_silc_08b`, stesso motivo, **sulla popolazione che dichiara di aver avuto bisogno**:

| | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| Italia, totale | 3,7 | 3,8 | 4,5 |
| UE27, totale | 3,5 | 3,6 | 3,6 |
| Italia, sotto il 60% del reddito mediano | 9,2 | 9,9 | 9,7 |
| UE27, sotto il 60% | 6,0 | 6,0 | 5,9 |
| Italia, sopra il 60% | 2,7 | 2,6 | 3,6 |
| UE27, sopra il 60% | 3,0 | 3,2 | 3,1 |

Istat (F1): nel 2024 rinuncia a visite o accertamenti il 9,9% della popolazione (quasi 5,8 milioni), contro il 6,4% del 2019. Donne 11,4%, uomini 8,3%, classe 45-64 anni 12,6%. Sardegna 23,9% tra chi aveva già ricevuto prestazioni e 8,7% nel resto del collettivo.

### S7. Libera professione intramuraria (F9, Ministero, anno 2022)

Medici che esercitano ALPI: 53.000 nel 2014, 45.434 nel 2020, 45.302 nel 2021, circa 44.800 nel 2022 (-511 sul 2021). Quota sul totale dei dirigenti medici: 44,2% (2014), 40,6% (2019), 38,5% (2022). Nel 2022 il 42,3% dei dirigenti medici con rapporto esclusivo esercita ALPI. Per regione, quota di medici in esclusività che fanno ALPI: Valle d'Aosta 66%, Veneto 53%, Piemonte 53%, Lombardia 52%, Liguria 52%. Minimi: Sicilia 33%, Campania 32%, Calabria 30%, Molise 24%, Sardegna 22%, P.A. Bolzano 14%. Solo i valori citati nel testo: la tavola completa per regione non è stata estratta.
