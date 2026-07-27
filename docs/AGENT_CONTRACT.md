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
python3 scripts/pipeline_merge.py --stage <stadio> --pr <numero>
```

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

Succede, e con Routine giornaliere succede spesso. Non e' un guasto ed e' l'unico
caso in cui il cancello ti accusa di una cosa che non hai fatto. Riconoscilo dal
verdetto:

```
[NO ] base: la base 'origin/master' non e' un antenato di HEAD
```

Quando c'e' quella riga, **tutte le righe rosse sotto sono finzione**: il diff
misurato non e' il tuo lavoro, e' il tuo lavoro piu' tutto quello che master ha
fatto senza di te. Il verificatore in particolare si vede accusare di aver
cancellato righe di `verifiche.csv` che non ha mai avuto davanti. Non correggere
niente sulla scorta di quel verdetto: e' l'errore che il verdetto stesso ti dice
di non fare.

Si esce in tre comandi, e sono sempre gli stessi tre:

```bash
git fetch origin master
git merge origin/master        # risolvi, vedi sotto
python3 scripts/pipeline_gate.py --stage <stadio>
```

**I due registri in coda si risolvono tenendo tutte e due le parti**, sempre, e
senza pensarci: `data/pipeline/runs.jsonl` e `data/pipeline/verifiche.csv`. Sono
file a cui si aggiunge in fondo, quindi due stadi che girano vicini scrivono
nello stesso punto e git chiama conflitto quello che e' solo la somma di due
righe. Nessuna delle due e' sbagliata e nessuna sostituisce l'altra: **scegliere
e' l'unico errore possibile**, e su `verifiche.csv` e' anche una violazione del
tuo stesso cancello, che il registro lo pretende append-only.

`app/static/data/indicator_texts.json` e' un caso diverso e riguarda solo
scrittore e revisore. Su articoli diversi git fonde da solo e non vedi niente. Sullo
**stesso** articolo il conflitto e' vero e nessuna regola meccanica lo risolve,
perche' sono due versioni della stessa frase: tieni quella del revisore se il
revisore ha firmato, altrimenti la piu' recente, e **dichiara nel corpo della PR
e nel diario che hai scelto**, con l'altra versione scritta accanto. E' l'unico
punto della catena in cui un agente decide al posto di un altro, quindi e' anche
l'unico che va lasciato leggibile.

Se il conflitto non e' in nessuno di questi file, non improvvisare: lascia il
branch committato, scrivi la riga di diario con esito `stopped` e di' quale file
era. Fermarsi e' un esito legittimo, indovinare no.

## 4. Registrare la run nel diario, sempre

Ultimo passo di ogni run, **anche quando non hai prodotto niente**:

```bash
python3 scripts/pipeline_log.py --write \
    --stage <stadio> --outcome <merged|pr-open|blocked|nothing|stopped|error> \
    --summary "una riga: che cosa hai fatto" \
    --detail "una riga per decisione, con i numeri veri" \
    --gate <il campo merge del verdetto> --pr <numero, se l'hai aperta>
```

Il caso che conta di piu' e' `nothing`. Una Routine che gira e non produce
niente ha lo stesso aspetto di una Routine che non e' mai partita, ed e'
esattamente cosi' che lo scrittore ha lavorato per settimane su un file morto
senza che nessuno se ne accorgesse. La riga di diario e' l'unica cosa che
distingue "ho controllato e non c'era niente da fare" da "non sono partito".

Il diario (`data/pipeline/runs.jsonl`) e' nel perimetro di ogni stadio, quindi
la riga viaggia insieme al tuo lavoro. Committala con il resto. Se ti sei
fermato o il cancello ti ha bloccato, scrivi comunque la riga e committala sul
branch: sono le run che serve di piu' poter leggere.

Se git segnala un conflitto su `runs.jsonl`, tieni tutte e due le righe: e' il
passo 3-bis, che vale identico per `verifiche.csv` e spiega anche il verdetto
rosso che vedrai prima.

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
| `writer` | `app/static/data/indicator_texts.json` |
| `reviewer` | `app/static/data/indicator_texts.json` |
| `verificatore` | `data/pipeline/verifiche.csv`, **e non i testi** |

Ogni stadio puo' inoltre scrivere `data/pipeline/runs.jsonl`, il diario. Sono due
file, non uno: un prompt che ti dice "il tuo perimetro e' un file solo" sta
riassumendo male, e il diario va committato con il resto.

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
  Il venv serve solo per la suite e per le due code che leggono il view model.
