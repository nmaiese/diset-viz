# La catena autonoma

Come Divario Italia trova, verifica, cura, scrive, rilegge e pubblica un
indicatore **senza intervento umano**, e quali sono le tre cose che ancora lo
richiedono e perche'.

Documento profondo. Per il contratto operativo che ogni agente segue a ogni run
vedi [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md); per lo strato dati sotto,
[`DATA_PIPELINE.md`](DATA_PIPELINE.md) e
[`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md); per l'anatomia di una pagina
indicatore, [`INDICATOR_PAGES.md`](INDICATOR_PAGES.md).

## L'obiettivo, detto per intero

Indicatori nuovi **senza intervento**, ma verificati e curati, con testi pronti e
corretti. Non "un agente che apre PR che qualcuno legge": una catena che porta
una serie da un catalogo SDMX a una pagina pubblica leggibile, e che poi ci
**torna sopra** quando i dati si muovono.

Le due meta' contano allo stesso modo. Una catena che scopre e non rilegge
produce un archivio che invecchia in silenzio, e l'invecchiamento e' peggio di
un buco: un buco si vede.

## I sei stadi

```
  scout          hunter            promoter         curator          writer        reviewer
  quali fonti    quali indicatori  li integra       quale verso      l'articolo    lo rilegge
     |               |                |                |                |             |
 source_        candidates.csv   layer esterno   curation.csv    indicator_    reviewed_at
 candidates.csv                  + manifest      + descrizioni    texts.json    + vintage
     |               |                |                |                |             |
  manuale         checks           checks           checks            auto          auto
```

Ogni stadio ha tre cose, e sono sempre le stesse tre: una **coda deterministica**
calcolata da file committati, un **agente** con un file di definizione in
`.claude/agents/`, e un **verdetto del cancello** che decide se puo' pubblicare.

| stadio | agente | coda | comando |
| --- | --- | --- | --- |
| scout | `source-scout` | `data/discovery/source_candidates.csv` | `scripts/scout_sources.py` |
| hunter | `indicator-hunter` | `data/discovery/candidates.csv` | `scripts/discover_candidates.py` |
| promoter | `indicator-hunter` | i candidati `approved` | `scripts/promote_candidates.py` |
| curator | `indicator-curator` | `curate.worklist()` | `scripts/curate.py --include-recheck` |
| writer | `indicator-writer` | `pending_notes` + `text_queue` | `scripts/pending_notes.py` |
| reviewer | `indicator-reviewer` | `review_queue` | `scripts/review_queue.py` |

Un solo comando dice lo stato di tutti e sei:

```bash
python3 scripts/pipeline_status.py            # leggibile
python3 scripts/pipeline_status.py --json     # per un agente
```

Esiste per una ragione precisa. Ogni agente vede la propria casella e nient'altro,
quindi nessuno riesce a distinguere "sono fermo perche' ho finito" da "sono fermo
perche' e' bloccato lo stadio sopra di me", che sono situazioni opposte e si
somigliano moltissimo. Ogni agente lo lancia per primo.

## Il cancello: cosa rende sicuro togliere l'umano

`scripts/pipeline_gate.py` e' il punto in cui ogni stadio chiude. Non e' una
formalita': e' la cosa che sta fra "autonomo" e "autonomamente sbagliato su
scala". Restituisce un verdetto calcolato dal diff e dalla suite, mai
dall'opinione che l'agente ha del proprio lavoro.

```bash
python3 scripts/pipeline_gate.py --stage writer
```

Controlla, in ordine di danno:

1. **Il perimetro.** Ogni stadio puo' toccare una lista corta di file, scritta
   in `STAGE_PATHS`. Un prompt si puo' modificare, fraintendere o ignorare, il
   repo no: uno scrittore che si mette a "sistemare" `app/views.py` fallisce
   qui, prima che qualcuno legga il suo ragionamento. E' questo controllo a
   rendere automatizzabili gli altri.
2. **La suite intera**, non il sottoinsieme preferito dello stadio. Le guardie su
   prosa, deriva del vintage, cifre attribuite a una regione, schema CSV e
   `/legacy` sono la memoria accumulata di tutto quello che qui e' gia' andato
   storto.
3. **Gli invarianti sul diff**, che la suite non puo' vedere perche' riguardano
   il cambiamento e non lo stato: una decisione di triage senza motivazione
   scritta, un'approvazione sotto la copertura minima o senza licenza,
   `score_eligible=true` su un verso non direzionale, una revisione che non firma
   niente, un `vintage` oltre i dati.
4. **L'igiene**: whitespace, e il trailer `Co-Authored-By` che CLAUDE.md vieta.

I test in `tests/test_pipeline_gate.py` costruiscono **prima l'input cattivo** e
verificano che il cancello rifiuti. Un cancello che ha sempre risposto verde non
e' un cancello.

## La politica di merge, e perche' non e' uniforme

Il verdetto porta un campo `merge`, che e' l'ordine:

| stadio | `merge` | perche' |
| --- | --- | --- |
| `writer`, `reviewer` | `auto` | prosa in un file solo, non raggiunge nessun'altra pagina, si annulla con un commit |
| `hunter`, `promoter`, `curator` | `checks` | muovono numeri vivi (catalogo, punteggio qualita' della vita), quindi passano dai check remoti e lasciano una finestra |
| `scout` | `manual` | ammettere una fonte decide **quale istituzione e quale licenza** legge un utente su una pagina pubblica |

Un verdetto rosso non porta nessun `merge`: fra "i controlli sono falliti" e "ma
solo un po'" non c'e' niente da negoziare.

Questa tabella e' una **decisione**, non una limitazione tecnica. Se un domani si
vuole che anche lo scout si fonda da solo, si cambia `MERGE_POLICY` in un diff
che qualcuno ha letto, e non per deriva.

## Il rientro: la catena lavora anche sul pubblicato

E' la meta' che mancava. Prima ogni stadio drenava la propria coda una volta e
poi restava fermo per sempre, il che faceva sembrare la catena finita mentre il
catalogo invecchiava sotto.

**Curatore.** `curation.csv` porta `data_year`, l'anno su cui il verso e' stato
giudicato. Quando la fonte ne pubblica uno piu' recente, l'indicatore rientra in
`recheck`. Un verso e' un'affermazione su quale estremo della classifica sia
quello buono, ed e' esattamente cio' che una ridefinizione, un rebase o una
rottura di serie possono invertire.

**Revisore.** L'articolo porta `reviewed_vintage`, il `vintage` che il revisore
aveva davanti. Quando lo scrittore aggiorna l'articolo su un anno nuovo, tutte le
cifre cambiano e i due valori smettono di combaciare: l'articolo torna in coda
con il segnale `rilettura`, che pesa piu' di ogni segnale di rischio. Gli altri
marcano una frase che *potrebbe* essere sbagliata, questo marca un articolo in
cui non e' stato controllato niente.

**Scrittore.** Ha gia' `stale` in `pending_notes` e `text_queue`: un articolo il
cui `vintage` e' rimasto indietro. Lo scrittore **non tocca** `reviewed_at` ne'
`reviewed_vintage`, ed e' proprio non toccandoli che rimette in coda dal revisore
l'articolo appena riscritto.

In tutti e tre l'innesco sono **i dati, mai il calendario**. Rileggere tutto ogni
N mesi riporterebbe la deriva gia' corretta una volta, cioe' un indicatore
contestuale che si ripresenta per sempre perche' `score_eligible` resta `false`
per definizione (vedi il docstring di `curate.uncurated_targets`).

## Far crescere il bacino senza scrivere codice

Il cacciatore si esaurisce nel momento in cui le fonti cablate smettono di
crescere, ed e' esattamente cosa era successo: cinque serie cablate, cinque
trovate, niente altro da scoprire. Due file rompono quel tetto, e sono entrambi
**dati** dentro il perimetro di un agente:

- `config/istat_series.yaml` (scout): una riga = un indicatore Istat SDMX.
  `dataflow` e' un campo per serie, non piu' una costante di modulo, quindi un
  dominio nuovo non richiede un adapter nuovo.
- `config/theme_categories.csv` (curatore): la mappa tema -> categoria. Un tema
  che il catalogo non conosce fa sparire l'indicatore dai totali per macro-area
  pur lasciandolo in catalogo, cioe' un buco silenzioso, e la correzione stava
  dentro `app/taxonomy.py`, un modulo Python.

Resta codice, e quindi resta umano: un adapter per una fonte che **non** e' un
dataflow SDMX Istat, e l'invenzione di una **categoria** nuova (che e' una
sezione del sito con un nome e una descrizione, non una riga).

## Le Routine

Gli agenti girano come Routine Claude Code: sessione nuova a ogni firing,
checkout git proprio, nessuna memoria della volta prima. Si gestiscono su
<https://claude.ai/code/routines>. Gli id correnti stanno in
[`DISCOVERY_STATUS.md`](DISCOVERY_STATUS.md).

Il prompt di una Routine **non riproduce il contratto**, lo indica. E' la lezione
piu' cara di questo sistema: la Routine dello scrittore riproduceva il proprio
contratto per intero, il repo e' andato avanti, e per settimane l'agente ha
scritto in `analyst_notes.json`, un file che l'app non legge piu'. Girava, non
falliva, e non arrivava in nessuna pagina. Un prompt che ricopia una regola va
fuori sincrono senza che nessuno se ne accorga, un prompt che punta a un file no.

Cadenza sfalsata di proposito: ogni stadio ha senso solo dopo che quello a monte
ha prodotto qualcosa, e il ritardo e' anche la finestra in cui un umano puo'
ancora intervenire su un `checks`.

## Quando qualcosa va storto

```bash
python3 scripts/pipeline_status.py          # dove si e' fermata
python3 scripts/pipeline_gate.py --stage <stadio> --json    # perche' e' bloccata
```

Sintomi ricorrenti e cosa significano davvero:

- **Uno stadio non apre PR da settimane.** Guarda `pipeline_status`: se la sua
  coda e' a zero il problema e' a monte, non in lui.
- **Il cancello blocca su `blast-radius`.** L'agente ha toccato un file fuori
  perimetro. Non allargare il perimetro: quasi sempre significa che ha provato a
  risolvere in codice un problema che andava riportato.
- **Un indicatore rientra in `recheck` a ogni run.** Manca `data_year` nella sua
  riga di `curation.csv`. Scriverlo una volta chiude il ciclo.
- **Un articolo rientra in `rilettura` a ogni run.** Manca `reviewed_vintage`. La
  suite lo fa fallire apposta, invece di lasciarlo silenzioso.
- **Un indicatore e' in catalogo ma sparito dai totali per macro-area.** Il suo
  tema non e' mappato: una riga in `config/theme_categories.csv`.

## Cosa resta umano, e perche'

Tre cose, e sono scelte:

1. **Ammettere una fonte** (`scout`, `merge: manual`). Decide quale istituzione,
   quale licenza e quale nome legge un utente su una pagina pubblica sotto il
   nome di questo progetto.
2. **Scrivere un adapter** per una fonte che non e' un dataflow SDMX Istat.
   E' codice, e nessun agente scrive codice.
3. **Creare una categoria** della qualita' della vita. E' una sezione del sito,
   con un nome, una descrizione e una macro-area.

Tutto il resto, dalla scelta dell'indicatore alla pagina pubblicata e poi
rivisitata, gira da solo.
