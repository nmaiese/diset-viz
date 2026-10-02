# Ricerca R2b: Istat regionale 2025 non ancora in catalogo

Data: 2026-10-01. Solo ricerca, nessuna modifica al codice. Flusso: Istat regionale da Multiscopo e altri flussi.

## Metodo e budget di rete

- Catalogo dataflow letto dalla cache condivisa (`data/istat_cache`, symlink alla cache gitignorata, ultimo aggiornamento del catalogo 2026-06-25): zero richieste. Ogni dataflow porta l'annotazione `LAST_UPDATE`, usata per capire quali sono stati rilasciati con l'edizione 2025.
- Richieste di rete fatte: **23 su 25**, tutte con `scripts/istat_sdmx.py` (cache-first, 16 s, un solo processo): 21 dataflow dati (intero flusso, nessun filtro, `Accept: application/vnd.sdmx.data+csv;version=1.0.0`) e 2 codelist (`CL_TIPO_DATO_AVQ`, `CL_MISURA_AVQ`) per leggere le etichette dei codici. Nessun curl diretto a esploradati, nessun 429/403.
- Licenza: pagina `https://www.istat.it/note-legali/`, letta con WebFetch (riassunto del modello, non copia integrale): "Attribuzione — Devi riconoscere una menzione di paternità adeguata, fornire un link alla licenza e indicare se sono state effettuate delle modifiche." Cioè CC BY 4.0, come per il resto dei flussi Istat già in catalogo.
- URL pagina di metodo (preso dall'annotazione `METADATA_URL` del dataflow, **non aperto** per il vincolo di rete: "non verificato"): `https://esploradati.istat.it/RefMeta/template/GenericMetadataTemplate.html?nodeId=DW&metadataSetId=MS_ISTAT_TOPMETA2&reportId=<DSD>&lang=en&BaseUrlMDA=https://esploradati.istat.it/METADATA_API`, con `<DSD>` = `DCCV_AVQ_PERSONE1` (flussi 83_85), `DCCV_AVQ_PERSONE` (flussi 83_63), `DCCV_AVQ_FAMIGLIE` (flussi 82_87). Il `reportId` per 83_63 e 82_87 è dedotto dal nome del DSD, non letto dall'annotazione.
- URL del dato (uguale per tutti): `https://esploradati.istat.it/SDMXWS/rest/data/<FLOW_ID>` con header Accept SDMX-CSV 1.0.0.

## Fatti comuni a tutti i candidati

- Famiglia di flussi: Indagine Multiscopo «Aspetti della vita quotidiana» (AVQ), Istat. Sono le stesse tre famiglie già usate da `scripts/multiscopo_sources.py` (`82_87_..._AVQ_FAMIGLIE_*`, `83_63_..._AVQ_PERSONE_*`, `83_85_..._AVQ_PERSONE1_*`), ma flussi diversi: **nessuno dei flussi qui sotto è in `MULTISCOPO_INDICATORS`** (in catalogo ci sono 82_87_101, 83_63_141, 83_85_231, e i flussi 33_*, 34_216/226, 31_740, 32_*, 60_130).
- Territorio: `REF_AREA` NUTS2 `ITC1..ITG2`, **21 codici su 21 in ogni serie del 2025** (Bolzano `ITD1` e Trento `ITD2` separati: vanno composti in Trentino-Alto Adige con la media ponderata già prevista, `TRENTINO_WEIGHTS`). I flussi contengono anche codici di ripartizione (`ITC`, `ITD`...), `ITCD`, `ITFG` e codici numerici `1..9` per tipo di comune: vanno scartati come nei flussi già in catalogo.
- Dimensioni fisse: `FREQ=A`; `SEX=9`, `AGE`, `EDU_LEV_HIGHEST=99`, `LABOUR_PROFESS_STATUS_B=99` costanti (totale). Il flusso 82_87_15 ha `NUMBER_HOUSEHOLD_COMP=TOT`.
- Misure (codelist `CL_MISURA_AVQ`): `HSC` = «per 100 persone con le stesse caratteristiche», `HSC_F` = per 100 famiglie, `TSC` = «per 1000 persone con le stesse caratteristiche», `AVE` = valore medio, `THV` = valori in migliaia (**assoluto: da scartare**, va sempre filtrato `MEASURE`).
- Ultimo anno di riferimento: **2025 in tutte le serie dei candidati**, 21/21 regioni, `OBS_STATUS` vuoto. Primo anno 2001 (flussi 83_63), 1993 o 2001 (83_85), 1997 (82_87_15). Frequenza annuale; il rilascio 2025 è di aprile-giugno 2026 (`LAST_UPDATE` dei flussi: 2026-02-26, 2026-04-01, 2026-05-19, 2026-06-25). Il catalogo letto è del 25 giugno: non si può escludere un rilascio successivo, ma sono già le edizioni 2025.
- Attenzione al manifest esistente: alcuni flussi AVQ già in catalogo si fermano al 2024 (83_63_141 soddisfazione per la vita, 60_130 ICT) perché quei flussi non hanno ancora il 2025. I flussi qui sotto invece sì.
- Integrazione comune: stesso formato SDMX-CSV già letto da `update_multiscopo_regions.py`; stesso join (codici NUTS2); filtro da dare = `DATA_TYPE` + `MEASURE` (+ `SEX=9` dove la colonna è presente). Nessun anno mancante nelle serie scelte (24 anni consecutivi, 2001-2025, dove indicato).

## Candidati (ordinati per valore)

Tutti i valori sotto sono letti dai file scaricati, anno 2025, regioni NUTS2 (Bolzano e Trento sono righe separate). "basso / medio / alto" = minimo, mediano e massimo tra le 21 regioni.

### 1. Pronto soccorso e guardia medica: persone che li hanno usati negli ultimi 3 mesi

- Istituzione: Istat, Indagine Multiscopo Aspetti della vita quotidiana.
- Flusso `83_63_DF_DCCV_AVQ_PERSONE_216` («First aid and holiday and night-time medical care - regions and type of municipality»). DATA_TYPE `0_FA` (pronto soccorso) e `0_MG` (guardia medica), `MEASURE=TSC`, `SEX=9`.
- Unità: per 1000 persone (relativo). Serie 2001-2025, 24 anni.
- Verso: **contextual**. Un uso alto del pronto soccorso può segnalare una medicina territoriale debole o semplicemente più accesso; non c'è un verso onesto.
- Doppione: nuovo. Nessun nome con «pronto soccorso» o «guardia medica» in `Assoluti_Regione.csv`, né nei manifest BES/province/Multiscopo/esterni (cercati: pronto soccorso, guardia, ricover).
- Esempio `0_FA` 2025: Campania 42,5 (basso), Toscana 71,5 (medio), Emilia-Romagna 100,5 (alto). `0_MG` 2025: Liguria 23,8, Toscana 39,4, Basilicata 68,5.
- Difficoltà: nessuna oltre al join NUTS2; campione regionale con intervallo di confidenza non letto (rischio di rumore sulle regioni piccole, per questo conviene mostrarne la serie, non il solo anno).

### 2. Attesa agli sportelli: utenti con fila oltre 20 minuti (ASL, banca)

- Flussi `83_85_DF_DCCV_AVQ_PERSONE1_104` (ASL) e `83_85_DF_DCCV_AVQ_PERSONE1_109` (banca). DATA_TYPE `18_ASL_DUR_GE20` («persone di 18 anni e più che si sono recate alla ASL: per durata della fila: più di 20 minuti») e `18_BA_DUR_GE20`; `MEASURE=HSC`, `SEX=9`. (Il flusso 83_85_108, ufficio postale, ha la stessa struttura: `18_UP_...`; non proposto perché le serie per tipo di operazione sono troppo frammentate.)
- Unità: %, relativo; la base è chi è andato allo sportello: le tre classi di durata di ASL sommano a 100 (controllato sul file: Piemonte 15 + 33,8 + 50,8 = 99,6, arrotondamento). Serie ASL 1993-2025, banca 2001-2025.
- Verso: **lower_better** (fila lunga = servizio peggiore), onesto perché misura il tempo di attesa, non il volume.
- Doppione: nuovo. Il BES `12SER004` «Difficoltà di accesso ad alcuni servizi» (2024) è un composto sulla raggiungibilità, non sul tempo di fila.
- Esempio `18_ASL_DUR_GE20` 2025: Bolzano 22,2 (basso), Lombardia 49,4 (medio), Calabria 71,5 (alto). `18_BA_DUR_GE20`: Bolzano 3,4, Toscana 14,3, Sicilia 33,9.
- Difficoltà: nessuna. Attenzione alla base ridotta (solo chi ha usato lo sportello).

### 3. Soddisfazione per il ricovero (assistenza medica, infermieristica, servizi igienici, vitto)

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_256` («Satisfaction with health care facilities - regions and type of municipality»). DATA_TYPE: `0_MED_CAREQ` (assistenza medica «molto e abbastanza»), `0_NURS_Q` (infermieristica), `0_SANFAC_Q` (servizi igienici), `0_HFOOD_Q` (vitto) e le varianti `_V` («molto»). `MEASURE=HSC`, `SEX=9`. L'etichetta ufficiale è lunga: «persone con almeno un ricovero nei tre mesi precedenti l'intervista per soddisfazione per vari aspetti del ricovero: ...».
- Unità: %, relativo. Serie 2001-2025.
- Verso: **higher_better** (soddisfazione).
- Doppione: nuovo (il BES ha `12SER026` Rinuncia a prestazioni sanitarie, 2024, che è altra cosa).
- Esempio `0_MED_CAREQ` 2025: Marche 72,1 (basso), Lazio 84,2 (medio), Sardegna 92,0 (alto). `0_SANFAC_Q`: Campania 60,9, Valle d'Aosta 78,9, Trento 88,0.
- Difficoltà: **campione piccolo** (solo chi è stato ricoverato in 3 mesi): rumore alto, specie nelle regioni piccole. Consigliabile una sola serie sintetica (assistenza medica) e una nota di cautela; non usarla in indici compositi.

### 4. Incidenti domestici: persone infortunate negli ultimi 3 mesi

- Flusso `83_85_DF_DCCV_AVQ_PERSONE1_235` («Domestic accidents - regions and type of municipality»). DATA_TYPE `0_DOM_ACC` («persone che hanno subito incidenti in ambiente domestico negli ultimi tre mesi: persone che hanno subito incidenti»), `MEASURE=TSC`, `SEX=9`. (`AV0_DOM_ACC`, numero medio di incidenti per infortunato, ha anch'esso `TSC` come codice ma è un numero medio: non usarlo.)
- Unità: per 1000 persone, relativo. Serie 2001-2025.
- Verso: **lower_better**.
- Doppione: nuovo (cercati: incident → solo mortalità stradale 15-34 anni nel BES/province).
- Esempio 2025: Molise 4,4 (basso), Veneto 12,2 (medio), Trento 21,9 (alto).
- Difficoltà: valori piccoli e rumorosi (conteggio raro): meglio la media mobile di 3 anni, o mostrarlo con cautela.

### 5. Trasporto pubblico locale: soddisfazione di chi usa bus, filobus e tram

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_160` («Bus - regions and type of municipality»). DATA_TYPE (tutti `MEASURE=HSC`, `SEX=9`, età 14+): `14_BUS_SAT_FC` (frequenza delle corse), `14_BUS_SAT_WAIT` (comodità dell'attesa alle fermate), `14_BUS_SAT_COMF` (comodità degli orari), `14_BUS_SAT_CLEAN` (pulizia), `14_BUS_SAT_PS` (posto a sedere), più `14_BUS_FQ_EVD` (uso tutti i giorni o qualche volta a settimana). Etichetta: «persone di 14 anni e più che utilizzano l'autobus, il filobus e il tram molto e abbastanza soddisfatte per alcuni aspetti: ...».
- Unità: %, relativo (base: utenti). Serie 2001-2025.
- Verso: **higher_better** per le soddisfazioni; l'uso è contextual.
- **Doppione parziale**: il BES `12SER010` «Soddisfazione per i servizi di trasporto pubblico» (2024) e `12SER021` «Utenti assidui dei mezzi pubblici» (2024) sono composti dalla stessa indagine; qui si guadagna il 2025 e il dettaglio per aspetto (frequenza corse, attesa, orari). Da dichiarare «nuovo come dettaglio, non come tema».
- Esempio `14_BUS_SAT_FC` 2025: Lazio 37,0 (basso), Sardegna 68,1 (medio), Bolzano 88,4 (alto). `14_BUS_SAT_WAIT`: Lazio 22,2, Lombardia 47,5, Bolzano 77,7.
- Difficoltà: lo stesso flusso ha anche 83_63_158 (treno) e 83_63_159 (pullman), non scaricati.

### 6. Come si va al lavoro: occupati che usano auto, piedi o bicicletta

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_170` («Usual way of getting to work - regions and type of municipality»). DATA_TYPE (`MEASURE=HSC`, `SEX=9`, età 15+): `15_EMPMOV_PCAR` (auto privata come conducente), `15_EMPMOV_FOOT` (a piedi), `15_EMPMOV_BICYC` (bicicletta), `15_EMPMOV_BUS` (tram, bus), `15_EMPMOV_TRAIN` (treno), `15_EMPMOV_METRO`. Base: occupati che escono di casa per andare al lavoro.
- Unità: %, relativo. Serie 2001-2025.
- Verso: **contextual** (nessun verso onesto: dipende dal territorio). Per mobilità attiva (piedi + bici) un verso higher_better è difendibile ma è una scelta editoriale.
- **Doppione parziale**: `ter-129`, `ter-207`, `ter-208` «Utilizzo di mezzi pubblici di trasporto da parte di occupati, studenti...» (2025) coprono i mezzi pubblici. Qui sono nuovi auto privata, piedi, bici.
- Esempio `15_EMPMOV_PCAR` 2025: Liguria 55,8 (basso), Piemonte 72,1 (medio), Umbria 81,9 (alto). `15_EMPMOV_BICYC`: Basilicata 0,2, Valle d'Aosta 1,5, Bolzano 11,1.
- Difficoltà: nessuna.

### 7. Giovani 18-34 anni, celibi e nubili, che vivono con almeno un genitore

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_121` («Young people living in family - reg.»). DATA_TYPE `18_YOUNG` («giovani di 18-34 anni, celibi e nubili, che vivono in famiglia con almeno un genitore»), `MEASURE=HSC`, `SEX=9` (esistono anche `1` e `2`). Varianti: `18_YOUNG_EMP` (occupati), `18_YOUNG_STU` (studenti), `18_YOUNG_UNE` (in cerca).
- Unità: %, relativo. Serie 2001-2025. Ultimo aggiornamento del flusso 2026-06-25.
- Verso: **contextual** (alto = meno autonomia abitativa ma anche costi di casa; non c'è verso onesto).
- Doppione: nuovo (nessuna misura sulla convivenza con i genitori in catalogo).
- Esempio 2025: Bolzano 51,3 (basso), Valle d'Aosta 62,2 (medio), Sardegna 71,0 (alto).
- Difficoltà: nessuna. Si lega bene a `MULTI_ABIT_AFFITTO` e ai NEET.

### 8. Partecipazione culturale: cinema, teatro, musei e siti archeologici (persone 6+, almeno una volta nell'ultimo anno)

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_227` («Entertainments - regions and type of municipality»). DATA_TYPE `6_THEATR`, `6_CINEMA`, `6_ARCHEO_MUSEUM` («siti archeologici e monumenti»), più `6_MUS_SHOW` (musei e mostre: dato presente, etichetta non letta intera), `6_CONCER_CLAS_OPE`, `6_SPORT_ENTERT`, `6_DISCOT`. `MEASURE=HSC`, `SEX=9` (anche 1 e 2).
- Unità: %, relativo. Serie 2001-2025.
- Verso: **higher_better** (partecipazione), abbastanza onesto.
- **Doppione parziale**: BES `02IST022` «Partecipazione culturale fuori casa» (2025) è il composto; ter-27/611 sono domanda di spettacolo SIAE (altra fonte). Qui è nuovo il dettaglio per forma di spettacolo, con lo stesso anno.
- Esempio `6_THEATR` 2025: Basilicata 12,6 (basso), Campania 23,2 (medio), Bolzano 34,6 (alto). `6_ARCHEO_MUSEUM`: Calabria 17,9, Friuli-Venezia Giulia 32,4, Lazio 40,9.
- Difficoltà: nessuna.

### 9. Socialità: persone che incontrano gli amici ogni giorno o almeno una volta a settimana

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_107` («Meetings with friends - regions and type of municipality»). DATA_TYPE `6_EVERYD` (tutti i giorni), `6_1PWEEK` (una volta a settimana), `6_STIM_WEEK`, `6_GE1PWEEK`, `6_NEVER`, `6_NFRIEND`; `MEASURE=HSC`, `SEX=9`, età 6+.
- Unità: %, relativo. Serie 2001-2025.
- Verso: **contextual** (le categorie sono esclusive: «tutti i giorni» e «una volta a settimana» non si sommano da sole; una soglia «almeno settimanale» andrebbe composta).
- Doppione: nuovo come frequenza (BES `05REL002` è soddisfazione per le relazioni amicali, `05REL010` partecipazione sociale: concetti vicini ma diversi).
- Esempio `6_EVERYD` 2025: Lazio 6,2 (basso), Umbria 11,3 (medio), Calabria 15,9 (alto).
- Difficoltà: serve la composizione di categorie.

### 10. Dotazioni delle famiglie: condizionatori, più di un'auto, accesso a Internet

- Flusso `82_87_DF_DCCV_AVQ_FAMIGLIE_15` («Ownership of durable goods - reg. and type of municipality»). `MEASURE=HSC_F`, `NUMBER_HOUSEHOLD_COMP=TOT`. DATA_TYPE: `HOUS_AIRCON` (condizionatori, climatizzatori), `HOUS_CARS` (più di un'automobile), `HOUS_CAR`, `HOUS_BICY`, `HOUS_DISH` (lavastoviglie), `HOUS_INTER` (accesso a Internet), `HOUS_GPC` (PC). Serie fino al 2025 (alcune, come fax e modem, si fermano al 2020: scartarle).
- Unità: per 100 famiglie, relativo. Serie 1997-2025, 28 anni.
- Verso: **contextual** per condizionatori (alto al Sud per clima, non per benessere) e auto; `HOUS_INTER` higher_better ma **vicino al BES** `11RIC021` (2024).
- Doppione: nuovo per condizionatori, biciclette, lavastoviglie, più auto. Internet/PC sono quasi doppioni di `11RIC021` e di `ter-62`.
- Esempio `HOUS_AIRCON` 2025: Valle d'Aosta 6,6 (basso), Toscana 46,7 (medio), Sicilia 72,2 (alto). `HOUS_CARS`: Liguria 20,0, Molise 35,2, Marche 44,0. `HOUS_BICY` (biciclette): Calabria 23,9 (basso), il massimo è 76,2 (codice ITD3, Veneto) e il medio 46,8 (ITF1, Abruzzo).
- Difficoltà: nessuna; il flusso ha ~46.000 righe (molte serie).

### 11. Alimentazione: colazione adeguata, frutta e verdura quotidiana, 5 porzioni

- Flussi `83_85_DF_DCCV_AVQ_PERSONE1_239` (`3_ADEQ_BREAK`, «colazione adeguata (con latte e/o del cibo)», 1993-2025) e `83_85_DF_DCCV_AVQ_PERSONE1_251` (`3_VEG_FRUIT`, «verdure, ortaggi o frutta almeno una volta al giorno»; `3_GE5_PORTION`, «5 e più porzioni al giorno», 2005-2025). `MEASURE=HSC`, `SEX=9`, età 3+.
- Unità: %, relativo.
- Verso: **higher_better** (linee guida nutrizionali), ma solo per `3_GE5_PORTION` e `3_ADEQ_BREAK`; `3_VEG_FRUIT` è molto vicino a BES `01SAL013`.
- **Doppione parziale**: BES `01SAL013` «Adeguata alimentazione (tassi standardizzati)» (2025) è il composto; qui sono nuove la colazione e le 5 porzioni.
- Esempio `3_GE5_PORTION` 2025: Sicilia 3,2 (basso), Bolzano 5,4 (medio), Trento 11,1 (alto). `3_ADEQ_BREAK`: Calabria 73,9, Friuli-Venezia Giulia 81,0, Emilia-Romagna 83,8.
- Difficoltà: valore basso di rilevanza per l'atlante; meglio come scheda di contesto.

### 12. Ricoveri: persone ricoverate negli ultimi 3 mesi e giorni di degenza medi

- Flusso `83_63_DF_DCCV_AVQ_PERSONE_220` («Hospitalization - regions and type of municipality»). DATA_TYPE `0_1HOSP` (`TSC`, per 1000, «persone con almeno un ricovero nei 3 mesi precedenti l'intervista»), `AV_D_HOSP_0` (`AVE`, «giorni di degenza: media per ricovero»), `AV_P_HOSP_0` (media per persona ricoverata), `NHOSP_0` (ricoveri per 1000).
- Unità: per 1000 e giorni (relativi, ma la degenza media non è per abitante). Serie 2001-2025.
- Verso: **contextual** (nessun verso onesto: più ricoveri non è né meglio né peggio).
- Doppione: nuovo, ma di valore basso e rumoroso per le stesse ragioni del candidato 3.
- Esempio `0_1HOSP` 2025: Molise 17,3 (basso), Valle d'Aosta 25,4 (medio), Piemonte 33,6 (alto). `AV_D_HOSP_0`: Campania 4,9, Valle d'Aosta 6,6, Molise 11,4.
- Difficoltà: campione piccolo, serie che salta da un anno all'altro.

## Scartati e perché

Scartati per **ultimo anno ≤ 2024** (sezione richiesta: «a parte»):

- Soddisfazione per la vita (`83_63_DF_DCCV_AVQ_PERSONE_141`), ICT famiglie (`60_130_DF_DCCV_ICT_*`), reddito netto e fonte di reddito (`32_292`, `32_223`), spesa delle famiglie e Gini consumi (`31_740_..._11`, `LAST_UPDATE` 2025-10-07, ultimo anno 2024 nel manifest), `32_221` e `32_38` (reddito, aggiornati 2026-04-21 ma l'anno di riferimento dei redditi è 2024): già in catalogo o fermi al 2024 per manifest. Povertà assoluta regionale `34_727_DF_DCCV_POVERTA_8/10` (rilascio 2025-10-14): anno di riferimento 2024, il 2025 uscirà in autunno 2026. Non verificato con dato scaricato (non ho speso richieste su questi: è dedotto da `LAST_UPDATE` e dal manifest).
- Volontariato regionale (`85_84_DF_DCSA_VOLON1_6`): doppione del BES `05REL006` «Attività di volontariato» (2025).

Scartati per **territorio non regionale** (scaricati e controllati):

- `34_215_DF_DCCV_ARRETRATI_6` (famiglie con arretrati nei pagamenti, `FAM_ARR_SPESA`) e `34_217_DF_DCCV_CARICOPES_6` (giudizio sul carico delle spese, `FAM_GIUD_CARICO`): hanno il 2025 ma i `REF_AREA` sono solo Italia, ripartizioni (`ITC..ITG`) e tipi di comune; **nessun NUTS2**, nonostante il nome del flusso «Geographical areas and type of municipality».
- `82_87_DF_DCCV_AVQ_FAMIGLIE_9` (persone sole per età e sesso): 2025 ma solo ripartizioni.

Scartati per **assoluto**: ogni serie `MEASURE=THV` (valori in migliaia) di tutti i flussi sopra; i flussi `73_230` (vittime di reati per regione, assoluti), `122_54_DF_DCSC_TUR_*` (turismo per regione di residenza, assoluti), `121_*`, `11_111_*`, `22_222_*` (edilizia e trasporti merci, assoluti).

Scartati per **doppione**: lavoro regionale (`150_*`, `151_*`, `152_*`, `172_931` NEET: già coperti da ter e BES); `42_325`, `47_1219` non verificati (rilascio 2026 ma anno di riferimento probabilmente 2023, **non verificato**).

Scartati per **valore basso**: religiosità (`83_63_136`, `6_WEEK_RELIG`: Friuli-Venezia Giulia 13,6, Umbria 17,2, Calabria 27,1; verso inesistente), consumo di farmaci negli ultimi due giorni (`83_63_212`, `0_DRUGS_D`: Bolzano 35,5, Abruzzo 45,2, Liguria 49,4; contextual), uso del PC (`83_63_243`, `3_PCSI`: Calabria 45,6, Umbria 56,4, Bolzano 67,8; vicino a BES `11RIC020`/`11RIC021` che hanno 2024), pasti principali.

Non scaricati per rispettare il budget, ma presenti nel catalogo con `LAST_UPDATE` 2026 e nome regionale (candidati per un secondo giro): `83_63_158` (treno), `83_63_159` (pullman), `83_63_167` (come si va a scuola), `83_63_204` (fumo), `83_63_208` (stato di salute), `83_63_132` (attività sociali), `83_85_103` (anagrafe), `83_85_214/218/222/226` (acqua, vino e birra, superalcolici, alcol fuori pasto), `82_87_102` (fornitura di gas), `82_87_12/2/3/5/6` (tipologie familiari).

## Raccomandazione

Primi quattro da fare: 1 (pronto soccorso/guardia medica), 2 (fila oltre 20 minuti), 4 (incidenti domestici) e 7 (giovani con i genitori): sono nuovi, relativi, 21/21 al 2025 e non toccano il BES. Il 5, il 6 e l'8 sono utili ma solo come dettaglio dei composti BES già presenti. 3, 9, 10, 11, 12 hanno verso poco onesto o campione piccolo: farli dopo. Un'unica estrazione da `scripts/multiscopo_sources.py` copre tutti: serve solo aggiungere voci con `flow_id`, `DATA_TYPE` e `MEASURE` (e `SEX: 9` dove presente) e prevedere il parametro `MEASURE` `TSC`/`AVE`/`HSC_F` (il codice esistente usa `HSC` e `HSC_F`).

Non fatto: non ho aperto la pagina dei metadati Istat (esploradati, fuori budget di rete): la licenza viene da istat.it/note-legali; non ho verificato gli intervalli di confidenza.
