# Ricerca nuovi indicatori, flusso A: Istat, livello provinciale

Sola ricerca, nessuna modifica al codice. Valori letti dai file scaricati tramite `scripts/istat_sdmx.py` (cache-first, spaziatura 16 s).
Vincolo del committente applicato: in testa solo le serie con **ultimo anno 2025 o 2026**; le altre stanno nella sezione "ultimo anno 2024 o prima".

## Budget di rete e cosa non è stato verificato

Richieste di rete usate: **24 su 30**, tutte dal solo client `istat_sdmx.py`, mai in parallelo, nessun 403/429, quindi nessun segno di ban.

| esito | richieste |
| --- | --- |
| dati ottenuti e usati | 8 |
| dati ottenuti ma serie ferma al 2020 o al 2021, scartati (`..._UNT2020_*`, `DF_DCSS_HUDW_4_PROV`) | 4 |
| dati ottenuti ma non adatti (`29_317_DF_DCIS_POPSTRCIT1_24`, solo numeratore) | 1 |
| timeout del server (nessun dato) | 9 (SIR: 5 tentativi a flusso intero, 1 con un codice, 1 con `startPeriod=2024`; mortalità per causa; popolazione per età) |
| HTTP 400 sul SIR con chiave a più codici | 2 |

**Non verificati, dichiarati tali:**
- **SIR `DF_DIPS_SIR_IND_TERR_DRT_MUN_1`**: non ho ottenuto un solo dato. Flusso intero e con `startPeriod=2024`: timeout (il server non risponde entro 120-420 s; l'id contiene `MUN`, quindi con tutta probabilità porta anche i comuni e pesa molto). Chiave con elenco di codici `A..COD1+COD2`: HTTP 400, anche con `+` codificato `%2B` e REF_AREA ristretta alle 107 province. Resta quindi ignoto l'ultimo anno (le statistiche ASIA escono con 1-2 anni di ritardo, quindi è probabile 2023 o 2022 e rientrerebbe comunque in "ultimo anno 2024 o prima"). La lista dei 88 codici indicatore (`CL_SIR_INDICATORS`) è in `data/provincia/codelist_CL_SIR_INDICATORS.csv`: la selezione dei relativi sotto è sulla sola base dei nomi, senza dati.
- **Mortalità per causa provinciale** (`39_494_DF_DCIS_CMORTE1_RES_8`, "Quozienti di mortalità - prov."): timeout. Non verificato se i tassi sono standardizzati.
- **Quota di stranieri residenti**: il numeratore esiste (`29_317_DF_DCIS_POPSTRCIT1_24`, CITIZENSHIP=`WORLD`, 1 gennaio 2024 e 2025, 107 province); il denominatore (`22_289_DF_DCIS_POPRES1_1`) è andato in timeout. Non verificato come indicatore.
- Censimento permanente `DCSS_*`: l'endpoint risponde (vedi C1-C4 e scartati); non ho esplorato le altre tabelle.
- Pagine di metodo: ho aperto soltanto l'informativa legale e i portali tematici sotto; **non ho aperto la scheda metodologica specifica** di ciascun flusso, quindi "pagina di metodo" è il portale tematico, non la nota tecnica.

**Licenza (letta, valida per tutti i candidati):** da https://www.istat.it/note-legali/ : *"Salvo diversa indicazione, tutti i contenuti pubblicati su questo sito sono soggetti alla licenza Creative Commons – Attribuzione – versione 4.0."* (CC BY 4.0). Vale per i dati Istat; Eurostat non entra in questa lista.

**Come leggere i dati (tutti):** endpoint `https://esploradati.istat.it/SDMXWS/rest/data/<flusso>/<chiave>?startPeriod=<anno>` con `Accept: application/vnd.sdmx.data+csv;version=1.0.0` (è ciò che fa `SdmxClient.data`). Pagine di metodo (portali tematici Istat, verificati): https://www.istat.it/statistiche-per-temi/popolazione/popolazione-e-famiglie/ e https://www.istat.it/statistiche-per-temi/istruzione-e-lavoro/lavoro-e-retribuzioni/.

**Territori, trappola comune:** in `REF_AREA` Bolzano e Trento sono `ITD10`/`ITD20` nei flussi demografici e Censimento permanente (come in `province_codes.csv`), ma `ITD1`/`ITD2` nei flussi forze di lavoro. I flussi forze di lavoro hanno quindi 105 codici che coincidono con `province_codes.csv`: con la mappa `ITD1→ITD10`, `ITD2→ITD20` le province sono 107 (valori Bolzano e Trento letti 2025, attività 15-64: 75,2 e 73,6). Il file ha anche aggregati (`IT`, `ITC`, `ITC1`...) e vecchi codici sardi: filtrare su `province_codes.csv`.

---

# A. Candidati con ultimo anno 2025 o 2026 (ordinati per valore)

## A1. Indicatori demografici provinciali (23 serie in un solo flusso)

1. **Nome / ente**: "Indicatori demografici", per provincia. Istituto nazionale di statistica (Istat).
2. **Dato**: flusso `22_293_DF_DCIS_INDDEMOG1_1` (DSD `DCIS_INDDEMOG1`, chiave `FREQ.REF_AREA.DATA_TYPE`); codelist nomi `CL_TIPO_DATO15`. URL: `https://esploradati.istat.it/SDMXWS/rest/data/22_293_DF_DCIS_INDDEMOG1_1/A..?startPeriod=2015` (scaricato con chiave vuota, 35.620 righe). Licenza: CC BY 4.0 (frase sopra).
3. **Livello**: 107 province su 107 (codici Istat `ITxxx`, Bolzano `ITD10`, Trento `ITD20`; anche regioni e ripartizioni). Nessun buco: ogni DATA_TYPE ha 107 province all'ultimo anno.
4. **Anni**: 2015-2025 per i flussi di anno (natalità, fecondità, mortalità, saldi, speranze di vita), 2015-2026 per la struttura per età al 1° gennaio. Aggiornamento annuale. Parte dei valori recenti è provvisoria o stimata (`OBS_STATUS` `p` 1.096 celle, `e` 2.055 celle).
5. **Unità**: tutti relativi (percentuali, per mille, anni, figli per donna). Nessun assoluto.
6. **Verso onesto**: per lo più **contextual**, da dichiarare così. Fa eccezione la speranza di vita (higher_better). La fecondità (TFR) si può leggere come higher_better solo con una nota; l'indice di vecchiaia, l'età media e la dipendenza degli anziani descrivono la struttura e non meritano un giudizio.
7. **Doppioni**: la **speranza di vita alla nascita** è già in catalogo provinciale (BES dei Territori `01SAL001`): **non** riproporla (`LIFEEXP0F/M/T`). A livello **regionale** le stesse serie sono già in catalogo (`dem:BIRTHRATE`, `dem:MARRATE`, `dem:POP65OVER`, `dem:NMIGRATEIN`... in `external_indicator_manifest.csv`, più gli id 913 speranza di vita a 65, 921 indice di vecchiaia, 922 figli per donna, 923 saldo migratorio): per le province sono **nuovi**. Nessuno dei 67 codici BES provinciali copre natalità, fecondità, struttura per età, nuzialità, saldi migratori o speranza di vita a 65 anni (cercato per parola chiave in `province_manifest.csv`).
8. **Esempi letti (ultimo anno, totale, valore: basso / medio / alto)**:
   - Indice di vecchiaia, 2026: Bolzano 145,2 / Benevento 230,0 / Oristano 352,2 (`AGEINDEX`, %).
   - Età media della popolazione, 2026: Caserta 43,9 / Pavia 47,6 / Oristano 50,9 (`MEANAGEP`).
   - Popolazione 65 anni e più, 2026: Caserta 20,2 / Lecco 26,1 / Oristano 30,7 (`POP65OVER`, %).
   - Numero medio di figli per donna, 2025: Cagliari 0,75 / Aosta 1,12 / Bolzano 1,55 (`TFR`).
   - Speranza di vita a 65 anni (totale), 2025: Napoli 20,0 / Grosseto 21,5 / Rimini 22,5 (`LIFEEXP65T`, anni).
   - Tasso di natalità, 2025: Cagliari 3,8 / Trieste 5,8 / Bolzano 8,6 (`BIRTHRATE`, per mille).
   - Saldo migratorio interno, 2025: Matera -6,3 / Reggio Emilia 0,8 / Pavia 5,3 (`NMIGRATEIN`, per mille).
   - Tasso di mortalità, 2025: Bolzano 8,8 / Brindisi 11,5 / Savona 14,5 (`DEATHRATE`, per mille; dipende dall'età della popolazione, mai da leggere come "peggio/meglio").
9. **Integrazione**: facilissima, è la stessa struttura SDMX già letta per i BES (3 dimensioni, nessun filtro da fissare oltre al `DATA_TYPE`). Join sui codici di `province_codes.csv` senza eccezioni. Unica attenzione: l'ultimo anno è 2025 per alcuni codici e 2026 per altri, quindi l'"ultimo anno" va calcolato per codice. I codici utili:
   `AGEINDEX` indice di vecchiaia · `DEPENDRATE` dipendenza strutturale · `OLDAGEDEPR` dipendenza degli anziani · `POP014` / `POP1564` / `POP65OVER` quote per età · `MEANAGEP` età media · `TFR` figli per donna · `MEANAGECH` età media della madre al parto · `BIRTHRATE` natalità · `DEATHRATE` mortalità · `MARRATE` nuzialità · `GROWTHRATEN` crescita naturale · `GROWTHRATET` crescita totale · `TMIGRATE` saldo migratorio totale · `NMIGRATEIN` interno · `NMIGRATEAB` estero · `LIFEEXP65T/F/M` speranza di vita a 65 anni.
   **Consiglio**: portarne 5-6 con verso onesto o chiaramente descrittivo: speranza di vita a 65 anni (higher), figli per donna (contextual con nota), indice di vecchiaia (contextual), saldo migratorio interno (contextual, misura l'attrattività), quota 65+ e età media della madre al parto solo se servono famiglie con più dimensioni. Rischio: sono tutte molto correlate tra loro (struttura per età), quindi poco informative se aggiunte in blocco.

## A2. Tasso di disoccupazione provinciale (forze di lavoro)

1. **Nome / ente**: "Tasso di disoccupazione", per provincia. Istat, rilevazione sulle forze di lavoro.
2. **Dato**: flusso `151_914_DF_DCCV_TAXDISOCCU1_8` ("Dati provinciali", serie corrente; **non** la `..._UNT2020_7`, ferma al 2020). Colonne: `FREQ.REF_AREA.DATA_TYPE.SEX.AGE.EDU_LEV_HIGHEST.CITIZENSHIP.DURATION_UNEMPLOYMENT`. Da fissare: `FREQ=A` (c'è anche `Q`, trimestrale fino al 2026-Q2), `DATA_TYPE=UNEM_R`, `SEX=9` (totale; 1 maschi, 2 femmine), `AGE=Y15-74`, `EDU_LEV_HIGHEST=99`, `CITIZENSHIP=TOTAL`, `DURATION_UNEMPLOYMENT=TOTAL`. URL: `https://esploradati.istat.it/SDMXWS/rest/data/151_914_DF_DCCV_TAXDISOCCU1_8` (47.228 righe). CC BY 4.0.
3. **Livello**: 107 province (105 codici + `ITD1`/`ITD2` per Bolzano e Trento, vedi sopra). Disponibile anche per regione.
4. **Anni**: 2018-2025 annuale (la serie parte nel 2018 per il cambio di regolamento; la vecchia fino al 2020 non si accoda). Trimestrale a 2026-Q2. Aggiornamento trimestrale.
5. **Unità**: % delle forze di lavoro, relativo.
6. **Verso**: **lower_better** (onesto).
7. **Doppione**: a livello **regionale** esiste (id 12, 15 giovanile, 17 lunga durata). A livello **provinciale** il BES ha `03LAV002-N22` (mancata partecipazione al lavoro, che include forze di lavoro potenziali) e `03LAV001-N22` (occupazione 20-64): sono misure vicine ma **diverse**; il tasso di disoccupazione 15-74 provinciale non c'è. Nuovo con riserva: correlato con la mancata partecipazione.
8. **Esempi 2025 (15-74, totale)**: Bergamo 1,3 / Savona 5,2 / Agrigento 19,8. Giovani 15-24: Bergamo 3,0 / Bologna 17,0 / Taranto 67,9 (campione piccolo, instabile: per i giovani meglio 15-34: Bergamo 2,5 / Piacenza 10,0 / Taranto 43,9).
9. **Integrazione**: filtro su 6 dimensioni; mappare `ITD1`/`ITD2`; per i giovani valori molto instabili tra un anno e l'altro (campione provinciale), meglio 15-74 o 20-64.

## A3. Tasso di attività provinciale (15-64 anni)

1. **Nome / ente**: "Tasso di attività 15-64 anni", per provincia. Istat, forze di lavoro.
2. **Dato**: flusso `150_916_DF_DCCV_TAXATVT1_5` (serie corrente "Dati provinciali"; la `..._UNT2020_4` è ferma al 2020). Colonne `FREQ.REF_AREA.DATA_TYPE.SEX.AGE.EDU_LEV_HIGHEST.CITIZENSHIP`; fissare `FREQ=A`, `DATA_TYPE=ACT_R`, `SEX=9`, `AGE=Y15-64`, `EDU_LEV_HIGHEST=99`, `CITIZENSHIP=TOTAL`. 81.455 righe. CC BY 4.0.
3. **Livello**: 107 province con la stessa mappa `ITD1`/`ITD2`.
4. **Anni**: 2018-2025 annuale; trimestrale a 2026-Q2.
5. **Unità**: % della popolazione 15-64, relativo.
6. **Verso**: higher_better (partecipazione al lavoro) con cautela: va letto insieme al tasso di occupazione già in catalogo; da sola non distingue chi cerca lavoro da chi lavora.
7. **Doppione**: regionale parzialmente presente ("Partecipazione della popolazione al mercato del lavoro", tasso di attività per sesso). Provinciale nuovo.
8. **Esempi 2025 (15-64, totale)**: Reggio Calabria 46,1 / Como 69,8 / Ferrara 76,9. Bolzano 75,2, Trento 73,6.
9. **Integrazione**: come A2. Variante per sesso (`SEX=1`,`2`) permette il divario di genere provinciale (derivato, da dichiarare come tale).

---

# B. Fonti ai bordi: promettenti ma non verificate

- **Quota di stranieri residenti** (Istat, 1° gennaio, 2024-2025): numeratore verificato (`29_317_DF_DCIS_POPSTRCIT1_24`, `CITIZENSHIP=WORLD`, `SEX=9`, `FREQ=A`, esempio Torino ITC11 2025 = 224.964), denominatore non scaricato. Verso: contextual. Con un solo scaricamento in più (popolazione residente 1° gennaio 2025/2026 per provincia) si chiude; ultimo anno 2025.
- **Mortalità per causa provinciale** (`39_494_DF_DCIS_CMORTE1_RES_8`): timeout, forse troppo grande: provare con `startPeriod` recente e DATA_TYPE fissato. Potrebbe aggiungere circolatorio, diabete, suicidi; ultimo anno presumibilmente 2022-2023.

---

# C. Ultimo anno 2024 o prima

## C1. Censimento permanente, soddisfazione per la vita (voti 8-10), per provincia

1. "Persone di 14 anni e più per livello di soddisfazione della vita - province e grandi comuni". Istat, Censimento permanente della popolazione, Indagine "Aspetti..." (nome esatto dell'indagine non verificato).
2. Flusso `DF_DCSS_BEST_PPC_2_GC` (18.915 righe). Dimensioni da fissare: `INDICATOR=RESPOP_Y_GE14`, `GENDER=T`, e per il denominatore `LIFE_SATISF=ALL`; numeratore somma di `SA_8`, `SA_9`, `SA_10`. Altre dimensioni già costanti (`PERC_CRIME_RISK=ALL`, `FAMILY_MEM_COUNT=9`, `FRIENDS_COUNT=9`, `NEIGHBORS_COUNT=ALL`, `PERC_SAF_WAD=ALL`). CC BY 4.0.
3. 107 province con codici `ITxxx` (+ grandi comuni con codice Istat a 6 cifre da scartare).
4. **2022-2024** (3 anni), ultimo anno 2024.
5. **I valori sono stime di numero di persone, non percentuali**: la quota va **calcolata** (somma dei voti 8-10 diviso `ALL`). Resta un rapporto interno al dato, non un assoluto che premia la taglia.
6. higher_better.
7. A livello regionale il BES ha `08BSO001` (soddisfazione per la propria vita); **il BES dei Territori non ha il dominio 8 a livello provinciale** (`BES_08` è 404). Provinciale: nuovo.
8. Esempi 2024, quota 8-10: Napoli 44,3% / Sud Sardegna 54,4% / Bolzano 67,8%.
9. Calcolo della quota nel build; il denominatore include "non risponde" (voci `NO_ANSWER`): se si esclude cambia di poco. Tre anni sono pochi per un trend.

## C2. Sicurezza camminando da soli al buio

Flusso `DF_DCSS_BEST_PPC_6_GC` (11.640 righe), stessa struttura. Fissare `GENDER=T`, `PERC_SAF_WAD` denominatore `ALL`, numeratore `SI_COMP_SAFE` + `SI_QUITE_SAFE` (molto/abbastanza sicuro). 2022-2024, 107 province. higher_better. Doppione: regionale `07SIC020`. Esempi 2024: Prato 47,9% / Pesaro e Urbino 64,2% / Enna 85,0%. Attenzione: `SI_NEVER_GO` e `SI_NEVER_GO_AL` ("non esce mai da solo") non entrano nel numeratore ma nel denominatore.

## C3. Rischio di criminalità percepito nella zona

Flusso `DF_DCSS_BEST_PPC_1_GC` (2.446 righe, **famiglie**: `INDICATOR=NPHH_AV`, `GENDER=T`). Numeratore `CR_V_MUCH` + `CR_QUITE_BIT`, denominatore `ALL`. 2022-2024, 107 province. lower_better. Doppione: regionale `07SIC022` (BES) e id 43. Esempi 2024: Oristano 3,7% / Grosseto 18,0% / Napoli 46,3%.

## C4. Occupati che lavorano da casa

Flusso `DF_DCSS_LCAS_FRISC_1` (3.888 righe). Fissare `INDICATOR=EMPLP`, `GENDER=T`, `AGE_CLASS=Y_GE15`; numeratore `WORK_HOME` = `ATLHDAY` + `LESSHDAY`, denominatore `TOTAL`. 2023-2024, 107 province. Verso contextual (smart working: dipende dal tessuto economico). Doppione: regionale `03LAV021-N22`. Esempi 2024: Nuoro 6,9% / Arezzo 10,2% / Milano 29,5% (premia il terziario del Nord: rischio dichiarato).

## C5. Indice di mortalità degli incidenti stradali

Flusso `41_287_DF_DCIS_INDINCIDENT_1` (12.326 righe): `DATA_TYPE=KILLEDINDX` (morti per 100 incidenti con lesioni), `ACCIDENT_LOCALIZATON=9` (totale; 1 urbano, 2 autostrade, 3 strade extraurbane). 2001-2024, 107 province per il totale. lower_better. Doppione parziale: BES `01SAL005` (mortalità stradale 15-34) e `07SIC008P` (quota mortalità stradale extraurbana): misura diversa (gravità degli incidenti, non rischio per abitante). Esempi 2024 totale: Verbano-Cusio-Ossola 0,28 / Forlì-Cesena 2,07 / Sud Sardegna 5,96. Instabile nelle province piccole (pochi incidenti).

## C6. Flusso SIR "Indicatori e territorio" (non verificato)

Vedi sopra: nessun dato scaricato. Valutazione sui soli nomi dei 88 codici, dichiarata **non verificata**:
- Relativi con verso accettabile: `AIAT_MICLUXLU_LU_SH_PCT` incidenza microimprese, `AOIN_PEXPOP_POP_SH_PCT` addetti per 100 residenti, `FTIN_LUXPOP_POP_RT_PCT` unità locali per 100 residenti, `AOIN_TEDPEXPE_PEA_SH_PCT` addetti con istruzione terziaria per 100 addetti, `AOIN_PEFXPE_PE_SH_PCT` femmine per 100 addetti, `ATFT_PEHTXPE_LU_SH_PCT` addetti ad alta tecnologia e intensi in conoscenza.
- Da evitare: i 30+ assoluti (`AT_LU_LU_ABS_NUM`, `FT_VA_LU_ABS_EURTH`...) per la taglia.
- Rischio "premia il Nord industriale": per valore aggiunto per addetto, costo del lavoro e alta tecnologia è **alto e non gestibile** (la classifica riproduce la geografia della grande industria); per addetti per 100 residenti e microimprese è **gestibile** solo se il verso resta contextual. Raccomandazione: tenere fuori dallo score, usare solo come contesto.

---

# D. Scartati

| candidato | motivo |
| --- | --- |
| `150_1189/1190/1191`, `151_1192/1193`, `152_1185/1196` `..._UNT2020_*` (forze di lavoro provinciali "regolamento precedente") | ultimo anno **2020** (verificato su 3 file) |
| `DF_DCSS_HUDW_4_PROV` (abitazioni per densità abitativa, regioni e province) | un solo anno: **2021**; anche HUDW_2/3/5 sono del Censimento 2021 (non scaricati) |
| `99_..._DCCN_OCCTSEC2010` occupazione provinciale, `DCIS_MIGRAZIONI`, `DCIS_PERMSOGG1`, residenti per classe di età | assoluti (la metropoli vincerebbe sempre) |
| `DF_DCSS_FAMILY_NUCLEI_*`, `POPHH_PHH_*`, `FORPOP_*`, `CONVIVENZE_*` | conteggi di famiglie o persone senza un verso onesto, da derivare a mano, ultimo anno non verificato |
| `DF_BULK_CEN2011_*`, `DF_BULK_CAG2010_*`, `DCSE_CPA_*`, `DCSC_RESID_CONSTR_*` | storici (Censimento 2011, Agricoltura 2010) o assoluti o a un solo anno; non scaricati |
| `DF_BES_TERRIT_0T` | già integrato (67 codici) |
| `122_54_DF_DCSC_TUR_*` (turismo per provincia) | assoluti (arrivi/presenze); presenze per abitante richiederebbe denominatore e un anno vicino al 2024: non verificato |
| speranza di vita alla nascita provinciale (`LIFEEXP0*`) | doppione di `01SAL001` |
| reddito IRPEF per provincia (Ministero dell'Economia e delle Finanze) | fuori dal mio flusso (non Istat), non aperto: segnalo solo come pista per il flusso B |

# E. Raccomandazione netta

1. **Primo giro (basso costo, valore reale)**: A2 (disoccupazione 15-74), A3 (attività 15-64) e 5-6 serie da A1 (speranza di vita a 65, figli per donna, indice di vecchiaia, saldo migratorio interno, età media della madre al parto). Tutte con ultimo anno 2025 o 2026, 107 province, SDMX già nel client.
2. **Secondo giro (se si accetta 2024)**: C1 soddisfazione per la vita (è l'unica dimensione soggettiva provinciale) e C2 sicurezza al buio. C3 e C4 solo come contesto.
3. **Non fare ora**: il SIR (non scaricabile con le richieste testate, rischio Nord industriale), e nessun'altra query pesante prima di aver capito perché il server dà timeout sui flussi grandi (mortalità per causa, popolazione per età): suggerisco `startPeriod` recente e `DATA_TYPE` fissato fin dalla prima chiamata, non chiavi vuote.
4. **Costo**: ~8 richieste di rete per tutto il primo giro; nessuna modifica di schema: stesso formato SDMX-CSV del BES.
