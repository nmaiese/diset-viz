# Prompt per riprendere il team editoriale

Da incollare in una sessione nuova di Claude Code aperta in
`/home/nilo/dev/sites/divarioitalia/.orca/worktrees/divarioitalia/orca-team-test`
(ramo `nmaiese/orca-team-test`, commit solo locali).

---

Riprendi il lavoro del team editoriale di Divario Italia. Il tuo ruolo è quello del team
leader. Prima leggi:
- `STATUS.md`, sezione 4, le voci del 28 settembre;
- `docs/design_drafts/team/PIANO.md`, il piano approvato;
- `docs/design_drafts/team/04_orca_github.md`, il runbook;
- `docs/WORKFLOW_ORCA.md` §6, i guasti misurati e le quote dei provider.

Poi guarda lo stato su GitHub, perché le issue sono l'unico posto dello stato:
`gh issue list -l run:team --json number,title,body` e
`gh pr list -l run:team --json number,isDraft,headRefOid,reviews`.

## Vincoli di Nello, dalla sera del 28 settembre

- **Niente Claude e niente Codex come worker.** Si usano i provider rimasti, dopo averne
  controllato la quota con `ripresa/ping_quote.sh`: Antigravity (`agy`, gemini-3.1-pro-high o
  3.8-flash-high), OpenCode Zen (`opencode/big-pickle`, `nemotron-3-ultra-free`,
  `mimo-v2.6-flash-free`) e ollama-cloud (`gpt-oss:120b`, `nemotron-3-ultra`, `gemma4:31b`,
  una richiesta alla volta).
- **Headless, lanciati dal leader:** `timeout N opencode run "<msg>" -m <modello> -f <file nella
  cwd> < /dev/null` e `timeout N agy --model <id> --dangerously-skip-permissions -p "..."
  --print-timeout Ns < /dev/null`, in background.
- **Il revisore non pubblica.** Rende il testo della review. Il leader controlla che
  `git rev-parse HEAD` coincida con `headRefOid`, poi pubblica con
  `gh pr review <n> --comment --body-file`. Mai `--approve` né `--request-changes`.
- **Commit:** li fa il leader, con `git add` per percorsi espliciti, senza trailer
  `Co-Authored-By`. Push dei rami di lavoro sì. Merge, push su `master` e cancellazione di rami
  sono di Nello.
- **Test:** la suite intera su questa macchina va in segfault. Si lanciano solo test mirati, con
  `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m unittest <moduli>`.
  La CI della PR è il controllo completo.

## Dove eravamo

1. **#291 (2c):** PRONTA PER NELLO.
2. **#289 (2a) e #290 (2b):** review 2 lanciate in headless.
   - Le spec sono `ripresa/spec_review2_289_headless.txt` (Antigravity) e `…_290_…` (big-pickle).
   - Se nella PR non c'è una review più recente di quelle delle 16:01 (#289) e delle 15:12
     (#290), la review 2 non è stata pubblicata: rilanciala con la stessa spec.
   - Il verdetto DA CORREGGERE porta a una riparazione con un modello diverso dall'autore, poi a
     una review 3. PRONTA porta a `gh pr ready`, alla label `gate-b` e allo Stato della issue
     (#286 e #287).
3. **Allineare la pila** con merge e senza force push: `origin/nmaiese/strumento-2a-brief` in
   `nmaiese/strumento-2b-guardia`, poi 2b in `nmaiese/strumento-2c-review`, poi push.
4. **Pilota ter-12, issue #292.** I ruoli sono nel corpo della issue, la copia è
   `ripresa/issue_292_corpo.md`.
   - Lo scout è partito fuori dal worktree con `ripresa/spec_scout_ter12.md`. Se i suoi output
     non sono in `ripresa/scout_ter12/`, rilancialo.
   - Poi crea il worktree `ind-ter-12` dalla cima della pila (runbook, passo 2). Il dossier si
     rigenera con `bin/py -m scripts.editoriale.brief ter-12 --out lavoro/ter-12/dossier.json`.
     Il leader verifica le citazioni di `fonti.md` aprendo gli URL.
   - Poi il brief del leader, lo scrittore, il grafico (dispersione con ter-901), la guardia, la
     PR draft con base il ramo 2c, e il revisore con il secondo parere.
   - Alla fine la lettura cieca e il giudizio di Nello.
5. **Dopo il pilota:** la fase 5 del piano (CLAUDE.md, AGENTS.md, README, WORKFLOW_ORCA,
   INDICATOR_PAGES, rules, label `run:team`, template della issue).
6. **Da chiedere a Nello:**
   - la pulizia dei worktree `rev-*`, compreso il doppione `rev-285-2-2`;
   - la nota su `< /dev/null` in dev-tools;
   - la quarantena stabile delle tre skill.
