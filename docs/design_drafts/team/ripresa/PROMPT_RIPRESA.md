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

## Dove eravamo (28 settembre, notte)

Strumenti e pilota sono **uniti su `master`**: #289, #290, #291, #293. Le issue #286, #287,
#288 e #292 sono chiuse. Nello ha giudicato ter-12 buono, "anche se migliorabile": l'attacco del
vecchio testo era migliore.

Da fare, in ordine:
1. **Fase 5** del piano, ora sbloccata: CLAUDE.md, AGENTS.md, README, WORKFLOW_ORCA (la deroga
   "un agente alla volta nel worktree dell'indicatore, revisore sempre fuori", e il flusso
   headless), INDICATOR_PAGES, `.claude/rules/editorial.md`, FAMIGLIE_INDICATORI, la label
   `run:team`, il template della issue. L'inventario riga per riga è `07_documenti_da_aggiornare.md`.
2. **Fase 4:** ter-281, da `master`, con tre correzioni che vengono dal pilota:
   - brief più corto, una cifra per idea;
   - tetto di parole indicativo di 600-800;
   - domanda 3 del revisore estesa alla lunghezza e all'attacco.
3. Il limite di disegno della guardia: una cifra giusta attribuita al territorio sbagliato
   passa. Va progettato, non riparato in due righe.
4. Le Note non bloccanti delle review 3 e 4 di #290 e #291, in un passaggio di pulizia.

## Come si lancia un ruolo in headless (le lezioni della sera)

- **OpenCode:** `cd <worktree> && timeout 2400 opencode run "$(cat spec)" -m opencode/big-pickle
  < /dev/null > out 2> err`.
  - Nella spec va scritto "niente fuori dal worktree, niente percorsi assoluti, neanche
    /dev/null o /tmp, temporanei in `.<nome>/`".
  - Due `opencode run` non partono nello stesso istante (database bloccato).
- **Antigravity:** `timeout 2400 agy --model gemini-3.1-pro-high --dangerously-skip-permissions
  -p "$(cat spec)" --print-timeout 2350s < /dev/null`.
  - Lascia file di lavoro nella radice: spostali prima del `git add`.
  - In una riparazione elenca le correzioni una per una, altrimenti ne salta.
- **Le citazioni** si verificano con `ripresa/verifica_fonti.py`, la figura con
  `ripresa/shot_figura.py`.
