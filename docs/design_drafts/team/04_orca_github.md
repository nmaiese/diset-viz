# Orca e GitHub per il team editoriale, runbook del pilota

Stato: runbook eseguibile per il pilota descritto in `docs/design_drafts/team/`.
Non automatizza niente da solo: ogni comando qui sotto lo lancia il team leader
(Claude, questa sessione) a mano, un passo alla volta. Repository:
`nmaiese/diset-viz`, branch di default `master`. In WSL il comando è sempre
`orca-ide`, mai `orca`, che è il lettore di schermo GNOME.

Questo documento sostituisce la versione precedente dopo la revisione
avversaria in `06_revisione_avversaria.md` (23 rilievi, 6 bloccanti) e il piano
approvato da Nello, `docs/design_drafts/team/PIANO.md`. Ogni comando è stato verificato con il suo
`--help` sul runtime installato: Orca `1.4.215`, GitHub CLI `2.101.0`, il 28
settembre 2026. Dove un flag non esiste ancora, questo documento lo dice
esplicitamente invece di darlo per fatto.

Non c'è più Gate A. Non parte niente che non sia già nella lista degli
indicatori approvata da Nello, quindi non c'è un'approvazione separata da
aspettare prima di aprire la issue. La label `gate-a` resta nel repository per
lo storico ma questo runbook non la usa mai.

## 0. I quattro ruoli, in serie, un solo worker vivo

| ruolo | dove gira | modello | tetto di dispatch per scheda |
| --- | --- | --- | --- |
| Team leader | questa sessione | Claude opus | nessuno, coordina soltanto |
| Scout | worker Orca nel worktree dell'indicatore | Claude sonnet medium | 1 dispatch, con 1 giro `agy` dentro il suo turno |
| Scrittore | worker Orca, stesso worktree, dopo lo scout | Claude opus high | 1 dispatch, più al massimo 1 riparazione chiesta dal grafico, più al massimo 2 riparazioni dopo review |
| Grafico | worker Orca, stesso worktree, dopo lo scrittore | Codex gpt-5.6-sol high | 1 dispatch |
| Revisore | worker Orca in un worktree nuovo sul ramo della PR | Codex gpt-5.6-sol high | al massimo 3 dispatch, ciascuno con 1 secondo parere |

Antigravity (`agy`) e i modelli gratuiti (`opencode` su `ollama-cloud`) non sono
ruoli: sono processi headless che uno dei quattro worker lancia dentro il
proprio turno, sempre con `timeout` e `< /dev/null` (guasto misurato in
`docs/WORKFLOW_ORCA.md`, sezione 6: senza `< /dev/null` il processo resta
appeso ad aspettare la fine dello stdin e non produce mai una sessione). Non
contano come worker aggiuntivi sulla RAM perché sono figli di breve durata del
worker che li lancia.

**Regola operativa unica**: un solo worker Orca vivo alla volta nel worktree
dell'indicatore. Dopo ogni `worker-start` il ciclo è sempre lo stesso, nello
stesso ordine:

1. `orca-ide orchestration check --wait` finché non arriva `worker_done` (o
   `escalation`/`question`, che si processano prima di continuare).
2. Si decide il destino di ogni terminale della delivery, poi
   `orca-ide orchestration worker-release --dispatch <dispatchId>`.
3. Solo dopo, un solo `check --ack <deliveryId>` per l'intera delivery (una
   delivery è l'intero batch, si riconosce una volta sola). `check` senza
   `--wait` ripresenta lo stesso batch finché non viene riconosciuto: un
   `worker_done` non fa avanzare niente da solo.
4. Solo ad ack confermato si avvia il worker successivo.

Non c'è mai un secondo worker vivo per "far prima". Scrittore e grafico non
partono insieme: il grafico aspetta il `worker-release` dello scrittore, anche
se in teoria potrebbero lavorare su file disgiunti.

## 1. Controlli preliminari, prima di aprire la issue

Quota e RAM si leggono prima di impegnare qualunque risorsa, non dopo. Le tre
sonde ollama di `agent-probe.sh` girano in serie e antigravity da solo arriva
a 300 secondi: nel caso peggiore lo script impiega circa sei minuti a
stampare la tabella, quindi si lancia in background, non con un `timeout`
breve che lo ucciderebbe prima:

```bash
~/dev/dev-tools/scripts/agent-probe.sh > /tmp/agent-probe.log 2>&1 &
free -m
swapon --show
wait
cat /tmp/agent-probe.log
```

- `agent-probe.sh` non dà una percentuale, solo ok, quota, errore o timeout
  per agente. La finestra residua di Codex in percentuale si legge a schermo
  su una sessione Codex aperta apposta (riga "5h limit: N% left"): se è sotto
  il 30%, la scheda non parte.
- Se lo swap cresce con un solo worker vivo già misurato, la scheda non parte.
- Se il modello primario di un ruolo non è disponibile, si usa il ripiego
  indicato nella tabella del piano una volta sola. Se anche il ripiego fallisce
  ci si ferma, senza cascata di ripieghi ulteriori.

Il ramo `<ramo-2c>` (fase 2 del piano: PR 2a, 2b, 2c impilate) non ha ancora
un nome definitivo. Prima di aprire la issue si conferma il nome esatto e si
verifica che il ramo remoto contenga già le quattro skill, lo script del
brief e la guardia:

```bash
git fetch origin
git ls-tree --name-only -r "origin/<ramo-2c>" -- skills/editorial-team scripts/editoriale
```

L'elenco deve contenere le quattro `SKILL.md`, `brief.py` e il modulo della
guardia. Se manca qualcosa, la scheda non parte.

## 2. La issue, senza Gate A

Il team leader apre la issue prima di creare qualunque worktree. Il template
`.github/ISSUE_TEMPLATE/indicatore-team.yml` funziona solo dal branch di
default, quindi finché il ramo del pilota non è `master` la issue si apre con
`--body-file`:

```bash
gh issue create --repo nmaiese/diset-viz \
  --title "Indicatore TER-12: <domanda editoriale>" \
  --body-file /tmp/ter-12-issue.md \
  --label run:team
```

Corpo minimo del file, con la sezione `## Stato` del corpo già presente come
blocco unico che si modifica sul posto (sezione 12):

```markdown
### Intent
[domanda editoriale, senza anticipare una conclusione]

### Che cosa misura, in una riga
[per una persona normale, con la soglia per leggerlo: la rilegge Nello qui]

### Dati e fonti
- Dataset:
- Periodo:
- Territorio:
- Fonti esterne ammesse:

### Output posseduti
- Testo: `content/indicators/<file>.md` (per ter-12 e' `12.md`, per un BES `bes__<id>.md`: lo dice `scripts/indicator_store.filename_for`)
- Grafica: `<percorsi esatti>`

### Accettazione
- [ ] cifre riproducibili dal dossier
- [ ] fonti in `fonti.md` verificate, URL aperto e citazione letterale
- [ ] test del repository verdi
- [ ] verdetto del revisore Orca `PRONTA PER NELLO`
- [ ] giudizio di Nello prima del merge

## Stato
Run: nessuno
Fase: issue aperta
SHA: nessuno
Prossimo passo: creare il worktree
Chi lo fa: team leader
```

Nessun lavoro parte prima di questo comando, e nessun lavoro aspetta
un'approvazione separata dopo: la lista degli indicatori del pilota è già
quella approvata da Nello.

## 3. Worktree dell'indicatore, senza agente

Il worktree si crea senza lanciare nessun agente al suo interno, così non
nasce un secondo coordinatore. Niente `scripts/orca_dispatch.py --role
worker`: quello script crea un Codex nel worktree con `TASK.md` proprio, ed è
esattamente il coordinatore concorrente che la revisione avversaria ha
bocciato (rilievo 2).

Ogni blocco Bash di questo runbook parte con una shell nuova: niente `export`
che debba sopravvivere da un blocco all'altro. I valori della scheda (issue
`123`, slug `ind-ter-12`) si scrivono per intero in ogni blocco che li usa.
Gli id che Orca restituisce (`RUN_ID`, gli id dei task) si leggono
dall'output `--json` con `jq`, si assegnano nello stesso blocco in cui
vengono usati e si tengono anche in `/tmp/ter-12-ids.env`, fuori dal worktree
dell'indicatore, letto con `source` da ogni blocco successivo che ne ha
bisogno.

```bash
: > /tmp/ter-12-ids.env

orca-ide worktree create --name ind-ter-12 --issue 123 \
  --base-branch "origin/<ramo-2c>" --no-parent --setup skip --json
```

`<ramo-2c>` è il ramo dello strumento `orca_review.py` esteso (fase 2 del
piano, PR 2c), verificato in sezione 1. A regime, dopo che Nello ha unito 2a,
2b e 2c, `<ramo-2c>` diventa `master`. Nessun flag `--agent` qui: senza agente
non c'è un terminale mutante finché non parte il primo worker con
`worker-start`.

Se Orca chiude la connessione durante questo comando ("The Orca runtime
closed the connection before responding"), il worktree può essere stato
creato lo stesso, sia in git sia in Orca (`docs/WORKFLOW_ORCA.md`, sezione 6):
prima si guarda `git worktree list`, poi si aspetta che `orca-ide worktree
show --worktree branch:nmaiese/ind-ter-12 --json` lo trovi, perché la
registrazione in Orca arriva qualche secondo dopo quella in git. Si riprova
solo se dopo l'attesa il worktree non c'è: un secondo `worktree create`
lanciato subito non dà errore e crea un doppione con il suffisso `-2`.

```bash
orca-ide worktree show --worktree "issue:123" --json

WT_PATH="$(git worktree list --porcelain \
  | awk -v b="branch refs/heads/nmaiese/ind-ter-12" \
    '/^worktree /{p=$2} $0==b{print p}')"
echo "WT_PATH=$WT_PATH"
```

`worktree show` conferma il collegamento fra worktree e issue prima di
procedere. L'`awk` cerca il branch per uguaglianza esatta con
`refs/heads/nmaiese/<slug>`, mai una sottostringa dello slug: dopo la sezione
9 esistono anche i rami di review (`nmaiese/ind-ter-12-review-1`), e un match
per sottostringa ne stampa più di uno. `WT_PATH` non sopravvive a questo
blocco: si ricalcola con lo stesso `awk` in ogni sezione successiva che ne ha
bisogno (5, 8, 10, 14).

## 4. Il namespace del run

```bash
RUN_ID="$(orca-ide orchestration run-create \
  --objective "Issue #123: scheda TER-12 arricchita, testo e grafica verificati" \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "RUN_ID=$RUN_ID" >> /tmp/ter-12-ids.env
```

Da qui in poi ogni blocco che usa `$RUN_ID` comincia con
`source /tmp/ter-12-ids.env`. Ogni `task-create` e ogni `worker-start` di
questa scheda usano lo stesso `$RUN_ID`.

## 5. Scout

```bash
source /tmp/ter-12-ids.env
SCOUT_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" --task-title scout \
  --display-name "#123 scout" \
  --spec "Leggi skills/editorial-team/scout/SKILL.md e seguila, questa spec la precisa: dove dicono cose diverse vale la spec, e lo scrivi nel worker_done. Target: lavoro/ter-12/dossier.json e lavoro/ter-12/fonti.md. Change: dossier deterministico da scripts/editoriale/brief.py e tabella fonti con dato osservato più recente, previsioni 2026, economia della regione più alta e più bassa, fattori che muovono l'indicatore, chi altri ne ha scritto. Colonne fonti.md: istituzione, data di pubblicazione, URL aperto, citazione letterale, limite d'uso; per le previsioni anche orizzonte e cautela. Una voce senza fonte si scrive 'non trovato'. Constraints: sola lettura sul resto del repo, nessuna modifica a content/ o app/. Lancia in parallelo alla tua ricerca: timeout 900 agy --model gemini-3.1-pro-high --dangerously-skip-permissions -p '<consegna del giro web>' --print-timeout 900s < /dev/null > lavoro/ter-12/scout_web.md. Porta in fonti.md solo le voci di cui hai aperto l'URL e trovato la citazione. Observable acceptance: dossier.json presente, fonti.md con tutte le voci obbligatorie o 'non trovato'." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "SCOUT_TASK=$SCOUT_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$SCOUT_TASK" \
  --worktree "issue:123" --agent claude --model sonnet --effort medium --json
```

Poi il ciclo della sezione 0. Solo dopo il rilascio il team leader ricalcola
`WT_PATH` come in sezione 3 e scrive `"$WT_PATH/lavoro/ter-12/brief.md"` con
le parti di `PIANO.md`, "Il brief dello scrittore": che cosa misura in una
riga, la fotografia, le dimensioni, il perché, l'attualità, il file di
`content/esempi/` da usare come modello, e se c'è una figura da proporre (per
ter-12 la dispersione con ter-901). Prende le cifre dal dossier e le cause da
`fonti.md`, e ne pubblica una copia come commento sulla issue. È materiale per
lo scrittore, non una scaletta.

Ripiego se Claude sonnet non è disponibile: Codex gpt-5.6-sol medium. Ripiego
per `agy` se `gemini-3.1-pro-high` non risponde: `gemini-3.8-flash-high`, una
volta sola. Se fallisce anche quello, lo scout va avanti senza giro web e lo
scrive nel `worker_done`: il giro non blocca (`PIANO.md`).

## 6. Scrittore

Parte solo dopo il `worker-release` dello scout, mai in parallelo.

```bash
source /tmp/ter-12-ids.env
WRITER_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" --task-title scrittore \
  --display-name "#123 scrittore" --deps "[\"$SCOUT_TASK\"]" \
  --spec "Leggi skills/editorial-team/scrittore/SKILL.md e seguila, questa spec la precisa: dove dicono cose diverse vale la spec, e lo scrivi nel worker_done. Target: content/indicators/12.md. Change: articolo in forma libera (LIBERA in app/indicator_texts.py), nessuna sezione predefinita, titoli-affermazione dove il pezzo cambia argomento. Chiave: ter-12. Brief: lavoro/ter-12/brief.md, se manca escalation. Cifre solo dal brief e dalle citazioni letterali di lavoro/ter-12/fonti.md, che serve anche per cause e URL. Modello di registro: il file di content/esempi/ indicato dal brief. Issue: #123. Non ricevi: frasi fatte del dossier, polarità come giudizio, cifre di servizio, gergo interno, un angolo già deciso, una scaletta. Vietati: em-dash, en-dash, ';', '…'. Constraints: solo content/indicators/12.md, niente git add/commit, niente asset. Observable acceptance: articolo leggibile come prosa discorsiva, ogni cifra riconducibile al dossier o a fonti.md." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "WRITER_TASK=$WRITER_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$WRITER_TASK" \
  --worktree "issue:123" --agent claude --model opus --effort high --json
```

Ciclo della sezione 0. Ripiego: Codex gpt-5.6-sol high, una volta sola.

## 7. Grafico

Parte solo dopo il `worker-release` dello scrittore.

```bash
source /tmp/ter-12-ids.env
GRAPHIC_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" --task-title grafico \
  --display-name "#123 grafico" --deps "[\"$WRITER_TASK\"]" \
  --spec "Leggi skills/editorial-team/grafico/SKILL.md e seguila, questa spec la precisa: dove dicono cose diverse vale la spec, e lo scrivi nel worker_done. Chiave: ter-12. Brief: lavoro/ter-12/brief.md. Target: marcatore <!-- grafico --> dentro content/indicators/12.md, tipo dispersione con=ter-901. Change: una figura sola, disoccupazione contro PIL pro capite, una regione per punto, i punti grigi e l'arancio solo per le regioni in evidenza, come fa oggi il renderer (i colori delle ripartizioni richiederebbero una PR di app/charts.py da unire prima). Vietato ridisegnare serie, mappa o classifica già nel cruscotto, e vietato costruire un tipo di grafico nuovo in questo pilota. Specifica richiesta: provenienza e unità, anni e dati mancanti, didascalia autonoma, resa a 375 e 768px, tema chiaro e scuro. Constraints: solo il marcatore assegnato, niente testo, niente git add/commit. Observable acceptance: marcatore reso, figcaption con i due indicatori e gli anni, tema scuro corretto." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "GRAPHIC_TASK=$GRAPHIC_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$GRAPHIC_TASK" \
  --worktree "issue:123" --agent codex --model gpt-5.6-sol --effort high --json
```

Ciclo della sezione 0. Ripiego: Claude sonnet, una volta sola.

Se il `worker_done` del grafico chiede di cambiare una frase per far leggere
meglio la figura, parte **prima del commit** una riparazione dello scrittore,
con una spec propria, non quella della sezione 10 (che è per dopo la review):

```bash
source /tmp/ter-12-ids.env
GRAPHIC_REPAIR_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" \
  --task-title riparazione-grafico --deps "[\"$GRAPHIC_TASK\"]" \
  --spec "Leggi skills/editorial-team/scrittore/SKILL.md, la parte In una riparazione. Target: content/indicators/12.md. Change: correggere solo le frasi citate parola per parola nel worker_done del grafico: <frasi del grafico>. Se la frase corretta tocca il paragrafo che richiama la figura, verifica di nuovo la resa del marcatore <!-- grafico --> prima di segnalare finito. Constraints: nessun allargamento di scopo, niente git add/commit. Observable acceptance: frasi corrette, marcatore ancora reso." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "GRAPHIC_REPAIR_TASK=$GRAPHIC_REPAIR_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$GRAPHIC_REPAIR_TASK" \
  --worktree "issue:123" --agent claude --model opus --effort high --json
```

Ciclo della sezione 0. Questa riparazione conta nel tetto dello scrittore
(sezione 0): al massimo una, e non è una delle due riparazioni dopo review.

## 8. Guardia, commit e draft PR

Fuori da qualunque sandbox che impedisce il commit, il team leader rilancia
la guardia, i test, poi committa:

```bash
WT_PATH="$(git worktree list --porcelain \
  | awk -v b="branch refs/heads/nmaiese/ind-ter-12" \
    '/^worktree /{p=$2} $0==b{print p}')"

(cd "$WT_PATH" && DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json)
git -C "$WT_PATH" diff --check
(cd "$WT_PATH" && DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py -m unittest discover -s tests -v)
git -C "$WT_PATH" status --short
git -C "$WT_PATH" add content/indicators/12.md lavoro/ter-12/dossier.json lavoro/ter-12/fonti.md lavoro/ter-12/brief.md
git -C "$WT_PATH" commit -m "Scheda ter-12 riscritta dal team: <una frase su che cosa dice il pezzo>"
```

`scripts/orca_review.py`, così com'è oggi, pubblica sempre con `--base master`
e non accetta `--label` né `--body-file`: non è ancora lo strumento esteso
della fase 2 (PR 2c). Finché quella PR non è unita, o quando la base del
pilota non è `master`, il team leader apre la PR a mano, in draft, con base
`<ramo-2c>`:

```bash
PR_BRANCH="$(git -C "$WT_PATH" branch --show-current)"
git -C "$WT_PATH" push -u origin "$PR_BRANCH"
echo "PR_BRANCH=$PR_BRANCH" >> /tmp/ter-12-ids.env

gh pr create --repo nmaiese/diset-viz \
  --draft --base "<ramo-2c>" --head "$PR_BRANCH" \
  --title "Indicatore TER-12: <domanda editoriale>" \
  --body-file /tmp/ter-12-pr-body.md \
  --label run:team
```

`/tmp/ter-12-pr-body.md` contiene testo precedente e testo proposto affiancati,
le fonti nuove di `fonti.md`, l'SHA del commit e `Closes #123`. Unita la 2c,
lo strumento `orca_review.py` ha già `--label` e `--body-file` e si usa così
com'è, con `--base` puntato al ramo giusto e il conteggio dei commit fatto
rispetto a quella base: la PR del pilota resta impilata su `<ramo-2c>` finché
Nello non giudica il testo (`PIANO.md`, decisione 9), non va aperta verso
`master`.

La PR resta **in draft** finché il revisore non pubblica un verdetto. Non si
chiama `gh pr ready` prima di questo punto (rilievo 8).

```bash
orca-ide worktree set --worktree "issue:123" \
  --comment "Draft PR aperta, attesa revisore Orca" \
  --workspace-status in-review --json
```

## 9. Revisore

Nasce in un worktree nuovo e separato, sul ramo della PR, con un modello di
famiglia diversa da chi ha scritto il testo. Esempio: autore Claude, revisore
Codex. Se l'autore fosse Codex, il revisore è Claude.

```bash
source /tmp/ter-12-ids.env
PR_NUMBER="$(gh pr view "$PR_BRANCH" --repo nmaiese/diset-viz \
  --json number --jq .number)"
HEAD_SHA="$(gh pr view "$PR_BRANCH" --repo nmaiese/diset-viz \
  --json headRefOid --jq .headRefOid)"
ITERATION=1
REVIEW_SLUG="ind-ter-12-review-${ITERATION}"
echo "PR_NUMBER=$PR_NUMBER" >> /tmp/ter-12-ids.env
echo "HEAD_SHA=$HEAD_SHA" >> /tmp/ter-12-ids.env
echo "ITERATION=$ITERATION" >> /tmp/ter-12-ids.env
echo "REVIEW_SLUG=$REVIEW_SLUG" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
REVIEW_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" --task-title revisore \
  --display-name "PR #$PR_NUMBER review $ITERATION" \
  --deps "[\"$WRITER_TASK\",\"$GRAPHIC_TASK\"]" \
  --spec "Leggi skills/editorial-team/revisore/SKILL.md e seguila, questa spec la precisa: dove dicono cose diverse vale la spec, e lo scrivi nel worker_done. Guardia: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json. Issue: #123. Target: PR #$PR_NUMBER al ramo $PR_BRANCH, commit atteso $HEAD_SHA. Change: review read-only, le cinque domande della skill, senza modifiche. Per ogni no: frase citata, motivo, correzione minima. Prima di pubblicare confronta git rev-parse HEAD nel tuo worktree con l'headRefOid corrente da gh pr view; se sono diversi non pubblicare. Pubblica sempre con gh pr review --comment, mai --approve né --request-changes (stessa identità GitHub dell'autore). Verdetto testuale DA CORREGGERE o PRONTA PER NELLO più lo SHA. Lancia anche, dentro il tuo turno, il secondo parere: timeout 600 opencode run '<consegna, solo le domande 1 e 3, di leggibilità>' -m ollama-cloud/gpt-oss:120b -f <path-articolo> -f <path-brief> < /dev/null, con i due file dentro il worktree perche' opencode rifiuta i path esterni come /tmp. Se l'output e' vuoto il parere non c'e', anche con exit 0. Non bloccante, riporta risposte e disaccordi nel tuo commento senza aprire un altro giro. Aggiorna la sezione Stato nel corpo della issue (gh issue view --json body, poi gh issue edit --body-file). Constraints: nessuna modifica al repo, nessun merge. Ownership: referto su PR e issue." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "REVIEW_TASK=$REVIEW_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
# prima il worktree, da solo: dentro worker-start la creazione puo' superare
# il timeout del dispatch, e allora il prompt non arriva mai all'agente
orca-ide worktree create --name "$REVIEW_SLUG" \
  --repo id:d2ae0385-1020-40e5-8859-7fbd55a33e03 \
  --base-branch "origin/$PR_BRANCH" --no-parent --setup skip --json
```

Se Orca chiude la connessione durante questo comando, vale lo stesso rimedio
della sezione 3: prima `git worktree list`, poi l'attesa che `orca-ide
worktree show --worktree branch:nmaiese/$REVIEW_SLUG --json` lo trovi, e solo
allora, se manca, si riprova. Un secondo tentativo immediato crea un doppione
`-2`.

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$REVIEW_TASK" \
  --worktree "branch:nmaiese/$REVIEW_SLUG" \
  --agent codex --model gpt-5.6-sol --effort high --json
```

Tre cose misurate il 28 settembre alla prima review vera, sulla issue #285:
- **`--repo path:/home/nilo/...` fallisce con `repo_not_found`.** Orca registra
  il repo con il percorso Windows (`\\wsl.localhost\Ubuntu-24.04\...`), quindi il
  selettore giusto è l'id, `id:d2ae0385-1020-40e5-8859-7fbd55a33e03`, che si
  legge con `orca-ide repo list --json`.
- **`worker-start --worktree new-top-level` può andare in timeout.** La
  creazione del worktree ha superato i 120 secondi. Il dispatch è finito
  `failed` con `lastError: timeout`, e l'agente è partito con la casella vuota.
  Per questo il worktree si crea prima, con `worktree create`, e il worker si
  lancia dopo sul worktree che esiste già.
- **Un terminale non si riusa dopo la fine del suo dispatch**, né con
  `--terminal` né con `--retry-of`: Orca risponde "is not running a recognized
  agent". Si rilascia il worker e se ne lancia uno nuovo sullo stesso worktree,
  con `--task <id> --retry-of <dispatch>`.

Ciclo della sezione 0.

Nel proprio worktree il revisore verifica prima di pubblicare:

```bash
source /tmp/ter-12-ids.env
git rev-parse HEAD
gh pr view "$PR_NUMBER" --repo nmaiese/diset-viz --json headRefOid --jq .headRefOid
```

Se i due valori non coincidono (un push è arrivato nel frattempo), il
revisore non pubblica e lo dice nel suo `worker_done`: si rilegge lo SHA e si
rilancia la review, senza pubblicare un verdetto su un commit diverso da
quello dichiarato.

Pubblicazione, sempre con `--comment`, mai `--approve` né `--request-changes`,
perché autore e revisore condividono la stessa identità GitHub e GitHub non
consente di approvare o chiedere modifiche sulla propria PR:

```bash
source /tmp/ter-12-ids.env
gh pr review "$PR_NUMBER" --repo nmaiese/diset-viz --comment \
  --body-file "/tmp/review-$PR_NUMBER-$ITERATION.md"
```

Il file di review contiene lo SHA verificato, il verdetto (`DA CORREGGERE` o
`PRONTA PER NELLO`), i rilievi con frase citata e correzione minima, e la
risposta del secondo parere `gpt-oss` se è arrivata in tempo.

## 10. Riparazione, con un worker nuovo

Se il verdetto è `DA CORREGGERE`, la correzione non torna al terminale dello
scrittore: quel worker è già concluso e rilasciato. Parte un worker nuovo, nel
worktree dell'indicatore, con i soli path indicati dal revisore.

```bash
source /tmp/ter-12-ids.env
REPAIR_TASK="$(orca-ide orchestration task-create --run "$RUN_ID" --task-title riparazione \
  --deps "[\"$REVIEW_TASK\"]" \
  --spec "Leggi skills/editorial-team/scrittore/SKILL.md, la parte In una riparazione. Target: <soli path indicati dal revisore>. Change: correggere solo i rilievi confermati nel commento PR #$PR_NUMBER, iterazione $ITERATION. SHA rivisto: $HEAD_SHA. Prima di correggere controlla che git rev-parse HEAD coincida, altrimenti escalation. Constraints: nessun allargamento di scopo, niente file oltre quelli indicati, niente git add/commit. Observable acceptance: rilievi risolti, test del repository ancora verdi." \
  --json | jq -r '.id')"          # campo da verificare alla prima esecuzione
echo "REPAIR_TASK=$REPAIR_TASK" >> /tmp/ter-12-ids.env
```

```bash
source /tmp/ter-12-ids.env
orca-ide orchestration worker-start --run "$RUN_ID" --task "$REPAIR_TASK" \
  --worktree "issue:123" --agent claude --model opus --effort high --json
```

Ciclo della sezione 0. Al `worker_done` il team leader rilancia guardia e
test (sezione 8), committa, fa push:

```bash
source /tmp/ter-12-ids.env
WT_PATH="$(git worktree list --porcelain \
  | awk -v b="branch refs/heads/nmaiese/ind-ter-12" \
    '/^worktree /{p=$2} $0==b{print p}')"
(cd "$WT_PATH" && DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json)
(cd "$WT_PATH" && DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py -m unittest discover -s tests -v)
git -C "$WT_PATH" add <soli-file-riparati>
git -C "$WT_PATH" commit -m "Scheda ter-12, correzioni della review $ITERATION: <quali>"
git -C "$WT_PATH" push
gh issue edit 123 --repo nmaiese/diset-viz \
  --add-label corretta-prima-del-merge
```

Dopo il push, un **nuovo** revisore, nome `review-2`, worktree nuovo, mai il
worktree della review precedente: si ripete la sezione 9 con
`ITERATION=2` e uno `HEAD_SHA` riletto da capo. Al massimo tre iterazioni.
Al terzo `DA CORREGGERE` la scheda si ferma e va a Nello così com'è, senza un
quarto giro.

## 11. PRONTA PER NELLO

Solo quando il revisore pubblica `PRONTA PER NELLO` sullo SHA corrente:

```bash
source /tmp/ter-12-ids.env
gh pr ready "$PR_NUMBER" --repo nmaiese/diset-viz
gh issue edit 123 --repo nmaiese/diset-viz --add-label gate-b
```

Non prima. Una PR draft con `DA CORREGGERE` non diventa mai pronta da sola.

## 12. Lo stato della issue, nel corpo della issue

La issue è l'unico posto dove sta lo stato completo, ed è la sezione `## Stato`
in fondo al **corpo** della issue (sezione 2), non un commento. Il motivo è
pratico: tutti gli agenti scrivono con l'identità di Nello, quindi
`gh issue comment --edit-last` modificherebbe l'ultimo commento di chiunque, per
esempio il brief pubblicato dal team leader, non quello di stato.

A ogni passaggio si rilegge il corpo, si riscrive solo la sezione `## Stato` e
lo si ripubblica:

```bash
gh issue view 123 --repo nmaiese/diset-viz --json body --jq .body > /tmp/ter-12-body.md
# sostituire il blocco "## Stato" fino alla fine del file
gh issue edit 123 --repo nmaiese/diset-viz --body-file /tmp/ter-12-body.md
```

Lo schema del blocco è sempre lo stesso:

```markdown
## Stato
Run: <RUN_ID o nessuno>
Fase: <issue aperta | scout | scrittore | grafico | draft PR | review 1 | riparazione 1 | review 2 | riparazione 2 | review 3 | PRONTA PER NELLO | ferma, a Nello | merge>
SHA: <sha corrente o nessuno>
Prossimo passo: <descrizione breve>
Chi lo fa: <team leader | scout | scrittore | grafico | revisore | riparatore | Nello>
```

I commenti della issue restano per il materiale (il brief, i verdetti), mai per
lo stato. Label, commenti sulla PR, `TASK.md` e la scheda Orca sono prove o
viste derivate: rimandano alla sezione Stato, non la ripetono.

## 13. Ripresa dopo un'interruzione

Non esiste un trigger GitHub su Orca: `orca-ide automations` accetta solo
preset temporali, cron o RRULE, non eventi `pull_request` (verificato con
`orca-ide automations create --help`). Una sessione nuova del team leader non
è legata al run precedente: `orca-ide orchestration check` legge il run
agganciato al terminale, quindi da sola non mostra né una delivery non
riconosciuta né il terminale di un worker ancora vivo di un run diverso. Se la
sessione del team leader si interrompe fra un push e una review, la ripresa
parte da questi comandi, senza script nuovi:

```bash
orca-ide orchestration run-use --id "$RUN_ID" --json
orca-ide orchestration check --json
orca-ide orchestration worker-list --run "$RUN_ID" --json

gh issue list --repo nmaiese/diset-viz -l run:team \
  --json number,title,body

gh pr list --repo nmaiese/diset-viz --draft -l run:team \
  --json number,headRefOid,reviews
```

`run-use` riaggancia il terminale al run della scheda (`$RUN_ID` letto da
`/tmp/ter-12-ids.env`), `check` mostra le delivery pendenti da riconoscere e
`worker-list` i worker ancora attivi da riprendere o rilasciare. La prima `gh`
elenca le issue aperte del team con la loro sezione `## Stato` dentro `body`.
La seconda elenca le PR draft ancora in attesa, con lo SHA e le review già
pubblicate: uno SHA in `headRefOid` più recente dell'ultimo verdetto significa
che serve un nuovo revisore prima di procedere.

## 14. Pulizia dopo il merge

Il merge resta sempre umano, di Nello: su `master` un merge equivale a un
deploy. Il worker del revisore è già rilasciato dal ciclo della sezione 0:
qui non c'è un altro `worker-release` da fare.

`scout_web.md` è una traccia del giro `agy`, non va nella PR e resta non
tracciato nel worktree: `orca_clean.py` rifiuta la pulizia se `git status
--porcelain` non è vuoto, quindi va tolto prima, per ogni worktree di review
creato e per il worktree dell'indicatore:

```bash
WT_PATH="$(git worktree list --porcelain \
  | awk -v b="branch refs/heads/nmaiese/ind-ter-12" \
    '/^worktree /{p=$2} $0==b{print p}')"
rm -f "$WT_PATH/lavoro/ter-12/scout_web.md"

for n in 1 2 3; do
  REVIEW_PATH="$(git worktree list --porcelain \
    | awk -v b="branch refs/heads/nmaiese/ind-ter-12-review-$n" \
      '/^worktree /{p=$2} $0==b{print p}')"
  [ -n "$REVIEW_PATH" ] && DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
    bin/py scripts/orca_clean.py "ind-ter-12-review-$n"
done

# dopo il merge confermato da Nello
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
  bin/py scripts/orca_clean.py ind-ter-12
```

`scripts/orca_clean.py` rifiuta un worktree sporco, preferisce `orca-ide
worktree rm`, usa Git solo se il runtime Orca non è disponibile e non forza la
cancellazione di un ramo non fuso. Dopo il merge il team leader promuove le
fonti nuove in `data/corpus/sources.json` e chiude lo stato sulla issue.

## 15. Convivenza dei ruoli nello stesso worktree

Un worktree per indicatore isola quell'indicatore dagli altri. Dentro quel
confine, ogni ruolo scrive solo i propri path:

| Ruolo | Può scrivere | Non può fare |
| --- | --- | --- |
| scout | `lavoro/<chiave>/dossier.json`, `lavoro/<chiave>/fonti.md`, `lavoro/<chiave>/scout_web.md` (traccia, non va nella PR) | toccare `content/`, `app/`, promuovere fonti nel registro |
| scrittore | il file contenuto assegnato | asset, config, `git add`/`commit` |
| grafico | il marcatore grafico assegnato | testo, `git add`/`commit` |
| revisore | referto in `/tmp`, pubblicato con `gh pr review --comment`, e sezione `## Stato` del corpo della issue dopo il verdetto | entrare nel worktree dell'autore o correggere durante la review |
| riparatore | solo i path del rilievo assegnato | refactor o pulizie non richieste |
| team leader | integrazione, `git add`/`commit`/`push`, PR, label, sezione `## Stato` del corpo | scrivere mentre un worker possiede ancora quel path |

Durante la review lo Stato lo aggiorna il revisore, non il team leader (vedi
sopra). Negli altri passaggi lo aggiorna il team leader.

Protocollo:

1. Un solo worker vivo alla volta (sezione 0): non c'è mai un conflitto reale
   sull'indice Git perché non c'è mai un secondo mutatore attivo.
2. Ogni worker rilegge la propria spec di task prima di iniziare.
3. Nessun worker usa `git add`, `commit`, `stash`, `checkout` o `clean`: lo fa
   solo il team leader, fuori dalle sandbox che lo impediscono.
4. Il passaggio di proprietà di un path avviene solo dopo un `worker_done`
   accettato e il `worker-release` che segue.
5. Il revisore nasce sempre dopo la draft PR, in un worktree nuovo, con un
   modello di famiglia diversa da chi ha scritto.

## 16. GitHub, CI, Cloud Build e costo

Stato verificato del repository: pubblico, branch di default `master`.

| Evento | Sistema | Cosa gira | Costo operativo |
| --- | --- | --- | --- |
| push su feature branch senza PR aperta | GitHub Actions | niente da `ci.yml` | nessun runner |
| apertura, sync o riapertura PR, anche draft | GitHub Actions `ci.yml` | job Python (install e suite), job Node (`npm ci`, build, controllo bundle) | minuti runner, dipendenze scaricate, tempo umano sui fallimenti |
| push su `master` | GitHub Actions `ci.yml` | stessi due job | runner e download |
| schedulazione `17 6 * * *` o avvio manuale | GitHub Actions `public-discoverability.yml` | audit HTTP produzione, timeout 10 minuti | runner, richieste HTTP, non attivo su push o PR |
| push su `master`, trigger Cloud Build esterno | Google Cloud Build (`cloudbuild.yaml`) | install e test, build Docker, push di due tag, deploy Cloud Run produzione | minuti build, rete, storage Artifact Registry, nuova revisione Cloud Run |
| push su `stage`, trigger Cloud Build esterno | Google Cloud Build (`cloudbuild-staging.yaml`) | test, build/push Docker, `bin/deploy-staging`, verifica HTTP protezione e noindex | stessi costi build/registry più revisione e smoke test staging |

I file Cloud Build non contengono la definizione del trigger: esistenza e
filtri vivono in Google Cloud e vanno auditati lì, non nei file del repo. Una
PR sul ramo del pilota (non `master`) non invoca Cloud Build. Nessun agente fa
merge: l'approvazione umana e il merge restano un atto di Nello, perché ogni
merge su `master` avvia la pubblicazione.

## 17. Concorrenza su WSL 8 GB

Budget del pilota, più stretto di quello generale di
`docs/WORKFLOW_ORCA.md`: un coordinatore più **un solo** worker Orca vivo,
mai due. Misura di riferimento del 28 settembre 2026: 7,9 GiB totali, circa
2,6 GiB usati e 1,3 GiB di swap occupato a riposo (`free -m`, `swapon
--show`).

- `free -m` e `swapon --show` prima e dopo ogni worker (sezione 1 e sezione
  0), non solo all'inizio della scheda.
- Un solo `unittest`, `npm ci`/`build`, build Docker o browser pesante alla
  volta.
- Le create di worktree restano sequenziali: avvii simultanei hanno già
  prodotto `terminal_handle_stale`.
- `agy` e `opencode` in headless (sezioni 5 e 9) sono processi figli di breve
  durata del worker che li lancia, non worker aggiuntivi: restano comunque
  soggetti a `timeout` e vanno misurati se lo swap cresce.
- Se lo swap cresce con un solo worker vivo, la scheda si ferma (sezione 1).

## 18. Skill per agente

Directory di caricamento osservate su questa macchina:

| Agente | Directory utente |
| --- | --- |
| Claude | `~/.claude/skills/<skill>/SKILL.md` |
| Codex | `~/.codex/skills/<skill>/SKILL.md` |
| Skill condivise da harness compatibili | `~/.agents/skills/<skill>/SKILL.md` |
| OpenCode | agenti Markdown in `~/.config/opencode/agents/*.md` |
| Antigravity | stato e skill sotto `~/.gemini/antigravity*`, le skill builtin le gestisce il prodotto, non si toccano a mano |

Fonte proposta nel repo, dalla fase 2 del piano (PR 2a):

```text
skills/editorial-team/
  scout/SKILL.md
  scrittore/SKILL.md
  grafico/SKILL.md
  revisore/SKILL.md
```

Ogni skill dichiara input, path posseduti, divieti, formato `worker_done` e
criteri di accettazione. Ogni `--spec` di questo runbook comincia con "Leggi
`skills/editorial-team/<ruolo>/SKILL.md`". Il riparatore non ha una skill sua:
è lo scrittore in modalità riparazione, descritta in fondo alla sua skill.

Le skill della vecchia catena (`~/.codex/skills/editorial-pipeline` e
`italian-editorial-quality-gate`) si attivavano anche su frasi generiche come
"scrivi l'articolo". Dal 28 settembre sono in quarantena in
`~/.codex/skills-quarantena/`, quindi Codex non le carica più. Si rimettono con
un `mv` solo se Nello lo chiede.

## 19. Cosa richiede mano umana, in ogni caso

- Il merge su `master` e ogni deploy.
- L'approvazione di Nello prima della pubblicazione (Gate B, unico gate
  rimasto).
- Segreti: nessuna lettura di `.env`, chiavi o credenziali, nessuna scrittura
  di `auth.json`.
- Il container GTM, la regola per il traffico interno in GA4, la creazione di
  dimensioni e metriche, Bing Webmaster Tools.
- Nessun `Co-Authored-By` nei messaggi di commit.
