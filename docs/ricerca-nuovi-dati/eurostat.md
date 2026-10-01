# Ricerca Eurostat regionale e provinciale

Verifica eseguita il 1 ottobre 2026. Tutte le serie sotto sono state aperte con una richiesta reale alla API Eurostat JSON-stat. Le coperture e gli esempi riguardano l'Italia, non il dataset europeo nel suo insieme.

## Metodo e condizioni comuni

- I 21 territori NUTS2 verificati sono `ITC1`, `ITC2`, `ITC3`, `ITC4`, `ITH1`, `ITH2`, `ITH3`, `ITH4`, `ITH5`, `ITI1`, `ITI2`, `ITI3`, `ITI4`, `ITF1`, `ITF2`, `ITF3`, `ITF4`, `ITF5`, `ITF6`, `ITG1`, `ITG2`. Per il modello a 20 regioni di Divario Italia, `ITH1` Bolzano e `ITH2` Trento vanno sempre ricomposti come Trentino-Alto Adige usando il denominatore proprio della misura. Una media semplice non è accettabile.
- I 107 territori provinciali sono i codici NUTS3 italiani correnti restituiti nel 2024. Sono stati esclusi gli otto codici sardi etichettati `NUTS 2016`.
- I cinque inventari controllati per i doppioni sono `Assoluti_Regione.csv`, `bes_regione_manifest.csv`, `province_manifest.csv`, `multiscopo_regione_manifest.csv`, `external_indicator_manifest.csv`.
- I dati sono pubblicati da **Eurostat, ufficio statistico dell'Unione europea**.
- Licenza e riuso: [copyright e riuso Eurostat](https://ec.europa.eu/eurostat/help/copyright-notice), aperta con HTTP 200. La pagina mostra CC BY 4.0 per il contenuto editoriale. Per dati e metadati autorizza il riuso commerciale e non commerciale, con questo passaggio: “Reuse of statistical data [...] is authorised provided the source is acknowledged.” Quindi ok-licenza per queste serie italiane, con attribuzione a Eurostat e indicazione delle trasformazioni. La base giuridica richiamata è la decisione 2011/833/UE.
- Frequenza: tutte le serie candidate sono annuali. I valori esemplificativi sono quelli restituiti dalla API, senza memoria o fonti secondarie. `u` significa bassa affidabilità nel vocabolario Eurostat.

## Candidati, ordinati per valore

### 1. Persone che non riescono a riscaldare adeguatamente la casa

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `ilc_mdes01_r`.
- **Dato scaricabile:** [API JSON-stat, NUTS2, percentuale](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_mdes01_r?format=JSON&lang=EN&geoLevel=nuts2&unit=PC). **Metodo:** [EU-SILC, reddito e condizioni di vita](https://ec.europa.eu/eurostat/cache/metadata/en/ilc_sieusilc.htm). Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 italiane nel 2025, quindi 20/20 regioni dopo ricomposizione di Bolzano e Trento. È un'indagine campionaria sulle persone nelle famiglie, non un dato comunale.
- **Anni e aggiornamento:** 2021-2025 per tutte le 21 unità; annuale. Dataset aggiornato il 17 settembre 2026.
- **Unità e verso:** percentuale; relativo. `lower_better`.
- **Doppione:** **nuovo**. Ricerca `riscald`, `casa calda`, `povertà energetica`, `energia domestica`: nessun nome nei cinque inventari. Non coincide con difficoltà ad arrivare a fine mese, umidità o spesa per abitazione.
- **Esempi reali, 2025:** Trento 2,0%; Piemonte 7,0%; Sicilia 18,5%.
- **Integrazione:** bassa-media. JSON-stat semplice. Per il Trentino-Alto Adige serve una media pesata con il numero ponderato di persone, non la media 2-province. Valutare intervalli ed errore campionario EU-SILC per regioni piccole.

### 2. Scienziati e ingegneri sulla popolazione attiva

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `hrst_st_rcat`; filtri `category=SE`, `unit=PC_ACT`.
- **Dato scaricabile:** [API JSON-stat, scienziati e ingegneri](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hrst_st_rcat?format=JSON&lang=EN&geoLevel=nuts2&category=SE&unit=PC_ACT). **Metodo:** [Human resources in science and technology](https://ec.europa.eu/eurostat/cache/metadata/en/hrst_esms.htm). La pagina metodo conferma NUTS1/NUTS2 e diffusione annuale. Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2025, quindi 20 regioni ricomponibili.
- **Anni e aggiornamento:** 1999-2025; annuale. Dataset aggiornato il 10 settembre 2026.
- **Unità e verso:** percentuale della popolazione attiva; relativo. `higher_better` come dotazione di capitale umano tecnico.
- **Doppione:** **nuovo**. Ricerca `scienziati`, `ingegneri`, `risorse umane in scienza`: zero risultati. “Laureati in scienza e tecnologia” misura titoli conseguiti; personale R&S misura una diversa popolazione lavorativa.
- **Esempi reali, 2025:** Valle d'Aosta 3,0% (`u`, bassa affidabilità); Umbria 4,4%; Lazio 6,3%.
- **Integrazione:** media. Il join NUTS2 è diretto. Bolzano+Trento richiedono pesi della popolazione attiva. Conservare il flag `u`; opportuno non usare Valle d'Aosta nello scoring finché il dato resta a bassa affidabilità.

### 3. Nascite da madri con meno di 20 anni

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `demo_r_fagec3`; filtri `age=Y_LT20` e `age=TOTAL`, `unit=NR`.
- **Dato scaricabile:** [API JSON-stat, NUTS3, due conteggi](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_fagec3?format=JSON&lang=EN&geoLevel=nuts3&unit=NR&age=TOTAL&age=Y_LT20). **Metodo:** [demografia regionale e nascite](https://ec.europa.eu/eurostat/cache/metadata/en/demo_r_gind3_esms.htm), che dichiara dati a NUTS2 e NUTS3. Licenza: condizioni comuni sopra.
- **Territorio:** 107/107 province NUTS3 correnti nel 2024. L'indicatore proposto è derivato come `nascite da madri <20 / nascite totali * 100`; può essere aggregato esattamente a regione sommando prima numeratore e denominatore. Nessun dato comunale.
- **Anni e aggiornamento:** 2013-2024 per la geografia corrente; annuale. Dataset aggiornato il 30 settembre 2026.
- **Unità e verso:** percentuale delle nascite; relativo, anche se la fonte fornisce i due conteggi necessari. `lower_better`.
- **Doppione:** **nuovo**. Ricerca `madri`, `maternità`, `nascite`, `parto`, `fecondità`: unico vicino “Età media della madre al parto (Istat, regioni)”, misura diversa e solo regionale.
- **Esempi reali calcolati dai conteggi 2024:** Sondrio 0,26% (3 su 1.148); L'Aquila 0,77% (13 su 1.690); Siracusa 3,05% (75 su 2.458).
- **Integrazione:** media. Derivazione obbligatoria e test su denominatore zero. Join NUTS3 su 107 codici correnti; scartare esplicitamente gli otto codici storici sardi `NUTS 2016`. Aggregazione regionale semplice e onesta tramite somme.

### 4. Ore settimanali abituali nel lavoro principale

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `lfst_r_lfe2ehour`; filtri `age=Y20-64`, `sex=T`, `unit=HR`.
- **Dato scaricabile:** [API JSON-stat, occupati 20-64 anni](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/lfst_r_lfe2ehour?format=JSON&lang=EN&geoLevel=nuts2&age=Y20-64&sex=T&unit=HR). **Metodo:** [statistiche regionali del mercato del lavoro](https://ec.europa.eu/eurostat/cache/metadata/en/reg_lmk_esms.htm). La fonte è EU-LFS; la pagina dichiara informazione annuale a NUTS2. Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2025, quindi 20 regioni ricomponibili.
- **Anni e aggiornamento:** 1999-2025; annuale. Dataset aggiornato il 10 settembre 2026.
- **Unità e verso:** ore medie settimanali; relativo alla persona occupata, non volume assoluto. `contextual`: più ore non equivalgono automaticamente a maggiore benessere o produttività.
- **Doppione:** **nuovo**. Ricerca `ore settimanali`, `orario`, `tempo di lavoro`: unico vicino “Occupati ... oltre 60 ore settimanali”, fermo al 2014 e concettualmente diverso.
- **Esempi reali, 2025:** Sardegna 35,9 ore; Lazio 37,0; Emilia-Romagna 38,2.
- **Integrazione:** media. Bolzano+Trento richiedono pesi degli occupati 20-64. Dato da indagine campionaria; non usarlo nello scoring con verso positivo o negativo.

### 5. Tasso standardizzato di mortalità per autolesionismo intenzionale

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `hlth_cd_asdr2`; filtri `icd10=X60-X84_Y870`, `sex=T`, `age=TOTAL`, `unit=RT`.
- **Dato scaricabile:** [API JSON-stat, autolesionismo intenzionale](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hlth_cd_asdr2?format=JSON&lang=EN&geoLevel=nuts2&icd10=X60-X84_Y870&sex=T&age=TOTAL&unit=RT). **Metodo:** [cause di morte](https://ec.europa.eu/eurostat/cache/metadata/en/hlth_cdeath_sims.htm). La pagina definisce il tasso come media pesata dei tassi specifici per età sulla popolazione standard europea. Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2023, quindi copertura regionale completa prima della ricomposizione.
- **Anni e aggiornamento:** 2011-2023; annuale. Dataset aggiornato l'8 giugno 2026.
- **Unità e verso:** tasso standardizzato per 100.000 abitanti; relativo. `lower_better`.
- **Doppione:** **nuovo**. Ricerca `suicidio`, `autolesionismo`: zero risultati nei cinque inventari.
- **Esempi reali, 2023:** Campania 2,70; Marche 6,16; Valle d'Aosta 13,04 per 100.000.
- **Integrazione:** media-alta. Il join è semplice, ma due tassi standardizzati non si aggregano esattamente con una media di popolazione. Per Trentino-Alto Adige servono decessi e popolazioni per classe d'età, oppure va esposto esplicitamente un proxy pesato non scoreabile.

### 6. Quota di pernottamenti di turisti residenti all'estero

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `tour_occ_nin2`; filtri `c_resid=FOR`, `unit=PC_TOT`, `nace_r2=I551-I553`.
- **Dato scaricabile:** [API JSON-stat, quota estera](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tour_occ_nin2?format=JSON&lang=EN&geoLevel=nuts2&c_resid=FOR&unit=PC_TOT&nace_r2=I551-I553). **Metodo:** [occupazione delle strutture ricettive](https://ec.europa.eu/eurostat/cache/metadata/en/tour_occ_esms.htm). La pagina precisa che residenti/non residenti sono calcolati in percentuale del totale. Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2025, quindi 20 regioni ricomponibili.
- **Anni e aggiornamento:** 1990-2025; annuale. Dataset aggiornato il 22 settembre 2026.
- **Unità e verso:** percentuale dei pernottamenti totali; relativo. `contextual`: internazionalizzazione non equivale da sola a qualità della vita.
- **Doppione:** **nuovo**. Ricerca `turisti stranieri`, `turismo estero`, `pernottamenti`, `notti straniere`, `presenze straniere`: nessuna misura corrispondente. “Tasso di turisticità” misura volume per popolazione, non composizione della domanda.
- **Esempi reali, 2025:** Molise 11,34%; Liguria 45,88%; Bolzano 72,10%.
- **Integrazione:** bassa-media. Per Trentino-Alto Adige recuperare nello stesso dataset `unit=NR` per stranieri e totale, sommare i conteggi di Bolzano e Trento, poi ricalcolare la quota. Mai media semplice delle due percentuali.

### 7. Tasso netto di occupazione dei posti letto alberghieri

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `tour_occ_anor2`; filtri `accomunit=BEDPL`, `unit=PC`.
- **Dato scaricabile:** [API JSON-stat, posti letto alberghieri](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tour_occ_anor2?format=JSON&lang=EN&geoLevel=nuts2&accomunit=BEDPL&unit=PC). **Metodo:** [occupazione delle strutture ricettive](https://ec.europa.eu/eurostat/cache/metadata/en/tour_occ_esms.htm). Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2025, quindi 20 regioni ricomponibili.
- **Anni e aggiornamento:** 2012-2025; annuale. Dataset aggiornato il 22 settembre 2026.
- **Unità e verso:** percentuale netta di occupazione della capacità aperta; relativo. `contextual`: maggiore utilizzo è efficienza economica, ma può anche indicare pressione turistica.
- **Doppione:** **nuovo**. Ricerca `occupazione alberghi`, `occupazione posti letto`, `capacità ricettiva`, `utilizzo posti letto`: nessun indicatore corrispondente.
- **Esempi reali, 2025:** Calabria 37,2%; Abruzzo 49,0%; Bolzano 65,5%.
- **Integrazione:** alta per il Trentino-Alto Adige. Il tasso va pesato per posti-letto-giorno effettivamente disponibili; questi denominatori non sono nella stessa cella del tasso. La serie è ottima per atlante, ma non va aggregata con media semplice né messa nello scoring.

### 8. Tasso standardizzato di mortalità per diabete

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `hlth_cd_asdr2`; filtri `icd10=E10-E14`, `sex=T`, `age=TOTAL`, `unit=RT`.
- **Dato scaricabile:** [API JSON-stat, diabete](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hlth_cd_asdr2?format=JSON&lang=EN&geoLevel=nuts2&icd10=E10-E14&sex=T&age=TOTAL&unit=RT). **Metodo:** [cause di morte](https://ec.europa.eu/eurostat/cache/metadata/en/hlth_cdeath_sims.htm). Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2023, quindi copertura regionale completa prima della ricomposizione.
- **Anni e aggiornamento:** 2011-2023; annuale. Dataset aggiornato l'8 giugno 2026.
- **Unità e verso:** tasso standardizzato per 100.000 abitanti; relativo. `lower_better`.
- **Doppione:** **nuovo**. Ricerca `diabete`: zero risultati. Le mortalità BES già presenti riguardano tumori, demenze, incidenti, mortalità infantile ed evitabile aggregata.
- **Esempi reali, 2023:** Bolzano 15,33; Umbria 22,27; Campania 52,83 per 100.000.
- **Integrazione:** media-alta. Stesso problema di aggregazione della serie precedente: il Trentino-Alto Adige esatto richiede dati per età, non una media dei due tassi standardizzati.

### 9. Aggressioni registrate dalla polizia

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `crim_gen_reg`; filtri `iccs=ICCS02011`, `unit=P_HTHAB`.
- **Dato scaricabile:** [API JSON-stat, NUTS3](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/crim_gen_reg?format=JSON&lang=EN&geoLevel=nuts3&iccs=ICCS02011&unit=P_HTHAB). **Metodo:** [reati registrati dalla polizia per NUTS3](https://ec.europa.eu/eurostat/cache/metadata/en/crim_gen_reg_esms.htm). La pagina definisce l'unità come reato registrato e avverte che il sommerso non denunciato resta fuori. Licenza: condizioni comuni sopra.
- **Territorio:** 106/107 province correnti nel 2023; manca Sud Sardegna. Nel 2024 l'Italia ha solo 53/107 province, quindi 2024 non è usabile. Aggregabile a regione usando conteggi e popolazione.
- **Anni e aggiornamento:** dataset 2008-2024; ultimo anno italiano quasi completo 2023. Frequenza annuale; aggiornato il 29 giugno 2026.
- **Unità e verso:** reati registrati per 100.000 residenti; relativo. `lower_better`, con forte cautela perché propensione alla denuncia e prassi di registrazione influenzano il dato.
- **Doppione:** **nuovo**. Ricerca `aggressioni`, `lesioni`, `assault`: nessuna misura amministrativa equivalente. Le violenze contro le donne nel BES sono indicatori di indagine; “altri delitti mortali” è altra fattispecie.
- **Esempi reali, 2023:** Oristano 47,23; Viterbo 107,09; Imperia 193,02 per 100.000.
- **Integrazione:** media-alta. Join NUTS3, gestione esplicita di Sud Sardegna mancante e dei codici sardi storici. Per aggregare, usare numero di aggressioni e popolazione, non media dei tassi. Tenere fuori dallo scoring finché copertura non è 107/107 e la comparabilità italiana non è documentata.

### 10. Autovetture per 1.000 abitanti

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `tran_r_vehst`; filtri `vehicle=CAR`, `unit=P_THAB`.
- **Dato scaricabile:** [API JSON-stat, autovetture](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tran_r_vehst?format=JSON&lang=EN&geoLevel=nuts2&vehicle=CAR&unit=P_THAB). **Metodo:** [trasporti regionali](https://ec.europa.eu/eurostat/cache/metadata/en/tran_r_esms.htm), che dichiara dati annuali. Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2024, quindi 20 regioni ricomponibili.
- **Anni e aggiornamento:** 1990-2024; annuale. Dataset aggiornato il 31 agosto 2026.
- **Unità e verso:** autovetture per 1.000 abitanti; relativo. `contextual`: un valore alto può significare ricchezza, dipendenza dall'auto, registrazioni di flotte o scarso trasporto pubblico.
- **Doppione:** **nuovo**. Ricerca `autovetture`, `motorizzazione`, `veicoli`, `parco circolante`: zero risultati.
- **Esempi reali, 2024:** Liguria 563; Piemonte 723; Valle d'Aosta 1.936 per 1.000. Il valore valdostano segnala l'effetto delle immatricolazioni e conferma che non va interpretato come disponibilità familiare né premiato.
- **Integrazione:** bassa-media. Recuperare anche `unit=NR` e popolazione per ricomporre Bolzano+Trento esattamente. Conservare `contextual`; aggiungere nota editoriale sulle flotte registrate.

### 11. Stanze disponibili per persona

- **Fonte e codice:** Eurostat, ufficio statistico dell'Unione europea; dataset `ilc_lvho04n`; filtro `unit=AVG`.
- **Dato scaricabile:** [API JSON-stat, stanze per persona](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_lvho04n?format=JSON&lang=EN&geoLevel=nuts2&unit=AVG). **Metodo:** [EU-SILC, reddito e condizioni di vita](https://ec.europa.eu/eurostat/cache/metadata/en/ilc_sieusilc.htm). Licenza: condizioni comuni sopra.
- **Territorio:** 21/21 unità NUTS2 nel 2025, quindi 20 regioni ricomponibili. Indagine campionaria, non dato comunale.
- **Anni e aggiornamento:** 2004-2025; annuale. Dataset aggiornato l'8 luglio 2026.
- **Unità e verso:** numero medio di stanze per persona; relativo. `contextual`: più spazio può indicare comfort, ma anche sottoutilizzo del patrimonio e spopolamento.
- **Doppione:** **nuovo come misura**. Ricerca `stanze`, `vani`, `locali per persona`: nessun nome uguale. Esistono “Indice di affollamento delle abitazioni” e una misura composita di sovraffollamento/disagio: sono concetti vicini, non la stessa unità né lo stesso indicatore.
- **Esempi reali, 2025:** Trento 1,3; Marche 1,5; Umbria 1,7 stanze per persona.
- **Integrazione:** bassa-media. Media pesata per popolazione per Bolzano+Trento. Serie EU-SILC campionaria, valori molto ravvicinati e arrotondati a un decimale: meglio atlante descrittivo, non scoring.

## Controllo doppioni sintetico

| candidato | parole cercate nei cinque inventari | esito |
| --- | --- | --- |
| casa calda | `riscald`, `casa calda`, `povertà energetica` | 0 corrispondenze |
| scienziati e ingegneri | `scienziati`, `ingegneri`, `risorse umane in scienza` | 0; laureati STEM e addetti R&S sono diversi |
| madri sotto 20 anni | `madri`, `maternità`, `nascite`, `parto`, `fecondità` | solo età media della madre, diverso |
| ore abituali | `ore settimanali`, `orario`, `tempo di lavoro` | solo quota oltre 60 ore, diverso |
| autolesionismo | `suicidio`, `autolesionismo` | 0 |
| notti estere | `turisti stranieri`, `pernottamenti`, `notti straniere`, `presenze straniere` | 0 |
| occupazione alberghi | `occupazione alberghi`, `capacità ricettiva`, `utilizzo posti letto` | 0 |
| diabete | `diabete` | 0 |
| aggressioni | `aggressioni`, `lesioni`, `assault` | 0; indicatori di violenza BES non equivalenti |
| autovetture | `autovetture`, `motorizzazione`, `veicoli`, `parco circolante` | 0 |
| stanze per persona | `stanze`, `vani`, `locali per persona` | 0 esatti; due misure affini di affollamento |

## Scartati

- `hlth_rs_bdsrg2`, posti letto ospedalieri per 100.000: **doppione** di “Posti letto negli ospedali” e “Posti letto per specialità ad elevata assistenza” nel manifest provinciale, oltre alle serie regionali affini.
- `hlth_rs_physreg`, medici: **doppione** di “Medici” regionale e “Medici specialisti” provinciale.
- `edat_lfse_16`, uscita precoce da istruzione: **doppione** BES regionale e serie Istat già in catalogo.
- `edat_lfse_22`, NEET: **doppione** regionale e provinciale.
- Famiglie con banda larga e copertura ultraveloce: **doppioni** Multiscopo e BES.
- `pat_ep_rtot`, brevetti per milione: **doppione** di “Propensione alla brevettazione” regionale e provinciale.
- `rd_p_persreg`, `rd_e_gerdreg`: già registrati nell'adattatore Eurostat e nell'inventario esterno; non nuovi.
- `nama_10r_2gdp`: già registrato; escluso anche dalla spec.
- `htec_emp_reg2`, occupati nei settori ad alta tecnologia: **doppione** di “Specializzazione produttiva nei settori ad alta tecnologia”.
- `ilc_peps11n`, rischio di povertà o esclusione: **doppione** delle serie Europa 2030 già in `Assoluti_Regione.csv`.
- `ilc_di11_r`, rapporto S80/S20: **doppione esatto** di `04BEC002` “Disuguaglianza del reddito netto (s80/s20)”.
- `ilc_lvho07_r`, sovraccarico del costo dell'abitazione: **doppione esatto** di `SDG-222`.
- `educ_uoe_enrt05`, attrazione di studenti terziari: **doppione concettuale** di “Indice di attrattività delle università”, già nel catalogo anche se il manifest esterno lo segnala non aggiornato.
- `tour_occ_nin2`, pernottamenti per 1.000 abitanti: **doppione** del “Tasso di turisticità”. È stata trattenuta solo la quota estera, misura diversa.
- `demo_r_gind3`, saldo migratorio: **doppione** di saldo totale, interno ed estero già presenti.
- `tran_r_acci`, vittime stradali per milione: troppo vicino alle mortalità stradali BES regionale e provinciale.
- `hlth_cd_ypyll`, anni potenziali di vita persi: l'unità disponibile è un **assoluto** in anni; senza una normalizzazione ufficiale favorirebbe i territori piccoli e non rispetta il requisito.
- `tran_r_vehst`, motocicli e autobus: per queste categorie Eurostat restituisce solo `NR`, **assoluto**. L'unità `P_THAB` è popolata per le autovetture, non per queste due categorie.
- `isoc_r_ske_itspen2`, imprese con specialisti ICT: richiesta reale 2024 per `ITC1` restituita con dimensione geo vuota e zero celle; **copertura italiana NUTS2 non verificata**, quindi escluso.

## Priorità operativa suggerita

Per integrazione immediata: 1 (casa non adeguatamente calda), 2 (scienziati e ingegneri), 3 (madri sotto 20 anni), 4 (ore abituali), 6 (quota notti estere), 10 (autovetture, solo contestuale). Le mortalità 5 e 8 sono solide ma richiedono una decisione metodologica esplicita per il Trentino-Alto Adige. Il tasso alberghiero 7, le aggressioni 9 e le stanze 11 sono utili per atlante descrittivo, non per scoring.
