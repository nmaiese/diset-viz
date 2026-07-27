# Il contratto comune degli agenti

Ogni agente della catena (repo `nmaiese/diset-viz`) obbedisce a questo
contratto. I file in `.claude/agents/` dicono **che cosa** fa ciascuno, questo
dice **come** apre e chiude ogni run, e vale per tutti senza eccezioni.

Serve perche' gli agenti girano **a freddo**: sessione nuova a ogni firing,
nessuna memoria della volta prima. Tutto quello che sanno deve venire da file
committati, e tutto quello che fanno deve poter essere giudicato da chi legge il
diff sei mesi dopo.

## 1. Aprire: guarda la catena, non solo la tua casella

```bash
python3 scripts/pipeline_status.py --json
```

Un solo comando dice quanto e' in attesa in ognuno dei sette stadi e qual e' il
prossimo passo. Leggilo sempre per primo, anche quando la tua coda e' vuota:
serve a distinguere "non ho niente da fare perche' ho finito" da "non ho niente
da fare perche' e' fermo lo stadio sopra di me", che sono due situazioni opposte
e si somigliano molto.

Poi leggi la coda del tuo stadio, che e' quella che decide il lavoro.

**Non decidi tu quando girare.** Chi ti ha lanciato e' il dispatcher
(`scripts/pipeline_dispatch.py`), che gira a battito, guarda tutte le code e
lancia **un solo stadio per volta**. E' l'unica ragione per cui non ti trovi
mai un altro stadio addosso, quindi non lanciare mai un altro agente e non
"portarti avanti" su uno stadio che non e' il tuo: e' esattamente la
concorrenza che il dispatcher esiste per togliere.

Se il dispatcher ti ha passato un `run_id`, usalo. Se non ce l'hai, lo conia
`pipeline_log` al passo 4.

## 2. Lavorare: una cosa per volta, sempre motivata

- **Un blocco ragionevole per run.** Da tre a otto unita' di lavoro, non una e
  non cinquanta. Abbastanza da avanzare, abbastanza poco che un umano possa
  ancora controllare il tuo giudizio in una lettura.
- **Ogni decisione lascia una motivazione scritta** nel file di coda, con i
  numeri veri. Il cancello rifiuta le decisioni mute.
- **Nel dubbio, rimanda.** Una decisione sbagliata costa piu' di una decisione
  rinviata. `needs-info` con il dubbio scritto e' sempre una risposta accettabile.
- **Solo numeri reali**, riproducibili da un comando che hai lanciato tu. Mai
  inventare una cifra, mai inventare una fonte.
- **Non toccare mai** il cancello (`scripts/pipeline_gate.py`), i test, o la
  lista dei percorsi permessi. Se il cancello ti blocca, l'errore e' nel tuo
  lavoro. Un agente che allarga il proprio perimetro ha smesso di essere
  verificabile.

## 3. Chiudere: il cancello decide, non tu

Lavora su un branch dedicato (`automation/<stadio>-<YYYY-MM-DD>`), committa
**senza** il trailer `Co-Authored-By`, poi:

```bash
python3 scripts/pipeline_gate.py --stage <scout|hunter|promoter|curator|writer|reviewer|verificatore>
```

Il verdetto porta un `merge`. **Non eseguire tu il merge**: apri la pull request
e passa il numero al passo di merge, che rilegge il cancello per conto suo e
decide.

```bash
gh pr create --title "..." --body "..."
.venv/bin/python scripts/pipeline_merge.py --stage <stadio> --pr <numero> --run-id <il tuo run_id>
```

**Il `--run-id` non e' facoltativo in pratica.** E' l'unica cosa che lega la
riga che hai scritto tu, dentro la pull request, alla riga di esito che questo
passo scrivera' su master. Senza, le due restano due run separate nel diario, e
la domanda "che cosa ha fatto e come e' finita" torna a non avere risposta.

**L'interprete e' quello del venv, e non e' un dettaglio.** Il passo di merge
rilancia il cancello, e il cancello per verificare il vintage deve importare
l'app. Con `python3` di sistema non ci riesce, dichiara il vintage non
verificabile e rifiuta, che e' il verso giusto ma blocca ogni stadio che tocchi
un articolo. Lo scrittore in quel modo e' bloccato **sempre**: stesso branch,
stesso commit, `python3` da' `blocked` su `vintage` e `.venv/bin/python` da'
`auto`. Se il venv non c'e', crealo prima (`python3 -m venv .venv`), come gia'
serve per la suite.

| `merge` | che cosa fa il passo di merge |
| --- | --- |
| `auto` | fonde subito. E' prosa in un file solo, e la suite l'ha gia' girata il cancello |
| `checks` | **aspetta davvero** che ogni check remoto concluda, poi fonde. Se uno fallisce, rifiuta |
| `blocked` | non fonde niente. Correggi il lavoro e rilancia il cancello |

Non usare `gh pr merge --auto`. **Su questo repository non aspetta niente**:
`allow_auto_merge` e' falso e `master` non e' protetto, quindi `gh` ripiega su un
merge immediato. Una PR sonda e' stata fusa con il job dei test ancora in corso,
e per tutto il tempo in cui il contratto ha detto di usare quel comando i tre
stadi `checks` hanno fuso al buio credendo di aspettare. L'attesa vive dentro
`scripts/pipeline_merge.py`, dove si puo' leggere e testare.

La politica non e' uniforme, e il criterio e' il raggio d'azione:

- la prosa (`writer`, `reviewer`) sta in un file solo, non raggiunge nessun'altra
  pagina e si annulla con un commit,
- tutto il resto (`scout`, `hunter`, `promoter`, `curator`) muove numeri vivi o
  decide quale istituzione compare su una pagina pubblica, quindi non fonde
  finche' la CI non e' verde.

Nessuno stadio aspetta un umano. Se il tuo lavoro ha bisogno di una decisione che
non puoi prendere, il posto dove scriverla e' il corpo della PR e la riga di
diario, non un merge sospeso: **nessuno sta guardando**.

Se `blocked`, non aggirare mai il cancello disattivando un controllo o
modificando un test. Correggi il lavoro, oppure lascia il branch committato e
spiega perche' ti sei fermato.

## 3-bis. Se un altro stadio ha fuso prima di te

Prima questa sezione era lunga il doppio e spiegava come risolvere a mano tre
conflitti diversi. Quasi tutta e' sparita, perche' quei conflitti non esistono
piu': **ogni registro della catena e' uno store a un file per record**, e due
stadi che lavorano su cose diverse non toccano mai lo stesso percorso.

| store | un file per |
| --- | --- |
| `content/indicators/` | articolo |
| `data/pipeline/runs/` | run |
| `data/pipeline/verifiche/` | verifica |

Erano tre file unici a cui tutti appendevano in coda, quindi due run vicine
collidevano **sempre**, e la sezione che leggevi qui era una pagina di prosa per
rimediare a un difetto di formato.

**Un master che va avanti non ti riguarda piu'.** Il cancello non boccia piu'
un branch la cui base ha fatto altri commit: il diff si misura con i tre punti
(`base...HEAD`), che confrontano contro la base comune e restano esatti. Il
verdetto lo dice e basta:

```
[ok ] base: origin/master e' andata avanti senza questo branch
```

Era il difetto piu' costoso della catena. Ogni scrittura su master faceva
diventare rosse tutte le pull request aperte, il passo di merge scrive su master
anche quando **rifiuta**, quindi un rifiuto solo bastava a fermare tutti gli
altri stadi con un'accusa che non riguardava il loro lavoro.

Resta un solo caso che devi saper leggere, ed e' l'unico che significhi
qualcosa: **due stadi che hanno modificato lo stesso articolo**. Non lo puo'
risolvere una regola meccanica, quindi la regola sta qui sotto ed e' l'unico
controllo che esiste.

**`vintage` diverso: vince quello piu' alto, sempre.** Vuol dire che lo scrittore
ha aggiornato l'articolo su un anno nuovo mentre il revisore firmava quello
vecchio. La firma del revisore copre cifre che non esistono piu', quindi non vale
niente: tenere il lato firmato butterebbe via l'aggiornamento e, peggio,
lascerebbe un testo vecchio con `reviewed_vintage` che combacia, cioe' un
articolo che **risulta riletto e non torna mai in coda**. E' esattamente il
guasto che il rientro esiste per impedire. Quindi tieni il testo dello scrittore
e **non riportare `reviewed_at` ne' `reviewed_vintage` dal lato che hai scartato**:
lasciarli indietro e' ciò che rimette l'articolo in coda al revisore con il
segnale `rilettura`, che e' il comportamento giusto. Se il revisore aveva
corretto un errore vero, quella correzione non e' persa: e' un rilievo da
riportare nel corpo della PR, e il revisore la rifara' sul testo nuovo.

**`vintage` uguale: e' una scelta editoriale, e la fai.** Sono due versioni della
stessa frase sulle stesse cifre. Tieni quella del revisore, che e' una passata in
piu' sugli stessi dati, e **dichiara nel corpo della PR e nel diario che hai
scelto**, con l'altra versione scritta accanto. E' l'unico punto della catena in
cui un agente decide al posto di un altro, quindi e' anche l'unico che va
lasciato leggibile.

Nessuna guardia automatica vede una risoluzione sbagliata qui: il cancello
controlla che il `vintage` non superi i dati e che una revisione firmi qualcosa,
non che tu abbia tenuto il lato giusto. Questa regola e' l'unico controllo che
esiste.

Se il conflitto non e' su un articolo, non improvvisare: lascia il branch
committato, scrivi la riga di diario con esito `stopped` e di' quale file era.
Fermarsi e' un esito legittimo, indovinare no.

## 4. Registrare la run nel diario, sempre

Ultimo passo di ogni run, **anche quando non hai prodotto niente**:

```bash
python3 scripts/pipeline_log.py --write \
    --stage <stadio> --outcome <merged|pr-open|blocked|nothing|stopped|error> \
    --summary "una riga: che cosa hai fatto" \
    --detail "una riga per decisione, con i numeri veri" \
    --gate <il campo merge del verdetto> \
    --queue-before <quanto c'era> --queue-after <quanto resta>
```

Stampa un `run_id`. **Prendilo**: e' quello che passi al passo di merge, ed e'
l'unica cosa che lega questa riga a come andra' a finire. Non scrivere `--pr`:
quando scrivi la riga la pull request non esiste ancora, ed e' proprio per
questo che appaiare le due meta' sul numero non funzionava.

Il caso che conta di piu' e' `nothing`. Una Routine che gira e non produce
niente ha lo stesso aspetto di una Routine che non e' mai partita, ed e'
esattamente cosi' che lo scrittore ha lavorato per settimane su un file morto
senza che nessuno se ne accorgesse. La riga di diario e' l'unica cosa che
distingue "ho controllato e non c'era niente da fare" da "non sono partito".

**La tua riga descrive la tua run, non come e' finita la pull request**, e non e'
una sfumatura: quando la scrivi, come e' finita non lo sai ancora. La riga viaggia
dentro la PR, quindi va committata prima che la PR si fonda. Scrivi `pr-open` e
fermati li'.

**La riga con l'esito vero la scrive `pipeline_merge.py`**, che e' l'unico a
conoscerlo, e la scrive direttamente su master per ogni uscita terminale:
`merged`, `blocked`, `stopped`, `error`. Non provare a scriverla tu e non
aggiungerne una seconda dopo il merge. Due righe per run sono normali e attese:
la tua dentro la PR, la sua su master.

Serviva perche' il buco era doppio. Il cacciatore ha scritto `pr-open` e si e'
fuso trenta secondi dopo, e per mezza giornata il diario ha raccontato che
nessuno stadio `checks` si fosse mai chiuso da solo mentre la PR #45 diceva il
contrario. La meta' peggiore pero' e' l'altra: quando il cancello o i check
rifiutano, la tua riga resta su un branch che non si fonde mai, e **da master non
si vede affatto**. La run dello scout del 26 luglio esiste, dice `blocked`, e
vive su `automation/scout-2026-07-26` dove nessuno strumento la legge.

Il diario (`data/pipeline/runs/`) e' nel perimetro di ogni stadio, quindi la
tua riga viaggia insieme al tuo lavoro. Committala con il resto. Se ti sei
fermato o il cancello ti ha bloccato, scrivi comunque la riga e committala sul
branch: sono le run che serve di piu' poter leggere.

Il diario non puo' andare in conflitto. Ogni run scrive il proprio file, quindi
non c'e' un punto condiviso su cui due stadi possano scrivere insieme.

Alla riga si aggiungono da soli, quando l'ambiente li sa, i campi di
provenienza: `model`, `claude_code_version`, `session_id`, `duration_seconds`
e `base_commit`. Non li passi tu e non li inventi: `pipeline_log.py` li legge
dall'ambiente e dal meta di sessione che l'hook di avvio lascia in locale.
Esistono perche' una regressione di qualita' dopo un cambio di modello o di
runtime, senza di loro, non ha nessuna pista nel diario.

Chi legge, legge cosi':

```bash
python3 scripts/pipeline_log.py               # la timeline
python3 scripts/pipeline_dashboard.py --open  # tutto in una pagina
```

## 5. Non aprire PR vuote

Se la tua coda e' vuota, chiudi la run dicendo che cosa hai controllato e con
quale esito. Una PR vuota a settimana e' rumore che insegna a non leggere le PR.

## 6. Il perimetro, stadio per stadio

Scritto in `scripts/pipeline_gate.py:STAGE_PATHS`, che e' l'unica versione che
conta. Qui per comodita':

| stadio | puo' scrivere in |
| --- | --- |
| `scout` | `data/discovery/source_candidates.csv`, `config/istat_series.yaml` |
| `hunter` | `data/discovery/candidates.csv` |
| `promoter` | la coda piu' il layer esterno e il manifest |
| `curator` | `data/discovery/curation.csv`, layer esterno, manifest, descrizioni curate |
| `writer` | `content/indicators/` |
| `reviewer` | `content/indicators/` |
| `verificatore` | `data/pipeline/verifiche/`, **e non i testi** |

Ogni stadio puo' inoltre scrivere `data/pipeline/runs/`, il diario, e va
committato con il resto: un prompt che ti dice "il tuo perimetro e' una cosa
sola" sta riassumendo male.

Le voci che finiscono con una barra sono directory, e il perimetro le tratta
come prefissi. La barra e' quello che gli impedisce di allargarsi: dentro
`content/indicators/` puoi scrivere qualunque articolo, ma
`content/indicators-bozze/` e' fuori.

Tutto il resto e' fuori perimetro e fa fallire il cancello, compreso il codice
dell'app, i test e i documenti. Se ti accorgi che serve una modifica al codice,
**non farla**: scrivila nel corpo della PR come cosa che serve, e lascia che sia
un umano ad aprirla.

## 7. Regole del repo che valgono per tutti

- Non rompere `/legacy` ne' lo schema dati (`tests/test_app.py` li sorveglia).
- Mantenere la SEO tecnica: canonical, `noindex` sulle varianti, JSON-LD
  coerente con il visibile.
- Stile dei testi: `content/STYLE.md`, vincolante. Niente em-dash, en-dash,
  punto e virgola, carattere di ellissi.
- Messaggi di commit senza `Co-Authored-By`.
- Gli script della catena sono **stdlib puri**: girano senza il venv dell'app.
  Il venv serve per la suite, per le due code che leggono il view model e per il
  passo di merge, che rilancia il cancello e quindi eredita il suo bisogno di
  importare l'app. Stdlib puro vuol dire che gli script non importano niente di
  esterno, non che ogni controllo sia soddisfacibile senza l'app.
