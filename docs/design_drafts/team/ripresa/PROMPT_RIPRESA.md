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

## Dove eravamo (28 settembre, sera, dopo il pilota)

Tutto è su GitHub: le issue portano lo Stato nel corpo, le PR hanno le review pubblicate.

1. **#289 (2a, brief e skill):** PRONTA PER NELLO, ready più `gate-b`.
2. **#290 (2b, guardia):** tre giri fatti.
   - La review 3 dà DA CORREGGERE su un punto solo: l'arrotondamento al centinaio va confrontato
     con dossier e `fonti.md`, non con tutta la matrice. Più due test.
   - La correzione è già provata dal revisore.
   - **Nello decide** se fare un quarto giro o unire così e riparare dopo. La spec del quarto
     giro si scrive dalla review 3.
3. **#291 (2c, `orca_review.py`):** PRONTA PER NELLO dopo tre giri (`b1ac953b`), ready più `gate-b`.
   Il difetto di `--scheda` trovato sul pilota è riparato. Le Note della review 3 sono per una
   pulizia dopo il merge.
4. **Pila allineata:** la 2c contiene la 2b, che contiene la 2a (`bb1464db`). Il ramo del
   pilota contiene la 2c allineata.
5. **#293 (pilota ter-12):** PRONTA PER NELLO dopo tre giri, ready più `gate-b`, `8be35ae2`, CI
   verde. L'ultimo commit tocca solo il test della guardia, non il testo.
   - La valutazione è `docs/design_drafts/team/09_valutazione_pilota_ter12.md`.
   - La lettura cieca preferisce il nuovo per le fonti e il vecchio per l'attacco e la prosa.
   - **Nello legge e decide.** Se convince, unisce in ordine #289, #290, #291 e #293.
6. **Prima della prossima scheda (ter-281):** brief più corto (una cifra per idea), un tetto di
   parole indicativo di 600-800, e la domanda 3 del revisore estesa alla lunghezza.
7. **Dopo il giudizio di Nello:** la fase 5 del piano (CLAUDE.md, AGENTS.md, README,
   WORKFLOW_ORCA, INDICATOR_PAGES, rules, label `run:team`, template della issue).
8. **Da chiedere a Nello:**
   - la pulizia dei worktree `rev-*` (compreso il doppione `rev-285-2-2`), di `ind-ter-12`
     dopo il merge e dei terminali Orca vecchi;
   - la nota su `< /dev/null` in dev-tools;
   - la quarantena stabile delle tre skill.

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
