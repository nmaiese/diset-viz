# Stato della catena

Il documento che si tiene aggiornato. Dice **dove sta il sistema adesso**: cosa
gira da solo, con quale cadenza, cosa resta umano e cosa non è ancora fatto.

Per come funziona: [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).
Per il meccanismo della scoperta: [`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md).
Per il contratto di ogni agente: [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md).

Aggiornato al **2026-07-26**.

## In una riga

Sei stadi, cinque agenti, tutti schedulati. Un indicatore va da un catalogo SDMX
a una pagina pubblica senza intervento, e la catena ci ritorna sopra quando i
dati si muovono. Restano umane tre cose, elencate in fondo, ognuna per un motivo
scritto.

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
ha prodotto qualcosa, e il ritardo è anche la finestra in cui un umano può ancora
intervenire su un merge `checks`. Il revisore gira ogni giorno perché lavora su
un arretrato di centinaia di articoli e non su ciò che è appena arrivato.

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

1. **Le 40 proposte dello scout** in `data/discovery/source_candidates.csv` sono
   tutte `new`: nessuna è mai stata valutata. È il primo collo di bottiglia della
   catena, ed è per questo che lo scout gira per primo nella settimana.
2. **Il secondo adapter di famiglia**: oggi la catena cabla da sola solo dataflow
   SDMX Istat. Eurostat resta a selezione curata in `EUROSTAT_SERIES`, dentro
   `scripts/eurostat_source.py`, quindi ammettere una serie Eurostat è ancora
   codice. Stessa forma dell'adapter Istat, quindi lo stesso trattamento a
   config è possibile.
3. **Profili regionali** (`app/profiles.py`): calcolati sui soli territoriali
   core, non includono ancora le famiglie esterne.
4. **Livello provinciale (NUTS3)** nella watchlist, sempre con priorità al
   regionale fresco.

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
- **La suite crasha in uscita, a caso, circa una run su quattro.** SIGSEGV a
  interprete che smonta, dopo che unittest ha gia' stampato `OK`: i test passano
  tutti, il processo esce 139. Per questo `pipeline_gate.check_suite` legge il
  **referto** di unittest e non il codice di uscita, e quando i due divergono lo
  dice invece di ingoiarlo. Senza, un quarto delle run di ogni stadio verrebbe
  bloccato da un fallimento che non esiste. La causa vera resta da trovare: sei
  run con `-X faulthandler` non l'hanno riprodotto.
- In una shell dell'utente `python3` è una funzione che rilancia il comando
  quando esce non-zero, quindi l'output di uno script che fallisce **appare due
  volte**. Non è un bug del programma.
