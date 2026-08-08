# La catena autonoma

> **Chi possiede che cosa.** Quattro testi descrivevano la stessa catena, e
> `run_id`, `pipeline_gate`, `STAGE_PATHS`, il perimetro e il diario comparivano
> in tutti e quattro. Adesso ognuno possiede un soggetto e cita gli altri invece
> di ripeterli:
>
> | soggetto | dove sta |
> | --- | --- |
> | le regole sempre vere, che si caricano da sole | `.claude/rules/pipeline.md` |
> | che cosa fa la catena, perché, e che cosa manca | `docs/AUTONOMOUS_PIPELINE.md` |
> | come apre e chiude una run (run_id, worktree, diario, perimetro, merge) | `docs/AGENT_CONTRACT.md` |
> | come si scrive un articolo adesso | `.claude/workflows/produci-indicatori.js` e `officina/` |
>
> Se due di questi si contraddicono, ha ragione il codice. Se uno ripete l'altro,
> il duplicato va tolto, non aggiornato: è la lezione che questo repo ha già
> pagato una volta.

Come Divario Italia trova, verifica, cura, scrive, rilegge e pubblica un
indicatore **senza intervento umano**, e quali sono le tre cose che ancora lo
richiedono e perché.

Documento profondo. Per il contratto operativo che ogni agente segue a ogni run
vedi [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md); per lo strato dati sotto,
[`DATA_PIPELINE.md`](DATA_PIPELINE.md) e
[`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md); per l'anatomia di una pagina
indicatore, [`INDICATOR_PAGES.md`](INDICATOR_PAGES.md). Per il modello a pratica
editoriale che dà un nome all'indicatore-lungo-un-ciclo,
[`archive/EDITORIAL_PRACTICE.md`](archive/EDITORIAL_PRACTICE.md).

## L'obiettivo, detto per intero

Indicatori nuovi **senza intervento**, ma verificati e curati, con testi pronti e
corretti. Non "un agente che apre PR che qualcuno legge": una catena che porta
una serie da un catalogo SDMX a una pagina pubblica leggibile, e che poi ci
**torna sopra** quando i dati si muovono.

Le due metà contano allo stesso modo. Una catena che scopre e non rilegge
produce un archivio che invecchia in silenzio, e l'invecchiamento è peggio di
un buco: un buco si vede.

## I tre ruoli

La catena è passata da **sette stadi** a **tre ruoli**, e insieme da un'unità di
lavoro per **stadio** a un'unità di lavoro per **indicatore**. Non è un
rinominare: è che sette sessioni fredde che si passavano un indicatore via CSV
tenevano quell'indicatore peggio di quanto lo tenga una testa sola che lo porta
fino in fondo.

```
  ammissione                      produttore                 i due critici
  (scout+hunter+promoter+curator) (writer+reviewer)          verificatore: i fatti
  quali fonti, quali indicatori   due bozze -> giudizio       reader-editor: la prosa
  li promuove, ne cura il verso   cieco -> revisione -> lint
       |                               |                            |
  batch, l'intera coda            un indicatore alla volta    un articolo alla volta
       |                               |                            |
  data/discovery/*                content/indicators/         data/pipeline/verifiche/
                                  data/pipeline/runs/         data/pipeline/letture/
```

- **Ammissione** (agente `admissions`) scandaglia i cataloghi, decide quali
  fonti e quali indicatori entrano, e promuove ciò che approva. Fonde scout,
  cacciatore e promotore. Il suo passo distintivo è l'**auto-refutazione**:
  prima di scrivere "approvato" prova a demolire la propria approvazione ("come
  la faccio cadere?"), perché l'istituzione e la licenza che lascia passare
  finiscono su una pagina pubblica sotto il nome del progetto e nessuno legge la
  pull request prima del merge.
- **Produttore** (l'officina, `.claude/workflows/produci-indicatori.js`) porta
  **un** indicatore da ammesso a pubblicato: monta il pacchetto, fa scrivere due
  bozze dai due angoli più forti, le fa scegliere a due giudici ciechi, applica
  la diagnosi e chiude sul lint. Fonde scrittore e revisore. La **cura** sta a
  monte, con l'ammissione, che è il ruolo che ne ha i file nel perimetro. **Non è
  un agente**: quattro tipi stretti dentro un workflow fanno lo stesso lavoro a
  un ventesimo del costo, e il coordinamento dentro un workflow non costa token.
  Il passo distintivo è il **giudizio cieco**, non la rilettura sul proprio
  testo: chi ha appena scritto è il lettore peggiore del proprio testo, e due
  bozze confrontate da chi non ha il progetto in contesto dicono ciò che una
  sola rilettura non dice.
- **Verificatore** (agente `verificatore`) prova a falsificare ogni
  affermazione di un articolo firmato. È rimasto **invariato** nella
  ri-architettura, ed è l'unico ruolo che misura il lavoro di un altro ruolo
  invece dei dati. Non corregge niente: una smentita torna in coda al
  produttore, che ha assorbito il revisore.

- **Reader-editor** (agente `reader-editor`) è il quarto, arrivato dopo, ed è
  il gemello del verificatore su un altro asse: lui misura se i fatti reggono,
  questo se un lettore comune capisce la pagina al primo passaggio. Non corregge
  niente nemmeno lui, e a differenza degli altri è `soft`: accoda una
  riscrittura, non blocca nessun merge. La sezione "I tre ruoli" tiene il nome
  che aveva la ri-architettura, che ne fuse sette in tre; il reader-editor è
  nato dopo, e li porta a quattro.

Il verificatore è arrivato per ultimo fra i tre perché è servito misurarlo
prima di credergli. Una firma di chi si è riletto è la parola del produttore sul lavoro
del produttore, e finché nessuno provava a farla cadere quanto valesse non si
sapeva. Ora si sa:

| stato dell'articolo | affermazioni controllate | false | tasso |
| --- | --- | --- | --- |
| note migrate, mai rilette | 113 | 11 | 9,7% |
| scritte e non ancora rilette | 392 | 19 | 4,8% |
| scritte e rilette | 529 | 7 | 1,3% |

La rilettura toglie la gran parte degli errori e ne lascia qualcuno, e quel
qualcuno resta in pagina finché qualcosa non prova a farlo cadere. È il motivo
per cui il produttore si rilegge (passo interno) **e** il verificatore rilegge
di nuovo, indipendente, dopo la firma.

Ogni ruolo ha una **coda deterministica** calcolata da file committati. I tre
che sono **agenti** hanno anche un file di definizione in `.claude/agents/`, un
perimetro in `pipeline_gate.STAGE_PATHS` e un **verdetto del cancello** che
decide se possono pubblicare; il quarto, il produttore, è un workflow, non apre
una pull request e non ha un perimetro nel cancello, e il suo cancello è
editoriale (`officina/lint.py`).

Le code sono ancora quelle dei sette stadi (il vocabolario interno non cambia:
il produttore legge la coda dello scrittore e quella del revisore, l'ammissione
anche quella del curatore), ma chi le drena sono quattro ruoli, non sette. La
mappa da vecchio stadio a ruolo vivo sta in un posto solo,
`pipeline_launch.ROLE_OF_STAGE`, e `pipeline_status` e `pipeline_monitor` la
importano invece di ricopiarla.

| ruolo | chi lo esegue | coda | comando |
| --- | --- | --- | --- |
| ammissione | agente `admissions` | `source_candidates.csv`, `candidates.csv`, gli `approved`, `curate.worklist()` | `scripts/scout_sources.py`, `scripts/discover_candidates.py`, `scripts/promote_candidates.py`, `scripts/curate.py`, `scripts/apply_curation.py` |
| produttore | workflow `.claude/workflows/produci-indicatori.js` | `pending_notes` + `review_queue` | `scripts/pending_notes.py`, `scripts/review_queue.py` |
| verificatore | agente `verificatore` | `verification_queue` | `scripts/verification_queue.py` |
| reader-editor | agente `reader-editor` | `reading_queue` (i pubblicati che nessuno ha ancora letto) | `scripts/reading_queue.py` |

Il reader-editor è arrivato dopo gli altri tre e non compare in
`pipeline_status`, che ragiona ancora per **vecchio stadio**: la sua riga
`reviewer` è la coda del produttore, non questa. La coda di leggibilità si
legge dal suo comando, oppure dal piano (`pipeline_launch.py`), che invece
ragiona per ruolo e la elenca.

Un comando dice lo stato delle code per vecchio stadio:

```bash
python3 scripts/pipeline_status.py            # leggibile
python3 scripts/pipeline_status.py --json     # per un agente
```

Esiste per una ragione precisa. Ogni agente vede la propria casella e nient'altro,
quindi nessuno riesce a distinguere "sono fermo perché ho finito" da "sono fermo
perché è bloccato il ruolo sopra di me", che sono situazioni opposte e si
somigliano moltissimo. Ogni agente lo lancia per primo.

## Il lanciatore: che cosa lanciare, e quanto in parallelo

```bash
python3 scripts/pipeline_launch.py            # il piano, leggibile
python3 scripts/pipeline_launch.py --json     # per l'agente lanciatore
python3 scripts/pipeline_launch.py --top 3    # solo le prime tre voci
```

Il **dispatcher è ritirato**. `scripts/pipeline_dispatch.py` non esiste più.
Serializzava: un tick, uno stadio, il primo con lavoro in ordine di catena, e
rifiutava di partire finché una pull request della catena era ancora aperta.
Aveva senso quando l'unità di lavoro era lo **stadio** e sette stadi separati si
scrivevano addosso i registri condivisi: la concorrenza si eliminava non
gestendola. Ma quella forma congelava tutto. Una sola PR non chiusa fermava
l'intera catena, e due stadi che partivano vicini finivano in conflitto di merge.

Al suo posto c'è `scripts/pipeline_launch.py`, un **lanciatore per-indicatore**.
Non sceglie uno stadio: legge il dossier per-indicatore (`practice_timeline`) e
le code (`pipeline_status.queue_sizes`) e restituisce una **lista prioritizzata
di lanci**, ordinata per priorità e **tagliata alle prime tre voci per tick**
(`--max-parallel`, default 3; `--max-parallel 0` toglie il taglio, `--top N` lo
forza a N). Il taglio tiene basso il numero di ruoli che partono insieme senza
mai lasciare fuori la voce più urgente, perché agisce dopo l'ordinamento: una
smentita pubblica (peso 100) è sempre dentro. Le voci in eccesso aspettano il
tick dopo.

- **Produttore, verificatore e reader-editor sono per-indicatore.** Ogni
  indicatore pronto è una voce a sé, perché due produttori su due indicatori
  diversi toccano file diversi (un articolo per record) e non si toccano mai. La
  priorità viene dal dossier, la stessa di `stage_priorities`: una smentita su
  una pagina online (peso 100) apre il piano davanti a una candidatura nuova. Per
  il reader-editor la regola è anche la sua sicurezza: legge **l'articolo che il
  lanciatore gli passa e nessun altro**, così due letture aperte nello stesso
  tick scrivono file con nomi diversi. Una lettura che si scegliesse un lotto
  dalla coda sceglierebbe gli stessi articoli dell'altra, e la catena
  guadagnerebbe conflitti di merge e giudizi doppi.
- **L'ammissione è batch.** Una sessione triaga l'intera coda di fonti e
  candidati e promuove ciò che approva, quindi è una voce sola. La sua
  esistenza si legge dalle code pre-pratica (scout, hunter, promoter) più le
  pratiche in stato `proposta`.

**Niente più lock una-PR-aperta.** Indicatori diversi non contendono, quindi
non c'è niente da serializzare e niente da aspettare: il lanciatore elenca, e
chi esegue (l'agente lanciatore, o una persona) mette in volo in parallelo le
voci che il piano gli offre, fino al cap di tre per tick. Un blocco su un
indicatore malato non ferma un indicatore pronto e indipendente.

Come il dispatcher, non lancia lui l'agente, e non potrebbe: un agente è una
sessione Claude Code, il lanciatore è stdlib. Dice **che cosa** lanciare, con
ruolo e indicatore, e per i ruoli che aprono una run anche il `run_id` già
coniato: le voci `producer` non ne portano, perché l'officina non apre una pull
request e il diario rifiuterebbe quell'identificativo. Chi legge il piano (una
persona, o la Routine) fa il resto: **l'agente `launcher.md` non esiste più**,
era un workflow scritto in prosa. La decisione resta così deterministica e
verificabile da un test, l'esecuzione no.

Con `--publish` il lanciatore segna il **battito del lanciatore** nel diario: una
riga `launch` che `land_on_master` porta su master, così un tick vero lascia una
traccia anche quando non produce altro. Non è più una verifica del sito: quel
passo è stato rimosso quando il progetto ha ratificato **merge = pubblicazione**
(vedi [`archive/EDITORIAL_PRACTICE.md`](archive/EDITORIAL_PRACTICE.md), §8, e più sotto). Senza
`--publish` (come nei test e nelle ispezioni a mano) il lanciatore è di sola
lettura e non scrive niente.

## Gli store: perché i conflitti non esistono più

Tre registri della catena erano file unici a cui ogni stadio appendeva **in
fondo**. Due stadi che girano vicini scrivono nello stesso punto, quindi git
chiama conflitto quella che è solo la somma di due righe che non si
contraddicono. Adesso sono directory, un file per record:

| store | un file per | scritto da | committato |
| --- | --- | --- | --- |
| `content/indicators/` | articolo | l'officina | sì |
| `data/pipeline/runs/` | run | tutti i ruoli | sì |
| `data/pipeline/verifiche/` | verifica | verificatore | sì |
| `data/pipeline/letture/` | lettura di leggibilità | reader-editor | sì |
| `data/pipeline/practices/` | pratica (record di stato) | riconciliatore | sì |
| `data/pipeline/heartbeats/` | sessione in volo | ogni ruolo all'avvio | no (è il vivo) |

Non è una riduzione della probabilità di conflitto, è la sua rimozione: due
ruoli che lavorano su indicatori diversi non toccano lo stesso percorso, quindi
non c'è niente da fondere. Resta contendibile solo la modifica **allo stesso**
articolo, che è l'unico caso in cui un conflitto significa davvero qualcosa. È
proprio questa proprietà che permette al lanciatore di lanciare in parallelo
senza un lock.

Ne vengono due cose che non erano l'obiettivo e valgono quanto l'obiettivo. Il
diff di una run del produttore adesso è leggibile, perché dice di quali
articoli parla invece di mostrare hunk dentro mezzo megabyte di JSON. E
`git log content/indicators/920.json` è la storia editoriale di quella
pagina, che prima non esisteva.

Il perimetro del cancello capisce le directory: una voce di `STAGE_PATHS` che
finisce con una barra è un prefisso. La barra è ancorata di proposito, così
`content/indicators` non autorizza `content/indicators-bozze`.

## Il verificatore, e perché non ripara niente

`data/pipeline/verifiche/` è tutto quello che produce: un file per verifica,
con i quattro contatori e l'impronta della prosa che ha letto.

**Non ha `content/indicators/` nel perimetro**, e l'assenza è la definizione
del ruolo più che il suo prompt. Un ruolo che trova e ripara i propri rilievi
corregge i propri compiti, che è esattamente il difetto che esiste per prendere
un livello sopra. Quindi una smentita torna al produttore (che ha assorbito il
revisore), come il segnale `smentita` di `review_queue`, che pesa più di ogni
altro segnale di quella coda: tutti gli altri marcano una frase che *potrebbe*
essere sbagliata, quello marca una frase che qualcuno ha già fatto cadere, con
la prova, e che è ancora in pagina.

**Una verifica scade quando cambia il testo, non quando passa il tempo.** La riga
porta un'impronta della prosa, e l'articolo risulta verificato solo finché la sua
prosa hasha a quel valore. La prima versione confrontava `reviewed_at` con la data
della verifica ed è stata buttata: due eventi nello stesso giorno sono
indistinguibili, e il produttore che ripara una frase smentita firma il giorno in
cui il verificatore l'ha smentita. Con l'impronta non c'è aritmetica e non c'è
pareggio.

Le due code si passano il lavoro senza che nessuna cancelli una riga dell'altra:

```
  verificatore trova una smentita  ->  review_queue la mostra in cima
  il produttore riscrive la frase  ->  l'impronta cambia, la smentita e' spenta
  l'impronta cambia                ->  l'articolo torna in coda al verificatore
```

`affermazioni_controllate` è il campo che non si negozia, e il cancello lo
impone invece di ricordarlo: senza, "zero smentite" e "non ho guardato" producono
la stessa riga, e un ruolo che non sa distinguerle costa una pull request per
articolo e non garantisce niente.

### Il registro errori: il learning loop

Le smentite confermate non restano solo un rilievo su un articolo: diventano
memoria. `officina/brief.py`, che lo ha assorbito (la sola fonte dei numeri per il
produttore) ha una sezione **ERRORI NOTI**, una vista sulle smentite già
confermate in `data/pipeline/verifiche/` (`esito=smentito`), a **cerchi
concentrici**: prima quelle su **questo** indicatore, poi quelle della sua
**famiglia**, poi le **classi ricorrenti** che il verificatore ha etichettato
(`classe/gravita:` nel campo `rilievi`). Solo smentite confermate, mai una sfida
grezza: una falsa smentita non deve avvelenare il registro. Il produttore che
legge il brief prima di scrivere ci si rilegge più duro proprio sulle classi
che qui hanno già fatto cadere qualcosa, così un errore corretto una volta non
si ripresenta senza che nessuno lo sappia.

## Guardare la catena senza aprire file

Il **monitoraggio** è `scripts/pipeline_monitor.py`, e non è un secondo modello
di stato: è una **vista di lettura** sullo stesso dossier per-indicatore che
`practice_timeline` ricostruisce dagli artefatti committati. La domanda a cui
risponde è quella che prima costava sette comandi e una testa che li teneva
insieme: **dov'è fermo, e perché**.

```bash
python3 scripts/pipeline_monitor.py           # dov'è fermo, in una schermata
python3 scripts/pipeline_monitor.py --json    # per la rotta o un altro programma
```

È servito vivo dalla rotta Flask protetta **`/_pipeline`** (noindex sempre,
auto-refresh che si può mettere in pausa). La vista ha tre livelli. In testa ci
sono la frase di diagnosi e i numeri operativi: correzioni urgenti, azioni
pronte, sessioni vive e indicatori pubblicati. Subito sotto ci sono il flusso completo
**ammissione -> produzione -> verifica -> pubblicazione**, le sessioni e le PR
vive, e la coda prioritaria.

La sezione **"Tutti gli indicatori"** è il dossier leggibile. Ogni riga porta
nome, id, stato, avanzamento nelle quattro fasi, ultima attività e una prossima
azione espressa come gesto con il suo responsabile. Aprendola si vedono il
percorso completo degli eventi e tutte le run associate, inclusi esito, durata,
modello, trigger, PR, variazione della coda, token e motivazioni dettagliate.
Ricerca, filtri per fase, stato e prossimo responsabile, e ordinamenti per
priorità, attività, avanzamento o nome permettono di leggere tutto il catalogo
senza perdere il contesto. Filtri, schede aperte e pausa del refresh restano
memorizzati nella sessione del browser. La pagina pubblicata è collegata quando
l'articolo è fuso su master.
Se `PIPELINE_TOKEN` è impostato serve solo con `?token=` giusto, altrimenti 404
(non 403: una pagina interna non conferma nemmeno di esistere); vuoto, in locale,
è aperta. Si ricalcola a ogni caricamento dai file committati, non da uno stato
a parte.

Il **vivo** viene dai **battiti** (`data/pipeline/heartbeats/`, ignorati da git):
ogni ruolo scrive un file all'avvio della sua run e lo cancella alla chiusura, un
file per `run_id` così due ruoli in volo insieme non si sovrascrivono. È best
effort: se un ruolo non ha battuto il vivo tace, il committato no. Un battito
più vecchio della soglia si considera morto, una sessione caduta senza pulire.

Il **consumo token** è telemetria durevole, tenuta a parte dai battiti. Il
lanciatore è l'unico a vedere i `subagent_tokens` di ogni ruolo che lancia (il
ruolo, dentro la sua sessione, non conosce il proprio totale), quindi è lui a
POSTarli a `/_pipeline/beat` (azione `tokens`) chiavati sul `run_id` del ruolo:
finiscono in una tabella dedicata dello **stesso** SQLite replicato su GCS, che
**non scade** come un battito. Il cruscotto li somma per indicatore e li mostra
per step. È **solo in avanti**: le run precedenti a questa telemetria non hanno
un totale e non c'è backfill (i token delle run passate non esistono da nessuna
parte).

Il **diario** (`data/pipeline/runs/`) è la storia. Prima l'unico segno che una
run fosse avvenuta era il commit che produceva: una run che non produce niente,
perché la coda è vuota o perché il cancello l'ha bloccata, non lasciava
assolutamente nulla. Il che significa che **una Routine che gira a vuoto ha lo
stesso aspetto di una Routine che non è mai partita**, ed è esattamente così
che lo scrittore ha lavorato per settimane su un file morto. Ora ogni ruolo ci
scrive una riga a fine run, sempre, con l'esito preso da un vocabolario corto
(`merged`, `pr-open`, `blocked`, `nothing`, `stopped`, `error`), che cosa ha
deciso e che cosa ha detto il cancello. È committato, quindi la storia
sopravvive alla sessione, ed è un file per run, quindi due run concorrenti non
si contendono nessun percorso. Sta nel perimetro di **tutti** i ruoli: senza,
metà delle run non lo raggiungerebbe.

Ogni riga porta un **`run_id`**, ed è quello che risponde alla domanda "chi ha
fatto cosa". Una run lascia due righe, la propria dentro la pull request e quella
di esito che il passo di merge scrive su master, e prima si univano su
`(stadio, pr)`. Non poteva funzionare: la riga dell'agente viaggia dentro la pull
request, quindi va committata **prima** che la pull request esista, quindi non ne
può portare il numero. Il `run_id` lo conia il lanciatore quando decide il lancio
e non dipende da niente che succeda dopo.

Restano due comandi più vecchi, ancora validi:

```bash
python3 scripts/pipeline_log.py               # che cosa hanno fatto gli agenti
python3 scripts/pipeline_dashboard.py --open  # una pagina HTML autonoma, offline
```

Il cruscotto HTML è una fotografia da file, comoda offline; il monitoraggio
vivo, con la headline e i battiti, è `/_pipeline`.

## Il cancello: cosa rende sicuro togliere l'umano

`scripts/pipeline_gate.py` è il punto in cui ogni ruolo chiude. Non è una
formalità: è la cosa che sta fra "autonomo" e "autonomamente sbagliato su
scala". Restituisce un verdetto calcolato dal diff e dalla suite, mai
dall'opinione che l'agente ha del proprio lavoro.

```bash
python3 scripts/pipeline_gate.py --stage verificatore
```

**Gli stadi che il cancello conosce sono tre**, uno per agente esistente:
`admissions`, `verificatore`, `reader-editor`. Erano dieci, e sette
appartenevano a ruoli cancellati: un perimetro senza un agente non è inerte, è
un permesso che resta aperto. L'officina non è fra loro e non è una
dimenticanza: non è una run, non apre pull request, e il suo cancello è
`officina/lint.py`. Il cancello controlla, in ordine di danno:

1. **Il perimetro.** Ogni ruolo può toccare una lista corta di file, scritta in
   `STAGE_PATHS`. Un prompt si può modificare, fraintendere o ignorare, il repo
   no: un produttore che si mette a "sistemare" `app/views.py` fallisce qui,
   prima che qualcuno legga il suo ragionamento. È questo controllo a rendere
   automatizzabili gli altri. La guardia per-agente (`scripts/agent_guard.py`,
   dichiarata nel frontmatter di ogni agente) applica lo stesso perimetro al
   momento del gesto, PreToolUse per PreToolUse.
2. **La suite intera**, non il sottoinsieme preferito del ruolo. Le guardie su
   prosa, deriva del vintage, cifre attribuite a una regione, schema CSV e
   `/legacy` sono la memoria accumulata di tutto quello che qui è già andato
   storto.
3. **Gli invarianti sul diff**, che la suite non può vedere perché riguardano
   il cambiamento e non lo stato: una decisione di triage senza motivazione
   scritta, un'approvazione sotto la copertura minima o senza licenza,
   `score_eligible=true` su un verso non direzionale, una revisione che non firma
   niente, un `vintage` oltre i dati.
4. **L'igiene**: whitespace, e il trailer `Co-Authored-By` che CLAUDE.md vieta.

I test in `tests/integration/test_pipeline_gate.py` costruiscono **prima l'input cattivo** e
verificano che il cancello rifiuti. Un cancello che ha sempre risposto verde non
è un cancello.

## La politica di merge: adesso è uniforme, e perché

Il verdetto porta un campo `merge`, che è l'ordine. **Oggi ogni ruolo fonde
`auto`**, sul cancello locale, ed è un cambiamento rispetto a prima, quando la
prosa fondeva da sola ma promozione, curatela e ammissione di una fonte
aspettavano i check remoti (`checks`).

La ragione è un deadlock scoperto sul campo. La CI remota **non parte** sulle
pull request aperte via il GitHub MCP: GitHub non gira i workflow per un evento a
token d'app, quindi i check non compaiono mai. Il passo di merge rifiutava
(correttamente) uno stadio `checks` i cui check non arrivavano, la pull request
restava `pr-open` per sempre, e il vecchio dispatcher rifiutava di lanciare
qualsiasi cosa finché una PR della catena era aperta. Una sola PR incagliata
congelava l'intera catena. `checks` non comprava nessun verdetto remoto
indipendente, solo un blocco.

Il cancello locale tiene la garanzia vera al posto suo: gira la stessa suite che
il job `python` della CI gira, più il perimetro che il job `gate` della CI gira,
e la gira **prima** del merge invece che mai. Un verde `auto` è un cambiamento
di cui la catena ha già misurato tutto quello che sa misurare. `checks` resta
una parola che il cancello sa ancora dire, e l'attesa vive ancora in
`pipeline_merge.py`, ma nessun ruolo la usa oggi: se un domani la CI remota
venisse fatta partire su queste PR, gli stadi che muovono numeri (scout, hunter,
promoter, curator, verificatore) sono quelli da riportare a `checks`.

**Nessun ruolo è `manual`.** Lo scout lo era, ed era il tappo: la scoperta di
indicatori nuovi si fermava alla sua pull request e non ripartiva finché un
umano non la guardava. In una catena non presidiata "aspetta una firma" vuol dire
"aspetta per sempre", quindi il controllo si è spostato dove può girare da solo,
cioè nella suite. `tests/unit/test_source_admission.py` rifiuta una riga di fonte a cui
manchi un campo, con un verso sconosciuto, con una categoria inesistente o con un
tema che nessuno ha mappato, che è il guasto più silenzioso di tutti:
l'indicatore resta in catalogo e sparisce da ogni totale per macro-area.

### L'attesa dei check è codice, non un flag

`gh pr merge --auto` **non aspetta niente su questo repository**. Con
`allow_auto_merge` a falso e `master` non protetto, `gh` ripiega su un merge
immediato: una PR sonda è stata fusa con il job dei test ancora `IN_PROGRESS`.
Per questo l'attesa (per il giorno in cui `checks` tornerà attivo) vive in
`scripts/pipeline_merge.py`, che rilegge il cancello per conto suo (non si fida
del rapporto dell'agente sul proprio verdetto), sonda i check finché non
concludono, e rifiuta se uno fallisce, se non ne compare nessuno, o se il cancello
è rosso.

### E parla REST, non GraphQL

Lo stesso script chiedeva i check con `gh pr checks` e fondeva con `gh pr merge`,
che sono GraphQL tutti e due. GraphQL però non c'è sempre: una sessione dietro
il proxy di uscita ha risposto a ogni chiamata REST su questo repository e ha
rifiutato l'endpoint GraphQL con `HTTP 403: This GraphQL query is not enabled for
this session`. Il passo di merge lo vedeva come un comando fallito e basta, senza
un indizio sul perché, e un ruolo che non sa chiudersi non si distingue da uno
che ha deciso di non chiudersi.

Adesso passa da `gh api`, cioè dalla REST, che è la superficie più piccola e
più vecchia: per un passo il cui unico mestiere è essere affidabile, è la
scelta giusta anche a proxy spento. Tre conseguenze che vale la pena conoscere:

- **`owner/repo` se lo ricava da solo** (`repo_slug`). Il proxy riscrive `origin`
  in un URL su `127.0.0.1`, e davanti a quello `gh` dice "none of the git remotes
  point to a known GitHub host" e si ferma. Gli ultimi due segmenti del percorso
  però sono ancora owner e repo. `GH_REPO` **è ignorato**, non è più un
  override: da environment ereditato faceva aprire o fondere la PR sul repo
  sbagliato (o fallire perché lì il branch non esiste), ed erano i rifiuti
  orfani "il cancello è rosso" su master. Chiedere agli agenti di non impostarlo
  non bastava se l'ambiente lo conservava, quindi il percorso automatico lo
  ignora del tutto e ricava lo slug sempre dal remote. Per la stessa ragione
  **anche la PR si apre via REST** (`pipeline_merge.py --open`, `create_pr`), non
  con `gh pr create` (GraphQL, cieco al remote proxato).
- **La classificazione dei check è nostra** (`_bucket`). REST non ha il `bucket`
  di `gh`, quindi lo ricostruiamo dalle conclusioni grezze, con lo stesso
  vocabolario di prima. Davanti a una conclusione che non conosciamo il verso di
  default è `fail`: rifiutare costa una PR da rilanciare, passare fonde alla
  cieca. Si leggono anche le vecchie commit status, non solo le check run.
- **Fondere e cancellare il branch sono due chiamate**, non più un flag solo. La
  seconda non può disfare la prima: se il branch non si cancella il merge resta
  fatto, e lo si dice invece di scrivere `error` su una PR che si è fusa.

## La pubblicazione: il merge, non un passo a sé

Il progetto ha ratificato **merge = pubblicazione**: un articolo fuso su master
**è** pubblicato. Prima la catena teneva distinti il merge e la pubblicazione,
con uno stato `fusa` in mezzo e una verifica del sito che portava da `fusa` a
`pubblicata`. Quella macchina è stata **rimossa**: `scripts/verify_publication.py`,
il registro delle prove in `data/pipeline/pubblicazioni/`, lo stadio `publisher`
del cancello e la transizione `fusa -> pubblicata` non esistono più. Lo stato
`pubblicata` si raggiunge al merge, per costruzione.

Il compromesso è dichiarato, non nascosto (vedi
[`archive/EDITORIAL_PRACTICE.md`](archive/EDITORIAL_PRACTICE.md), §8): "repo avanti / sito
indietro" non è più osservabile dalla catena. Il deploy segue il merge (un push
su master ridispiega il sito), ma se fallisce in silenzio il cruscotto continua a
dire `pubblicata`. In cambio la catena toglie una macchina intera e lo stato
diventa deterministico, letto dal solo fatto che l'articolo è su master.

Il flag `--publish` del lanciatore **resta**, ma non fa più la verifica del sito:
segna solo il **battito del lanciatore** nel diario, una riga `launch` che
`land_on_master` porta su master così un tick vero lascia una traccia anche
quando non produce altro. `land_on_master` mette file **nuovi** su master da
qualsiasi branch, costruendo un commit sopra `origin/master` che contiene **solo**
quei file (un indice temporaneo seminato da `origin/master` più i soli percorsi
da scrivere): l'invariante "non spinge altro che se stesso" vale per costruzione,
non per guardia. Chi perde la corsa del push si ricostruisce sopra il master
aggiornato e ritenta.

La **verifica del contenuto** è un'altra cosa e resta intatta: il verificatore
prova a smentire le affermazioni della prosa contro i dati, su file committati,
**prima** del merge. È editoriale, non è la verifica del sito che è stata
rimossa.

## Il rientro: la catena lavora anche sul pubblicato

È la metà che mancava. Prima ogni stadio drenava la propria coda una volta e
poi restava fermo per sempre, il che faceva sembrare la catena finita mentre il
catalogo invecchiava sotto. Oggi i tre innesco sono gli stessi, ma li drenano i
tre ruoli:

**Ammissione, lato cataloghi.** La coda dello scout riflette lo stato del
catalogo (vedi sotto), non un troncamento.

**Ammissione, lato curatela**, ed è il suo rientro sul pubblicato.
`curation.csv` porta `data_year`, l'anno su cui il verso è stato giudicato.
Quando la fonte ne pubblica uno più recente, l'indicatore rientra in `recheck`.
Un verso è un'affermazione su quale estremo della classifica sia quello buono,
ed è esattamente ciò che una ridefinizione, un rebase o una rottura di serie
possono invertire.

**Produttore, lato testo.** Ha `stale` in `pending_notes` e `text_queue` (un
articolo il cui `vintage` è rimasto indietro) e, dopo un rinfresco,
l'articolo porta `reviewed_vintage`, il `vintage` che era stato firmato: quando
le cifre cambiano i due valori smettono di combaciare e l'articolo torna in coda
con il segnale `rilettura`, che pesa più di ogni segnale di rischio. Riscrivere
l'articolo su un anno nuovo e non ri-firmarlo è proprio ciò che lo rimette in
coda per la rilettura.

**Verificatore.** Rientra quando l'impronta della prosa cambia (§verificatore): un
articolo riscritto torna da provare a smentire.

In tutti l'innesco sono **i dati, mai il calendario**. Rileggere tutto ogni N
mesi riporterebbe la deriva già corretta una volta, cioè un indicatore
contestuale che si ripresenta per sempre perché `score_eligible` resta `false`
per definizione (vedi il docstring di `curate.uncurated_targets`).

## Far crescere il bacino senza scrivere codice

L'ammissione si esaurisce nel momento in cui le fonti cablate smettono di
crescere, ed è esattamente cosa era successo con il vecchio cacciatore: cinque
serie cablate, cinque trovate, niente altro da scoprire. Due file rompono quel
tetto, e sono entrambi **dati** dentro il perimetro di un agente:

- `config/istat_series.yaml` (ammissione): una riga = un indicatore Istat SDMX.
  `dataflow` è un campo per serie, non più una costante di modulo, quindi un
  dominio nuovo non richiede un adapter nuovo.
- `config/theme_categories.csv` (ammissione): la mappa tema -> categoria. Un tema
  che il catalogo non conosce fa sparire l'indicatore dai totali per macro-area
  pur lasciandolo in catalogo, cioè un buco silenzioso, e la correzione stava
  dentro `app/taxonomy.py`, un modulo Python.

C'era però un tappo a monte di quei due file: lo **scout** (oggi dentro
l'ammissione) proponeva al massimo 40 fonti per run (`scout_sources.py --limit
40` di default) e, con un punteggio uniforme, l'ordinamento cadeva sull'alfabeto.
Su un catalogo di quasi 5000 dataflow proponeva sempre gli stessi 40, quindi
decine di domini regionali nuovi (turismo, occupazione per settore, reddito,
popolazione per titolo di studio, giustizia) restavano invisibili e la coda
appariva vuota mentre non lo era. Adesso il tetto è tolto (proposte senza cap) e
la query del catalogo, che è cache-forever, si ri-sonda con `--refresh`: così
l'ammissione vede i dataflow che Istat pubblica dopo l'ultima run, e la scoperta
non si ferma alla prima fotografia.

Resta codice, e quindi resta umano: un adapter per una fonte che **non** è un
dataflow SDMX Istat, e l'invenzione di una **categoria** nuova (che è una
sezione del sito con un nome e una descrizione, non una riga).

## Le Routine

Gli agenti girano come Routine Claude Code: sessione nuova a ogni firing,
checkout git proprio, nessuna memoria della volta prima. Si gestiscono su
<https://claude.ai/code/routines>. Gli id correnti stanno in
[`DISCOVERY_STATUS.md`](DISCOVERY_STATUS.md).

Il prompt di una Routine **non riproduce il contratto**, lo indica. È la lezione
più cara di questo sistema: la Routine dello scrittore riproduceva il proprio
contratto per intero, il repo è andato avanti, e per settimane l'agente ha
scritto in `analyst_notes.json`, un file che l'app non legge più. Girava, non
falliva, e non arrivava in nessuna pagina. Un prompt che ricopia una regola va
fuori sincrono senza che nessuno se ne accorga, un prompt che punta a un file no.

**La Routine è una sola**, ed è quella del **lanciatore**: i ruoli non hanno un
cron proprio. Il lanciatore non è più un agente, è uno script che si legge e
un piano che si lancia (vedi `.claude/rules/pipeline.md`). La Routine legge
`scripts/pipeline_launch.py --json --publish --publish-base https://divarioitalia.it`,
segna il battito del lanciatore nel diario, poi mette in volo le voci in cima al
piano **in parallelo**. A differenza del dispatcher non ne lancia una sola:
indicatori diversi non contendono.

**Come si lancia una voce lo dice la voce**, e sono due forme, non una:

- `agent` valorizzato: è una sessione Claude Code (`Agent`, più d'uno nello
  stesso messaggio), con il suo `run_id` e il suo indicatore.
- `agent: null`: è un **workflow**, e la voce porta già il comando in
  `comando`. Non ha un `run_id`, e non è una dimenticanza: l'officina non apre
  una pull request e non scrive nel diario, quindi non è una run (vedi
  `plan_launches`). Una Routine che lanciasse solo `Agent`, o che pretendesse un
  `run_id` da ogni voce, lascerebbe le voci `producer` a terra e la coda della
  scrittura non si drenerebbe mai.

Il prompt della Routine è un puntatore a questa definizione, mai una copia.

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
python3 scripts/pipeline_monitor.py         # dov'è fermo, e perché (la headline)
python3 scripts/pipeline_launch.py          # che cosa dovrebbe partire adesso
python3 scripts/pipeline_gate.py --stage <ruolo> --json    # perché è bloccata
```

Sintomi ricorrenti e cosa significano davvero:

- **La catena non fa più niente.** Guarda per prima cosa la storia recente nel
  monitoraggio (o `pipeline_log.py`). Se nessun ruolo registra da giorni il
  problema è la Routine del lanciatore, non i ruoli: nessuno sta lanciando il
  lavoro.
- **Un ruolo non apre PR da settimane.** Guarda il monitoraggio: se la sua coda
  è a zero non è fermo, è in pari, e il diario lo distingue.
- **Il cancello blocca su `blast-radius`.** L'agente ha toccato un file fuori
  perimetro. Non allargare il perimetro: quasi sempre significa che ha provato a
  risolvere in codice un problema che andava riportato.
- **Un indicatore rientra in `recheck` a ogni run.** Manca `data_year` nella sua
  riga di `curation.csv`. Scriverlo una volta chiude il ciclo.
- **Un articolo rientra in `rilettura` a ogni run.** Manca `reviewed_vintage`. La
  suite lo fa fallire apposta, invece di lasciarlo silenzioso.
- **Un indicatore è in catalogo ma sparito dai totali per macro-area.** Il suo
  tema non è mappato: una riga in `config/theme_categories.csv`.

## Cosa resta umano, e perché

Due cose, e nessuna delle due è un'approvazione:

1. **Scrivere un adapter** per una fonte che non è un dataflow SDMX Istat.
   È codice, e nessun agente scrive codice. L'ammissione che approva una fonte
   del genere lo dice nella PR e descrive che adapter servirebbe.
2. **Creare una categoria** della qualità della vita. È una sezione del sito,
   con un nome, una descrizione e una macro-area, non una riga di CSV. Mappare
   un tema a una categoria che già esiste invece è dell'**ammissione**, che ha
   `config/theme_categories.csv` nel proprio perimetro, e non è codice: quel
   CSV ha le colonne `added_by` e `added_at` perché lo scriva la catena.

Tutto il resto, dalla fonte alla pagina pubblicata e poi rivisitata, gira da
solo e si fonde da solo. Non c'è nessun punto in cui la catena aspetta che
qualcuno guardi: il controllo non è un'approvazione, sono il perimetro, il
cancello e la suite, e girano tutti e tre senza di te.
