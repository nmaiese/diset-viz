---
name: pipeline-close-run
description: >-
  Come uno stadio della catena Divario Italia chiude la propria run: diario
  prima della pull request, cancello, merge delegato. Da usare alla fine di
  ogni run di scout, hunter, curator, writer, reviewer o verificatore.
---

# Chiudere una run della catena

La sequenza e' identica per tutti gli stadi, e per questo vive qui una volta
sola: era ripetuta parola per parola in sei prompt, cioe' la forma di drift che
questo progetto ha gia' pagato (`docs/AUTONOMOUS_PIPELINE.md` racconta il caso
`analyst_notes.json`). La regola che conta sta in `docs/AGENT_CONTRACT.md`,
che resta vincolante: questa pagina e' la procedura, non il contratto.

## 1. La suite, tutta

```bash
.venv/bin/python -m unittest discover -s tests
```

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
l'unica cosa che lega questa riga a come finira'.

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
gh pr create --base master --title "..." --body "..."
.venv/bin/python scripts/pipeline_merge.py --stage <stadio> --pr <numero> --run-id <run_id>
```

Il tuo modo di merge (`auto` o `checks`) e' un ordine al passo di merge, non un
permesso per te: **non fondi mai da solo**, in nessuna forma di `gh pr merge`.
`--auto` in particolare non aspetta niente su questo repository: con
`allow_auto_merge` spento e master non protetto fonde subito, e un probe l'ha
dimostrato con i test ancora in corsa. L'attesa dei check vive in
`pipeline_merge.py`, che prima di fondere ri-esegue il cancello per conto suo:
un merge che si fida del verdetto raccontato dall'agente non protegge niente.

Nel corpo della pull request: che cosa hai fatto, con i numeri veri, e che cosa
hai deciso di NON fare, con il perche'. Nessun trailer `Co-Authored-By`.
