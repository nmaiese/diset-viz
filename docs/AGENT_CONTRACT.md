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

Un solo comando dice quanto e' in attesa in ognuno dei sei stadi e qual e' il
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
python3 scripts/pipeline_gate.py --stage <scout|hunter|promoter|curator|writer|reviewer>
```

Il verdetto porta un `merge`, e quello e' l'ordine:

| `merge` | che cosa fai |
| --- | --- |
| `auto` | apri la PR e falla merge subito: `gh pr merge --squash --delete-branch` |
| `checks` | apri la PR e lascia che i check remoti la chiudano: `gh pr merge --auto --squash --delete-branch` |
| `manual` | apri la PR e **fermati**. Spiega nel corpo cosa deve decidere un umano |
| `blocked` | **non aprire nessun merge.** Correggi il tuo lavoro e rilancia il cancello |

La politica non e' uniforme e il motivo e' il raggio d'azione, non la fiducia:

- la prosa (`writer`, `reviewer`) sta in un file solo, non raggiunge nessun'altra
  pagina e si annulla con un commit,
- la curatela e la promozione (`curator`, `hunter`, `promoter`) muovono numeri
  vivi, cioe' il punteggio qualita' della vita e il catalogo, quindi passano dai
  check remoti,
- ammettere una **fonte** (`scout`) decide quale istituzione, quale licenza e
  quale nome legge un utente su una pagina pubblica. Quella resta una firma
  umana.

Se `blocked`, non aggirare mai il cancello disattivando un controllo o
modificando un test. Correggi il lavoro, oppure lascia il branch committato e
spiega perche' ti sei fermato.

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

Ogni stadio puo' inoltre scrivere `data/pipeline/runs.jsonl`, il diario.

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
