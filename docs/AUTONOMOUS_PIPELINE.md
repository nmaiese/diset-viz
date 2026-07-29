# La catena autonoma

Come Divario Italia trova, verifica, cura, scrive, rilegge e pubblica un
indicatore **senza intervento umano**, e quali sono le tre cose che ancora lo
richiedono e perche'.

Documento profondo. Per il contratto operativo che ogni agente segue a ogni run
vedi [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md); per lo strato dati sotto,
[`DATA_PIPELINE.md`](DATA_PIPELINE.md) e
[`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md); per l'anatomia di una pagina
indicatore, [`INDICATOR_PAGES.md`](INDICATOR_PAGES.md). Per il modello a pratica
editoriale che dà un nome all'indicatore-lungo-un-ciclo,
[`EDITORIAL_PRACTICE.md`](EDITORIAL_PRACTICE.md).

## L'obiettivo, detto per intero

Indicatori nuovi **senza intervento**, ma verificati e curati, con testi pronti e
corretti. Non "un agente che apre PR che qualcuno legge": una catena che porta
una serie da un catalogo SDMX a una pagina pubblica leggibile, e che poi ci
**torna sopra** quando i dati si muovono.

Le due meta' contano allo stesso modo. Una catena che scopre e non rilegge
produce un archivio che invecchia in silenzio, e l'invecchiamento e' peggio di
un buco: un buco si vede.

## I tre ruoli

La catena e' passata da **sette stadi** a **tre ruoli**, e insieme da un'unita' di
lavoro per **stadio** a un'unita' di lavoro per **indicatore**. Non e' un
rinominare: e' che sette sessioni fredde che si passavano un indicatore via CSV
tenevano quell'indicatore peggio di quanto lo tenga una testa sola che lo porta
fino in fondo.

```
  ammissione                      produttore                    verificatore
  (scout+hunter+promoter)         (curator+writer+reviewer)     (invariato)
  quali fonti, quali indicatori   cura -> scrive -> si rilegge   prova a smentirlo
  li promuove                     -> firma
       |                               |                              |
  batch, l'intera coda            un indicatore alla volta        un articolo alla volta
       |                               |                              |
  data/discovery/*                content/indicators/             data/pipeline/verifiche/
                                  data/pipeline/runs/
```

- **Ammissione** (agente `admissions`) scandaglia i cataloghi, decide quali
  fonti e quali indicatori entrano, e promuove cio' che approva. Fonde scout,
  cacciatore e promotore. Il suo passo distintivo e' l'**auto-refutazione**:
  prima di scrivere "approvato" prova a demolire la propria approvazione ("come
  la faccio cadere?"), perche' l'istituzione e la licenza che lascia passare
  finiscono su una pagina pubblica sotto il nome del progetto e nessuno legge la
  pull request prima del merge.
- **Produttore** (agente `producer`) porta **un** indicatore da ammesso a
  pubblicato in una sessione: cura il verso e la categoria, scrive l'intero
  articolo, si rilegge, firma. Fonde curatore, scrittore e revisore. Il passo
  distintivo e' la **rilettura sul proprio testo** (reflexion): ha appena
  scritto, quindi e' il lettore peggiore, e si rilegge con la durezza con cui lo
  farebbe il verificatore.
- **Verificatore** (agente `indicator-verifier`) prova a falsificare ogni
  affermazione di un articolo firmato. E' rimasto **invariato** nella
  ri-architettura, ed e' l'unico ruolo che misura il lavoro di un altro ruolo
  invece dei dati. Non corregge niente: una smentita torna in coda al
  produttore, che ha assorbito il revisore.

Il verificatore e' arrivato per ultimo perche' e' servito misurarlo prima di
credergli. Una firma di chi si e' riletto e' la parola del produttore sul lavoro
del produttore, e finche' nessuno provava a farla cadere quanto valesse non si
sapeva. Ora si sa:

| stato dell'articolo | affermazioni controllate | false | tasso |
| --- | --- | --- | --- |
| note migrate, mai rilette | 113 | 11 | 9,7% |
| scritte e non ancora rilette | 392 | 19 | 4,8% |
| scritte e rilette | 529 | 7 | 1,3% |

La rilettura toglie la gran parte degli errori e ne lascia qualcuno, e quel
qualcuno resta in pagina finche' qualcosa non prova a farlo cadere. E' il motivo
per cui il produttore si rilegge (passo interno) **e** il verificatore rilegge
di nuovo, indipendente, dopo la firma.

Ogni ruolo ha tre cose, e sono sempre le stesse tre: una **coda deterministica**
calcolata da file committati, un **agente** con un file di definizione in
`.claude/agents/`, e un **verdetto del cancello** che decide se puo' pubblicare.
Le code sono ancora quelle dei sette stadi (il vocabolario interno non cambia:
un produttore legge la coda del curatore e quella dello scrittore), ma chi le
drena sono tre ruoli, non sette.

| ruolo | agente | coda | comando |
| --- | --- | --- | --- |
| ammissione | `admissions` | `source_candidates.csv`, `candidates.csv`, gli `approved` | `scripts/scout_sources.py`, `scripts/discover_candidates.py`, `scripts/promote_candidates.py` |
| produttore | `producer` | `curate.worklist()` + `pending_notes` + `review_queue` | `scripts/curate.py`, `scripts/pending_notes.py`, `scripts/review_queue.py` |
| verificatore | `indicator-verifier` | `verification_queue` | `scripts/verification_queue.py` |

Un solo comando dice lo stato di tutte le code:

```bash
python3 scripts/pipeline_status.py            # leggibile
python3 scripts/pipeline_status.py --json     # per un agente
```

Esiste per una ragione precisa. Ogni agente vede la propria casella e nient'altro,
quindi nessuno riesce a distinguere "sono fermo perche' ho finito" da "sono fermo
perche' e' bloccato il ruolo sopra di me", che sono situazioni opposte e si
somigliano moltissimo. Ogni agente lo lancia per primo.

## Il lanciatore: che cosa lanciare, e quanto in parallelo

```bash
python3 scripts/pipeline_launch.py            # il piano, leggibile
python3 scripts/pipeline_launch.py --json     # per l'agente lanciatore
python3 scripts/pipeline_launch.py --top 3    # solo le prime tre voci
```

Il **dispatcher e' ritirato**. `scripts/pipeline_dispatch.py` non esiste piu'.
Serializzava: un tick, uno stadio, il primo con lavoro in ordine di catena, e
rifiutava di partire finche' una pull request della catena era ancora aperta.
Aveva senso quando l'unita' di lavoro era lo **stadio** e sette stadi separati si
scrivevano addosso i registri condivisi: la concorrenza si eliminava non
gestendola. Ma quella forma congelava tutto. Una sola PR non chiusa fermava
l'intera catena, e due stadi che partivano vicini finivano in conflitto di merge.

Al suo posto c'e' `scripts/pipeline_launch.py`, un **lanciatore per-indicatore**.
Non sceglie uno stadio: legge il dossier per-indicatore (`practice_timeline`) e
le code (`pipeline_status.queue_sizes`) e restituisce una **lista prioritizzata
di lanci**, tutto il lavoro lanciabile insieme.

- **Produttore e verificatore sono per-indicatore.** Ogni indicatore pronto e'
  una voce a se', perche' due produttori su due indicatori diversi toccano file
  diversi (un articolo per record) e non si toccano mai. La priorita' viene dal
  dossier, la stessa di `stage_priorities`: una smentita su una pagina online
  (peso 100) apre il piano davanti a una candidatura nuova.
- **L'ammissione e' batch.** Una sessione triaga l'intera coda di fonti e
  candidati e promuove cio' che approva, quindi e' una voce sola. La sua
  esistenza si legge dalle code pre-pratica (scout, hunter, promoter) piu' le
  pratiche in stato `proposta`.

**Niente piu' lock una-PR-aperta.** Indicatori diversi non contendono, quindi
non c'e' niente da serializzare e niente da aspettare: il lanciatore elenca, e
chi esegue (l'agente lanciatore, o una persona) ne mette in volo quanti ne vuole
in parallelo. Un blocco su un indicatore malato non ferma un indicatore pronto e
indipendente.

Come il dispatcher, non lancia lui l'agente, e non potrebbe: un agente e' una
sessione Claude Code, il lanciatore e' stdlib. Dice **che cosa** lanciare, con
ruolo, indicatore e `run_id` gia' coniato, e l'agente lanciatore
(`.claude/agents/launcher.md`) fa il resto. La decisione resta cosi'
deterministica e verificabile da un test, l'esecuzione no.

Con `--publish` il lanciatore fa anche il **passo del sito**, un secondo passo
meccanico e post-deploy che riusa `verify_publication.publish_step`: verifica gli
indicatori in stato `fusa` contro `divarioitalia.it` e committa le prove di
pubblicazione su master, chiudendo la transizione `fusa -> pubblicata`
(vedi [`EDITORIAL_PRACTICE.md`](EDITORIAL_PRACTICE.md), §8, e piu' sotto). Non e'
un ruolo, non lancia un agente e non apre PR: e' deterministico, si committa da
solo con un file nuovo per record, e scrive una prova solo dove il sito conferma
la versione committata. Un sito irraggiungibile o non ancora dispiegato non
scrive niente e l'indicatore resta `fusa` per il giro dopo.

## Gli store: perche' i conflitti non esistono piu'

Tre registri della catena erano file unici a cui ogni stadio appendeva **in
fondo**. Due stadi che girano vicini scrivono nello stesso punto, quindi git
chiama conflitto quella che e' solo la somma di due righe che non si
contraddicono. Adesso sono directory, un file per record:

| store | un file per | scritto da | committato |
| --- | --- | --- | --- |
| `content/indicators/` | articolo | produttore | si' |
| `data/pipeline/runs/` | run | tutti i ruoli | si' |
| `data/pipeline/verifiche/` | verifica | verificatore | si' |
| `data/pipeline/pubblicazioni/` | prova di pubblicazione | passo del sito | si' |
| `data/pipeline/practices/` | pratica (record di stato) | riconciliatore | si' |
| `data/pipeline/heartbeats/` | sessione in volo | ogni ruolo all'avvio | no (e' il vivo) |

Non e' una riduzione della probabilita' di conflitto, e' la sua rimozione: due
ruoli che lavorano su indicatori diversi non toccano lo stesso percorso, quindi
non c'e' niente da fondere. Resta contendibile solo la modifica **allo stesso**
articolo, che e' l'unico caso in cui un conflitto significa davvero qualcosa. E'
proprio questa proprieta' che permette al lanciatore di lanciare in parallelo
senza un lock.

Ne vengono due cose che non erano l'obiettivo e valgono quanto l'obiettivo. Il
diff di una run del produttore adesso e' leggibile, perche' dice di quali
articoli parla invece di mostrare hunk dentro mezzo megabyte di JSON. E
`git log content/indicators/ter__920.json` e' la storia editoriale di quella
pagina, che prima non esisteva.

Il perimetro del cancello capisce le directory: una voce di `STAGE_PATHS` che
finisce con una barra e' un prefisso. La barra e' ancorata di proposito, cosi'
`content/indicators` non autorizza `content/indicators-bozze`.

## Il verificatore, e perche' non ripara niente

`data/pipeline/verifiche/` e' tutto quello che produce: un file per verifica,
con i quattro contatori e l'impronta della prosa che ha letto.

**Non ha `content/indicators/` nel perimetro**, e l'assenza e' la definizione
del ruolo piu' che il suo prompt. Un ruolo che trova e ripara i propri rilievi
corregge i propri compiti, che e' esattamente il difetto che esiste per prendere
un livello sopra. Quindi una smentita torna al produttore (che ha assorbito il
revisore), come il segnale `smentita` di `review_queue`, che pesa piu' di ogni
altro segnale di quella coda: tutti gli altri marcano una frase che *potrebbe*
essere sbagliata, quello marca una frase che qualcuno ha gia' fatto cadere, con
la prova, e che e' ancora in pagina.

**Una verifica scade quando cambia il testo, non quando passa il tempo.** La riga
porta un'impronta della prosa, e l'articolo risulta verificato solo finche' la sua
prosa hasha a quel valore. La prima versione confrontava `reviewed_at` con la data
della verifica ed e' stata buttata: due eventi nello stesso giorno sono
indistinguibili, e il produttore che ripara una frase smentita firma il giorno in
cui il verificatore l'ha smentita. Con l'impronta non c'e' aritmetica e non c'e'
pareggio.

Le due code si passano il lavoro senza che nessuna cancelli una riga dell'altra:

```
  verificatore trova una smentita  ->  review_queue la mostra in cima
  il produttore riscrive la frase  ->  l'impronta cambia, la smentita e' spenta
  l'impronta cambia                ->  l'articolo torna in coda al verificatore
```

`affermazioni_controllate` e' il campo che non si negozia, e il cancello lo
impone invece di ricordarlo: senza, "zero smentite" e "non ho guardato" producono
la stessa riga, e un ruolo che non sa distinguerle costa una pull request per
articolo e non garantisce niente.

### Il registro errori: il learning loop

Le smentite confermate non restano solo un rilievo su un articolo: diventano
memoria. `scripts/indicator_brief.py` (la sola fonte dei numeri per il
produttore) ha una sezione **ERRORI NOTI**, una vista sulle smentite gia'
confermate in `data/pipeline/verifiche/` (`esito=smentito`), a **cerchi
concentrici**: prima quelle su **questo** indicatore, poi quelle della sua
**famiglia**, poi le **classi ricorrenti** che il verificatore ha etichettato
(`classe/gravita:` nel campo `rilievi`). Solo smentite confermate, mai una sfida
grezza: una falsa smentita non deve avvelenare il registro. Il produttore che
legge il brief prima di scrivere ci si rilegge piu' duro proprio sulle classi
che qui hanno gia' fatto cadere qualcosa, cosi' un errore corretto una volta non
si ripresenta senza che nessuno lo sappia.

## Guardare la catena senza aprire file

Il **monitoraggio** e' `scripts/pipeline_monitor.py`, e non e' un secondo modello
di stato: e' una **vista di lettura** sullo stesso dossier per-indicatore che
`practice_timeline` ricostruisce dagli artefatti committati. La domanda a cui
risponde e' quella che prima costava sette comandi e una testa che li teneva
insieme: **dov'e' fermo, e perche'**.

```bash
python3 scripts/pipeline_monitor.py           # dov'e' fermo, in una schermata
python3 scripts/pipeline_monitor.py --json    # per la rotta o un altro programma
```

E' servito vivo dalla rotta Flask protetta **`/_pipeline`** (noindex sempre,
auto-refresh che si puo' mettere in pausa). La vista ha tre livelli. In testa ci
sono la frase di diagnosi e i numeri operativi: correzioni urgenti, azioni
pronte, sessioni vive, indicatori fusi che aspettano il sito e pubblicazioni
confermate. Subito sotto ci sono il flusso completo
**ammissione -> produzione -> verifica -> pubblicazione**, le sessioni e le PR
vive, e la coda prioritaria.

La sezione **"Tutti gli indicatori"** e' il dossier leggibile. Ogni riga porta
nome, id, stato, avanzamento nelle quattro fasi, ultima attivita' e una prossima
azione espressa come gesto con il suo responsabile. Aprendola si vedono il
percorso completo degli eventi e tutte le run associate, inclusi esito, durata,
modello, trigger, PR, variazione della coda, token e motivazioni dettagliate.
Ricerca, filtri per fase, stato e prossimo responsabile, e ordinamenti per
priorita', attivita', avanzamento o nome permettono di leggere tutto il catalogo
senza perdere il contesto. Filtri, schede aperte e pausa del refresh restano
memorizzati nella sessione del browser. La pagina pubblicata e' collegata quando
esiste una prova valida sul sito.
Se `PIPELINE_TOKEN` e' impostato serve solo con `?token=` giusto, altrimenti 404
(non 403: una pagina interna non conferma nemmeno di esistere); vuoto, in locale,
e' aperta. Si ricalcola a ogni caricamento dai file committati, non da uno stato
a parte.

Il **vivo** viene dai **battiti** (`data/pipeline/heartbeats/`, ignorati da git):
ogni ruolo scrive un file all'avvio della sua run e lo cancella alla chiusura, un
file per `run_id` cosi' due ruoli in volo insieme non si sovrascrivono. E' best
effort: se un ruolo non ha battuto il vivo tace, il committato no. Un battito
piu' vecchio della soglia si considera morto, una sessione caduta senza pulire.

Il **consumo token** e' telemetria durevole, tenuta a parte dai battiti. Il
lanciatore e' l'unico a vedere i `subagent_tokens` di ogni ruolo che lancia (il
ruolo, dentro la sua sessione, non conosce il proprio totale), quindi e' lui a
POSTarli a `/_pipeline/beat` (azione `tokens`) chiavati sul `run_id` del ruolo:
finiscono in una tabella dedicata dello **stesso** SQLite replicato su GCS, che
**non scade** come un battito. Il cruscotto li somma per indicatore e li mostra
per step. E' **solo in avanti**: le run precedenti a questa telemetria non hanno
un totale e non c'e' backfill (i token delle run passate non esistono da nessuna
parte).

Il **diario** (`data/pipeline/runs/`) e' la storia. Prima l'unico segno che una
run fosse avvenuta era il commit che produceva: una run che non produce niente,
perche' la coda e' vuota o perche' il cancello l'ha bloccata, non lasciava
assolutamente nulla. Il che significa che **una Routine che gira a vuoto ha lo
stesso aspetto di una Routine che non e' mai partita**, ed e' esattamente cosi'
che lo scrittore ha lavorato per settimane su un file morto. Ora ogni ruolo ci
scrive una riga a fine run, sempre, con l'esito preso da un vocabolario corto
(`merged`, `pr-open`, `blocked`, `nothing`, `stopped`, `error`), che cosa ha
deciso e che cosa ha detto il cancello. E' committato, quindi la storia
sopravvive alla sessione, ed e' un file per run, quindi due run concorrenti non
si contendono nessun percorso. Sta nel perimetro di **tutti** i ruoli: senza,
meta' delle run non lo raggiungerebbe.

Ogni riga porta un **`run_id`**, ed e' quello che risponde alla domanda "chi ha
fatto cosa". Una run lascia due righe, la propria dentro la pull request e quella
di esito che il passo di merge scrive su master, e prima si univano su
`(stadio, pr)`. Non poteva funzionare: la riga dell'agente viaggia dentro la pull
request, quindi va committata **prima** che la pull request esista, quindi non ne
puo' portare il numero. Il `run_id` lo conia il lanciatore quando decide il lancio
e non dipende da niente che succeda dopo.

Restano due comandi piu' vecchi, ancora validi:

```bash
python3 scripts/pipeline_log.py               # che cosa hanno fatto gli agenti
python3 scripts/pipeline_dashboard.py --open  # una pagina HTML autonoma, offline
```

Il cruscotto HTML e' una fotografia da file, comoda offline; il monitoraggio
vivo, con la headline e i battiti, e' `/_pipeline`.

## Il cancello: cosa rende sicuro togliere l'umano

`scripts/pipeline_gate.py` e' il punto in cui ogni ruolo chiude. Non e' una
formalita': e' la cosa che sta fra "autonomo" e "autonomamente sbagliato su
scala". Restituisce un verdetto calcolato dal diff e dalla suite, mai
dall'opinione che l'agente ha del proprio lavoro.

```bash
python3 scripts/pipeline_gate.py --stage producer
```

Gli stadi che il cancello conosce sono ancora sette piu' `producer`, `admissions`
e `publisher`: un ruolo chiude sul verdetto del proprio (`--stage producer`,
`--stage admissions`, `--stage verificatore`). Controlla, in ordine di danno:

1. **Il perimetro.** Ogni ruolo puo' toccare una lista corta di file, scritta in
   `STAGE_PATHS`. Un prompt si puo' modificare, fraintendere o ignorare, il repo
   no: un produttore che si mette a "sistemare" `app/views.py` fallisce qui,
   prima che qualcuno legga il suo ragionamento. E' questo controllo a rendere
   automatizzabili gli altri. La guardia per-agente (`scripts/agent_guard.py`,
   dichiarata nel frontmatter di ogni agente) applica lo stesso perimetro al
   momento del gesto, PreToolUse per PreToolUse.
2. **La suite intera**, non il sottoinsieme preferito del ruolo. Le guardie su
   prosa, deriva del vintage, cifre attribuite a una regione, schema CSV e
   `/legacy` sono la memoria accumulata di tutto quello che qui e' gia' andato
   storto.
3. **Gli invarianti sul diff**, che la suite non puo' vedere perche' riguardano
   il cambiamento e non lo stato: una decisione di triage senza motivazione
   scritta, un'approvazione sotto la copertura minima o senza licenza,
   `score_eligible=true` su un verso non direzionale, una revisione che non firma
   niente, un `vintage` oltre i dati.
4. **L'igiene**: whitespace, e il trailer `Co-Authored-By` che CLAUDE.md vieta.

I test in `tests/integration/test_pipeline_gate.py` costruiscono **prima l'input cattivo** e
verificano che il cancello rifiuti. Un cancello che ha sempre risposto verde non
e' un cancello.

## La politica di merge: adesso e' uniforme, e perche'

Il verdetto porta un campo `merge`, che e' l'ordine. **Oggi ogni ruolo fonde
`auto`**, sul cancello locale, ed e' un cambiamento rispetto a prima, quando la
prosa fondeva da sola ma promozione, curatela e ammissione di una fonte
aspettavano i check remoti (`checks`).

La ragione e' un deadlock scoperto sul campo. La CI remota **non parte** sulle
pull request aperte via il GitHub MCP: GitHub non gira i workflow per un evento a
token d'app, quindi i check non compaiono mai. Il passo di merge rifiutava
(correttamente) uno stadio `checks` i cui check non arrivavano, la pull request
restava `pr-open` per sempre, e il vecchio dispatcher rifiutava di lanciare
qualsiasi cosa finche' una PR della catena era aperta. Una sola PR incagliata
congelava l'intera catena. `checks` non comprava nessun verdetto remoto
indipendente, solo un blocco.

Il cancello locale tiene la garanzia vera al posto suo: gira la stessa suite che
il job `python` della CI gira, piu' il perimetro che il job `gate` della CI gira,
e la gira **prima** del merge invece che mai. Un verde `auto` e' un cambiamento
di cui la catena ha gia' misurato tutto quello che sa misurare. `checks` resta
una parola che il cancello sa ancora dire, e l'attesa vive ancora in
`pipeline_merge.py`, ma nessun ruolo la usa oggi: se un domani la CI remota
venisse fatta partire su queste PR, gli stadi che muovono numeri (scout, hunter,
promoter, curator, verificatore) sono quelli da riportare a `checks`.

**Nessun ruolo e' `manual`.** Lo scout lo era, ed era il tappo: la scoperta di
indicatori nuovi si fermava alla sua pull request e non ripartiva finche' un
umano non la guardava. In una catena non presidiata "aspetta una firma" vuol dire
"aspetta per sempre", quindi il controllo si e' spostato dove puo' girare da solo,
cioe' nella suite. `tests/unit/test_source_admission.py` rifiuta una riga di fonte a cui
manchi un campo, con un verso sconosciuto, con una categoria inesistente o con un
tema che nessuno ha mappato, che e' il guasto piu' silenzioso di tutti:
l'indicatore resta in catalogo e sparisce da ogni totale per macro-area.

### L'attesa dei check e' codice, non un flag

`gh pr merge --auto` **non aspetta niente su questo repository**. Con
`allow_auto_merge` a falso e `master` non protetto, `gh` ripiega su un merge
immediato: una PR sonda e' stata fusa con il job dei test ancora `IN_PROGRESS`.
Per questo l'attesa (per il giorno in cui `checks` tornera' attivo) vive in
`scripts/pipeline_merge.py`, che rilegge il cancello per conto suo (non si fida
del rapporto dell'agente sul proprio verdetto), sonda i check finche' non
concludono, e rifiuta se uno fallisce, se non ne compare nessuno, o se il cancello
e' rosso.

### E parla REST, non GraphQL

Lo stesso script chiedeva i check con `gh pr checks` e fondeva con `gh pr merge`,
che sono GraphQL tutti e due. GraphQL pero' non c'e' sempre: una sessione dietro
il proxy di uscita ha risposto a ogni chiamata REST su questo repository e ha
rifiutato l'endpoint GraphQL con `HTTP 403: This GraphQL query is not enabled for
this session`. Il passo di merge lo vedeva come un comando fallito e basta, senza
un indizio sul perche', e un ruolo che non sa chiudersi non si distingue da uno
che ha deciso di non chiudersi.

Adesso passa da `gh api`, cioe' dalla REST, che e' la superficie piu' piccola e
piu' vecchia: per un passo il cui unico mestiere e' essere affidabile, e' la
scelta giusta anche a proxy spento. Tre conseguenze che vale la pena conoscere:

- **`owner/repo` se lo ricava da solo** (`repo_slug`). Il proxy riscrive `origin`
  in un URL su `127.0.0.1`, e davanti a quello `gh` dice "none of the git remotes
  point to a known GitHub host" e si ferma. Gli ultimi due segmenti del percorso
  pero' sono ancora owner e repo. `GH_REPO` **e' ignorato**, non e' piu' un
  override: da environment ereditato faceva aprire o fondere la PR sul repo
  sbagliato (o fallire perche' li' il branch non esiste), ed erano i rifiuti
  orfani "il cancello e' rosso" su master. Chiedere agli agenti di non impostarlo
  non bastava se l'ambiente lo conservava, quindi il percorso automatico lo
  ignora del tutto e ricava lo slug sempre dal remote. Per la stessa ragione
  **anche la PR si apre via REST** (`pipeline_merge.py --open`, `create_pr`), non
  con `gh pr create` (GraphQL, cieco al remote proxato).
- **La classificazione dei check e' nostra** (`_bucket`). REST non ha il `bucket`
  di `gh`, quindi lo ricostruiamo dalle conclusioni grezze, con lo stesso
  vocabolario di prima. Davanti a una conclusione che non conosciamo il verso di
  default e' `fail`: rifiutare costa una PR da rilanciare, passare fonde alla
  cieca. Si leggono anche le vecchie commit status, non solo le check run.
- **Fondere e cancellare il branch sono due chiamate**, non piu' un flag solo. La
  seconda non puo' disfare la prima: se il branch non si cancella il merge resta
  fatto, e lo si dice invece di scrivere `error` su una PR che si e' fusa.

## La pubblicazione: un passo meccanico del lanciatore, non del produttore

"Fuso su master" non e' "pubblicato". Il repository puo' essere avanti e il sito
indietro, quindi trattare il merge come pubblicazione e' un falso positivo. La
transizione `fusa -> pubblicata` e' un passo a se', e vive **fuori** dal
produttore per una ragione di tempo: il produttore gira **prima** del deploy,
quando il sito non serve ancora la versione nuova, quindi non puo' verificarla.
La verifica del sito si puo' fare solo dopo, sul sito gia' dispiegato.

Per questo e' il **passo del sito** del lanciatore (`pipeline_launch.py
--publish`, che l'agente lanciatore passa a ogni giro), non un passo del ciclo
editoriale. Riusa `verify_publication.publish_step`:

- `publication_queue` elenca gli indicatori in stato `fusa` senza una prova
  valida.
- per ciascuno prende la pagina pubblica (la forma a solo code, che l'app 301
  reindirizza allo slug canonico) e confronta una **firma di contenuto** (un
  frammento normalizzato del `lead` piu' l'anno del `vintage`) con l'HTML servito.
- se combacia, `write_proof` scrive la prova in `data/pipeline/pubblicazioni/`
  (un file per record, con l'impronta `prosa` che la fa scadere quando il testo
  cambia), e `commit_proofs` -> `land_on_master` la porta su master.

`land_on_master` mette file **nuovi** su master da qualsiasi branch, costruendo
un commit sopra `origin/master` che contiene **solo** quei file (un indice
temporaneo seminato da `origin/master` piu' i soli percorsi da pubblicare):
l'invariante "non spinge altro che se stesso" vale per costruzione, non per
guardia. E' sicuro perche' sono file nuovi con un nome che nessun altro puo'
scegliere, fuori da qualsiasi pull request. Chi perde la corsa del push si
ricostruisce sopra il master aggiornato e ritenta.

Regola di prudenza presa dal cancello: un controllo che non ha potuto girare
**non passa**. Un sito irraggiungibile (`ok=None`) non scrive niente e non e' un
fallimento, l'indicatore resta `fusa` per il giro dopo; solo un `ok=True` scrive
la prova. Lo stesso e' agganciato anche nel cancello come stadio `publisher`
(perimetro `data/pipeline/pubblicazioni/`, controllo `check_publications`: una
prova con `ok!=True`, o ancorata a un testo che non e' in pagina, non e' una
pubblicazione), inerte nel giro del lanciatore perche' quel passo committa da se'
senza aprire PR.

## Il rientro: la catena lavora anche sul pubblicato

E' la meta' che mancava. Prima ogni stadio drenava la propria coda una volta e
poi restava fermo per sempre, il che faceva sembrare la catena finita mentre il
catalogo invecchiava sotto. Oggi i tre innesco sono gli stessi, ma li drenano i
tre ruoli:

**Ammissione.** Non ha un rientro sul pubblicato: guarda solo i cataloghi. Il suo
"rientro" e' che la coda dello scout riflette lo stato del catalogo (vedi sotto),
non un troncamento.

**Produttore, lato curatela.** `curation.csv` porta `data_year`, l'anno su cui il
verso e' stato giudicato. Quando la fonte ne pubblica uno piu' recente,
l'indicatore rientra in `recheck`. Un verso e' un'affermazione su quale estremo
della classifica sia quello buono, ed e' esattamente cio' che una ridefinizione,
un rebase o una rottura di serie possono invertire.

**Produttore, lato testo.** Ha `stale` in `pending_notes` e `text_queue` (un
articolo il cui `vintage` e' rimasto indietro) e, dopo un rinfresco,
l'articolo porta `reviewed_vintage`, il `vintage` che era stato firmato: quando
le cifre cambiano i due valori smettono di combaciare e l'articolo torna in coda
con il segnale `rilettura`, che pesa piu' di ogni segnale di rischio. Riscrivere
l'articolo su un anno nuovo e non ri-firmarlo e' proprio cio' che lo rimette in
coda per la rilettura.

**Verificatore.** Rientra quando l'impronta della prosa cambia (§verificatore): un
articolo riscritto torna da provare a smentire.

In tutti l'innesco sono **i dati, mai il calendario**. Rileggere tutto ogni N
mesi riporterebbe la deriva gia' corretta una volta, cioe' un indicatore
contestuale che si ripresenta per sempre perche' `score_eligible` resta `false`
per definizione (vedi il docstring di `curate.uncurated_targets`).

## Far crescere il bacino senza scrivere codice

L'ammissione si esaurisce nel momento in cui le fonti cablate smettono di
crescere, ed e' esattamente cosa era successo con il vecchio cacciatore: cinque
serie cablate, cinque trovate, niente altro da scoprire. Due file rompono quel
tetto, e sono entrambi **dati** dentro il perimetro di un agente:

- `config/istat_series.yaml` (ammissione): una riga = un indicatore Istat SDMX.
  `dataflow` e' un campo per serie, non piu' una costante di modulo, quindi un
  dominio nuovo non richiede un adapter nuovo.
- `config/theme_categories.csv` (produttore): la mappa tema -> categoria. Un tema
  che il catalogo non conosce fa sparire l'indicatore dai totali per macro-area
  pur lasciandolo in catalogo, cioe' un buco silenzioso, e la correzione stava
  dentro `app/taxonomy.py`, un modulo Python.

C'era pero' un tappo a monte di quei due file: lo **scout** (oggi dentro
l'ammissione) proponeva al massimo 40 fonti per run (`scout_sources.py --limit
40` di default) e, con un punteggio uniforme, l'ordinamento cadeva sull'alfabeto.
Su un catalogo di quasi 5000 dataflow proponeva sempre gli stessi 40, quindi
decine di domini regionali nuovi (turismo, occupazione per settore, reddito,
popolazione per titolo di studio, giustizia) restavano invisibili e la coda
appariva vuota mentre non lo era. Adesso il tetto e' tolto (proposte senza cap) e
la query del catalogo, che e' cache-forever, si ri-sonda con `--refresh`: cosi'
l'ammissione vede i dataflow che Istat pubblica dopo l'ultima run, e la scoperta
non si ferma alla prima fotografia.

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

**La Routine e' una sola**, ed e' quella del **lanciatore**: i ruoli non hanno un
cron proprio. Anche il lanciatore e' un agente a pieno titolo
(`.claude/agents/launcher.md`, con modello e guardia nel frontmatter): legge
`scripts/pipeline_launch.py --json --publish --publish-base https://divarioitalia.it`,
fa il passo del sito, poi lancia gli agenti in cima al piano **in parallelo**
(piu' `Agent` nello stesso messaggio), ciascuno con il suo `run_id` e il suo
indicatore. A differenza del dispatcher non ne lancia uno solo: indicatori
diversi non contendono. Il prompt della Routine e' un puntatore a quella
definizione, mai una copia.

La stessa lezione anti-drift vale dentro `.claude/`. Ogni agente dichiara nel
frontmatter il proprio **modello** (niente modello implicito ereditato dalla
sessione: un cambio di default cambierebbe il giudizio editoriale in silenzio)
e i propri **hook**: `scripts/agent_guard.py` applica il perimetro di
`STAGE_PATHS` e una allowlist di comandi al momento del gesto, PreToolUse per
PreToolUse, e allo Stop rifiuta la chiusura di una run su `automation/*` senza
la riga di diario (il lanciatore non ha questo hook, di proposito: un tick che
lancia dei ruoli non lascia una riga propria, la lascia ogni ruolo lanciato). La
procedura di chiusura, le regole sui contenuti web e le classi di errore della
rilettura non sono ricopiate nei prompt: sono tre skill condivise in
`.claude/skills/` (`pipeline-close-run`, `untrusted-web`, `indicator-review`),
una copia sola a cui i prompt puntano. Il cancello gira anche in CI sui branch
`automation/*` (job `gate` di `.github/workflows/ci.yml`). Prima di cambiare
modello, prompt, skill o hook: [`CANARY.md`](CANARY.md) e le eval in `evals/`.

## Quando qualcosa va storto

```bash
python3 scripts/pipeline_monitor.py         # dov'e' fermo, e perche' (la headline)
python3 scripts/pipeline_launch.py          # che cosa dovrebbe partire adesso
python3 scripts/pipeline_gate.py --stage <ruolo> --json    # perche' e' bloccata
```

Sintomi ricorrenti e cosa significano davvero:

- **La catena non fa piu' niente.** Guarda per prima cosa la storia recente nel
  monitoraggio (o `pipeline_log.py`). Se nessun ruolo registra da giorni il
  problema e' la Routine del lanciatore, non i ruoli: nessuno sta lanciando il
  lavoro.
- **Un indicatore resta `fusa` e non passa a `pubblicata`.** Il passo del sito
  non ha trovato la versione online: o il deploy non e' ancora avvenuto, o il
  sito e' irraggiungibile, o la pagina non porta il lead atteso. Riprova al giro
  dopo; se persiste, verifica a mano con `verify_publication.py --indicator <id>`.
- **Un ruolo non apre PR da settimane.** Guarda il monitoraggio: se la sua coda
  e' a zero non e' fermo, e' in pari, e il diario lo distingue.
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
   E' codice, e nessun agente scrive codice. L'ammissione che approva una fonte
   del genere lo dice nella PR e descrive che adapter servirebbe.
2. **Creare una categoria** della qualita' della vita. E' una sezione del sito,
   con un nome, una descrizione e una macro-area, non una riga di CSV. Mappare
   un tema a una categoria che gia' esiste invece e' del produttore, e si fa in
   `config/theme_categories.csv`.

Tutto il resto, dalla fonte alla pagina pubblicata e poi rivisitata, gira da
solo e si fonde da solo. Non c'e' nessun punto in cui la catena aspetta che
qualcuno guardi: il controllo non e' un'approvazione, sono il perimetro, il
cancello e la suite, e girano tutti e tre senza di te.
