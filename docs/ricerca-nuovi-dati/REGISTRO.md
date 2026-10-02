# Registro della caccia ai nuovi indicatori (1-2 ottobre 2026)

Questo file dice che cosa è stato cercato, che cosa è entrato, che cosa è stato
scartato e perché, e che cosa conviene riprendere. **Una sessione nuova non deve
riscansionare queste fonti**, salvo che Nello chieda di ammettere anche dati meno
freschi (allora si parte dalla sezione "Pronti ma fermi al 2024").

I rapporti completi, con URL, licenze, copertura e valori d'esempio letti dai file,
stanno in questa cartella:

| rapporto | contenuto |
| --- | --- |
| `istat-province.md` | Istat provinciale: indicatori demografici, lavoro, Censimento, SIR |
| `economia-fisco.md` | MEF IRPEF, ACI, GSE, Movimprese, ISPRA rifiuti |
| `eurostat.md` | Eurostat regionale e NUTS3, undici candidati |
| `ambiente-salute-scuola.md` | ISPRA suolo e IdroGEO, qualità dell'aria, salute, scuola, fisco |
| `r2-imprese-mobilita.md` | seconda ondata: ACI, AGCOM, Movimprese, Terna, Banca d'Italia |
| `r2-istat-regionale-avq.md` | seconda ondata: Istat regionale AVQ 2025, flussi esaminati |
| `r2-eurostat.md` | seconda ondata Eurostat (debole: un solo candidato) |
| `estrazioni/*.md` | resoconti degli script di estrazione |
| `design-piattaforma.md`, `passaggio-piattaforma.md` | l'architettura e le API |

**Vincolo del committente (2 ottobre 2026):** ultimo anno di riferimento 2025 o
2026. Tutto ciò che si ferma al 2024 è stato estratto o descritto ma non pubblicato.

## Entrato in produzione (39 indicatori)

Istat provinciale (famiglia `ipr`, 8 serie, solo province): speranza di vita a 65
anni, figli per donna, indice di vecchiaia, saldo migratorio interno, natalità, età
media della madre al parto, disoccupazione 15-74, attività 15-64.
Eurostat regionale (`eur`, 5): `ilc_mdes01_r`, `hrst_st_rcat`, `lfst_r_lfe2ehour`,
`tour_occ_nin2`, `tour_occ_anor2`. ACI (`aci`, 2, province e regioni): auto
immatricolate fino al 2009, alimentazione alternativa. AGCOM (`agcom`, 1): fibra
FTTH, 105 province e 19 regioni (senza Bolzano, Trento e Trentino Alto Adige, per la
lacuna dichiarata dalla fonte). Multiscopo AVQ 2025 (23 serie regionali, `MULTI_*`).
Punteggio della qualità della vita: solo `eur:ilc_mdes01_r` e `eur:hrst_st_rcat`.

## Pronti ma fermi al 2024 (estratti, testati, non pubblicati)

Si accendono con **una riga** nella tabella `PUBBLICATI` di
`scripts/nuovi_dati/build_external.py` (più la famiglia in `app/sources.py` che esiste
già per `mef` e `ispra`). Condizione per riprenderli: Nello accetta dati al 2024, o
escono i dati più recenti.

- **MEF, IRPEF su base comunale** (ramo `nmaiese/nd-estr-mef`): reddito imponibile
  medio, imposta netta media, quota di contribuenti oltre 55.000 euro; 107 province e
  20 regioni, 2015-2024. Il Dipartimento delle Finanze ha pubblicato l'anno d'imposta
  2024 il 23 aprile 2026 (etichettato "2025 a.i. 2024"); gli ZIP per il 2025 e il 2026
  rispondono 404. Prossimo rilascio atteso primavera 2027. Licenza CC BY 3.0 IT.
  Le quattro province sarde abolite nel 2016 sono ricondotte alla provincia attuale.
- **ISPRA, consumo di suolo** (ramo `nmaiese/nd-estr-ispra`): quota di aree a
  pericolosità idraulica consumate, territorio alterato entro 100 m, nuovo consumo di
  suolo per ettaro; 107 province e 20 regioni, 2006-2024. Rapporto SNPA a cadenza
  annuale di ottobre: **controllare se è uscita l'edizione 2026 con dati 2025** prima
  di tutto il resto. L'URL pubblico del file completo (63 MB) non è stato ricostruito.
  La percentuale di suolo consumato è doppione di `10AMB018P`: non estrarla.
- **Eurostat `demo_r_fagec3`, madri con meno di 20 anni** (107 province NUTS3 e 20
  regioni, 2015-2024) e **`tran_r_vehst`, autovetture per 1.000 abitanti** (regioni,
  2015-2024, Valle d'Aosta a 1.936 per effetto delle flotte): sono in
  `app/static/data/nuovi/eurostat_nuovi.csv`, fuori da `PUBBLICATI`.

## Candidati buoni, non fatti

- **Quota di stranieri residenti** (Istat, 1 gennaio 2025): il numeratore è
  `29_317_DF_DCIS_POPSTRCIT1_24` (`CITIZENSHIP=WORLD`, `SEX=9`), il denominatore
  `22_289_DF_DCIS_POPRES1_1` è andato in timeout. Un solo scaricamento in più la
  chiude. Verso contextual.
- **Movimprese, tasso di crescita e mortalità delle imprese per provincia** (2025,
  trimestri 2026): il CSV sta dietro un reCAPTCHA, va scaricato a mano una volta; la
  licenza è "citare la fonte", non una CC: da chiarire con movimprese@infocamere.it.
- **Istat `DF_DCSS_BEST_PPC_*`, Censimento permanente provinciale** (soddisfazione per
  la vita 8-10, sicurezza camminando al buio, rischio di criminalità percepito, lavoro
  da casa `DCSS_LCAS_FRISC_1`): 107 province ma **ultimo anno 2024**, e i valori sono
  stime di persone, la quota si calcola. Il BES provinciale non ha il dominio 8.
- **Mortalità stradale per gravità** (`41_287_DF_DCIS_INDINCIDENT_1`, `KILLEDINDX`):
  2001-2024, instabile nelle province piccole.
- **Eurostat `isoc_r_iacc_h`, accesso a Internet** (2023-2025, NUTS2): probabile
  doppione dell'ICT Multiscopo `MULTI_ICT_*`, da confrontare cella per cella.
- **Eurostat `ilc`/`lfst` e altri** (stanze per persona, aggressioni, mortalità per
  diabete e autolesionismo): ultimo anno 2023 o campione piccolo, o richiedono una
  decisione metodologica per il Trentino Alto Adige (tassi standardizzati).
- **AVQ non estratti** (le sei serie a campione piccolo, tenute nell'atlante ma fuori
  dai quiz): vedi `MULTI_*` in `scripts/multiscopo_sources.py` e `_MULTI_QUIZ_EXCLUDED`
  in `app/quiz.py`. Non estratte per scelta: ricoveri e giorni di degenza, 5 porzioni
  al giorno (estratta, fuori dal gioco), mezzi di trasporto diversi dal bus.

## Scartati, e perché

| fonte | motivo |
| --- | --- |
| Istat SIR `DF_DIPS_SIR_IND_TERR_DRT_MUN_1` | 5 tentativi in timeout, HTTP 400 con più codici; **nessun dato letto**, ultimo anno ignoto (probabile 2022 o 2023). Il flusso porta anche i comuni. Se si riprova: un codice per volta con `startPeriod`, e solo i relativi (incidenza microimprese, addetti per 100 residenti, unità locali per 100 residenti, addetti con istruzione terziaria, alta tecnologia). Premia il Nord industriale: tenerlo contextual |
| Istat Forze di lavoro `..._UNT2020_*` | serie ferme al 2020 |
| Istat Censimento `DCSS_HUDW_*` (abitazioni) | Censimento 2021, un solo anno |
| Istat mortalità per causa provinciale `39_494_DF_DCIS_CMORTE1_RES_8` | timeout, tassi standardizzati non verificati |
| Istat `34_215`, `34_217` (arretrati, carico spese) | hanno il 2025 ma solo Italia e ripartizioni, nessun NUTS2 |
| Istat AVQ `83_63_141` (soddisfazione per la vita), ICT `60_130`, reddito `32_*`, spesa `31_740`, povertà `34_727` | ultimo anno 2024, già in catalogo |
| Istat turismo `122_54`, trasporto merci, edilizia, vittime di reati `73_230` | assoluti |
| ACI "Veicoli su popolazione" e incidenti ACI-Istat per provincia | 2024; il dettaglio provinciale 2025 degli incidenti esce a ottobre 2026 |
| GSE fotovoltaico, Terna consumi, INPS dipendenti, SINAB biologico, ISPRA IdroGEO e qualità dell'aria | 2024 o provvisori, tabelle in PDF, licenza non trovata (Terna), denominatore da aggiungere |
| Banca d'Italia (prestiti, depositi) | Base dati statistica non interrogabile da script, licenza ambigua, nessun valore letto |
| ANAC appalti | portale rifiuta il client, licenza CC BY-SA, assoluti |
| Ministero dell'Interno (delitti denunciati), OMI, AGENAS, ARERA, Protezione Civile | server in timeout o non raggiunti: **non verificati**, non scartati |
| Ministeri R2d (MIM a.s. 2024/25, farmacie, MUR iscritti, giustizia civile) | il worker è stato fermato prima del rapporto: i file scaricati non sono stati letti. Scuola e salute: estrattori incompleti, MIM a.s. 2024/25 al limite del vincolo. **Non verificati** |
| Salute: vaccinazioni (campagna 2024-25), screening ISS | campagna a cavallo del 2025, licenza ISS non trovata |

## Regole da non ripetere

- **Istat SDMX: 5 richieste al minuto per IP, blocco di giorni.** Un solo processo, mai
  in parallelo, solo `scripts/istat_sdmx.py`, e **prima la cache**:
  `/home/nilo/dev/sites/divarioitalia/data/istat_cache` (gitignorata, nel checkout
  principale) contiene già BES, Multiscopo AVQ 2025, indicatori demografici,
  forze di lavoro provinciali e i cataloghi dei dataflow. Nei worktree si collega con
  un symlink e si toglie prima di chiuderli.
- Ogni worktree Orca parte senza cache e senza `.venv`: `DIVARIO_PYTHON` punta
  all'interprete del checkout principale.
- Le cifre dichiarate da un worker si rifanno sempre. Visti qui: `big-pickle` come
  ricercatore Eurostat ha prodotto un solo candidato; `opencode` con `gpt-oss` e
  `longcat` non ha consegnato estrazioni usabili; grok ha finito la quota gratuita;
  Codex ha finito il limite settimanale fino al 4 ottobre 2026 dopo i passi 1-3 della
  piattaforma.
- Un revisore sbaglia come un autore: due falsi allarmi su dieci rilievi nella
  revisione del 2 ottobre (il `sorted()` nelle sfide c'era già, `theme_categories.csv`
  è vuota).

## Come si riprende

1. Nuova serie da una fonte già coperta: aggiungere la riga a `PUBBLICATI` in
   `scripts/nuovi_dati/build_external.py` e lanciare lo script (idempotente).
2. Fonte nuova: script in `scripts/nuovi_dati/`, famiglia in `app/sources.py` con
   licenza letta sulla pagina, procedura completa in `docs/DATA_PIPELINE.md`.
3. Punteggio: solo dopo la misura dello spostamento di rango (media assoluta sotto 1,
   nessun territorio oltre 3, su ogni profilo).
4. Giochi: nuova riga in `config/game_indicators.csv` con la colonna `dal` nel futuro,
   mai nel passato (`docs/GIOCO.md`, `POOL_CUTOVER`).
