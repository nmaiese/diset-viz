# Stato della catena

Il documento che si tiene aggiornato. Dice **dove sta il sistema adesso**: cosa
gira da solo, con quale cadenza, cosa resta umano e cosa non è ancora fatto.

Per come funziona: [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).
Per il meccanismo della scoperta: [`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md).
Per il contratto di ogni agente: [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md).

Aggiornato al **2026-07-26**.

## In una riga

Sei stadi, cinque agenti, tutti schedulati, **nessuno che aspetti una firma**.
Un indicatore va da un catalogo SDMX a una pagina pubblica senza intervento, e la
catena ci ritorna sopra quando i dati si muovono.

**Ma oggi lo stadio uno non passa.** Un test congela l'elenco delle serie
ammesse, quindi nessuna fonte nuova entra finché non viene liberato: vedi
[Il tappo](#il-tappo-lo-stadio-uno-non-passa). Tutto il resto della catena
funziona e lavora sull'arretrato che ha già.

## Lo stato, in un comando

```bash
python3 scripts/pipeline_status.py
```

Questo documento invecchia, quel comando no. Se i due non concordano, ha ragione
il comando.

## Le Routine

Agenti cloud, sessione nuova a ogni firing, checkout git proprio, environment
`divarioitalia` (`env_01VgKtjzcUbEYYgZb81pYEfS`). Si gestiscono su
<https://claude.ai/code/routines>.

| agente | definizione | cron (UTC) | merge | routine id |
| --- | --- | --- | --- | --- |
| scout | `source-scout.md` | `0 5 * * 0` (dom) | checks | `trig_01KZ1CHGPRgNmF9Ahni9VXfQ` |
| cacciatore | `indicator-hunter.md` | `0 6 * * 1` (lun) | checks | `trig_01VizeycZocZoeDE1RxjWj1f` |
| curatore | `indicator-curator.md` | `0 6 * * 4` (gio) | checks | `trig_019EP6TnEbYnKz8VpKFaRm4g` |
| scrittore | `indicator-writer.md` | `0 6 * * 6` (sab) | auto | `trig_01RymCgC8VsspDrHHnUJgFUk` |
| revisore | `indicator-reviewer.md` | `0 7 * * *` (ogni giorno) | auto | `trig_01LSZpaDasW18ZvxbKhXBJSj` |

Cadenza sfalsata di proposito: ogni stadio ha senso solo dopo che quello a monte
ha prodotto qualcosa. Il revisore gira ogni giorno perché lavora su un arretrato
di centinaia di articoli e non su ciò che è appena arrivato.

Nessuna riga di questa tabella dice `manual`, e non è una svista. La catena è non
presidiata per decisione presa: un modo che parcheggia la pull request finché
qualcuno guarda, in un sistema che nessuno guarda, vuol dire fermo per sempre.
`checks` non è un'attesa di approvazione, è un'attesa della CI, e la esegue
`scripts/pipeline_merge.py`.

**Il prompt di ogni Routine punta ai file, non li ricopia.** Vedi sotto perché.

## Cosa è successo il 2026-07-26

Giornata di lavoro sulla catena, dopo una prova end-to-end che ha trovato tre
cose rotte e due mancanti.

**Rotto e riparato:**

- La Routine dello scrittore girava dal 25 luglio scrivendo in
  `app/static/data/analyst_notes.json`, un file che l'app **non legge più** dalla
  migrazione al modello a quattro sezioni. Girava, non falliva, e non arrivava in
  nessuna pagina. Causa: il prompt riproduceva il contratto invece di puntarlo.
  Ora i prompt puntano a `.claude/agents/` e a `docs/AGENT_CONTRACT.md`, e lo
  strato `analyst_notes` è stato rimosso (il testo pre-migrazione resta leggibile
  in git a `9da6c0b`).
- Il documento diceva che le Routine di scrittore e revisore erano "da
  registrare". Lo scrittore era registrato da un giorno. Il revisore no.
- La catena non tornava mai su ciò che aveva già pubblicato: ogni coda drenava
  una volta e restava a zero, il che faceva sembrare il sistema finito mentre il
  catalogo invecchiava sotto.

**Aggiunto:**

- `scripts/pipeline_gate.py`, il verdetto deterministico con cui ogni stadio
  chiude, con `tests/test_pipeline_gate.py` che costruisce prima l'input cattivo.
- `scripts/pipeline_status.py`, lo stato di tutti e sei gli stadi in un comando.
- Il rientro: `data_year` in `curation.csv`, `reviewed_vintage` negli articoli.
- `source-scout`, il quinto agente, e `config/istat_series.yaml` /
  `config/theme_categories.csv`, i due file che fanno crescere il bacino senza
  scrivere codice.

## Cosa è successo dopo, lo stesso giorno

Seconda tornata, con un obiettivo esplicito: **zero intervento umano nel flusso**,
e una prova end to end dalla fonte alla pagina. Ha trovato altre quattro cose.

**Il merge `checks` non è mai esistito.** Il contratto diceva a tre stadi di
chiudere con `gh pr merge --auto`, convinto che parcheggiasse la PR fino ai check
verdi. Su questo repo non lo fa: `allow_auto_merge` è falso e `master` non è
protetto, quindi `gh` ripiega su un merge immediato. Una PR sonda si è fusa con
il job dei test ancora `IN_PROGRESS`. Da quando la politica è stata scritta, il
cacciatore, il promotore e il curatore fondevano al buio credendo di aspettare, e
non c'era niente da nessuna parte che lo dicesse. L'attesa ora vive in
`scripts/pipeline_merge.py`, che rilegge il cancello per conto suo, sonda i check
finché non concludono e rifiuta se uno fallisce, se non ne compare nessuno o se
il cancello è rosso. Verificato contro una PR vera, non solo con un `gh` finto.

**Lo scout non aspetta più una firma.** Era l'unico stadio `manual`, cioè il
tappo: la scoperta si fermava alla sua PR e non ripartiva. Ora è `checks`, e il
controllo si è spostato dove può girare da solo, in
`tests/test_source_admission.py`.

**Una riga di configurazione sbagliata uccideva l'intera scansione** del
cacciatore, non solo la propria serie, con un traceback che nessuno leggeva. Da
quando è lo scout a scrivere quelle righe, era il modo in cui la catena si
sarebbe rotta da sola. Ora una serie illeggibile costa solo se stessa, e viene
riportata su stderr, nella PR e nel diario.

**Il diario non vedeva il silenzio.** Una Routine che smette di partire non
lascia nessuna traccia, e uno stadio fermo da un mese ha lo stesso aspetto di uno
che ha finito il lavoro: è la stessa forma del bug dello scrittore.
`pipeline_log.silence()` lo misura contro `WATCH_GROUPS`, e status e cruscotto lo
mostrano.

## Il tappo: lo stadio uno non passa

Alla prima run vera con il merge automatico, lo scout ha verificato e cablato due
serie demografiche regionali nuove sul dataflow `22_293_DF_DCIS_INDDEMOG1_1`,
`NMIGRATEIN` (saldo migratorio interno) e `BIRTHRATE` (tasso di natalità),
copertura 20 regioni su 20, serie continua dal 2015 al 2024, valori controllati
contro il report Istat. Poi il cancello l'ha bloccato, e non per colpa sua.

`tests/test_discovery.py` congela l'elenco esatto degli id ammessi:

```python
assertEqual(sorted(series), ["DEPENDRATE", "OLDAGEDEPR"])   # riga 316
assertEqual(spec["unit"], "%")                              # riga 320, innescata dalla 316
assertEqual(len(discovered), len(ISTAT_SERIES))             # riga 409, in una run offline
```

La classe si chiama `AdmittingASeriesIsConfigNotCode`. Ammettere una serie **è**
configurazione e non codice, esattamente come dice il nome, ma poi il test la
inchioda a due valori: il tetto non è stato tolto dal Python, è stato spostato
nella suite. La terza asserzione è peggio, perché pretende un fixture offline per
ogni serie, e i fixture stanno fuori dal perimetro dello scout: una serie ammessa
non può averlo, quindi non può passare.

L'agente non ha toccato i test, ha scritto perché, e si è fermato. È la terza
volta che un agente di questa catena si ferma davanti a una guardia sbagliata
invece di aggirarla, e la terza volta che aveva ragione.

**PR [#41](https://github.com/nmaiese/diset-viz/pull/41) aperta e non fusa**, sul
branch `automation/scout-2026-07-26`. Contiene le due righe di configurazione e
il triage di 15 proposte. Il prossimo lavoro su questa catena è liberare quei tre
test, o lo stadio uno resta chiuso per costruzione e i cinque a valle lavorano
per sempre solo sull'arretrato che hanno già.

### Tre cose che lo scout ha trovato fuori dal proprio perimetro

1. **La licenza Istat nel repo è sbagliata.** `scripts/istat_regional_source.py`
   e `config/external_sources.yaml` dichiarano `CC BY 3.0 IT`, Istat dichiara
   **CC BY 4.0** su <https://www.istat.it/note-legali/>. Compare sulle pagine
   pubbliche degli indicatori di quella famiglia.
2. **`scout_sources.py` tronca la coda alfabeticamente.** Le proposte sono 87, il
   `limit=40` con punteggio uniforme ordina per nome, quindi la coda si ferma a
   "Notti in Italia" e le altre 47 non sono mai state viste da nessuno.
3. **`REGIONAL_HINT` non riconosce `- reg.`**, l'abbreviazione che Istat usa
   davvero: cerca `\b(region|nuts2)`. È il motivo per cui la spesa sociale dei
   comuni per regione non è mai arrivata in coda.

## Stato dei dati

Famiglie in atlante: backbone territoriale, esterni verticali, BES regionale,
Multiscopo, più le province SDMX. Le due famiglie arrivate dalla catena:

- **Eurostat regionale (NUTS2)**, `eurostat_regional`. `eur:rd_e_gerdreg` (spesa
  R&S sul PIL) e `eur:rd_p_persreg` (personale addetto a R&S): scoperti,
  promossi, curati con verso `higher_better` confermato dai dati, **entrambi nel
  punteggio qualità della vita**. PIL pro capite (`nama_10r_2gdp`) riconosciuto
  `proxy` dell'id territoriale 901: arricchisce quell'indicatore, non è una voce
  separata.
- **Indicatori demografici Istat**, `istat_demografia`. `dem:OLDAGEDEPR` (indice
  di dipendenza degli anziani): prima serie non Eurostat ad attraversare tutta la
  catena. Verso `contextual` confermato, quindi integrato e descritto ma **fuori
  dal punteggio**: un rapporto di dipendenza non ha un migliore.
  `istat_demografia:DEPENDRATE` è fermo a `needs-info`, perché si sovrappone in
  parte a OLDAGEDEPR e la scelta fra tenerne uno o entrambi non è stata presa.

## Cosa resta umano, e perché

Niente, nel flusso. Nessuno stadio aspetta un'approvazione: la catena è non
presidiata per decisione presa, e un modo `manual` in una catena che nessuno
guarda vuol dire fermo per sempre. Lo scout era l'unico rimasto così, ed era
esattamente il tappo che teneva ferma tutta la scoperta di indicatori nuovi.

Restano fuori due cose, che non sono approvazioni ma lavoro che gli agenti non
possono fare:

1. **Scrivere un adapter** per una fonte che non è un dataflow SDMX Istat. È
   codice, e nessun agente scrive codice. Lo scout che approva una fonte del
   genere lo scrive nella PR e descrive che adapter servirebbe.
2. **Creare una categoria** della qualità della vita. È una sezione del sito con
   un nome, una descrizione e una macro-area, non una riga di mappatura. Mappare
   un tema a una categoria esistente invece è del curatore.

## Cosa non è ancora fatto

1. **Liberare `tests/test_discovery.py`** dalle tre asserzioni che congelano
   l'elenco delle serie (vedi [Il tappo](#il-tappo-lo-stadio-uno-non-passa)).
   Finché restano, nessuna fonte nuova entra e la PR #41 non può fondersi. È il
   primo lavoro da fare, prima di qualunque altra cosa su questa catena.
2. **Le proposte dello scout** in `data/discovery/source_candidates.csv`: 15
   valutate il 26 luglio, nessuna approvata (ognuna con il motivo scritto in
   `triage_notes`), 72 mai viste, di cui 47 nemmeno proposte per via del
   troncamento alfabetico.
3. **Il secondo adapter di famiglia**: oggi la catena cabla da sola solo dataflow
   SDMX Istat. Eurostat resta a selezione curata in `EUROSTAT_SERIES`, dentro
   `scripts/eurostat_source.py`, quindi ammettere una serie Eurostat è ancora
   codice. Stessa forma dell'adapter Istat, quindi lo stesso trattamento a
   config è possibile.
4. **Profili regionali** (`app/profiles.py`): calcolati sui soli territoriali
   core, non includono ancora le famiglie esterne.
5. **Livello provinciale (NUTS3)** nella watchlist, sempre con priorità al
   regionale fresco.
6. **La licenza Istat sbagliata** e le due lacune di `scout_sources.py`
   segnalate dallo scout, elencate sopra.

## Gotcha per la prossima sessione

- Gli id BES contengono trattini (es. `09PAE009-N25`): per questo il codice
  `<acr>-<id>` è un **segmento separato in coda**
  (`/indicatore/<slug>/bes-09PAE009-N25`), e lo slug non è mai fuso con l'id.
- Non hardcodare etichette fonte o URL indicatore: passano tutti da
  `app/sources.py`. Non cablare mai un prefisso di famiglia.
- Gli script della catena sono **stdlib puri** (niente import di `app.*` a
  load-time): devono girare nell'agente schedulato senza Flask.
- Cache grezza Eurostat (`data/eurostat_cache/`) e Istat (`data/istat_cache/`)
  gitignorate; committati solo i fixture in `data/discovery/fixtures/`.
- Il curatore non dichiara mai `exact`; `score_eligible=true` è rifiutato se il
  verso non è direzionale.
- **Bolzano+Trento**: BES e territoriali ricevono già da Istat l'aggregato
  Trentino Alto Adige. Eurostat e Multiscopo lo combinano con **media pesata per
  popolazione**, non con media semplice.
- **Niente workflow GitHub per i dati**: il refresh dei backbone e del Multiscopo
  si esegue a mano con `scripts/refresh_official_local.sh`. Il branch
  `claude/discovery-schedule-action` (commit `22902fa`), che schedulava il
  cacciatore come workflow GitHub, **non va unito**: contraddice questa scelta.
- **La suite crasha di SIGSEGV, a caso, circa una run su venticinque**, e non è
  dove sembrava. Con `-X faulthandler` su 24 run consecutive si è riprodotto una
  volta, e il frame è dentro
  `app.indicator_view.build_indicator_view`, raggiunto da
  `pipeline_dashboard.render` mentre costruisce la vista di ogni indicatore del
  catalogo. Non è quindi un artefatto dello spegnimento dell'interprete, come si
  era creduto: può morire anche a metà, prima di qualunque referto. La causa vera
  resta ignota. Di conseguenza `pipeline_gate.check_suite` e `ci.yml` distinguono
  tre casi e non due: `FAILED` è rosso e **non si ritenta mai** (è un bug con un
  referto, e ritentarlo sarebbe nasconderlo), `OK` con uscita non-zero è verde e
  lo si dice a voce alta, morte **senza referto** è un'assenza di risposta e si
  ritenta una volta sola, con la seconda che è definitiva.
- In una shell dell'utente `python3` è una funzione che rilancia il comando
  quando esce non-zero, quindi l'output di uno script che fallisce **appare due
  volte**. Non è un bug del programma.
- **`gh pr merge --auto` non aspetta niente su questo repo.** Con
  `allow_auto_merge` a falso e `master` non protetto, `gh` ripiega su un merge
  immediato senza dirlo. Nessuno stadio deve usarlo: si chiude con
  `python3 scripts/pipeline_merge.py --stage <stadio> --pr <numero>`.
- **Il caso `nothing` del diario si regge solo sul contratto.** Una run a mani
  vuote non ha un branch da giudicare, quindi il cancello non la può raggiungere:
  se un agente non scrive quella riga, nessuna guardia se ne accorge. È il punto
  più debole del monitoraggio, ed è noto.
