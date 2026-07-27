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

## I sette stadi

```
  scout        hunter          promoter      curator       writer      reviewer    verificatore
  quali fonti  quali indic.    li integra    quale verso   l'articolo  lo rilegge  prova a smentirlo
     |             |               |             |             |           |             |
 source_      candidates.csv  layer est.   curation.csv  content/    reviewed_at  verifiche/
 candidates.csv               + manifest   + descrizioni  indicators/ + vintage   (impronta prosa)
     |             |               |             |             |           |             |
  checks        checks          checks        checks         auto        auto        checks
```

L'ultimo e' l'unico che misura un altro stadio invece dei dati, ed e' arrivato per
ultimo perche' e' servito misurarlo prima di credergli. Una firma del revisore e'
la parola del revisore sul lavoro del revisore, e finche' nessuno provava a farla
cadere quanto valesse non si sapeva. Ora si sa:

| stato dell'articolo | affermazioni controllate | false | tasso |
| --- | --- | --- | --- |
| note migrate, mai rilette | 113 | 11 | 9,7% |
| scritte e non ancora rilette | 392 | 19 | 4,8% |
| scritte e rilette | 529 | 7 | 1,3% |

La rilettura toglie la gran parte degli errori e ne lascia qualcuno, e quel
qualcuno resta in pagina finche' qualcosa non prova a farlo cadere.

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
| verificatore | `indicator-verifier` | `verification_queue` | `scripts/verification_queue.py` |

Un solo comando dice lo stato di tutti e sette:

```bash
python3 scripts/pipeline_status.py            # leggibile
python3 scripts/pipeline_status.py --json     # per un agente
```

Esiste per una ragione precisa. Ogni agente vede la propria casella e nient'altro,
quindi nessuno riesce a distinguere "sono fermo perche' ho finito" da "sono fermo
perche' e' bloccato lo stadio sopra di me", che sono situazioni opposte e si
somigliano moltissimo. Ogni agente lo lancia per primo.

## Il dispatcher: chi decide chi gira, e uno per volta

```bash
python3 scripts/pipeline_dispatch.py --json --check-open-prs
```

Gli stadi non hanno piu' un giorno della settimana. Una sola Routine gira a
battito, legge tutte le code e lancia **un solo stadio**, il primo con lavoro in
ordine di catena. Prima erano sei Routine con sei cron, e quella forma aveva due
difetti che si somigliavano poco.

**Le dipendenze sono di dato, la schedulazione era di calendario.** Il curatore
girava il giovedi': se il promotore aveva prodotto il venerdi' prima aspettava
sei giorni, se non aveva prodotto niente girava a vuoto e apriva una pull
request per dirlo. Dalla fonte alla pagina passavano fino a tre settimane, e
ogni passaggio era un tiro di dado sul fatto che a monte fosse successo
qualcosa.

**Nessuno aspettava nessuno.** Due stadi potevano partire insieme, dalla stessa
base, e scrivere negli stessi registri. Il conflitto era la norma al punto che il
contratto degli agenti aveva una sezione dedicata a risolverlo a mano.

Un tick, uno stadio: la concorrenza non si gestisce, non c'e'. Non serve un
lock, non serve un lease, e le sezioni del contratto che spiegavano come
convivere con un altro stadio sono sparite invece di essere state riscritte.

Il dispatcher rifiuta anche di lanciare quando una pull request della catena e'
ancora aperta, perche' quella e' una run ancora in corso. Se non riesce a
chiederlo a GitHub lo dichiara invece di far finta che non ci sia nessuna pull
request: un controllo che passa perche' non ha potuto girare e' peggio di
nessun controllo, ed e' lo stesso principio del cancello.

Non lancia lui l'agente, e non potrebbe: un agente e' una sessione Claude Code,
il dispatcher e' stdlib. Dice **quale** lanciare, con il suo `run_id` gia'
coniato, e il prompt della Routine fa il resto. La decisione resta cosi'
deterministica e verificabile da un test, l'esecuzione no.

Registra il proprio giro nel diario quando quel giro dice qualcosa, ed e' la
riga che distingue "nessuno stadio aveva lavoro" da "non e' partito niente".
Prima l'attesa era scritta in `pipeline_log.WATCH_GROUPS`, che ricopiava il cron
delle Routine cloud: una promessa che nessuno poteva verificare, e che sarebbe
andata fuori sincrono alla prima modifica della schedulazione.

Non a ogni giro, pero', e la parsimonia e' la parte progettata. Quando **lancia**
non scrive niente, perche' la prova che la catena ha girato la lascia lo stadio
lanciato: due righe direbbero la stessa cosa e gonfierebbero il conto delle run.
Quando **non lancia** ne scrive una sola al giorno, che e' la granularita' a cui
`silence` misura. Un battito orario registrato per intero sarebbe un commit ogni
ora e ottomila file l'anno per un'informazione che si legge una volta al giorno.

Quella riga la committa lui stesso su master, ed e' l'unico passo della catena
che lo fa fuori dal passo di merge: il dispatcher non ha un perimetro e non apre
pull request, quindi non esiste nessuna pull request dentro cui possa viaggiare.
E' sicuro perche' e' **un file nuovo** con un nome che nessun altro puo'
scegliere. Senza questo passo la riga resterebbe nel checkout usa e getta della
Routine e sparirebbe con la sessione, cioe' proprio nel caso, l'unico, per cui
esiste.

## Gli store: perche' i conflitti non esistono piu'

Tre registri della catena erano file unici a cui ogni stadio appendeva **in
fondo**. Due stadi che girano vicini scrivono nello stesso punto, quindi git
chiama conflitto quella che e' solo la somma di due righe che non si
contraddicono. Adesso sono directory, un file per record:

| store | un file per | scritto da |
| --- | --- | --- |
| `content/indicators/` | articolo | scrittore, revisore |
| `data/pipeline/runs/` | run | tutti |
| `data/pipeline/verifiche/` | verifica | verificatore |

Non e' una riduzione della probabilita' di conflitto, e' la sua rimozione: due
stadi che lavorano su cose diverse non toccano lo stesso percorso, quindi non
c'e' niente da fondere. Resta contendibile solo la modifica **allo stesso**
articolo, che e' l'unico caso in cui un conflitto significa davvero qualcosa e
merita di essere letto da qualcuno.

Ne vengono due cose che non erano l'obiettivo e valgono quanto l'obiettivo. Il
diff di una run del revisore adesso e' leggibile, perche' dice di quali articoli
parla invece di mostrare hunk dentro mezzo megabyte di JSON. E
`git log content/indicators/ter__920.json` e' la storia editoriale di quella
pagina, che prima non esisteva.

Il perimetro del cancello capisce le directory: una voce di `STAGE_PATHS` che
finisce con una barra e' un prefisso. La barra e' ancorata di proposito, cosi'
`content/indicators` non autorizza `content/indicators-bozze`.

## Il verificatore, e perche' non ripara niente

`data/pipeline/verifiche/` e' tutto quello che produce: un file per verifica,
con i quattro contatori e l'impronta della prosa che ha letto.

**Non ha `content/indicators/` nel perimetro**, e l'assenza e' la definizione
dello stadio piu' che il suo prompt. Uno stadio che trova e ripara i propri
rilievi corregge i propri compiti, che e' esattamente il difetto che esiste per
prendere un livello sopra. Quindi una smentita torna al revisore, come il segnale
`smentita` di `review_queue`, che pesa piu' di ogni altro segnale di quella coda:
tutti gli altri marcano una frase che *potrebbe* essere sbagliata, quello marca
una frase che qualcuno ha gia' fatto cadere, con la prova, e che e' ancora in
pagina.

**Una verifica scade quando cambia il testo, non quando passa il tempo.** La riga
porta un'impronta della prosa, e l'articolo risulta verificato solo finche' la sua
prosa hasha a quel valore. La prima versione confrontava `reviewed_at` con la data
della verifica ed e' stata buttata: due eventi nello stesso giorno sono
indistinguibili, e il revisore che ripara una frase smentita firma il giorno in
cui il verificatore l'ha smentita. Con l'impronta non c'e' aritmetica e non c'e'
pareggio.

Le due code si passano il lavoro senza che nessuna cancelli una riga dell'altra:

```
  verificatore trova una smentita  ->  review_queue la mostra in cima
  il revisore riscrive la frase    ->  l'impronta cambia, la smentita e' spenta
  l'impronta cambia                ->  l'articolo torna in coda al verificatore
```

`affermazioni_controllate` e' il campo che non si negozia, e il cancello lo
impone invece di ricordarlo: senza, "zero smentite" e "non ho guardato" producono
la stessa riga, e uno stadio che non sa distinguerle costa una pull request per
articolo e non garantisce niente.

## Guardare la catena senza aprire file

Tre comandi, e il terzo li contiene tutti.

```bash
python3 scripts/pipeline_status.py            # dove si e' fermata
python3 scripts/pipeline_log.py               # che cosa hanno fatto gli agenti
python3 scripts/pipeline_dashboard.py --open  # tutto in una pagina, nel browser
```

Il **diario** (`data/pipeline/runs/`) e' la parte che mancava. Prima l'unico
segno che una run fosse avvenuta era il commit che produceva: una run che non
produce niente, perche' la coda e' vuota o perche' il cancello l'ha bloccata,
non lasciava assolutamente nulla. Il che significa che **una Routine che gira a
vuoto ha lo stesso aspetto di una Routine che non e' mai partita**, ed e'
esattamente cosi' che lo scrittore ha lavorato per settimane su un file morto.

Ora ogni agente ci scrive una riga a fine run, sempre, con l'esito preso da un
vocabolario corto (`merged`, `pr-open`, `blocked`, `nothing`, `stopped`,
`error`), che cosa ha deciso e che cosa ha detto il cancello. E' committato,
quindi la storia sopravvive alla sessione, ed e' un file per run, quindi due run
concorrenti non si contendono nessun percorso. Sta nel perimetro di **tutti**
gli stadi: senza, meta' delle run non lo raggiungerebbe.

Ogni riga porta un **`run_id`**, ed e' quello che risponde alla domanda "chi ha
fatto cosa". Una run lascia due righe, la propria dentro la pull request e
quella di esito che il passo di merge scrive su master, e prima si univano su
`(stadio, pr)`. Non poteva funzionare: la riga dell'agente viaggia dentro la
pull request, quindi va committata **prima** che la pull request esista, quindi
non ne puo' portare il numero. Su trenta run reali diciannove non lo avevano, e
il diario dichiarava ventuno run in attesa mentre le pull request aperte erano
zero. Il `run_id` lo conia chi scrive per primo e non dipende da niente che
succeda dopo.

Il **cruscotto** e' una pagina HTML autonoma che mette insieme lo stato delle
code, il diario, i commit che la catena ha prodotto (riconosciuti dai file che
toccano, non dai messaggi) e le sue pull request. Si rigenera in un secondo e si
apre da file, anche offline. E' una fotografia: per lo stato **vivo** di una
Routine in corso serve <https://claude.ai/code/routines>, perche' l'API delle
Routine espone solo l'ora dell'ultimo firing.

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
| `scout`, `hunter`, `promoter`, `curator` | `checks` | muovono numeri vivi (catalogo, punteggio qualita' della vita) o decidono quale istituzione compare su una pagina pubblica: non fondono finche' la CI non e' verde |

Un verdetto rosso non porta nessun `merge`: fra "i controlli sono falliti" e "ma
solo un po'" non c'e' niente da negoziare.

**Nessuno stadio e' `manual`.** Lo scout lo era, ed era il tappo: la scoperta di
indicatori nuovi si fermava alla sua pull request e non ripartiva finche' un
umano non la guardava. In una catena non presidiata "aspetta una firma" vuol dire
"aspetta per sempre", quindi il controllo si e' spostato dove puo' girare da solo,
cioe' nella CI. `tests/test_source_admission.py` rifiuta una riga di fonte a cui
manchi un campo, con un verso sconosciuto, con una categoria inesistente o con un
tema che nessuno ha mappato, che e' il guasto piu' silenzioso di tutti:
l'indicatore resta in catalogo e sparisce da ogni totale per macro-area.

### L'attesa dei check e' codice, non un flag

`gh pr merge --auto` **non aspetta niente su questo repository**. Con
`allow_auto_merge` a falso e `master` non protetto, `gh` ripiega su un merge
immediato: una PR sonda e' stata fusa con il job dei test ancora `IN_PROGRESS`.
Il contratto ha detto per settimane a tre stadi di chiudere con quel comando,
quindi `checks` e' stato una bugia dal giorno in cui e' stato scritto, e non
c'era niente da nessuna parte che lo dicesse.

Adesso l'attesa e' in `scripts/pipeline_merge.py`, che rilegge il cancello per
conto suo (non si fida del rapporto dell'agente sul proprio verdetto), sonda i
check finche' non concludono, e rifiuta se uno fallisce, se non ne compare
nessuno, o se il cancello e' rosso.

### E parla REST, non GraphQL

Lo stesso script chiedeva i check con `gh pr checks` e fondeva con `gh pr merge`,
che sono GraphQL tutti e due. GraphQL pero' non c'e' sempre: una sessione dietro
il proxy di uscita ha risposto a ogni chiamata REST su questo repository e ha
rifiutato l'endpoint GraphQL con `HTTP 403: This GraphQL query is not enabled for
this session`. Il passo di merge lo vedeva come un comando fallito e basta, senza
un indizio sul perche', e uno stadio che non sa chiudersi non si distingue da uno
stadio che ha deciso di non chiudersi.

Adesso passa da `gh api`, cioe' dalla REST, che e' la superficie piu' piccola e
piu' vecchia: per un passo il cui unico mestiere e' essere affidabile, e' la
scelta giusta anche a proxy spento. Tre conseguenze che vale la pena conoscere:

- **`owner/repo` se lo ricava da solo** (`repo_slug`). Il proxy riscrive `origin`
  in un URL su `127.0.0.1`, e davanti a quello `gh` dice "none of the git remotes
  point to a known GitHub host" e si ferma. Gli ultimi due segmenti del percorso
  pero' sono ancora owner e repo. `GH_REPO` vince su tutto.
- **La classificazione dei check e' nostra** (`_bucket`). REST non ha il `bucket`
  di `gh`, quindi lo ricostruiamo dalle conclusioni grezze, con lo stesso
  vocabolario di prima. Davanti a una conclusione che non conosciamo il verso di
  default e' `fail`: rifiutare costa una PR da rilanciare, passare fonde alla
  cieca. Si leggono anche le vecchie commit status, non solo le check run.
- **Fondere e cancellare il branch sono due chiamate**, non piu' un flag solo. La
  seconda non puo' disfare la prima: se il branch non si cancella il merge resta
  fatto, e lo si dice invece di scrivere `error` su una PR che si e' fusa.

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

**La Routine adesso e' una sola**, ed e' quella del dispatcher: gli stadi non
hanno piu' un cron proprio. Il prompt lancia
`scripts/pipeline_dispatch.py --json --check-open-prs`, legge quale stadio ha
detto, e invoca quell'agente con il `run_id` che il dispatcher ha coniato.

Il vantaggio non e' solo la concorrenza. Sei cron erano anche sei promesse
ricopiate in `pipeline_log.WATCH_GROUPS`, che nessuno poteva verificare da
dentro il repo: se cambiava la schedulazione, quella tabella andava fuori
sincrono in silenzio. Con un battito solo, quello che va sorvegliato e' un
battito solo, e il tick lo registra invece di dichiararlo.

La stessa lezione anti-drift vale dentro `.claude/`. Ogni agente dichiara nel
frontmatter il proprio **modello** (niente modello implicito ereditato dalla
sessione: un cambio di default cambierebbe il giudizio editoriale in silenzio)
e i propri **hook**: `scripts/agent_guard.py` applica il perimetro di
`STAGE_PATHS` e una allowlist di comandi al momento del gesto, PreToolUse per
PreToolUse, e allo Stop rifiuta la chiusura di una run su `automation/*` senza
la riga di diario. La procedura di chiusura, le regole sui contenuti web e le
classi di errore della rilettura non sono piu' ricopiate nei sei prompt: sono
tre skill condivise in `.claude/skills/` (`pipeline-close-run`,
`untrusted-web`, `indicator-review`), una copia sola a cui i prompt puntano.
Il cancello, oltre che nel passo di merge, gira anche in CI sui branch
`automation/*` (job `gate` di `.github/workflows/ci.yml`), quindi la politica
`checks` lo aspetta come aspetta la suite. Prima di cambiare modello, prompt,
skill o hook: [`CANARY.md`](CANARY.md) e le eval in `evals/`.

## Quando qualcosa va storto

```bash
python3 scripts/pipeline_status.py          # dove si e' fermata
python3 scripts/pipeline_dispatch.py        # chi dovrebbe girare adesso
python3 scripts/pipeline_gate.py --stage <stadio> --json    # perche' e' bloccata
```

Sintomi ricorrenti e cosa significano davvero:

- **La catena non fa piu' niente.** Guarda per prima cosa il tick del
  dispatcher (`pipeline_log.py --stage dispatch`). Se non ne registra da giorni
  il problema e' la Routine, non gli stadi: nessuno sta assegnando il lavoro.
- **Il dispatcher gira e non lancia mai niente.** Ha trovato una pull request
  della catena sempre aperta. Una run che non si chiude blocca tutte le altre,
  di proposito: guarda perche' quella non e' fusa.
- **Uno stadio non apre PR da settimane.** Guarda `pipeline_status`: se la sua
  coda e' a zero non e' fermo, e' `idle`, e il diario lo distingue.
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

Due cose, e nessuna delle due e' un'approvazione:

1. **Scrivere un adapter** per una fonte che non e' un dataflow SDMX Istat.
   E' codice, e nessun agente scrive codice. Lo scout che approva una fonte del
   genere lo dice nella PR e descrive che adapter servirebbe.
2. **Creare una categoria** della qualita' della vita. E' una sezione del sito,
   con un nome, una descrizione e una macro-area, non una riga di CSV. Mappare
   un tema a una categoria che gia' esiste invece e' del curatore, e si fa in
   `config/theme_categories.csv`.

Tutto il resto, dalla fonte alla pagina pubblicata e poi rivisitata, gira da
solo e si fonde da solo. Non c'e' nessun punto in cui la catena aspetta che
qualcuno guardi: il controllo non e' un'approvazione, sono il perimetro, il
cancello e la CI, e girano tutti e tre senza di te.
