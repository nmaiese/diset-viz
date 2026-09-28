# Orca e GitHub per un team editoriale multi-agente

Stato: design operativo, non automazione attiva. Repository: `nmaiese/diset-viz`,
branch predefinito `master`. Tutti gli esempi usano `orca-ide`, mai `orca` in
WSL. Questo documento non autorizza merge o deploy automatici.

## 1. Flusso completo di un indicatore

### Issue, Gate A e label

Team leader apre una issue prima di creare risorse Orca. Issue form proposto:
`.github/ISSUE_TEMPLATE/indicatore-team.yml`, con campi obbligatori:

- ID e slug indicatore, URL pubblico se esiste
- domanda editoriale e pubblico
- fonti primarie ammesse, periodo e territorio
- file attesi per testo e grafica
- criteri misurabili, comandi di verifica e casi da non cambiare
- rischi noti, stato Gate A e decisione umana richiesta

Titolo consigliato: `Indicatore <ID>: <domanda editoriale>`. Corpo minimo:

```markdown
### Intent
[tesi o domanda, senza anticipare una conclusione]

### Dati e fonti
- Dataset:
- Periodo:
- Territorio:
- Fonti esterne ammesse:

### Output posseduti
- Testo: `content/indicators/<id>.md`
- Grafica: `<percorsi esatti>`

### Accettazione
- [ ] cifre riproducibili dai dati
- [ ] fonti e link verificati
- [ ] test repository verdi
- [ ] Gate B umano prima del merge
```

Le label esistenti bastano e vanno riusate, senza crearne sinonimi:

| Label | Uso |
|---|---|
| `run:team` | Permanente per issue e PR prodotte da questa regia |
| `gate-a` | Intent in attesa di approvazione. Si rimuove quando il team leader autorizza il lavoro |
| `gate-b` | Draft completo in attesa del giudizio umano pre-merge |
| `bocciata` | Gate A o Gate B respinto. Non equivale a errore tecnico |
| `corretta-prima-del-merge` | Review ha imposto almeno una correzione prima della pubblicazione |
| `difetto-pubblicato` | Solo difetto scoperto dopo un merge già pubblicato |
| `canary` | Solo run dichiarata esperimento. Non è label generica del team |

Esempio GitHub CLI. Il file del corpo va preparato dal team leader:

```bash
gh issue create --repo nmaiese/diset-viz \
  --title "Indicatore TER-105: <domanda editoriale>" \
  --body-file /tmp/ter-105-issue.md \
  --label "run:team,gate-a"
```

Nessun lavoro editoriale parte prima della decisione Gate A. Dopo approvazione:

```bash
export ISSUE=123
export SLUG="${ISSUE}-ter-105-team"
export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python
gh issue edit "$ISSUE" --repo nmaiese/diset-viz --remove-label gate-a
```

### Worktree Orca collegato alla issue

Percorso compatibile con gli script attuali: il dispatcher crea checkout,
branch, primo terminale agente e `TASK.md`, poi `worktree set` registra il
collegamento GitHub. Le create si lanciano in sequenza.

```bash
bin/py scripts/orca_dispatch.py "$SLUG" \
  --title "Indicatore TER-105, run team" \
  --objective "Produrre testo e grafica verificati per la issue #$ISSUE" \
  --role worker
orca-ide worktree set --worktree "name:$SLUG" --issue "$ISSUE" \
  --comment "Gate A approvato; run team avviata" \
  --workspace-status in-progress --json
orca-ide worktree show --worktree "issue:$ISSUE" --json
```

Il primo Codex creato dal dispatcher è coordinatore/integratore del worktree.
Non modifica contenuti mentre un worker mutante possiede il checkout. In una
futura estensione, `scripts/orca_dispatch.py --issue <numero>` potrà rendere
atomici i primi due comandi. Fino ad allora, risposta JSON di `worktree set` e
`worktree show` è la prova del collegamento.

### Grafo Orca

Grafo logico:

```text
Gate A
  |
scout
  |\
  | +--> grafico --------+
  +----> scrittore -------+--> integrazione + draft PR
                                      |
                         revisore Orca separato
                           /                 \
              request changes             chiaro
                    |                        |
    riparazione nel worktree origine      Gate B umano
                    |
         push --> nuovo revisore
```

- `scout`: sola lettura. Restituisce dataset, cifre, fonti, rischi e query
  riproducibili.
- `scrittore`: dipende da `scout`. Possiede solo testo e metadati assegnati.
- `grafico`: dipende da `scout`. Possiede solo asset e configurazione grafica
  assegnati.
- `revisore`: nasce solo dopo la draft PR, in un nuovo worktree basato sul ramo
  PR. Usa modello diverso da chi ha scritto, resta in sola lettura, esegue test
  e pubblica rilievi localizzati su PR e issue.
- `riparazione`: task creato solo se il revisore trova difetti. Torna al
  proprietario del file nel worktree indicatore, poi richiede un nuovo
  revisore Orca separato.

`scrittore` e `grafico` sono pronti nella stessa wave. Possono lavorare davvero
in parallelo solo con ownership disgiunta applicata come descritto nella sezione
2. Profilo predefinito su WSL da 8 GB: avvio dei due task in sequenza. Per
parallelismo mutante pieno e conforme a `docs/WORKFLOW_ORCA.md`, usare due child
worktree e integrare dopo.

Comandi del coordinatore. Copiare dagli output JSON gli ID in `RUN_ID`,
`SCOUT_TASK`, `WRITER_TASK` e `GRAPHIC_TASK`:

```bash
orca-ide orchestration run-create \
  --objective "Issue #$ISSUE: articolo indicatore verificato e draft PR" --json

orca-ide orchestration task-create --run "$RUN_ID" --task-title scout \
  --display-name "#$ISSUE scout" \
  --spec "Target: issue #$ISSUE e dati TER-105. Change: dossier cifre e fonti. Constraints: sola lettura, nessun file. Ownership: nessuna modifica. Observable acceptance: query e fonti riproducibili." --json

orca-ide orchestration task-create --run "$RUN_ID" --task-title scrittore \
  --display-name "#$ISSUE scrittore" --deps "[\"$SCOUT_TASK\"]" \
  --spec "Target: content/indicators/ter-105.md. Change: testo conforme a issue e dossier scout. Constraints: non toccare asset o Git. Ownership: solo file target. Observable acceptance: cifre e link verificati." --json

orca-ide orchestration task-create --run "$RUN_ID" --task-title grafico \
  --display-name "#$ISSUE grafico" --deps "[\"$SCOUT_TASK\"]" \
  --spec "Target: percorsi grafici dichiarati in TASK.md. Change: grafica da dati verificati. Constraints: non toccare testo o Git. Ownership: solo asset assegnati. Observable acceptance: build e controllo dati verdi." --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$SCOUT_TASK" \
  --worktree "issue:$ISSUE" --agent antigravity --json
orca-ide orchestration check --run "$RUN_ID" --wait \
  --types "worker_done,escalation,question" --timeout-ms 900000 --json

# Dopo worker_done dello scout: avviare in questo ordine. Senza deroga esplicita,
# attendere lo scrittore prima di avviare il grafico.
orca-ide orchestration worker-start --run "$RUN_ID" --task "$WRITER_TASK" \
  --worktree "issue:$ISSUE" --agent codex --json
orca-ide orchestration worker-start --run "$RUN_ID" --task "$GRAPHIC_TASK" \
  --worktree "issue:$ISSUE" --agent codex --json
```

Ogni `check` va processato e riconosciuto con il suo `deliveryId`. Ogni worker
settled va riusato, trattenuto esplicitamente o rilasciato prima della fine del
run. Un timeout è un checkpoint, non una prova di morte.

### Commit, draft PR, review separata e pulizia

Il coordinatore controlla diff e test fuori dalle sandbox che impediscono il
commit, poi crea un commit normale. Prima della review automatizzata il
worktree deve essere pulito e contenere almeno un commit sopra `origin/master`:

```bash
git -C <path-worktree> diff --check
(cd <path-worktree> && \
  DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py -m unittest discover -s tests -v)
git -C <path-worktree> status --short
git -C <path-worktree> add <soli-file-posseduti>
git -C <path-worktree> commit -m "content: aggiunge analisi TER-105"
bin/py scripts/orca_review.py "$SLUG" --issue "$ISSUE"
orca-ide worktree set --worktree "issue:$ISSUE" \
  --comment "Draft PR aperta; attesa review indipendente" \
  --workspace-status in-review --json
```

`scripts/orca_review.py` verifica worktree pulito e commit presente, esegue
`git push -u origin <branch>` e `gh pr create --draft --base master`, includendo
`TASK.md` e `Closes #<issue>` nel corpo. Non fa merge.

Quando draft è completa, team leader la rende pronta. Poi ricava ramo e numero,
crea task review e spawna un agente in un nuovo worktree sul commit della PR.
Esempio: autore Codex, revisore Claude. Se autore è Claude, scegliere Codex. Un
modello diverso della stessa famiglia non basta per questo controllo.

```bash
export WT_PATH=<path-worktree-indicatore>
export PR_BRANCH="$(git -C "$WT_PATH" branch --show-current)"
export PR_NUMBER="$(gh pr view "$PR_BRANCH" --repo nmaiese/diset-viz \
  --json number --jq .number)"
export ITERATION=1
export REVIEW_SLUG="${SLUG}-review-${ITERATION}"

gh pr ready "$PR_NUMBER" --repo nmaiese/diset-viz
gh issue edit "$ISSUE" --repo nmaiese/diset-viz --add-label gate-b

orca-ide orchestration task-create --run "$RUN_ID" --task-title revisore \
  --display-name "PR #$PR_NUMBER review $ITERATION" \
  --deps "[\"$WRITER_TASK\",\"$GRAPHIC_TASK\"]" \
  --spec "Target: PR #$PR_NUMBER al ramo $PR_BRANCH. Change: review read-only e pubblicazione esito GitHub. Constraints: nessuna modifica al repo; modello diverso dagli autori; nessun merge. Ownership: referto PR e issue. Observable acceptance: commit SHA, rilievi path:riga e comandi test nel referto." --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$REVIEW_TASK" \
  --worktree new-top-level --name "$REVIEW_SLUG" \
  --repo path:/home/nilo/dev/sites/divarioitalia \
  --base-branch "origin/$PR_BRANCH" --setup skip --agent claude --json
orca-ide worktree set --worktree "name:$REVIEW_SLUG" --issue "$ISSUE" \
  --comment "Revisione indipendente PR #$PR_NUMBER, iterazione $ITERATION" \
  --workspace-status in-review --json
```

`worker-start --worktree new-top-level` applica placement, readiness e prompt
supervisionato. Il revisore non entra nel worktree indicatore e non è mai chi
ha scritto. Alternativa non supervisionata completa:

```bash
orca-ide worktree create --name "$REVIEW_SLUG" \
  --repo path:/home/nilo/dev/sites/divarioitalia --no-parent \
  --base-branch "origin/$PR_BRANCH" --issue "$ISSUE" --setup skip \
  --agent claude \
  --prompt "Review read-only PR #$PR_NUMBER; pubblica esito su PR e issue, non modificare o fare merge" \
  --json
```

Flusso team preferisce `worker-start`: conserva Task, Dispatch ed esito.

Il revisore prepara `/tmp/review-$PR_NUMBER-$ITERATION.md` con formato fisso:

```markdown
# Orca review, iterazione <n>
- Commit: `<sha>`
- Autore: `<agente/modello>`
- Revisore: `<agente/modello diverso>`
- Verdetto: `REQUEST_CHANGES` | `CLEAR_FOR_HUMAN_GATE`

### Bloccanti
- `<path>:<riga>`: problema, prova, correzione minima

### Non bloccanti
- ...

### Evidenza
- `<comando>`: PASS | FAIL, sintesi
```

Pubblicazione esito, fatta dal revisore dopo i test:

```bash
# Con bloccanti.
gh pr review "$PR_NUMBER" --repo nmaiese/diset-viz --request-changes \
  --body-file "/tmp/review-$PR_NUMBER-$ITERATION.md"
gh issue comment "$ISSUE" --repo nmaiese/diset-viz \
  --body-file "/tmp/review-$PR_NUMBER-$ITERATION.md"

# Senza bloccanti, se credenziale GitHub del revisore è distinta e autorizzata.
gh pr review "$PR_NUMBER" --repo nmaiese/diset-viz --approve \
  --body-file "/tmp/review-$PR_NUMBER-$ITERATION.md"

# Se revisore usa stessa identità GitHub dell'autore, GitHub non consente
# approvazione: registra esito senza fingere un'approvazione.
gh pr review "$PR_NUMBER" --repo nmaiese/diset-viz --comment \
  --body-file "/tmp/review-$PR_NUMBER-$ITERATION.md"
```

Gate B resta umano anche dopo `--approve`. Se review chiede modifiche,
riparazione torna all'autore nel worktree indicatore, non al revisore:

```bash
orca-ide orchestration task-create --run "$RUN_ID" --task-title riparazione \
  --deps "[\"$REVIEW_TASK\"]" \
  --spec "Target: bloccanti della review PR #$PR_NUMBER. Change: correggere solo rilievi confermati nel worktree indicatore. Constraints: nessun allargamento o merge. Ownership: soli file indicati. Observable acceptance: test verdi, commit e push sul ramo PR." --json
orca-ide orchestration worker-show --dispatch "$WRITER_DISPATCH" --json
orca-ide orchestration worker-start --run "$RUN_ID" --task "$REPAIR_TASK" \
  --terminal "$WRITER_TERMINAL" --worktree "name:$SLUG" --json
```

Autore corregge nel worktree indicatore e invia `worker_done`. Coordinatore
riesegue test, committa e fa push, poi applica label:

```bash
git -C "$WT_PATH" add <soli-file-riparati>
git -C "$WT_PATH" commit -m "fix: corregge review TER-105"
git -C "$WT_PATH" push
gh issue edit "$ISSUE" --repo nmaiese/diset-viz \
  --add-label corretta-prima-del-merge
```

Dopo push della correzione, spawnare un nuovo revisore Orca da
`origin/$PR_BRANCH`, con nome `review-2` o `review-3`. Non riusare checkout o
contesto del revisore precedente. Massimo tre iterazioni agentiche. Al terzo
`REQUEST_CHANGES`, sospendere run e portare conflitto al team leader. Mai
ammorbidire criteri per ottenere verde.

### Trigger della review

`orca-ide automations` supporta solo schedule (`hourly`, `daily`, `weekdays`,
`weekly`, cron o RRULE). Non offre trigger webhook su `ready_for_review` o
push/synchronize della PR. Quindi oggi il coordinatore osserva GitHub e lancia
esplicitamente `worker-start` dopo `gh pr ready` e dopo ogni push correttivo.

Automazione schedulata può al massimo fare polling, con latenza, run inutili e
gestione deduplica. Non va confusa con trigger evento. Soluzione futura:
workflow GitHub su `pull_request` con tipi `ready_for_review` e `synchronize`
chiama un bridge autenticato verso Orca, che deduplica per SHA e crea Dispatch.
Richiede segreto, servizio raggiungibile e progetto separato. Non esiste oggi e
non va simulato creando automazioni locali.

Dopo ogni esito pubblicato e `worker_done` accettato, liberare Dispatch e
rimuovere il worktree review pulito. Il referto resta su GitHub:

```bash
orca-ide orchestration worker-release --dispatch "$REVIEW_DISPATCH" --json
bin/py scripts/orca_clean.py "$REVIEW_SLUG"
```

Dopo merge umano confermato:

```bash
bin/py scripts/orca_clean.py "$SLUG"
```

`scripts/orca_clean.py` rifiuta worktree sporchi, preferisce
`orca-ide worktree rm`, usa Git solo se runtime Orca non è disponibile e non
forza la cancellazione di un ramo non fuso. Merge resta umano perché su
`master` equivale a pubblicazione.

## 2. Convivenza dei ruoli nello stesso worktree

Un worktree per indicatore è confine di isolamento rispetto agli altri
indicatori. Dentro quel confine, `TASK.md` deve avere tabella ownership:

| Ruolo | Può scrivere | Non può fare |
|---|---|---|
| scout | niente, solo referto Orca | creare dossier temporanei condivisi |
| scrittore | file contenuto assegnato | asset, config, `git add/commit` |
| grafico | asset/config grafica elencati | testo, `git add/commit` |
| revisore | niente, in worktree separato sul ramo PR | entrare nel worktree autore o correggere durante review |
| riparatore | soli path del rilievo assegnato | refactor o pulizie laterali |
| coordinatore | `TASK.md`, integrazione e Git | modificare mentre altro ruolo possiede il path |

Protocollo:

1. coordinatore registra owner e stato in `TASK.md`
2. mutatori rileggono `TASK.md` prima di ogni fase. Revisore legge spec, issue,
   PR e SHA nel proprio worktree separato
3. nessun agente usa `git add`, `commit`, `stash`, checkout o clean
4. passaggio di proprietà solo dopo `worker_done` accettato
5. revisore parte dopo draft PR, in nuovo worktree e con modello diverso
6. coordinatore integra, testa e committa una volta sola

Questo design non nasconde il conflitto con la regola vigente di
`docs/WORKFLOW_ORCA.md`: “un task, un worktree, un agente” e “due agenti nello
stesso checkout non si coordinano”. Più agenti mutanti nello stesso checkout
sono una deroga proposta, non comportamento oggi conforme. File disgiunti
riduce collisioni di contenuto, ma non protegge indice Git, file generati o
comandi globali.

Configurazione conforme oggi: un solo mutatore attivo alla volta nello
stesso worktree. Configurazione realmente parallela: un child worktree per
`scrittore` e `grafico`, poi integrazione controllata nel worktree indicatore.
Solo dopo misure positive la regola generale potrà essere aggiornata. Questo
draft non modifica `docs/WORKFLOW_ORCA.md`.

## 3. GitHub, CI, Cloud Build e costo

Stato verificato del repository: pubblico, default branch `master`.

| Evento | Sistema | Cosa gira | Costo operativo |
|---|---|---|---|
| push su feature branch | GitHub Actions | Nulla da `ci.yml`, salvo PR già aperta che genera evento `pull_request` | Nessun runner per il solo push senza PR |
| apertura, sync o riapertura PR, anche draft | GitHub Actions `ci.yml` | job Python con install e suite, job Node con `npm ci`, build e controllo bundle | minuti runner, download dipendenze e tempo umano sui fallimenti. Runner standard del repo pubblico non va trattato come capacità infinita |
| push su `master` o `main` | GitHub Actions `ci.yml` | stessi due job | runner e download |
| schedulazione `17 6 * * *` o avvio manuale | GitHub Actions `public-discoverability.yml` | audit HTTP produzione, timeout 10 minuti | runner, richieste HTTP, possibile rumore operativo. Non gira su push o PR |
| push su `master`, tramite trigger Cloud Build esterno | Google Cloud Build con `cloudbuild.yaml` | install e test, Docker build, push di due tag, deploy Cloud Run produzione | minuti/build compute, rete, storage Artifact Registry, nuova revisione Cloud Run |
| push su `stage`, tramite trigger Cloud Build esterno | Google Cloud Build con `cloudbuild-staging.yaml` | test, Docker build/push, `bin/deploy-staging`, verifica HTTP di protezione e noindex | stessi costi build/registry più revisione e smoke test staging |

I file Cloud Build non contengono la definizione del trigger. Commenti e
contratto dichiarano push su `master` e `stage`, ma esistenza e filtri dei
trigger vivono in Google Cloud e vanno auditati lì. Una PR non invoca Cloud
Build dai file presenti. Draft PR invoca invece `pull_request` di GitHub
Actions.

GitHub valida. Cloud Build su `master` testa di nuovo e pubblica. Duplicazione
ha costo, ma impedisce deploy con suite rossa. Nessun agente esegue merge:
approvazione Gate B e merge sono atto umano, perché ogni merge in `master`
avvia percorso di pubblicazione.

## 4. Concorrenza su WSL 8 GB e difetti Orca noti

Budget conservativo:

- un coordinatore più massimo due agenti TUI vivi
- un solo `unittest`, `npm ci/build`, Docker build o browser pesante alla volta
- worktree create sempre sequenziali. Avvii simultanei hanno già prodotto
  `terminal_handle_stale`
- `scrittore` e `grafico` pronti insieme nel DAG, ma serializzati per default
- prima di aumentare parallelismo, misurare RAM e swap durante una run canary

Con 8 GB, terzo agente pesante o due build simultanee possono spingere WSL in
swap, allungare timeout e trasformare lentezza in falsi `outcome_unknown`.
L'assenza di output non prova arresto. Usare `worker-list --include-remote`,
`worker-show` e `worker-read` prima di retry, stop o abandon.

Difetti Antigravity già misurati in `docs/WORKFLOW_ORCA.md`, sezione 6:

1. primo avvio mostra dialogo trust non testuale. Iniezione testo viene
   scartata e il dispatch finisce `agent_prompt_blocked`
2. dopo trust, spec può risultare incollata ma non sottomessa. Serve Invio
   manuale, mentre capability del dispatch fallito può essere già revocata
3. `orca-ide` manca dal `PATH` del Bash figlio. Worker può trovarlo, ma consuma
   turni e deve verificare davvero esito di `worker_done`

Difetto nuovo, misurato il 28 settembre 2026 e distinto dal punto 2: anche in
worktree già fidato Orca può inviare il prompt prima che interfaccia
Antigravity sia pronta. Prompt non appare neppure incollato, input resta vuoto,
agente resta fermo e `worker-start` termina `outcome_unknown`. Non rilanciare
alla cieca. Leggere schermo e transcript del terminale ancora vivo, verificare
input vuoto e seguire recovery restituita dal comando. Finché readiness non è
affidabile, Antigravity non possiede una fase mutante o critica. Scout può
usare fallback headless documentato nel workflow, con output acquisito dal
coordinatore.

## 5. Skill per agente e skill di ruolo versionate

Directory di caricamento osservate su questa macchina:

| Agente | Directory utente |
|---|---|
| Claude | `~/.claude/skills/<skill>/SKILL.md` |
| Codex | `~/.codex/skills/<skill>/SKILL.md` |
| Skill condivise da harness compatibili | `~/.agents/skills/<skill>/SKILL.md` |
| OpenCode | agenti Markdown in `~/.config/opencode/agents/*.md` |
| Antigravity | stato e skill sotto `~/.gemini/antigravity*`; le skill builtin sono gestite dal prodotto e non vanno modificate a mano |

Le home non sono versionate col repository. Fonte proposta nel repo:

```text
skills/editorial-team/
  scout/SKILL.md
  scrittore/SKILL.md
  grafico/SKILL.md
  revisore/SKILL.md
  riparatore/SKILL.md
```

Ogni skill dichiara input, path posseduti, divieti, formato `worker_done` e
accettazione. Task spec cita sempre il path versionato e il commit atteso. Un
installer futuro può copiare la stessa versione nelle directory utente e
generare adapter OpenCode. Non usare symlink verso un singolo worktree Orca:
sparisce alla pulizia. Per Antigravity, finché non esiste installer stabile,
prompt ordina di leggere direttamente skill versionata nel worktree.

`~/.codex/skills/editorial-pipeline` non è base per questo team. Appartiene alla
vecchia catena editoriale dismessa e si attiva anche su frasi generiche come
“scrivi l'articolo”. Le spec del nuovo team devono nominare esplicitamente la
skill di ruolo versionata e dichiarare che `editorial-pipeline` non va usata.
Prima di rendere automatico il routing, vecchia skill va rimossa o resa
inattivabile per questo repository con decisione separata e verificata.
