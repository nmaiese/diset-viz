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

**Il tappo è tolto.** Il test che congelava l'elenco delle serie è stato
liberato, e per provare la catena due serie demografiche sono arrivate fino a una
pagina pubblica: `dem:NMIGRATEIN` (saldo migratorio interno) dentro il punteggio,
`dem:BIRTHRATE` (tasso di natalità) fuori. Vedi [Lo sblocco](#lo-sblocco-il-tappo-è-tolto).

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

## Lo sblocco: il tappo è tolto

Per un giorno lo stadio uno è rimasto chiuso per costruzione. Lo scout aveva
verificato e cablato due serie demografiche nuove sul dataflow
`22_293_DF_DCIS_INDDEMOG1_1`, `NMIGRATEIN` e `BIRTHRATE`, ma
`tests/test_discovery.py` congelava l'elenco esatto degli id ammessi in tre
asserzioni, dentro una classe chiamata `AdmittingASeriesIsConfigNotCode` che
faceva l'opposto del proprio nome. L'agente non aveva toccato i test, aveva
scritto perché, e si era fermato: la terza volta che un agente della catena si
ferma davanti a una guardia sbagliata invece di aggirarla, e la terza che aveva
ragione.

I tre test ora verificano il **meccanismo, non il contenuto**:

- il config carica ogni serie ben formata, ma l'elenco può crescere. La forma di
  ogni riga ammessa resta sorvegliata da `tests/test_source_admission.py`.
- il round trip di uno scalare quotato (`"%"`) si prova su una riga di test
  controllata, non pretendendo che ogni serie sia in percentuale.
- la discovery offline si confronta con le serie che hanno un fixture, così
  ammettere una serie live-only (lo scout scrive la riga di config ma non il
  fixture) non rompe più la suite.

Con il tappo tolto, `config/istat_series.yaml` è cresciuto da due a quattro serie,
e le due nuove sono state fatte scorrere lungo l'intera catena dai suoi agenti
reali (curatore, scrittore, revisore):

- **`dem:NMIGRATEIN`** (saldo migratorio interno): verso corretto da `contextual`
  a **`higher_better`** contro il report Istat sulle migrazioni interne (che
  inquadra l'emigrazione dal Mezzogiorno come una perdita), categoria
  `lavoro_opportunita`, **prima serie demografica a entrare nel punteggio**.
  Nessuna regione cambia posizione.
- **`dem:BIRTHRATE`** (tasso di natalità): verso **`contextual`** confermato. In
  cima convivono Trentino Alto Adige e Campania, un valore alto riflette struttura
  per età e fecondità, non un vantaggio. Resta fuori dal punteggio.

Fuso in **PR [#43](https://github.com/nmaiese/diset-viz/pull/43)**. La PR dello
scout **[#41](https://github.com/nmaiese/diset-viz/pull/41)** è chiusa, superata:
le sue due righe di config e la segnalazione della licenza vivono in #43.

### Tre cose che lo scout aveva trovato fuori dal proprio perimetro

1. **La licenza Istat era sbagliata, ora corretta.**
   `scripts/istat_regional_source.py`, `config/external_sources.yaml` (le quattro
   righe Istat) e `app/sources.py` (famiglia `dem`, anche il `license_url`)
   dichiaravano `CC BY 3.0 IT`; Istat dichiara **CC BY 4.0** su
   <https://www.istat.it/note-legali/> (verificato). Corretto in #43.
2. **`scout_sources.py` tronca la coda alfabeticamente.** Le proposte sono 87, il
   `limit=40` con punteggio uniforme ordina per nome, quindi la coda si ferma a
   "Notti in Italia" e le altre 47 non sono mai state viste da nessuno. Ancora
   aperto.
3. **`REGIONAL_HINT` non riconosce `- reg.`**, l'abbreviazione che Istat usa
   davvero: cerca `\b(region|nuts2)`. È il motivo per cui la spesa sociale dei
   comuni per regione non è mai arrivata in coda. Ancora aperto.

## Stato dei dati

Famiglie in atlante: backbone territoriale, esterni verticali, BES regionale,
Multiscopo, più le province SDMX. Le due famiglie arrivate dalla catena:

- **Eurostat regionale (NUTS2)**, `eurostat_regional`. `eur:rd_e_gerdreg` (spesa
  R&S sul PIL) e `eur:rd_p_persreg` (personale addetto a R&S): scoperti,
  promossi, curati con verso `higher_better` confermato dai dati, **entrambi nel
  punteggio qualità della vita**. PIL pro capite (`nama_10r_2gdp`) riconosciuto
  `proxy` dell'id territoriale 901: arricchisce quell'indicatore, non è una voce
  separata.
- **Indicatori demografici Istat**, `istat_demografia`. Tre serie in catalogo.
  `dem:OLDAGEDEPR` (indice di dipendenza degli anziani): prima serie non Eurostat
  ad attraversare la catena, verso `contextual`, fuori dal punteggio (un rapporto
  di dipendenza non ha un migliore). `dem:NMIGRATEIN` (saldo migratorio interno):
  verso `higher_better`, categoria `lavoro_opportunita`, **la prima serie
  demografica dentro il punteggio**. `dem:BIRTHRATE` (tasso di natalità): verso
  `contextual`, fuori dal punteggio. `istat_demografia:DEPENDRATE` è fermo a
  `needs-info`, perché si sovrappone in parte a OLDAGEDEPR e la scelta fra tenerne
  uno o entrambi non è stata presa.

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

1. **Le proposte dello scout** in `data/discovery/source_candidates.csv`: 15
   valutate il 26 luglio, nessuna approvata (ognuna con il motivo scritto in
   `triage_notes`), 72 mai viste, di cui 47 nemmeno proposte per via del
   troncamento alfabetico.
2. **Il secondo adapter di famiglia**: oggi la catena cabla da sola solo dataflow
   SDMX Istat. Eurostat resta a selezione curata in `EUROSTAT_SERIES`, dentro
   `scripts/eurostat_source.py`, quindi ammettere una serie Eurostat è ancora
   codice. Stessa forma dell'adapter Istat, quindi lo stesso trattamento a
   config è possibile.
3. **Profili regionali** (`app/profiles.py`): calcolati sui soli territoriali
   core, non includono ancora le famiglie esterne.
4. **Livello provinciale (NUTS3)** nella watchlist, sempre con priorità al
   regionale fresco.
5. **Le due lacune di `scout_sources.py`** segnalate dallo scout (il troncamento
   alfabetico della coda e `REGIONAL_HINT` che non riconosce `- reg.`, entrambe
   sopra). La licenza Istat, che era il terzo punto, è stata corretta in #43.
6. **La licenza del backbone `istat_lavoro`**: le righe di quella famiglia nel
   layer esterno (`normalized_external_indicators.csv`, tasso di disoccupazione e
   simili) portano ancora `CC BY 3.0 IT`, committate da un refresh precedente di
   `scripts/update_data.py`. La correzione di #43 ha sistemato la famiglia `dem` e
   `config/external_sources.yaml`, non quelle righe già scritte. Vanno corrette al
   prossimo refresh, o con una passata mirata sul CSV.

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
- **La CI non parte da sola sulle PR aperte via il GitHub MCP.** GitHub non lancia
  i workflow per eventi creati dal token dell'app (anti-ricorsione), quindi una PR
  aperta così resta senza check e il box di merge sembra bloccato pur non essendo
  fallito niente. Si fa partire a mano con `workflow_dispatch` su `ci.yml` (o dalla
  UI), oppure si apre la PR con `gh`, che usa il token dell'utente e li innesca.
- **`pipeline_dashboard.py` non crasha più senza `gh`.** `open_pull_requests`
  cattura `FileNotFoundError`/`OSError` e la sezione PR dice solo che `gh` non c'è,
  invece di far morire tutto il cruscotto. È quello che pretende la classe di test
  `TheDashboardReadsWithoutBreaking`.
- **Il caso `nothing` del diario si regge solo sul contratto.** Una run a mani
  vuote non ha un branch da giudicare, quindi il cancello non la può raggiungere:
  se un agente non scrive quella riga, nessuna guardia se ne accorge. È il punto
  più debole del monitoraggio, ed è noto.
