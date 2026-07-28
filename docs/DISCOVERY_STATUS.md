# Stato della catena

Il documento che si tiene aggiornato. Dice **dove sta il sistema adesso**: cosa
gira da solo, con quale cadenza, cosa resta umano e cosa non è ancora fatto.

Per come funziona: [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).
Per il meccanismo della scoperta: [`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md).
Per il contratto di ogni agente: [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md).

Aggiornato al **2026-07-28**.

## In una riga

**Tre ruoli, per-indicatore, un lanciatore che ne mette piu' di uno in volo
insieme**, e nessuno che aspetti una firma. Un indicatore va da un catalogo SDMX
a una pagina pubblica senza intervento, e la catena ci ritorna sopra quando i
dati si muovono.

> **La ri-architettura del 28 luglio (sera).** La catena e' passata da sette
> stadi a **tre ruoli** (ammissione = scout+hunter+promoter, produttore =
> curator+writer+reviewer, verificatore invariato) e da uno **stadio per tick** a
> un **lanciatore per-indicatore** (`scripts/pipeline_launch.py`, agente
> `launcher`) che lancia in parallelo, perche' indicatori diversi toccano file
> diversi e non contendono. Il dispatcher (`pipeline_dispatch.py`) e il lock
> una-PR-aperta sono ritirati. Il monitoraggio e' la rotta viva `/_pipeline`
> (piu' `scripts/pipeline_monitor.py`). **La Routine va ri-puntata**: il suo
> prompt cita ancora il dispatcher, va cambiato a `launcher.md` (vedi
> [Le Routine](#le-routine)); e' in pausa, quindi non fa danni finche' non si
> riaccende. Il perche' della forma nuova sta in
> [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).

**Il tappo è tolto.** Il test che congelava l'elenco delle serie è stato
liberato, e per provare la catena due serie demografiche sono arrivate fino a una
pagina pubblica: `dem:NMIGRATEIN` (saldo migratorio interno) dentro il punteggio,
`dem:BIRTHRATE` (tasso di natalità) fuori. Vedi [Lo sblocco](#lo-sblocco-il-tappo-è-tolto).

**E la catena ha smesso di pestarsi i piedi**, che era il difetto che restava.
Tre cose insieme, il 27 luglio: il dispatcher al posto di sei cron, i registri a
un file per record al posto di tre file unici a cui tutti appendevano, e il
`run_id` al posto di `(stadio, pr)` come identità di una run. Vedi
[Cosa è successo il 2026-07-27](#cosa-è-successo-il-2026-07-27).

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

**Una sola Routine, quella del dispatcher.** Gli stadi non hanno più un cron
proprio: il dispatcher gira a battito, legge tutte le code e lancia un solo
stadio per volta, il primo con lavoro in ordine di catena. Il perché sta in
[`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md#il-dispatcher-chi-decide-chi-gira-e-uno-per-volta),
in due righe: le dipendenze della catena sono di dato e il calendario le
ignorava, e sei Routine indipendenti si pestavano i piedi.

| Routine | cadenza (UTC) | che cosa fa | routine id |
| --- | --- | --- | --- |
| launcher | ogni 3 ore (minuto `:02`) | `pipeline_launch.py`, poi lancia in parallelo i ruoli che ha nominato | `trig_01Dv3ZDB4ch561GFYy2QwEUJ` (in pausa, il prompt va ri-puntato a `launcher.md`) |

> **Da ri-puntare.** La Routine (stesso id) e' nata per il dispatcher: il suo
> prompt cita `.claude/agents/dispatcher.md` e il comando `pipeline_dispatch.py`,
> entrambi ritirati. Prima di riaccenderla, cambia il prompt a quello sotto (che
> punta a `launcher.md`). Finche' e' in pausa non fa danni.

**L'inciampo del 28 luglio, perché non si ripeta.** La Routine si crea anche via
lo strumento MCP `create_trigger`, ma **deve essere in modalità sessione nuova**
(`create_new_session_on_fire`): è la sessione nuova nell'environment
`divarioitalia` che eredita il checkout git. Una prima Routine ricreata quel
giorno (`trig_01262KRLPmE7xJrG8fbKMz2y`) apriva invece sessioni **senza il repo**
(`is a git repository: false`, nessun `.claude/agents/`) e falliva a ogni firing
prima ancora di leggere il proprio contratto: è stata cancellata e rifatta in
modalità sessione nuova. `create_trigger` non aggancia connettori MCP, ma alla
catena non servono: parla con GitHub via `gh` e il proxy di uscita, non via il
connettore. La `trig_0145qYivpUMeYVcTAjBTmGHQ` citata nelle versioni precedenti di
questo documento non esiste più.

Impostazioni: **sessione nuova a ogni firing** (non legata a una sessione
esistente), environment `divarioitalia`, modello quello di default. Il modello
della sessione decide solo il dispatcher: ogni agente di stadio dichiara il
proprio nel frontmatter (`.claude/agents/`, campo `model`), e la riga di
diario di ogni run registra `model` e `claude_code_version`, quindi una
regressione osservata dopo il fatto si attribuisce da li'. La sessione
nuova non è un dettaglio: il prompt qui sotto è scritto per partire da zero, e
una Routine legata a una sessione esistente accumulerebbe il contesto di tutti i
giri precedenti, che è esattamente ciò che rende un agente incoerente con i file
che ha davanti.

### Il prompt, adesso un puntatore

Il giro del lanciatore (legge il piano per-indicatore, lancia i ruoli in
parallelo, riporta come e' andata) vive in **`.claude/agents/launcher.md`**, con
modello e guardia nel frontmatter come ogni altro agente della catena. Questo
documento non lo ricopia più: la versione che stava qui era l'ultima copia di
contratto dentro un prompt di Routine, cioè la forma esatta del drift di
`analyst_notes.json` (vedi sotto). Il prompt della Routine si copia com'è:

```
Agisci come il lanciatore della catena editoriale di Divario Italia. La tua
definizione sta in .claude/agents/launcher.md ed è vincolante: leggila ed
eseguila. Fai UN giro e fermati.
```

Le tre uscite sono distinte per una ragione precisa. `1` capita la maggior parte
delle ore, perché una catena a code vuote è ferma per il motivo giusto. Se
l'uscita non distinguesse quel caso da un guasto, la Routine registrerebbe un
errore a ogni ora di riposo, e un allarme che suona sempre non è un allarme.

`--record` scrive **e committa su master** il giro, ma solo quando serve: un
giro che lancia uno stadio non lascia riga, perché la lascia lo stadio, e un
giro a vuoto ne lascia una sola al giorno. Con un battito orario registrarli
tutti sarebbe un commit ogni ora per dire sempre la stessa cosa, e la cadenza
contro cui `pipeline_log.silence` misura il silenzio è di un giorno.

### Le sei vecchie, spente il 27 luglio

**In pausa, non cancellate**, finché il dispatcher non ha girato qualche giorno.
La distinzione conta: se il dispatcher si rivelasse sbagliato, riaccenderle è un
clic, ricrearle no.

| vecchia Routine | routine id | stato |
| --- | --- | --- |
| scout | `trig_01KZ1CHGPRgNmF9Ahni9VXfQ` | in pausa |
| cacciatore | `trig_01VizeycZocZoeDE1RxjWj1f` | in pausa |
| curatore | `trig_019EP6TnEbYnKz8VpKFaRm4g` | in pausa |
| scrittore | `trig_01RymCgC8VsspDrHHnUJgFUk` | in pausa |
| revisore | `trig_01LSZpaDasW18ZvxbKhXBJSj` | in pausa |
| verificatore | mai creata | niente da fare |

L'ordine è **prima spegnere, poi accendere**, e questa è la metà fatta. Al
contrario si sarebbe aperta una finestra in cui giravano tutti e sette, ed è la
finestra in cui la catena avrebbe potuto produrre proprio il guasto che questa
modifica ha tolto. Il prezzo dell'ordine giusto è che nel mezzo non gira niente:
finché il dispatcher non esiste, la catena è ferma e gli stadi si lanciano solo
a mano.

### Come si controlla che sia partita

```bash
python3 scripts/pipeline_log.py --stage dispatch   # i giri registrati
python3 scripts/pipeline_dashboard.py --open       # il battito, in cima
```

Il cruscotto dice in testa quando è stato l'ultimo giro del dispatch, e se non
ne ha mai visto uno lo scrive a lettere chiare invece di lasciare la riga vuota:
finché quella riga dice "mai", nessuno sta assegnando il lavoro.

Nessuno stadio è `manual`, e non è una svista. La catena è non presidiata per
decisione presa: un modo che parcheggia la pull request finché qualcuno guarda,
in un sistema che nessuno guarda, vuol dire fermo per sempre. E dal 28 luglio
nessuno stadio è più `checks`: ogni stadio fonde `auto`, sul cancello locale che
`scripts/pipeline_merge.py` rilegge (suite intera + perimetro + invarianti) prima
del merge. `checks` aspettava la CI remota, che però non parte sulle PR aperte via
il GitHub MCP, quindi non comprava un verdetto indipendente ma un deadlock (vedi
la voce del 28 luglio più sotto).

**Il prompt della Routine punta ai file, non li ricopia.** Vedi sotto perché.

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
  chiude, con `tests/integration/test_pipeline_gate.py` che costruisce prima l'input cattivo.
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
`tests/unit/test_source_admission.py`.

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

## Cosa è successo il 2026-07-27

Tre sintomi che sembravano scollegati, tre cause tutte di struttura. Il dettaglio
sta in [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md); qui che cosa è
cambiato e che cosa resta da fare fuori dal repo.

**Non si capiva chi avesse fatto cosa.** Le due righe di una run si univano su
`(stadio, pr)`, e non poteva funzionare: la riga dell'agente viaggia dentro la
pull request, quindi va committata prima che la pull request esista, quindi non
ne può portare il numero. Su trenta run reali diciannove non lo avevano, e il
diario dichiarava ventuno run in attesa mentre le pull request aperte erano zero.
Ora ogni run ha un **`run_id`** coniato da chi scrive per primo e passato al
passo di merge con `--run-id`, più `trigger` e le code prima e dopo.

**La sequenza non funzionava** perché le dipendenze della catena sono di dato e
la schedulazione era di calendario. `scripts/pipeline_dispatch.py` legge tutte le
code e lancia un solo stadio, il primo con lavoro in ordine di catena. Sei
Routine diventano una.

**I conflitti erano garantiti dal formato.** Tre registri erano file unici a cui
ogni stadio appendeva in fondo. Ora sono store a un file per record:
`content/indicators/` (365 articoli travasati), `data/pipeline/runs/` (30 run
travasate) e `data/pipeline/verifiche/`. Il conflitto non è meno probabile, è
impossibile. La sezione 3-bis del contratto si è accorciata invece di essere
riscritta.

**E l'anello di retroazione che teneva ferma la catena.** Il cancello bocciava un
branch la cui base fosse andata avanti, e il passo di merge scrive su master
anche quando *rifiuta*: un rifiuto solo faceva diventare rosse tutte le pull
request aperte, con un'accusa che non riguardava il loro lavoro. La severità non
serviva, perché il diff si misura già con i tre punti. Ora è rosso solo se non
esiste nessun antenato in comune.

Tre bug trovati strada facendo, tutti reali:

- `git status --porcelain` riassume una directory non tracciata in una voce sola,
  quindi da `content/indicators/` il cancello ricavava la chiave inventata
  `indicators`. Ora usa `--untracked-files=all`.
- `collapse_runs` lasciava che `pr-open`, che è l'*assenza* di un esito, coprisse
  un esito vero quando le due righe cadevano nello stesso secondo.
- I sei prompt mettevano la riga di diario **dopo** `gh pr create`, mentre va
  committata prima perché viaggia dentro la pull request.

**Cosa restava da fare fuori dal repo, ora fatto:** la Routine del dispatcher è
creata e attiva (28 luglio, id nella tabella sopra), e le sei per stadio restano
in pausa. Tenerle spente conta: se restassero accese insieme al dispatcher
tornerebbe esattamente la concorrenza che il dispatcher toglie.

## Cosa è successo il 2026-07-28: auto-merge su tutta la catena

Due giorni di runtime hanno mostrato un deadlock che nessun test vedeva. La CI
remota non parte sulle PR aperte via il GitHub MCP, quindi gli stadi `checks`
(scout, hunter, promoter, curator, verificatore) aspettavano check che non
comparivano mai. `pipeline_merge` rifiuta correttamente una PR `checks` i cui
check non appaiono, la PR restava `pr-open`, e il dispatcher si rifiuta di
lanciare finché una PR della catena è aperta: **una sola PR incastrata congelava
tutta la catena.** Nel diario si vedeva il segno opposto della salute: la metà
editoriale (writer/reviewer, già `auto`) girava, la metà di scoperta no.

**La decisione:** ogni stadio passa a `auto`. Il cancello locale che
`pipeline_merge` rilegge prima del merge gira già la stessa suite del job CI
`python` e lo stesso perimetro del job `gate`, quindi la garanzia vera resta, e
gira **prima** del merge invece che mai. `checks` resta una parola che il cancello
sa dire e il meccanismo di attesa resta testato in `pipeline_merge`: se un giorno
la CI parte su queste PR, i cinque stadi che muovono numeri vivi sono quelli da
riportare a `checks`. Il razionale completo è nel commento di
`pipeline_gate.MERGE_POLICY`.

Insieme: lo scout ritenta i 5xx transitori del catalogo SDMX invece di abortire
(un 500 di un minuto non deve produrre un giro a zero approvazioni), e
`REGIONAL_HINT` riconosce la forma abbreviata `reg.` che prima lasciava fuori
dalla coda, per esempio, la spesa sociale dei comuni per regione.

## Lo sblocco: il tappo è tolto

Per un giorno lo stadio uno è rimasto chiuso per costruzione. Lo scout aveva
verificato e cablato due serie demografiche nuove sul dataflow
`22_293_DF_DCIS_INDDEMOG1_1`, `NMIGRATEIN` e `BIRTHRATE`, ma
`tests/integration/test_discovery.py` congelava l'elenco esatto degli id ammessi in tre
asserzioni, dentro una classe chiamata `AdmittingASeriesIsConfigNotCode` che
faceva l'opposto del proprio nome. L'agente non aveva toccato i test, aveva
scritto perché, e si era fermato: la terza volta che un agente della catena si
ferma davanti a una guardia sbagliata invece di aggirarla, e la terza che aveva
ragione.

I tre test ora verificano il **meccanismo, non il contenuto**:

- il config carica ogni serie ben formata, ma l'elenco può crescere. La forma di
  ogni riga ammessa resta sorvegliata da `tests/unit/test_source_admission.py`.
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

1. **La licenza Istat era sbagliata, ora corretta ovunque e in un posto solo.**
   Istat dichiara **CC BY 4.0** su <https://www.istat.it/note-legali/>
   (verificato), non `CC BY 3.0 IT`. Corretta in due passaggi, e il secondo
   racconta più del primo. Primo: registro delle fonti e adapter (#43), righe
   `istat_lavoro` del layer esterno (`normalized_external_indicators.csv`) e i
   quattro fallback hardcoded a `by/3.0/it/` nel view model
   (`app/indicator_view.py`), nel catalogo (`app/atlas_catalog.py`) e nel JSON-LD
   delle pagine regione e classifica. Quel giro dichiarava "ovunque" e ne aveva
   mancati quattro, tutti in prosa e quindi invisibili al test che guardava solo
   il JSON-LD: la FAQ di `/metodologia` (testo visibile e JSON-LD), `/llms.txt` e
   `/llms-full.txt`, cioè proprio i file che un modello linguistico cita alla
   lettera. Secondo passaggio: quei quattro corretti, e la causa rimossa. La
   licenza ora è **una sola costante in `app/sources.py`**
   (`LICENSE_URL`, `LICENSE_LABEL`), ogni famiglia dichiara la propria in
   `SOURCES`, i template la ricevono da un context processor e nessun default
   copre più una famiglia che non l'ha dichiarata (le fonti non CC BY 4.0 in
   `config/external_sources.yaml`, INVALSI, Terna, InfoCamere, Infratel,
   avrebbero ereditato la deed sbagliata). `test_license_is_stated_the_same_way_on_every_surface`
   pinna le tre superfici in prosa e la coerenza del registro.
2. **`scout_sources.py` troncava la coda alfabeticamente.** Le proposte erano 87, il
   `limit=40` con punteggio uniforme ordinava per nome, quindi la coda si fermava a
   "Notti in Italia" e le altre non le vedeva nessuno. **Chiuso** (2026-07-28): il
   tetto ora e' `None` di default (`propose_sources` propone ogni dataflow
   superstite), la coda dello scout e' passata da 0 a 50 `new` sul catalogo reale
   (90 proposte, 50 mai triate), e `--refresh` ri-sonda il catalogo cache-forever
   cosi' i dataflow pubblicati dopo l'ultima run entrano in coda. Bloccato da
   `tests/unit/test_scout_sources.py::Uncapped`.
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
   sopra). La licenza Istat, che era il terzo punto, è stata corretta ovunque
   (vedi sopra).
6. ~~**La Routine del dispatcher**~~ Fatto il 28 luglio: creata e attiva, sessione
   nuova a ogni firing nell'environment `divarioitalia`. Le cinque vecchie
   restano in pausa dal 27 luglio. Il passaggio è completo e nell'ordine giusto.
7. **Una voce per (indicatore, livello)** nello store degli articoli. Oggi è una
   per indicatore, con il livello come campo dentro, mentre le code dello
   scrittore e del revisore hanno già una riga per coppia. Non è un difetto
   nuovo, è quello di prima lasciato dov'era di proposito: cambiare il modello
   dei dati dentro una modifica che serviva a togliere i conflitti avrebbe
   mescolato due cose che vanno potute rileggere separate.

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
  `.venv/bin/python scripts/pipeline_merge.py --stage <stadio> --pr <numero> --run-id <run_id>`.
- **La CI non parte da sola sulle PR aperte via il GitHub MCP.** GitHub non lancia
  i workflow per eventi creati dal token dell'app (anti-ricorsione), quindi una PR
  aperta così resta senza check. Prima questo bloccava la catena: gli stadi
  `checks` aspettavano check che non arrivavano, la PR restava `pr-open` e il
  dispatcher non lanciava più niente. Dal 28 luglio **nessuno stadio è `checks`**
  (fondono tutti `auto` sul cancello locale), quindi il deadlock non c'è più. La CI
  remota resta un feedback utile e si può far partire a mano con `workflow_dispatch`
  su `ci.yml`, ma il merge non la aspetta più.
- **`pipeline_dashboard.py` non crasha più senza `gh`.** `open_pull_requests`
  cattura `FileNotFoundError`/`OSError` e la sezione PR dice solo che `gh` non c'è,
  invece di far morire tutto il cruscotto. È quello che pretende la classe di test
  `TheDashboardReadsWithoutBreaking`.
- **Il caso `nothing` del diario si regge solo sul contratto.** Una run a mani
  vuote non ha un branch da giudicare, quindi il cancello non la può raggiungere:
  se un agente non scrive quella riga, nessuna guardia se ne accorge. Resta il
  punto più debole del monitoraggio, ma pesa meno di prima: il **tick del
  dispatcher** viene registrato a ogni giro, quindi "la catena non ha fatto
  niente stanotte" e "la catena non è partita" adesso si distinguono anche se un
  agente si dimentica della propria riga.
- **`--run-id` non è decorativo.** Senza, la riga di esito che il passo di merge
  scrive su master resta orfana, e il diario torna a non saper dire come è finita
  la run che l'ha aperta. Lo stampa `pipeline_log.py --write`.
- **Non lanciare uno stadio a mano mentre il dispatcher gira.** Non c'è nessun
  lock: l'unica cosa che impedisce a due stadi di lavorare insieme è che il
  dispatcher ne nomini uno solo per tick. Se serve girare a mano, spegni prima la
  Routine.
- **Gli store non si ricompattano.** `content/indicators/`,
  `data/pipeline/runs/` e `data/pipeline/verifiche/` sono a un file per record
  perché è quello a togliere i conflitti. Rimetterne uno in un file solo li
  riporta indietro tutti insieme.
