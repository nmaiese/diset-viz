# Pipeline dati provinciali (Istat SDMX)

Questa pipeline recupera dati **provinciali** (NUTS3, 107 codici pubblicati)
dal web service SDMX dell'Istat e li normalizza in un dataset
separato, pronto per arricchire la qualità della vita. È una fase di **sola
acquisizione**: non tocca il sito live, il dataset regionale
(`Assoluti_Regione.csv`) né `app/data.py`. L'integrazione nel motore di scoring è
una fase successiva (vedi in fondo).

## Regola d'oro: rate limit Istat

`https://esploradati.istat.it/SDMXWS/rest` permette **5 query al minuto per IP**.
Superarlo **banna l'IP per 1-2 giorni**. La pipeline è costruita per non arrivarci
mai:

- un solo processo, mai parallelo;
- spaziatura **>= 16s** tra le chiamate di rete (`SdmxClient(min_interval=16)`,
  cioè ~4/min);
- **cache su disco** in `data/istat_cache/` (gitignorata): una risposta in cache
  non consuma rete né budget, quindi le run sono ripetibili e riprendibili;
- backoff esponenziale su 429/503, stop esplicito su 403/risposte vuote (possibile
  blocco IP);
- cap di sicurezza `--max-requests` sul fetch.

Nota importante: la spaziatura è garantita **dentro un singolo processo**. Non
lanciare più script in parallelo e non spezzare il lavoro in tante invocazioni
ravvicinate: accorpa le chiamate in un'unica run.

## Dettagli SDMX usati

- Base: `https://esploradati.istat.it/SDMXWS/rest`, agenzia `IT1`.
- Formato **solo via header Accept**: dati `application/vnd.sdmx.data+csv;version=1.0.0`,
  struttura `application/vnd.sdmx.structure+json;version=1.0` (attenzione: la
  struttura vuole `version=1.0`, non `1.0.0`, altrimenti HTTP 406).
- `Accept-Language: it` per avere nomi italiani.
- Bug noto su `endPeriod` (restituisce anno+1): usiamo **solo `startPeriod`** e
  filtriamo gli anni in fase di build.

## Fonte principale: BES dei Territori

Dataflow **`DF_BES_TERRIT_0T`** ("All indicators - All territories", DSD
`BES_TERRIT`). Chiave per posizione: `FREQ.REF_AREA.DOMAIN.DATA_TYPE.SEX.EDITION`.
Scarichiamo **una query per dominio BES** (`BES_01`..`BES_12`), con REF_AREA,
DATA_TYPE, SEX, EDITION a wildcard e `startPeriod=2015`. Teniamo solo il sesso
totale e i codici NUTS3. `BES_08` (benessere soggettivo) non ha dati provinciali
(404) e viene saltato.

## Come si esegue

```bash
# 0. test offline (nessuna rete): SEMPRE prima
.venv/bin/python -m unittest discover -s tests -v

# 1. discovery: 1 query per la lista dataflow, poi shortlist (data/provincia/)
.venv/bin/python scripts/discover_provinces.py
#    ispezione mirata (DSD + codelist territorio): poche query
.venv/bin/python scripts/discover_provinces.py --inspect DF_BES_TERRIT,DF_BES_TERRIT_0T
#    dump codelist usate dalla normalizzazione (nomi italiani)
.venv/bin/python scripts/discover_provinces.py --no-dataflows \
    --dump-codelists CL_SUS_DOMAIN,CL_BES_INDICATOR,CL_SEXISTAT1,CL_ITTER107

# 2. fetch dati BES, ~11 query, throttled e riprendibile
.venv/bin/python scripts/fetch_provinces.py            # tutti i domini
.venv/bin/python scripts/fetch_provinces.py --domains BES_01   # validarne uno

# 3. normalizzazione offline provinciale (legge solo la cache)
.venv/bin/python scripts/build_province_dataset.py                 # province (NUTS3)
```

Il vecchio build `--level region` non va usato sul dataset live: dal 2026
`Assoluti_BES_Regione.csv` è prodotto da `scripts/update_bes_regions.py` usando
il BES nazionale più fresco. Il comando richiede ora un flag esplicito di
override per evitare sovrascritture accidentali. Il dataflow provinciale resta
la fonte corretta per province e città metropolitane.

## Output (in `app/static/data/`)

- **`Assoluti_Provincia.csv`** — stesse 12 colonne di `Assoluti_Regione.csv`, ma
  `Area="Provincia"`. ~48.700 righe, 67 indicatori, 103 unità classificate, 2015-2024.
  `idIndicatore` = codice BES (`DATA_TYPE`, es. `01SAL001`), `Tema` = dominio BES,
  `Dato` con la virgola decimale come nel dataset regionale.
- **`province_manifest.csv`** — la mappa **auditabile**: per ogni indicatore il
  dataflow sorgente, il dominio BES, la **categoria QoL proposta**, la
  **direzione proposta**, l'unità, gli anni e la copertura provinciale.
- **`province_codes.csv`** — le 103 unità classificate: codice NUTS3, nome normalizzato,
  slug (`province_key`), regione, flag città metropolitana.

I tre file sono versionati. La cache grezza (`data/istat_cache/`) no.

## File della pipeline (`scripts/`)

- `istat_sdmx.py` — client SDMX cache-first, rate-limited, con parser SDMX-CSV e
  SDMX-JSON struttura. Stdlib pura.
- `discover_provinces.py` — lista dataflow, shortlist, ispezione DSD/codelist,
  dump codelist.
- `province_sources.py` — selezione curata: dataflow BES, mapping dominio→categoria
  QoL, euristica della direzione proposta, pattern NUTS3/NUTS2.
- `province_names.py` — normalizzazione nomi provincia (bilingui, città
  metropolitane) e slug, coerente con `region_key_for`.
- `fetch_provinces.py` — scarica i domini BES (warma la cache).
- `build_province_dataset.py` — normalizza la cache nei tre CSV sopra.

## Note di qualità e limiti

- **Direzione e categoria nascono da un'euristica** sui nomi italiani, che sbaglia
  sui casi ambigui. Le correzioni stanno in
  `scripts/province_sources.py:CURATED_DIRECTION_BES`, come
  `app/indicator_notes.CURATED_DIRECTION` per i dati regionali. Il verso di un
  indicatore presente anche a livello regionale deve coincidere con quello di
  `bes_regione_manifest.csv`: oggi non coincide su 18 indicatori.
- La codelist Istat `CL_ITTER107` porta sia le **province sarde pre-2016**
  (Ogliastra, Medio Campidano, Carbonia-Iglesias, Olbia-Tempio), con dati solo
  fino al 2019, sia i codici delle province nate dopo, `IT108`-`IT111` (Monza e
  della Brianza, Fermo, Barletta-Andria-Trani, Sud Sardegna), che nella cache
  hanno dati fino all'edizione 2025.
- `BES_08` (benessere soggettivo) non è mappato a una categoria (resta contesto).

## Visualizzazione (già attiva)

La classifica è online con lo stesso motore per **regioni e province**, ma con
fonti adeguate al livello: BES nazionale 2026 per le regioni e BES dei Territori
per le province. Le route sono `/qualita-della-vita/classifica/regioni` e
`…/classifica/province` (con
`?profilo=`), API `/api/quality-life/<livello>/rankings[/<profilo>]` e
`/api/quality-life/<livello>/<key>`. Il motore unico è
[`app/quality_life_bes.py`](../app/quality_life_bes.py) (z-score orientato,
delta-rank, campioni e classifiche per categoria), con loader
[`app/bes_data.py`](../app/bes_data.py). Il loader legge
`Assoluti_Provincia.csv`, `province_manifest.csv` e `province_codes.csv`
direttamente, senza passare da `app/data.py` e senza toccare la soglia
`len(regions)==20` del catalogo regionale.

Che cosa entra nello score:
- gli indicatori con un verso: le direzioni curate a mano stanno in
  `scripts/province_sources.py:CURATED_DIRECTION_BES` (correggono sia gli errori
  dell'euristica, es. "mancata partecipazione" e "raccolta differenziata", sia i
  contestuali). Restano fuori gli indicatori privi di etichetta leggibile;
- le province che passano `NUTS3_PATTERN` (`scripts/province_sources.py`), meno le
  quattro sarde soppresse prima del 2016 (`DEFUNCT_PROVINCES`). La regex non
  riconosce i codici `IT1xx`, quindi oggi scarta anche `IT108`-`IT111`, che nella
  cache hanno i dati: non è una scelta. Il denominatore di copertura è scritto a
  mano in `build_province_dataset.py`;
- **campioni per categoria**: la pagina mostra la provincia che guida ogni
  categoria, per far emergere le specializzazioni;
- nessuno stretch artificiale dei punteggi: la cura delle direzioni basta a
  ridurre la compressione (media 50 per costruzione).

## Seconda fonte: valutata, non integrata (per scelta)

Esistono due dataflow provinciali "All indicators" puliti su SDMX:
- `DF_BES_TERRIT_0T` (BES, **usato**);
- `DF_DIPS_SIR_IND_TERR_DRT_MUN_1` ("Indicatori e territorio", DSD
  `DIPS_SIR_IND_TERR_DRT`, codelist indicatori `CL_SIR_INDICATORS`, 88 indicatori,
  NUTS3, chiave `FREQ.REF_AREA.DATA_TYPE`).

Il SIR è la parte **economica** (produttività, valore aggiunto per addetto, costo
del lavoro, micro-imprese, quota alta tecnologia, numero imprese/addetti). È valido
e pulito, ma **non integrato per scelta**: molti indicatori sono assoluti (taglia →
rivincerebbe sempre la metropoli) e anche i relativi premiano il Nord industriale,
quindi spingerebbe la classifica verso il Nord invece di aggiungere varietà. Resta
disponibile come futuro layer "dinamismo economico" per il profilo *Opportunità*,
coi soli indicatori relativi. Le dimensioni che darebbero varietà territoriale
(ambiente, servizi, trasporti, digitale, turismo a livello provinciale) non sono un
singolo dataflow consolidato, solo flussi sparsi mono-tema.

Vedi anche [`docs/DATA_PIPELINE.md`](DATA_PIPELINE.md) per lo strato dati regionale.
