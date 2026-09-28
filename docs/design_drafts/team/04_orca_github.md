# Orca e GitHub per il team editoriale, runbook del pilota

Stato: runbook eseguibile per il pilota descritto in `docs/design_drafts/team/`.
Non automatizza niente da solo: ogni comando qui sotto lo lancia il team leader
(Claude, questa sessione) a mano, un passo alla volta. Repository:
`nmaiese/diset-viz`, branch di default `master`. In WSL il comando è sempre
`orca-ide`, mai `orca`, che è il lettore di schermo GNOME.

Questo documento sostituisce la versione precedente dopo la revisione
avversaria in `06_revisione_avversaria.md` (23 rilievi, 6 bloccanti) e il piano
approvato da Nello in `docs/design_drafts/team/03...`, `05...` e nel piano
`sequential-seeking-brooks.md`. Ogni comando è stato verificato con il suo
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
| Scrittore | worker Orca, stesso worktree, dopo lo scout | Claude opus high | 1 dispatch più al massimo 2 riparazioni |
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
2. Ogni delivery del batch va riconosciuta con `check --ack <deliveryId>`.
   `check` senza `--wait` ripresenta lo stesso batch finché non viene
   riconosciuto: un `worker_done` non fa avanzare niente da solo.
3. `orca-ide orchestration worker-release --dispatch <dispatchId>`.
4. Solo a rilascio confermato si avvia il worker successivo.

Non c'è mai un secondo worker vivo per "far prima". Scrittore e grafico non
partono insieme: il grafico aspetta il `worker-release` dello scrittore, anche
se in teoria potrebbero lavorare su file disgiunti.

## 1. Controlli preliminari, prima di aprire la issue

Quota e RAM si leggono prima di impegnare qualunque risorsa, non dopo:

```bash
timeout 15 ~/dev/dev-tools/scripts/agent-probe.sh
free -m
swapon --show
```

- Se la finestra di Codex è sotto il 30%, la scheda non parte.
- Se lo swap cresce con un solo worker vivo già misurato, la scheda non parte.
- Se il modello primario di un ruolo non è disponibile, si usa il ripiego
  indicato nella tabella del piano una volta sola. Se anche il ripiego fallisce
  ci si ferma, senza cascata di ripieghi ulteriori.

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

Corpo minimo del file, con il commento "Stato" già presente come blocco unico
che si modifica sul posto (sezione 8):

```markdown
### Intent
[domanda editoriale, senza anticipare una conclusione]

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

```bash
export ISSUE=123
export SLUG="ind-ter-12"
export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python

orca-ide worktree create --name "$SLUG" --issue "$ISSUE" \
  --base-branch "origin/<ramo-2c>" --no-parent --setup skip --json
```

`<ramo-2c>` è il ramo dello strumento `orca_review.py` esteso (fase 2 del
piano, PR 2c). A regime, dopo che Nello ha unito 2a, 2b e 2c, `<ramo-2c>`
diventa `master`. Nessun flag `--agent` qui: senza agente non c'è un
terminale mutante finché non parte il primo worker con `worker-start`.

```bash
orca-ide worktree show --worktree "issue:$ISSUE" --json
```

`worktree show` conferma il collegamento fra worktree e issue prima di
procedere.

## 4. Il namespace del run

```bash
orca-ide orchestration run-create \
  --objective "Issue #$ISSUE: scheda TER-12 arricchita, testo e grafica verificati" \
  --json
```

Da qui in poi `$RUN_ID` è l'id restituito. Ogni `task-create` e ogni
`worker-start` di questa scheda usano lo stesso `$RUN_ID`.

## 5. Scout

```bash
orca-ide orchestration task-create --run "$RUN_ID" --task-title scout \
  --display-name "#$ISSUE scout" \
  --spec "Target: lavoro/ter-12/dossier.json e lavoro/ter-12/fonti.md. Change: dossier deterministico da scripts/editoriale/brief.py e tabella fonti con dato osservato più recente, previsioni 2026, economia della regione più alta e più bassa, fattori che muovono l'indicatore, chi altri ne ha scritto. Colonne fonti.md: istituzione, data di pubblicazione, URL aperto, citazione letterale, limite d'uso; per le previsioni anche orizzonte e cautela. Una voce senza fonte si scrive 'non trovato'. Constraints: sola lettura sul resto del repo, nessuna modifica a content/ o app/. Lancia in parallelo alla tua ricerca: timeout 900 agy --model gemini-3.1-pro-high --dangerously-skip-permissions -p '<consegna del giro web>' --print-timeout 900s < /dev/null > lavoro/ter-12/scout_web.md. Porta in fonti.md solo le voci di cui hai aperto l'URL e trovato la citazione. Observable acceptance: dossier.json presente, fonti.md con tutte le voci obbligatorie o 'non trovato'." \
  --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$SCOUT_TASK" \
  --worktree "issue:$ISSUE" --agent claude --model sonnet --effort medium --json
```

Poi il ciclo della sezione 0: `check --wait`, `check --ack <deliveryId>` su
ogni delivery del batch, `worker-release --dispatch <dispatchId>`. Solo dopo
il rilascio il team leader legge `lavoro/ter-12/fonti.md` e pubblica la riga
di una frase più la fotografia iniziale sulla issue, come materiale per lo
scrittore (non come scaletta).

Ripiego se Claude sonnet non è disponibile: Codex gpt-5.6-sol medium. Ripiego
per `agy` se `gemini-3.1-pro-high` non risponde: `gemini-3.6-flash`. Un solo
ripiego, poi ci si ferma.

## 6. Scrittore

Parte solo dopo il `worker-release` dello scout, mai in parallelo.

```bash
orca-ide orchestration task-create --run "$RUN_ID" --task-title scrittore \
  --display-name "#$ISSUE scrittore" --deps "[\"$SCOUT_TASK\"]" \
  --spec "Target: content/indicators/12.md. Change: articolo in forma libera (LIBERA in app/indicator_texts.py), nessuna sezione predefinita, titoli-affermazione dove il pezzo cambia argomento. Materiale disponibile: riga di una frase e fotografia dalla issue, dimensioni da ter-175 e ter-176, perché da fonti.md o 'non spiegato', attualità da fonti.md, un modello di registro da content/esempi/. Non ricevi: frasi fatte del dossier, polarità come giudizio, cifre di servizio, gergo interno, un angolo già deciso, una scaletta. Vietati: em-dash, en-dash, ';', '…'. Constraints: solo content/indicators/12.md, niente git add/commit, niente asset. Observable acceptance: articolo leggibile come prosa discorsiva, ogni cifra riconducibile al dossier o a fonti.md." \
  --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$WRITER_TASK" \
  --worktree "issue:$ISSUE" --agent claude --model opus --effort high --json
```

Ciclo della sezione 0. Ripiego: Codex gpt-5.6-sol high, una volta sola.

## 7. Grafico

Parte solo dopo il `worker-release` dello scrittore.

```bash
orca-ide orchestration task-create --run "$RUN_ID" --task-title grafico \
  --display-name "#$ISSUE grafico" --deps "[\"$WRITER_TASK\"]" \
  --spec "Target: marcatore <!-- grafico --> dentro content/indicators/12.md, tipo dispersione con=ter-901. Change: una figura sola, disoccupazione contro PIL pro capite, una regione per punto, colori delle ripartizioni, mai l'arancio. Vietato ridisegnare serie, mappa o classifica già nel cruscotto, e vietato costruire un tipo di grafico nuovo in questo pilota. Specifica richiesta: provenienza e unità, anni e dati mancanti, didascalia autonoma, resa a 375 e 768px, tema chiaro e scuro. Constraints: solo il marcatore assegnato, niente testo, niente git add/commit. Observable acceptance: marcatore reso, figcaption con i due indicatori e gli anni, tema scuro corretto." \
  --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$GRAPHIC_TASK" \
  --worktree "issue:$ISSUE" --agent codex --model gpt-5.6-sol --effort high --json
```

Ciclo della sezione 0. Ripiego: Claude sonnet, una volta sola.

## 8. Guardia, commit e draft PR

Fuori da qualunque sandbox che impedisce il commit, il team leader esegue la
guardia e i test, poi committa:

```bash
export WT_PATH="$(git worktree list --porcelain | awk -v s="$SLUG" '$0=="worktree "{p=$2} /worktree /{p=$2} $0 ~ "branch.*"s {print p}')"
git -C "$WT_PATH" diff --check
(cd "$WT_PATH" && DIVARIO_PYTHON="$DIVARIO_PYTHON" \
  bin/py -m unittest discover -s tests -v)
git -C "$WT_PATH" status --short
git -C "$WT_PATH" add content/indicators/12.md lavoro/ter-12/
git -C "$WT_PATH" commit -m "Scheda ter-12 riscritta dal team: <una frase su che cosa dice il pezzo>"
```

`scripts/orca_review.py`, così com'è oggi, pubblica sempre con `--base master`
e non accetta `--label` né `--body-file`: non è ancora lo strumento esteso
della fase 2 (PR 2c). Finché quella PR non è unita, o quando la base del
pilota non è `master`, il team leader apre la PR a mano, in draft, con base
`<ramo-2c>`:

```bash
export PR_BRANCH="$(git -C "$WT_PATH" branch --show-current)"
git -C "$WT_PATH" push -u origin "$PR_BRANCH"

gh pr create --repo nmaiese/diset-viz \
  --draft --base "<ramo-2c>" --head "$PR_BRANCH" \
  --title "Indicatore TER-12: <domanda editoriale>" \
  --body-file /tmp/ter-12-pr-body.md \
  --label run:team
```

`/tmp/ter-12-pr-body.md` contiene testo precedente e testo proposto affiancati,
le fonti nuove di `fonti.md`, l'SHA del commit e `Closes #$ISSUE`. Dopo il
merge di 2c, se la base torna `master`, `scripts/orca_review.py` va esteso con
`--label` e `--body-file` prima di tornare a usarlo qui. Questo runbook non
presume flag che lo script non ha ancora.

La PR resta **in draft** finché il revisore non pubblica un verdetto. Non si
chiama `gh pr ready` prima di questo punto (rilievo 8).

```bash
orca-ide worktree set --worktree "issue:$ISSUE" \
  --comment "Draft PR aperta, attesa revisore Orca" \
  --workspace-status in-review --json
```

## 9. Revisore

Nasce in un worktree nuovo e separato, sul ramo della PR, con un modello di
famiglia diversa da chi ha scritto il testo. Esempio: autore Claude, revisore
Codex. Se l'autore fosse Codex, il revisore è Claude.

```bash
export PR_NUMBER="$(gh pr view "$PR_BRANCH" --repo nmaiese/diset-viz \
  --json number --jq .number)"
export HEAD_SHA="$(gh pr view "$PR_BRANCH" --repo nmaiese/diset-viz \
  --json headRefOid --jq .headRefOid)"
export ITERATION=1
export REVIEW_SLUG="${SLUG}-review-${ITERATION}"

orca-ide orchestration task-create --run "$RUN_ID" --task-title revisore \
  --display-name "PR #$PR_NUMBER review $ITERATION" \
  --deps "[\"$WRITER_TASK\",\"$GRAPHIC_TASK\"]" \
  --spec "Target: PR #$PR_NUMBER al ramo $PR_BRANCH, commit atteso $HEAD_SHA. Change: review read-only, cinque domande (attacco chiaro, perché spiegato, prosa discorsiva non a elenco, coerenza col dossier e con fonti.md, grafico richiamato dal testo). Per ogni no: frase citata, motivo, correzione minima. Prima di pubblicare confronta git rev-parse HEAD nel tuo worktree con l'headRefOid corrente da gh pr view; se sono diversi non pubblicare. Pubblica sempre con gh pr review --comment, mai --approve né --request-changes (stessa identità GitHub dell'autore). Verdetto testuale DA CORREGGERE o PRONTA PER NELLO più lo SHA. Lancia anche, dentro il tuo turno, il secondo parere: timeout 600 opencode run '<consegna, solo domande 1-3 di leggibilità>' -m ollama-cloud/gpt-oss:120b -f <path-articolo> -f <path-brief> < /dev/null, con i due file dentro il worktree perche' opencode rifiuta i path esterni come /tmp. Se l'output e' vuoto il parere non c'e', anche con exit 0. Non bloccante, riporta risposte e disaccordi nel tuo commento senza aprire un altro giro. Aggiorna la sezione Stato nel corpo della issue (gh issue view --json body, poi gh issue edit --body-file). Constraints: nessuna modifica al repo, nessun merge. Ownership: referto su PR e issue." \
  --json

# prima il worktree, da solo: dentro worker-start la creazione puo' superare
# il timeout del dispatch, e allora il prompt non arriva mai all'agente
orca-ide worktree create --name "$REVIEW_SLUG" \
  --repo id:d2ae0385-1020-40e5-8859-7fbd55a33e03 \
  --base-branch "origin/$PR_BRANCH" --no-parent --setup skip --json

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

Ciclo della sezione 0: `check --wait`, `ack` di ogni delivery, poi
`worker-release --dispatch <dispatchId>`.

Nel proprio worktree il revisore verifica prima di pubblicare:

```bash
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
orca-ide orchestration task-create --run "$RUN_ID" --task-title riparazione \
  --deps "[\"$REVIEW_TASK\"]" \
  --spec "Target: <soli path indicati dal revisore>. Change: correggere solo i rilievi confermati nel commento PR #$PR_NUMBER, iterazione $ITERATION. Constraints: nessun allargamento di scopo, niente file oltre quelli indicati, niente git add/commit. Observable acceptance: rilievi risolti, test del repository ancora verdi." \
  --json

orca-ide orchestration worker-start --run "$RUN_ID" --task "$REPAIR_TASK" \
  --worktree "issue:$ISSUE" --agent claude --model opus --effort high --json
```

Ciclo della sezione 0. Al `worker_done` il team leader rilancia guardia e
test, committa, fa push:

```bash
git -C "$WT_PATH" add <soli-file-riparati>
git -C "$WT_PATH" commit -m "Scheda ter-12, correzioni della review $ITERATION: <quali>"
git -C "$WT_PATH" push
gh issue edit "$ISSUE" --repo nmaiese/diset-viz \
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
gh pr ready "$PR_NUMBER" --repo nmaiese/diset-viz
gh issue edit "$ISSUE" --repo nmaiese/diset-viz --add-label gate-b
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
gh issue view "$ISSUE" --repo nmaiese/diset-viz --json body --jq .body > /tmp/ter-12-body.md
# sostituire il blocco "## Stato" fino alla fine del file
gh issue edit "$ISSUE" --repo nmaiese/diset-viz --body-file /tmp/ter-12-body.md
```

Lo schema del blocco è sempre lo stesso:

```markdown
## Stato
Fase: <issue aperta | scout | scrittore | grafico | draft PR | review 1 | riparazione | review 2 | PRONTA PER NELLO | merge>
SHA: <sha corrente o nessuno>
Prossimo passo: <descrizione breve>
Chi lo fa: <team leader | scout | scrittore | grafico | revisore>
```

I commenti della issue restano per il materiale (il brief, i verdetti), mai per
lo stato. Label, commenti sulla PR, `TASK.md` e la scheda Orca sono prove o
viste derivate: rimandano alla sezione Stato, non la ripetono.

## 13. Ripresa dopo un'interruzione

Non esiste un trigger GitHub su Orca: `orca-ide automations` accetta solo
preset temporali, cron o RRULE, non eventi `pull_request` (verificato con
`orca-ide automations create --help`). Se la sessione del team leader si
interrompe fra un push e una review, la ripresa parte da due comandi, senza
script nuovi:

```bash
gh issue list --repo nmaiese/diset-viz -l run:team \
  --json number,title,body

gh pr list --repo nmaiese/diset-viz --draft -l run:team \
  --json number,headRefOid,reviews
```

La prima elenca le issue aperte del team con il loro commento Stato dentro
`body`. La seconda elenca le PR draft ancora in attesa, con lo SHA e le review
già pubblicate: uno SHA in `headRefOid` più recente dell'ultimo verdetto
significa che serve un nuovo revisore prima di procedere.

## 14. Pulizia dopo il merge

Il merge resta sempre umano, di Nello: su `master` un merge equivale a un
deploy.

```bash
orca-ide orchestration worker-release --dispatch "$REVIEW_DISPATCH" --json
bin/py scripts/orca_clean.py "$REVIEW_SLUG"
# dopo il merge confermato da Nello
bin/py scripts/orca_clean.py "$SLUG"
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
| scout | `lavoro/<chiave>/dossier.json`, `lavoro/<chiave>/fonti.md` | toccare `content/`, `app/`, promuovere fonti nel registro |
| scrittore | il file contenuto assegnato | asset, config, `git add`/`commit` |
| grafico | il marcatore grafico assegnato | testo, `git add`/`commit` |
| revisore | niente nel worktree indicatore, referto nel proprio worktree separato | entrare nel worktree dell'autore o correggere durante la review |
| riparatore | solo i path del rilievo assegnato | refactor o pulizie non richieste |
| team leader | integrazione, `git add`/`commit`/`push`, PR, label, commento Stato | scrivere mentre un worker possiede ancora quel path |

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
| push su `master` o sul ramo base del pilota | GitHub Actions `ci.yml` | stessi due job | runner e download |
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
