# Audit freschezza dati 2025

Generato: 2026-07-15T08:56:19.511010+00:00

## Riepilogo

- indicatori aggiornati direttamente: 33
- nuovi indicatori 2025 aggiunti: 0
- indicatori non aggiornabili: 293
- indicatori da revisionare manualmente: 67
- fonti non accessibili automaticamente: INVALSI, Movimprese, Terna e Infratel restano in fixture/metadata mode finche non viene promosso un parser verificato.

## Decisioni metodologiche

- I CSV legacy a 12 colonne restano invariati.
- Le fonti esterne entrano in un dataset normalizzato separato.
- Nessun nuovo indicatore entra nello scoring senza match esatto e direzione revisionata.
- Indicatori demografici di struttura, fecondita e saldo migratorio restano contestuali o profilo descrittivo.
- I dati assoluti non sono eleggibili per lo scoring.

## Fonti ufficiali configurate

- infratel: https://www.infratelitalia.it/home
- invalsi: https://invalsiopen.it/dati-rilevazione-invalsi-2025/
- istat_demografia: https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/
- istat_lavoro: https://www.istat.it/statistiche-per-temi/lavoro/
- istat_turismo: https://www.istat.it/statistiche-per-temi/servizi/turismo/
- movimprese: https://www.infocamere.it/movimprese
- terna: https://www.terna.it/it/sistema-elettrico/statistiche

## Dettaglio

| id | indicatore | anno attuale | fonte alternativa | anno disponibile | decisione |
|---|---|---:|---|---:|---|
| 920 | Eta media della popolazione | 2026 | istat_demografia | 2026 | integrated |
| 921 | Indice di vecchiaia | 2026 | istat_demografia | 2026 | integrated |
| 922 | Numero medio di figli per donna | 2025 | istat_demografia | 2025 | integrated |
| 923 | Saldo migratorio totale | 2025 | istat_demografia | 2025 | integrated |
| 913 | Speranza di vita a 65 anni | 2025 | istat_demografia | 2025 | integrated |
| 910 | Speranza di vita alla nascita | 2025 | istat_demografia | 2025 | integrated |
| 912 | Speranza di vita alla nascita (femmine) | 2025 | istat_demografia | 2025 | integrated |
| 911 | Speranza di vita alla nascita (maschi) | 2025 | istat_demografia | 2025 | integrated |
| 57 | Differenza tra tasso di occupazione maschile e femminile | 2025 | istat_lavoro | 2025 | integrated |
| 180 | Incidenza della disoccupazione di lunga durata (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 179 | Incidenza della disoccupazione di lunga durata (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 16 | Incidenza della disoccupazione di lunga durata (totale) | 2025 | istat_lavoro | 2025 | integrated |
| 12 | Tasso di disoccupazione | 2025 | istat_lavoro | 2025 | integrated |
| 176 | Tasso di disoccupazione (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 175 | Tasso di disoccupazione (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 17 | Tasso di disoccupazione di lunga durata | 2025 | istat_lavoro | 2025 | integrated |
| 184 | Tasso di disoccupazione di lunga durata (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 183 | Tasso di disoccupazione di lunga durata (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 15 | Tasso di disoccupazione giovanile | 2025 | istat_lavoro | 2025 | integrated |
| 174 | Tasso di disoccupazione giovanile (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 230 | Tasso di disoccupazione giovanile (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 178 | Tasso di occupazione (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 177 | Tasso di occupazione (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 13 | Tasso di occupazione (totale) | 2025 | istat_lavoro | 2025 | integrated |
| 345 | Tasso di occupazione 20-64 anni | 2025 | istat_lavoro | 2025 | integrated |
| 347 | Tasso di occupazione 20-64 anni (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 346 | Tasso di occupazione 20-64 anni (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 476 | Tasso di occupazione giovanile (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 475 | Tasso di occupazione giovanile (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 407 | Tasso di occupazione giovanile (totale) | 2025 | istat_lavoro | 2025 | integrated |
| 182 | Tasso di occupazione over 54 (femmine) | 2025 | istat_lavoro | 2025 | integrated |
| 181 | Tasso di occupazione over 54 (maschi) | 2025 | istat_lavoro | 2025 | integrated |
| 14 | Tasso di occupazione over 54 (totale) | 2025 | istat_lavoro | 2025 | integrated |
| 423 | Copertura con banda ultralarga a 100 Mbps | 2015 | infratel | - | needs_review |
| 422 | Copertura con banda ultralarga ad almeno 30 Mbps | 2015 | infratel | - | needs_review |
| 73 | Grado di diffusione della larga banda nelle amministrazioni locali | 2022 | infratel | - | needs_review |
| 62 | Grado di diffusione di Internet nelle famiglie | 2023 | infratel | - | needs_review |
| 426 | Grado di utilizzo di Internet nelle famiglie negli ultimi 12 mesi | 2023 | infratel | - | needs_review |
| 64 | Grado di utilizzo di Internet nelle famiglie negli ultimi 3 mesi | 2023 | infratel | - | needs_review |
| 429 | Penetrazione della banda ultra larga | 2023 | infratel | - | needs_review |
| 621 | Competenza alfabetica non adeguata (studenti classi II scuola secondaria secondo grado) | 2023 | invalsi | - | needs_review |
| 617 | Competenza alfabetica non adeguata (studenti classi III scuola secondaria primo grado) | 2025 | invalsi | - | needs_review |
| 623 | Competenza alfabetica non adeguata (studenti classi V scuola secondaria secondo grado) | 2025 | invalsi | - | needs_review |
| 622 | Competenza numerica non adeguata (studenti classi II scuola secondaria secondo grado) | 2023 | invalsi | - | needs_review |
| 618 | Competenza numerica non adeguata (studenti classi III scuola secondaria primo grado) | 2025 | invalsi | - | needs_review |
| 624 | Competenza numerica non adeguata (studenti classi V scuola secondaria secondo grado) | 2025 | invalsi | - | needs_review |
| 249 | Andamento dell'occupazione del settore della pesca | 2023 | istat_lavoro | - | needs_review |
| 465 | Occupati, disoccupati e inattivi che partecipano ad attività formative e di istruzione | 2014 | istat_lavoro | - | needs_review |
| 530 | Quota di lavoratori che percepiscono sussidi di politica del lavoro passiva: Indennità di disoccupazione e Assicurazione sociale per l'impiego | 2020 | istat_lavoro | - | needs_review |
| 482 | Tasso di occupazione della popolazione straniera (femmine) | 2020 | istat_lavoro | - | needs_review |
| 481 | Tasso di occupazione della popolazione straniera (maschi) | 2020 | istat_lavoro | - | needs_review |
| 455 | Tasso di occupazione della popolazione straniera (totale) | 2020 | istat_lavoro | - | needs_review |
| 460 | Tasso di occupazione nelle aree rurali (15-64 anni) | 2023 | istat_lavoro | - | needs_review |
| 50 | Tasso di occupazione regolare | 2018 | istat_lavoro | - | needs_review |
| 478 | Tasso giovani NEET (femmine) | 2024 | istat_lavoro | - | needs_review |
| 477 | Tasso giovani NEET (maschi) | 2024 | istat_lavoro | - | needs_review |
| 408 | Tasso giovani NEET (totale) | 2024 | istat_lavoro | - | needs_review |
| 132 | Produttività del lavoro nel turismo | 2016 | istat_turismo | - | needs_review |
| 165 | Turismo nei mesi non estivi | 2024 | istat_turismo | - | needs_review |
| 399 | Addetti alle imprese e alle istituzioni non profit che svolgono attività a contenuto sociale | 2015 | movimprese | - | needs_review |
| 398 | Addetti delle nuove imprese | 2023 | movimprese | - | needs_review |
| 600 | Addetti delle nuove imprese nei settori culturali e creativi | 2023 | movimprese | - | needs_review |
| 436 | Addetti occupati nelle unità locali delle imprese italiane a controllo estero | 2019 | movimprese | - | needs_review |
| 115 | Capacità di sviluppo dei servizi alle imprese | 2022 | movimprese | - | needs_review |
| 375 | Consumi di energia elettrica delle imprese dell'agricoltura | 2023 | movimprese | - | needs_review |
| 376 | Consumi di energia elettrica delle imprese dell'industria | 2023 | movimprese | - | needs_review |
| 377 | Consumi di energia elettrica delle imprese private del terziario (esclusa la PA) | 2023 | movimprese | - | needs_review |
| 65 | Grado di diffusione del personal computer nelle imprese con più di dieci addetti | 2019 | movimprese | - | needs_review |
| 597 | Grado di integrazione verticale delle imprese nei settori culturali e creativi | 2023 | movimprese | - | needs_review |
| 72 | Grado di utilizzo di Internet nelle imprese | 2024 | movimprese | - | needs_review |
| 161 | Impieghi bancari delle imprese non finanziarie sul PIL | 2021 | movimprese | - | needs_review |
| 417 | Imprese che hanno svolto attività di R&S in collaborazione con soggetti esterni | 2022 | movimprese | - | needs_review |
| 432 | Imprese che hanno svolto attività di R&S utilizzando infrastrutture di ricerca e altri servizi alla R&S da soggetti pubblici o privati | 2022 | movimprese | - | needs_review |
| 400 | Imprese e istituzioni non profit che svolgono attività a contenuto sociale | 2015 | movimprese | - | needs_review |
| 93 | Incidenza della spesa delle imprese in R&S | 2022 | movimprese | - | needs_review |
| 598 | Incidenza di dipendenti di genere femminile delle imprese nei settori culturali e creativi | 2023 | movimprese | - | needs_review |
| 599 | Incidenza di dipendenti in età giovanile delle imprese nei settori culturali e creativi | 2023 | movimprese | - | needs_review |
| 70 | Indice di diffusione dei siti web delle imprese | 2023 | movimprese | - | needs_review |
| 71 | Indice di diffusione della banda larga nelle imprese | 2021 | movimprese | - | needs_review |
| 133 | Produttività del lavoro nei servizi alle imprese | 2023 | movimprese | - | needs_review |
| 594 | Quota degli addetti delle imprese nei settori culturali e creativi sul totale | 2023 | movimprese | - | needs_review |
| 523 | Quota degli addetti nei settori ad alta intensità di conoscenza nelle imprese dell'industria e dei servizi | 2020 | movimprese | - | needs_review |
| 413 | Quota valore fidi globali fra 30.000 e 500.000 euro utilizzati dalle imprese | 2021 | movimprese | - | needs_review |
| 416 | Ricercatori occupati nelle imprese sul totale degli addetti (totale) | 2021 | movimprese | - | needs_review |
| 150 | Spesa media regionale per innovazione delle imprese | 2020 | movimprese | - | needs_review |
| 250 | Tasso di crescita dell'agricoltura | 2024 | movimprese | - | needs_review |
| 241 | Tasso di iscrizione lordo nel registro delle imprese | 2023 | movimprese | - | needs_review |
| 242 | Tasso di iscrizione netto nel registro delle imprese | 2023 | movimprese | - | needs_review |
| 54 | Tasso di natalità delle imprese | 2023 | movimprese | - | needs_review |
| 396 | Tasso di natalità delle imprese nei settori ad alta intensità di conoscenza | 2023 | movimprese | - | needs_review |
| 397 | Tasso di sopravvivenza a tre anni delle imprese nei settori ad alta intensità di conoscenza | 2023 | movimprese | - | needs_review |
| 157 | Tasso netto di turnover delle imprese | 2023 | movimprese | - | needs_review |
| 434 | Utilizzo dell'e-government da parte delle imprese | 2023 | movimprese | - | needs_review |
| 379 | Consumi di energia elettrica coperti con produzione da bioenergie | 2024 | terna | - | needs_review |
| 86 | Consumi di energia elettrica coperti da fonti rinnovabili (escluso idro) | 2024 | terna | - | needs_review |
| 85 | Consumi di energia elettrica coperti da fonti rinnovabili (incluso idro) | 2024 | terna | - | needs_review |
| 373 | Consumi di energia elettrica della PA per ULA | 2023 | terna | - | needs_review |
| 374 | Consumi di energia elettrica per illuminazione pubblica per superficie dei centri abitati | 2024 | terna | - | needs_review |
| 80 | Energia prodotta da fonti rinnovabili | 2012 | terna | - | needs_review |
| 81 | Potenza efficiente lorda delle fonti rinnovabili | 2024 | terna | - | needs_review |
| 251 | Addetti alla R&S | 2022 | - | - | unavailable |
| 198 | Adulti che partecipano all'apprendimento permanente (femmine) | 2024 | - | - | unavailable |
| 197 | Adulti che partecipano all'apprendimento permanente (maschi) | 2024 | - | - | unavailable |
| 99 | Adulti che partecipano all'apprendimento permanente (totale) | 2024 | - | - | unavailable |
| 630 | Alunni con disabilità (totale) | 2022 | - | - | unavailable |
| 627 | Alunni con disabilità motoria | 2022 | - | - | unavailable |
| 628 | Alunni con disabilità uditiva | 2022 | - | - | unavailable |
| 629 | Alunni con disabilità visiva | 2022 | - | - | unavailable |
| 415 | Anziani trattati in assistenza domiciliare socio-assistenziale | 2022 | - | - | unavailable |
| 264 | Aree terrestri protette | 2010 | - | - | unavailable |
| 461 | Beni confiscati e trasferiti al patrimonio dello stato o degli enti territoriali | 2015 | - | - | unavailable |
| 267 | Capacità di esportare | 2022 | - | - | unavailable |
| 168 | Capacità di esportare in settori a domanda mondiale dinamica | 2022 | - | - | unavailable |
| 94 | Capacità di finanziamento | 2018 | - | - | unavailable |
| 116 | Capacità di sviluppo dei servizi sociali | 2018 | - | - | unavailable |
| 425 | Cittadini che utilizzano il Fascicolo Sanitario Elettronico | 2015 | - | - | unavailable |
| 403 | Cohesion Open Government Index su trasparenza, partecipazione e collaborazione nelle politiche di coesione | 2013 | - | - | unavailable |
| 619 | Comprensione all'ascolto (listening) della lingua inglese non adeguata (studenti classi III scuola secondaria primo grado) | 2025 | - | - | unavailable |
| 625 | Comprensione all'ascolto (listening) della lingua inglese non adeguata (studenti classi V scuola secondaria secondo grado) | 2025 | - | - | unavailable |
| 620 | Comprensione della lettura (reading) della lingua inglese non adeguata (studenti classi III scuola secondaria primo grado) | 2025 | - | - | unavailable |
| 626 | Comprensione della lettura (reading) della lingua inglese non adeguata (studenti classi V scuola secondaria secondo grado) | 2025 | - | - | unavailable |
| 424 | Comuni con servizi pienamente interattivi | 2022 | - | - | unavailable |
| 395 | Comuni nei quali non è applicabile l'indicatore di resilienza ai terremoti per assenza di dati | 2016 | - | - | unavailable |
| 466 | Condizione occupazionale dei laureati dopo 1-3 anni dal conseguimento del titolo | 2024 | - | - | unavailable |
| 378 | Consumi di energia coperti da cogenerazione | 2024 | - | - | unavailable |
| 437 | Consumi finali di energia per Unità di lavoro | 2022 | - | - | unavailable |
| 386 | Corpi idrici in buono stato chimico di qualità | 2016 | - | - | unavailable |
| 544 | Corpi idrici in buono stato quantitativo di qualità | 2016 | - | - | unavailable |
| 390 | Costa non definita | 2019 | - | - | unavailable |
| 539 | Coste marine balneabili | 2019 | - | - | unavailable |
| 531 | Densità popolazione a rischio frane | 2015 | - | - | unavailable |
| 61 | Differenza tra tasso di attività maschile e femminile | 2025 | - | - | unavailable |
| 127 | Difficoltà delle famiglie nel raggiungere i supermercati | 2024 | - | - | unavailable |
| 126 | Difficoltà delle famiglie nel raggiungere negozi alimentari e/o mercati | 2024 | - | - | unavailable |
| 142 | Diffusione dei servizi per l'infanzia | 2023 | - | - | unavailable |
| 125 | Diffusione della pratica sportiva | 2025 | - | - | unavailable |
| 206 | Diffusione della pratica sportiva (femmine) | 2025 | - | - | unavailable |
| 205 | Diffusione della pratica sportiva (maschi) | 2025 | - | - | unavailable |
| 635 | Dimissioni ospedaliere di pazienti affetti da disturbi psichici per centomila abitanti | 2022 | - | - | unavailable |
| 388 | Dinamica dei litorali in avanzamento | 2019 | - | - | unavailable |
| 387 | Dinamica dei litorali in erosione | 2019 | - | - | unavailable |
| 389 | Dinamica dei litorali stabili | 2019 | - | - | unavailable |
| 430 | Dipendenti di amministrazioni locali che hanno seguito corsi di formazione ICT | 2022 | - | - | unavailable |
| 385 | Dispersione della rete di distribuzione | 2018 | - | - | unavailable |
| 411 | Disponibilità di nuove tecnologie per fini didattici | 2014 | - | - | unavailable |
| 8 | Disponibilità di risorse idropotabili | 2012 | - | - | unavailable |
| 592 | Disponibilità di verde urbano | 2020 | - | - | unavailable |
| 427 | Disponibilità di wi-fi pubblico nei Comuni | 2022 | - | - | unavailable |
| 611 | Domanda di spettacolo cinematografico | 2024 | - | - | unavailable |
| 612 | Domanda di spettacolo sportivo | 2023 | - | - | unavailable |
| 27 | Domanda di spettacolo teatrale e musicale | 2024 | - | - | unavailable |
| 613 | Domanda di spettacolo, intrattenimento e sport nei comuni situati in area interna | 2023 | - | - | unavailable |
| 610 | Domanda di spettacolo, intrattenimento e sport per abitante | 2023 | - | - | unavailable |
| 139 | Dotazione di parcheggi di corrispondenza | 2015 | - | - | unavailable |
| 542 | Durata media effettiva in giorni dei procedimenti definiti presso i tribunali ordinari | 2024 | - | - | unavailable |
| 9 | Efficienza nella distribuzione dell'acqua per il consumo umano | 2018 | - | - | unavailable |
| 33 | Elementi fertilizzanti usati in agricoltura | 2024 | - | - | unavailable |
| 590 | Emigrazione ospedaliera in altra regione | 2023 | - | - | unavailable |
| 383 | Emissioni di gas a effetto serra da trasporti stradali (Teq. CO2) | 2019 | - | - | unavailable |
| 382 | Emissioni di gas a effetto serra del settore energetico | 2019 | - | - | unavailable |
| 381 | Emissioni di gas a effetto serra in agricoltura | 2019 | - | - | unavailable |
| 511 | Emissioni di gas serra | 2019 | - | - | unavailable |
| 384 | Gestione dei siti contaminati | 2020 | - | - | unavailable |
| 404 | Giacenza media dei procedimenti civili | 2012 | - | - | unavailable |
| 200 | Giovani che abbandonano prematuramente i percorsi di istruzione e formazione professionale (femmine) | 2024 | - | - | unavailable |
| 199 | Giovani che abbandonano prematuramente i percorsi di istruzione e formazione professionale (maschi) | 2024 | - | - | unavailable |
| 102 | Giovani che abbandonano prematuramente i percorsi di istruzione e formazione professionale (totale) | 2024 | - | - | unavailable |
| 35 | Grado di apertura commerciale del comparto agro-alimentare | 2022 | - | - | unavailable |
| 431 | Grado di apertura commerciale del comparto manifatturiero | 2019 | - | - | unavailable |
| 97 | Grado di apertura dei mercati: importazioni | 2022 | - | - | unavailable |
| 100 | Grado di dipendenza economica | 2021 | - | - | unavailable |
| 231 | Grado di insoddisfazione dell'utenza per l'erogazione di gas | 2025 | - | - | unavailable |
| 428 | Grado di partecipazione dei cittadini attraverso il web a attività politiche e sociali | 2022 | - | - | unavailable |
| 24 | Grado di promozione dell'offerta culturale dei musei e degli istituti similari statali | 2024 | - | - | unavailable |
| 259 | Grado di promozione dell'offerta culturale dei musei e istituti similari non statali | 2022 | - | - | unavailable |
| 210 | Grado di soddisfazione del servizio di trasporto ferroviario a livello regionale (Femmine) | 2025 | - | - | unavailable |
| 209 | Grado di soddisfazione del servizio di trasporto ferroviario a livello regionale (Maschi) | 2025 | - | - | unavailable |
| 172 | Grado di soddisfazione del servizio di trasporto ferroviario a livello regionale (Totale) | 2025 | - | - | unavailable |
| 469 | Grado di utilizzo dell'e-procurement nella PA | 2022 | - | - | unavailable |
| 122 | Importanza economica del settore della pesca | 2023 | - | - | unavailable |
| 402 | Imprenditorialità femminile | 2023 | - | - | unavailable |
| 401 | Imprenditorialità giovanile (totale) | 2023 | - | - | unavailable |
| 32 | Incidenza dei biglietti venduti nei circuiti museali | 2024 | - | - | unavailable |
| 409 | Incidenza dei diplomati nei percorsi di istruzione tecnica e professionale sul totale dei diplomati | 2021 | - | - | unavailable |
| 145 | Incidenza del costo dell'ADI sul totale della spesa sanitaria | 2012 | - | - | unavailable |
| 595 | Incidenza del valore aggiunto dei settori culturali e creativi sul totale | 2023 | - | - | unavailable |
| 158 | Incidenza della certificazione ambientale | 2025 | - | - | unavailable |
| 615 | Incidenza della popolazione residente in comuni senza alcuna offerta culturale | 2022 | - | - | unavailable |
| 614 | Incidenza della popolazione residente in comuni senza offerta di spettacolo, intrattenimento e sport | 2023 | - | - | unavailable |
| 418 | Incidenza della spesa per R&S del settore privato sul PIL | 2022 | - | - | unavailable |
| 28 | Incidenza della spesa per ricreazione e cultura | 2021 | - | - | unavailable |
| 92 | Incidenza della spesa pubblica per R&S sul PIL | 2022 | - | - | unavailable |
| 114 | Incidenza della spesa totale per R&S sul PIL | 2022 | - | - | unavailable |
| 283 | Incidenza di associazione mafiosa | 2023 | - | - | unavailable |
| 44 | Indice del traffico aereo | 2023 | - | - | unavailable |
| 119 | Indice del traffico delle merci in navigazione di cabotaggio | 2023 | - | - | unavailable |
| 118 | Indice del traffico merci su strada | 2023 | - | - | unavailable |
| 930 | Indice di Gini del reddito | 2024 | - | - | unavailable |
| 445 | Indice di accessibilità verso i nodi urbani e logistici | 2013 | - | - | unavailable |
| 244 | Indice di attrattività delle università | 2020 | - | - | unavailable |
| 30 | Indice di domanda culturale (circuiti museali) | 2020 | - | - | unavailable |
| 257 | Indice di domanda culturale dei musei e istituti similari non statali (media per istituto) | 2022 | - | - | unavailable |
| 258 | Indice di domanda culturale dei musei e istituti similari non statali (per Kmq) | 2022 | - | - | unavailable |
| 18 | Indice di domanda culturale dei musei e istituti similari statali | 2024 | - | - | unavailable |
| 23 | Indice di domanda culturale dei musei e istituti similari statali (per Kmq) | 2024 | - | - | unavailable |
| 372 | Indice di domanda culturale dei musei e istituti similari statali e non statali | 2022 | - | - | unavailable |
| 134 | Indice di microcriminalità nelle città (1) | 2023 | - | - | unavailable |
| 135 | Indice di microcriminalità nelle città (2) | 2023 | - | - | unavailable |
| 633 | Indice di povertà relativa regionale familiare (famiglie) | 2024 | - | - | unavailable |
| 631 | Indice di povertà relativa regionale individuale (popolazione) | 2024 | - | - | unavailable |
| 46 | Indice di utilizzazione del trasporto ferroviario (1) | 2025 | - | - | unavailable |
| 212 | Indice di utilizzazione del trasporto ferroviario (1) (femmine) | 2024 | - | - | unavailable |
| 211 | Indice di utilizzazione del trasporto ferroviario (1) (maschi) | 2024 | - | - | unavailable |
| 47 | Indice di utilizzazione del trasporto ferroviario (2) | 2025 | - | - | unavailable |
| 170 | Indice traffico merci su ferrovia | 2010 | - | - | unavailable |
| 103 | Inquinamento causato dai mezzi di trasporto | 2019 | - | - | unavailable |
| 152 | Intensità brevettuale | 2012 | - | - | unavailable |
| 167 | Intensità di accumulazione del capitale | 2023 | - | - | unavailable |
| 60 | Interruzioni del servizio elettrico | 2023 | - | - | unavailable |
| 159 | Investimenti diretti della regione all'estero | 2011 | - | - | unavailable |
| 166 | Investimenti diretti netti dall'estero in Italia sul Pil | 2011 | - | - | unavailable |
| 164 | Investimenti in capitale di rischio - expansion e replacement | 2019 | - | - | unavailable |
| 471 | Investimenti privati sul PIL | 2023 | - | - | unavailable |
| 6 | Irregolarità nella distribuzione dell'acqua | 2025 | - | - | unavailable |
| 90 | Laureati in scienza e tecnologia | 2012 | - | - | unavailable |
| 196 | Laureati in scienza e tecnologia (femmine) | 2012 | - | - | unavailable |
| 194 | Laureati in scienza e tecnologia (maschi) | 2012 | - | - | unavailable |
| 77 | Livello di istruzione della popolazione 15-19 anni | 2024 | - | - | unavailable |
| 190 | Livello di istruzione della popolazione 15-19 anni (femmine) | 2024 | - | - | unavailable |
| 189 | Livello di istruzione della popolazione 15-19 anni (maschi) | 2024 | - | - | unavailable |
| 104 | Livello di istruzione della popolazione adulta | 2024 | - | - | unavailable |
| 276 | Lunghezza della rete autostradale | 2014 | - | - | unavailable |
| 273 | Lunghezza della rete stradale | 2014 | - | - | unavailable |
| 519 | Merce nel complesso della navigazione per tipo di carico - ALTRO CARICO | 2023 | - | - | unavailable |
| 515 | Merce nel complesso della navigazione per tipo di carico - CONTENITORI | 2023 | - | - | unavailable |
| 516 | Merce nel complesso della navigazione per tipo di carico - RINFUSA LIQUIDA | 2023 | - | - | unavailable |
| 517 | Merce nel complesso della navigazione per tipo di carico - RINFUSA SOLIDA | 2023 | - | - | unavailable |
| 518 | Merce nel complesso della navigazione per tipo di carico - RO-RO | 2023 | - | - | unavailable |
| 363 | Minori a rischio di povertà o esclusione sociale - Europa 2030 (femmine) | 2024 | - | - | unavailable |
| 364 | Minori a rischio di povertà o esclusione sociale - Europa 2030 (maschi) | 2024 | - | - | unavailable |
| 361 | Minori a rischio di povertà o esclusione sociale - Europa 2030 (totale) | 2024 | - | - | unavailable |
| 370 | Minori in condizione di grave deprivazione materiale e sociale - Europa 2030 (femmine) | 2024 | - | - | unavailable |
| 369 | Minori in condizione di grave deprivazione materiale e sociale - Europa 2030 (maschi) | 2024 | - | - | unavailable |
| 368 | Minori in condizione di grave deprivazione materiale e sociale - Europa 2030 (totale) | 2024 | - | - | unavailable |
| 265 | Monitoraggio della qualità dell'aria | 2012 | - | - | unavailable |
| 67 | Non occupati che partecipano ad attività formative e di istruzione | 2024 | - | - | unavailable |
| 188 | Non occupati che partecipano ad attività formative e di istruzione (femmine) | 2024 | - | - | unavailable |
| 187 | Non occupati che partecipano ad attività formative e di istruzione (maschi) | 2024 | - | - | unavailable |
| 63 | Occupati che partecipano ad attività formative e di istruzione | 2024 | - | - | unavailable |
| 186 | Occupati che partecipano ad attività formative e di istruzione (femmine) | 2024 | - | - | unavailable |
| 185 | Occupati che partecipano ad attività formative e di istruzione (maschi) | 2024 | - | - | unavailable |
| 637 | Ospiti adulti con disabilità o patologia psichiatrica dei presidi residenziali socio-assistenziali e socio-sanitari per centomila adulti | 2022 | - | - | unavailable |
| 638 | Ospiti anziani non autosufficienti dei presidi residenziali socio-assistenziali e socio-sanitari per centomila anziani | 2022 | - | - | unavailable |
| 640 | Ospiti con disabilità o non autosufficienti dei presidi residenziali socio-assistenziali e socio-sanitari per centomila abitanti | 2022 | - | - | unavailable |
| 639 | Ospiti minori con disabilità o disturbi mentali dei presidi residenziali socio-assistenziali e socio-sanitari per centomila minori | 2022 | - | - | unavailable |
| 901 | PIL pro capite | 2024 | - | - | unavailable |
| 108 | Partecipazione della popolazione al mercato del lavoro | 2025 | - | - | unavailable |
| 268 | Passeggeri trasportati dal TPL nei comuni capoluogo di provincia per abitante | 2023 | - | - | unavailable |
| 441 | Percentuale di habitat con stato di conservazione favorevole | 2018 | - | - | unavailable |
| 232 | Percentuale di rifiuti urbani smaltiti in discarica | 2024 | - | - | unavailable |
| 641 | Percentuale di scuole con alunni con disabilità nelle quali sono presenti postazioni informatiche adattate | 2023 | - | - | unavailable |
| 651 | Percentuale di scuole dotate di mappe a rilievo | 2023 | - | - | unavailable |
| 649 | Percentuale di scuole dotate di percorsi esterni accessibili | 2018 | - | - | unavailable |
| 648 | Percentuale di scuole dotate di percorsi interni accessibili | 2018 | - | - | unavailable |
| 647 | Percentuale di scuole dotate di porte a norma | 2023 | - | - | unavailable |
| 646 | Percentuale di scuole dotate di scale a norma | 2023 | - | - | unavailable |
| 645 | Percentuale di scuole dotate di servizi igienici a norma | 2023 | - | - | unavailable |
| 642 | Percentuale di scuole dotate di un accesso con rampe | 2023 | - | - | unavailable |
| 643 | Percentuale di scuole dotate di un ascensore per il trasporto di persone con disabilità | 2023 | - | - | unavailable |
| 644 | Percentuale di scuole dotate di un servoscala e/o piattaforma elevatrice | 2023 | - | - | unavailable |
| 650 | Percentuale scuole dotate di segnali acustici o/e visivi | 2023 | - | - | unavailable |
| 43 | Percezione delle famiglie del rischio di criminalità nella zona in cui vivono | 2024 | - | - | unavailable |
| 360 | Persone a rischio di povertà o esclusione sociale - Europa 2030 (femmine) | 2024 | - | - | unavailable |
| 359 | Persone a rischio di povertà o esclusione sociale - Europa 2030 (maschi) | 2024 | - | - | unavailable |
| 285 | Persone a rischio di povertà o esclusione sociale - Europa 2030 (totale) | 2024 | - | - | unavailable |
| 371 | Persone che vivono in situazioni di sovraffollamento abitativo, in abitazioni prive di alcuni servizi e con problemi strutturali | 2024 | - | - | unavailable |
| 367 | Persone in condizioni di grave deprivazione materiale e sociale - Europa 2030 (femmine) | 2024 | - | - | unavailable |
| 366 | Persone in condizioni di grave deprivazione materiale e sociale - Europa 2030 (maschi) | 2024 | - | - | unavailable |
| 365 | Persone in condizioni di grave deprivazione materiale e sociale - Europa 2030 (totale) | 2024 | - | - | unavailable |
| 120 | Peso delle società cooperative | 2019 | - | - | unavailable |
| 253 | Popolazione equivalente urbana servita da depurazione | 2015 | - | - | unavailable |
| 278 | Popolazione esposta a rischio alluvione | 2020 | - | - | unavailable |
| 277 | Popolazione esposta a rischio frane | 2024 | - | - | unavailable |
| 82 | Popolazione regionale servita da gas metano | 2006 | - | - | unavailable |
| 10 | Popolazione regionale servita da impianti di depurazione completa delle acque reflue | 2008 | - | - | unavailable |
| 245 | Popolazione residente nei comuni rurali | 2013 | - | - | unavailable |
| 247 | Popolazione residente nei comuni rurali (Maschi) | 2013 | - | - | unavailable |
| 246 | Popolazione residente nei comuni rurali (femmine) | 2013 | - | - | unavailable |
| 269 | Posti-km offerti dal TPL nei comuni capoluogo di provincia | 2023 | - | - | unavailable |
| 144 | Presa in carico degli anziani per il servizio di assistenza domiciliare integrata | 2022 | - | - | unavailable |
| 414 | Presa in carico di tutti gli utenti dei servizi per l'infanzia | 2023 | - | - | unavailable |
| 34 | Principi attivi contenuti nei prodotti fitosanitari | 2024 | - | - | unavailable |
| 31 | Produttività dei terreni agricoli | 2024 | - | - | unavailable |
| 1 | Produttività del lavoro in agricoltura | 2023 | - | - | unavailable |
| 596 | Produttività del lavoro nei settori culturali e creativi | 2023 | - | - | unavailable |
| 130 | Produttività del lavoro nel commercio | 2023 | - | - | unavailable |
| 107 | Produttività del lavoro nell'industria alimentare | 2023 | - | - | unavailable |
| 123 | Produttività del lavoro nell'industria in senso stretto | 2023 | - | - | unavailable |
| 124 | Produttività del lavoro nell'industria manifatturiera | 2023 | - | - | unavailable |
| 109 | Produttività del settore della pesca | 2023 | - | - | unavailable |
| 405 | Progetti e interventi che rispettano i crono-programmi di attuazione e un tracciato unico completo | 2013 | - | - | unavailable |
| 53 | Quantità di frazione umida trattata in impianti di compostaggio per la produzione di compost di qualità | 2024 | - | - | unavailable |
| 435 | Quota di lavoratori che percepiscono sussidi di politica del lavoro passiva: Cassa integrazione e Contratti di solidarietà | 2015 | - | - | unavailable |
| 11 | Quota di popolazione equivalente servita da depurazione | 2015 | - | - | unavailable |
| 593 | Quota di unità locali nei settori culturali e creativi sul totale | 2023 | - | - | unavailable |
| 52 | Raccolta differenziata dei rifiuti urbani | 2024 | - | - | unavailable |
| 905 | Redditi da lavoro dipendente per unità di lavoro | 2024 | - | - | unavailable |
| 902 | Reddito disponibile delle famiglie per abitante | 2024 | - | - | unavailable |
| 906 | Reddito primario per abitante | 2024 | - | - | unavailable |
| 391 | Resilienza ai Terremoti degli Insediamenti, per assenza del piano di emergenza | 2016 | - | - | unavailable |
| 392 | Resilienza ai Terremoti degli Insediamenti, per presenza del piano di emergenza | 2016 | - | - | unavailable |
| 394 | Resilienza ai Terremoti degli Insediamenti, per presenza di analisi della CLE | 2016 | - | - | unavailable |
| 393 | Resilienza ai Terremoti degli Insediamenti, per presenza di microzonazione sismica | 2016 | - | - | unavailable |
| 263 | Rete Natura 2000 | 2021 | - | - | unavailable |
| 270 | Rete ferroviaria | 2018 | - | - | unavailable |
| 272 | Rete ferroviaria a doppio binario | 2018 | - | - | unavailable |
| 271 | Rete ferroviaria elettrificata | 2018 | - | - | unavailable |
| 84 | Rifiuti urbani smaltiti in discarica per abitante | 2024 | - | - | unavailable |
| 162 | Rischio dei finanziamenti | 2018 | - | - | unavailable |
| 406 | Ritardo nei tempi di attuazione delle opere pubbliche | 2013 | - | - | unavailable |
| 907 | Saldo della redistribuzione del reddito per abitante | 2024 | - | - | unavailable |
| 412 | Scuole che hanno aderito al Sistema Nazionale di Valutazione (VALES) | 2014 | - | - | unavailable |
| 410 | Sicurezza degli edifici scolastici | 2012 | - | - | unavailable |
| 261 | Siti di Importanza Comunitaria (SIC) | 2021 | - | - | unavailable |
| 421 | Specializzazione produttiva nei settori ad alta tecnologia (femmine) | 2025 | - | - | unavailable |
| 420 | Specializzazione produttiva nei settori ad alta tecnologia (maschi) | 2025 | - | - | unavailable |
| 419 | Specializzazione produttiva nei settori ad alta tecnologia (totale) | 2025 | - | - | unavailable |
| 653 | Spesa dei Comuni per assistenza domiciliare per area utenza Anziani per utente anziano | 2021 | - | - | unavailable |
| 654 | Spesa dei Comuni per assistenza domiciliare per area utenza Disabilità per utente con disabilità | 2021 | - | - | unavailable |
| 634 | Spesa dei Comuni per strutture residenziali per area utenza Anziani per utente | 2021 | - | - | unavailable |
| 652 | Spesa dei Comuni per strutture residenziali per area utenza Disabilità per utente | 2021 | - | - | unavailable |
| 25 | Spesa del pubblico per spettacoli teatrali e musicali | 2023 | - | - | unavailable |
| 111 | Studenti con elevate competenze in lettura | 2012 | - | - | unavailable |
| 112 | Studenti con elevate competenze in matematica | 2012 | - | - | unavailable |
| 106 | Studenti con scarse competenze in lettura | 2012 | - | - | unavailable |
| 110 | Studenti con scarse competenze in matematica | 2012 | - | - | unavailable |
| 255 | Superficie boscata e non boscata percorsa dal fuoco | 2022 | - | - | unavailable |
| 514 | Superficie boscata percorsa dal fuoco | 2022 | - | - | unavailable |
| 442 | Superficie delle Aree agricole ad Alto Valore Naturale | 2010 | - | - | unavailable |
| 239 | Superficie forestale | 2005 | - | - | unavailable |
| 5 | Superficie irrigata/irrigabile nelle aziende agricole | 2020 | - | - | unavailable |
| 76 | TAVOLA DISMESSA - Indice di povertà regionale (famiglie) | 2021 | - | - | unavailable |
| 74 | TAVOLA DISMESSA - Indice di povertà regionale (popolazione) | 2021 | - | - | unavailable |
| 87 | Tasso di abbandono alla fine del primo anno delle scuole secondarie superiori | 2019 | - | - | unavailable |
| 254 | Tasso di abbandono alla fine del primo biennio delle scuole secondarie superiori | 2019 | - | - | unavailable |
| 89 | Tasso di abbandono alla fine del secondo anno delle scuole secondarie superiori | 2019 | - | - | unavailable |
| 203 | Tasso di attività totale della popolazione (femmine) | 2025 | - | - | unavailable |
| 213 | Tasso di attività totale della popolazione (maschi) | 2025 | - | - | unavailable |
| 284 | Tasso di criminalità minorile | 2016 | - | - | unavailable |
| 282 | Tasso di criminalità organizzata e di tipo mafioso | 2023 | - | - | unavailable |
| 279 | Tasso di furti denunciati | 2023 | - | - | unavailable |
| 148 | Tasso di innovazione del sistema produttivo | 2020 | - | - | unavailable |
| 113 | Tasso di irregolarità del lavoro | 2012 | - | - | unavailable |
| 339 | Tasso di istruzione terziaria nella fascia d'età 30-34 anni | 2023 | - | - | unavailable |
| 342 | Tasso di istruzione terziaria nella fascia d'età 30-34 anni (femmine) | 2023 | - | - | unavailable |
| 340 | Tasso di istruzione terziaria nella fascia d'età 30-34 anni (maschi) | 2023 | - | - | unavailable |
| 281 | Tasso di omicidi | 2023 | - | - | unavailable |
| 248 | Tasso di partecipazione nell'istruzione secondaria superiore | 2020 | - | - | unavailable |
| 192 | Tasso di partecipazione nell'istruzione secondaria superiore (femmine) | 2020 | - | - | unavailable |
| 191 | Tasso di partecipazione nell'istruzione secondaria superiore (maschi) | 2020 | - | - | unavailable |
| 280 | Tasso di rapine denunciate | 2023 | - | - | unavailable |
| 101 | Tasso di scolarizzazione superiore | 2024 | - | - | unavailable |
| 105 | Tasso di turisticità | 2024 | - | - | unavailable |
| 443 | Tasso di turisticità nei parchi nazionali e regionali | 2018 | - | - | unavailable |
| 451 | Tempo medio di sdoganamento nei porti | 2015 | - | - | unavailable |
| 22 | Tonnellate di merci in ingresso ed in uscita in navigazione di cabotaggio sul totale delle modalità | 2010 | - | - | unavailable |
| 20 | Tonnellate di merci in ingresso ed in uscita per ferrovia sul totale delle modalità | 2010 | - | - | unavailable |
| 26 | Tonnellate di merci in ingresso ed in uscita su strada sul totale delle modalità | 2010 | - | - | unavailable |
| 450 | Traffico ferroviario merci generato da porti e interporti | 2018 | - | - | unavailable |
| 452 | Traffico passeggeri da e per aeroporti su mezzi pubblici collettivi | 2015 | - | - | unavailable |
| 138 | Trasporto pubblico locale nelle città | 2013 | - | - | unavailable |
| 208 | Utilizzo di mezzi pubblici di trasporto da parte di occupati, studenti, scolari e utenti di mezzi pubblici (femmine) | 2025 | - | - | unavailable |
| 207 | Utilizzo di mezzi pubblici di trasporto da parte di occupati, studenti, scolari e utenti di mezzi pubblici (maschi) | 2025 | - | - | unavailable |
| 129 | Utilizzo di mezzi pubblici di trasporto da parte di occupati, studenti, scolari e utenti di mezzi pubblici (totale) | 2025 | - | - | unavailable |
| 903 | Valore aggiunto per abitante | 2024 | - | - | unavailable |
| 904 | Valore aggiunto per unità di lavoro | 2024 | - | - | unavailable |
| 163 | Valore degli investimenti in capitale di rischio - early stage | 2019 | - | - | unavailable |
| 568 | Valutazione dei livelli di apprendimento degli studenti della quinta classe primaria in inglese reading | 2019 | - | - | unavailable |
| 546 | Valutazione dei livelli di apprendimento degli studenti della quinta classe primaria in italiano | 2019 | - | - | unavailable |
| 547 | Valutazione dei livelli di apprendimento degli studenti della quinta classe primaria in matematica | 2019 | - | - | unavailable |
| 543 | Valutazione dei livelli di apprendimento degli studenti della seconda classe primaria in italiano | 2019 | - | - | unavailable |
| 545 | Valutazione dei livelli di apprendimento degli studenti della seconda classe primaria in matematica | 2019 | - | - | unavailable |
| 550 | Valutazione dei livelli di apprendimento degli studenti della seconda classe secondaria di secondo grado in italiano | 2019 | - | - | unavailable |
| 551 | Valutazione dei livelli di apprendimento degli studenti della seconda classe secondaria di secondo grado in matematica | 2019 | - | - | unavailable |
| 569 | Valutazione dei livelli di apprendimento degli studenti della terza classe secondaria di primo grado in inglese listening | 2019 | - | - | unavailable |
| 571 | Valutazione dei livelli di apprendimento degli studenti della terza classe secondaria di primo grado in inglese listening | 2019 | - | - | unavailable |
| 570 | Valutazione dei livelli di apprendimento degli studenti della terza classe secondaria di primo grado in inglese reading | 2019 | - | - | unavailable |
| 548 | Valutazione dei livelli di apprendimento degli studenti della terza classe secondaria di primo grado in italiano | 2019 | - | - | unavailable |
| 549 | Valutazione dei livelli di apprendimento degli studenti della terza classe secondaria di primo grado in matematica | 2019 | - | - | unavailable |
| 438 | Velocità del trasporto pubblico su gomma nei comuni capoluogo di provincia | 2020 | - | - | unavailable |
| 252 | Verde pubblico nelle città | 2016 | - | - | unavailable |
| 29 | Volume di lavoro impiegato nel settore ricreazione e cultura | 2012 | - | - | unavailable |
| 262 | Zone a Protezione Speciale (ZPS) | 2021 | - | - | unavailable |
