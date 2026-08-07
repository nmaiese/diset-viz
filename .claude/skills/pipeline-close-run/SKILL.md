---
name: pipeline-close-run
description: >-
  Come uno stadio della catena Divario Italia chiude la propria run: diario
  prima della pull request, cancello, merge delegato. Da usare alla fine di
  ogni run di admissions, verificatore o reader-editor.
---

# Chiudere una run della catena

La sequenza e' identica per tutti gli stadi, e per questo vive qui una volta
sola: era ripetuta parola per parola in sei prompt, cioe' la forma di drift che
questo progetto ha gia' pagato (`docs/AUTONOMOUS_PIPELINE.md` racconta il caso
`analyst_notes.json`). La regola che conta sta in `docs/AGENT_CONTRACT.md`,
che resta vincolante: questa pagina e' la procedura, non il contratto.

## 1. La suite veloce, come primo controllo

```bash
bin/py -m unittest discover -s tests/unit
```

Non la suite intera: il cancello (passo 3) la fa gia' girare tutta, e il
passo di merge la ripete una terza volta di proposito (non fidarsi del
verdetto auto-riportato). Farla girare tutta anche qui non aggiunge
copertura, solo tempo: la sola cosa che ha senso prendere prima di scrivere
il diario e' un errore grossolano (JSON rotto, import rotto), non i test
catalogo-largo che il cancello controllera' comunque tra due passi.

## 2. Il diario, PRIMA della pull request

Registra la run **anche se non hai prodotto niente**: `nothing` e' l'unica cosa
che distingue "ho controllato e non c'era niente da fare" da "non sono partito",
ed e' il caso in cui il diario serve di piu'.

```bash
python3 scripts/pipeline_log.py --write --stage <stadio> --outcome <esito> \
    --summary "..." --detail "..." --queue-before <N> --queue-after <N>
```

L'ordine conta: la riga viaggia dentro la pull request, quindi va committata
prima che la pull request esista. Per questo non scrivi `--pr`, che in quel
momento non c'e' ancora, ed e' esattamente il motivo per cui appaiare le due
meta' della run sul numero della pull request non funzionava.

Il comando stampa un `run_id`. **Prendilo e passalo al passo di merge**: e'
l'unica cosa che lega questa riga a come finira'. Senza `--run-id` lo script
si ferma (`--mint-run-id` esplicito se davvero non ne serve uno, come
`scripts/pipeline_launch.py` quando registra il proprio tick): un id coniato in
silenzio lascia un file orfano nel worktree, che poi blocca il merge come
"worktree non pulito".

Ogni cifra dentro `--detail` va riletta **dal file che hai scritto tu** proprio
ora (il tuo registro in `data/pipeline/`), mai da un draft che hai in mente: e'
lo stesso drift che questo passo esiste per impedire, solo tra il diario e cio'
che hai prodotto invece che tra la prosa e il file morto.

## 3. Il cancello

```bash
python3 scripts/pipeline_gate.py --stage <stadio>
```

Se e' `blocked`, sistemi il tuo lavoro. **Mai il cancello, mai un test**: il
perimetro che conta e' `pipeline_gate.STAGE_PATHS`, e uno stadio che lo
allarga per passare ha smesso di essere uno stadio.

Il cancello non diventa rosso perche' master si e' mosso: il diff e' misurato
contro l'antenato comune. L'unico conflitto che puo' ancora raggiungerti e'
due stadi sullo stesso file, e la regola e' il passo 3-bis del contratto.

## 4. La pull request e il merge, delegato

```bash
git push -u origin HEAD
PR=$(python3 scripts/pipeline_merge.py --open \
       --stage <stadio> --head <il tuo branch> --run-id <run_id> --title "..." --body "...")
bin/py scripts/pipeline_merge.py --stage <stadio> --pr "$PR" --run-id <run_id>
```

Due interpreti, e la differenza e' reale: l'apertura usa `python3` perche' e'
stdlib pura e deve funzionare su un checkout fresco, prima che esista un venv;
il merge rilancia il cancello, che importa l'app, quindi ha bisogno delle
dipendenze.

**Per il secondo si scrive `bin/py`, mai `.venv/bin/python`.** Il venv c'e'
quasi sempre (`pipeline_workspace.py --open` collega quello del checkout
principale), ma quando manca `.venv/bin/python` esce 127 con "no such file or
directory" e chi legge non sa che cosa cercare. `bin/py` prova i percorsi in
ordine e, se non ne trova nessuno, dice quali ha provato e come crearne uno.
Sono quattro fallimenti in due giorni in `data/pipeline/tool_failures.jsonl`.

La PR si apre con `pipeline_merge.py --open`, non con `gh pr create`, e **senza
`GH_REPO`**: `gh pr create` e' GraphQL e non riconosce il remote proxato, e
`GH_REPO` (il rimedio che si era diffuso) corto-circuita `repo_slug`, gli rompe un
test e causa rifiuti orfani "il cancello e' rosso" su master. Lo slug lo ricava
gia' `repo_slug` dal remote, e `--open` apre la PR sulla stessa REST del merge.

Il tuo modo di merge (`auto` o `checks`) e' un ordine al passo di merge, non un
permesso per te: **non fondi mai da solo**, in nessuna forma di `gh pr merge`.
`--auto` in particolare non aspetta niente su questo repository: con
`allow_auto_merge` spento e master non protetto fonde subito, e un probe l'ha
dimostrato con i test ancora in corsa. L'attesa dei check vive in
`pipeline_merge.py`, che prima di fondere ri-esegue il cancello per conto suo:
un merge che si fida del verdetto raccontato dall'agente non protegge niente.

Nel corpo della pull request: che cosa hai fatto, con i numeri veri, e che cosa
hai deciso di NON fare, con il perche'. Nessun trailer `Co-Authored-By`.

## 5. Chiudi il worktree

```bash
python3 scripts/pipeline_workspace.py --close --run-id <run_id>
```

Hai lavorato in un worktree isolato (passo 1 del contratto), non nel checkout
principale: chiuderlo dopo il merge non lascia un albero orfano sul disco. Il
passo di merge scrive su master da un worktree suo, quindi e' sicuro chiuderlo qui.
