---
paths:
  - "scripts/pipeline_*.py"
  - "scripts/agent_guard.py"
  - "data/pipeline/**"
  - "data/discovery/**"
  - ".claude/agents/**"
  - ".claude/skills/**"
---

# La catena autonoma: la costituzione in breve

Il documento che possiede la materia e'
[`docs/AUTONOMOUS_PIPELINE.md`](../../docs/AUTONOMOUS_PIPELINE.md); il
contratto di ogni run e' [`docs/AGENT_CONTRACT.md`](../../docs/AGENT_CONTRACT.md).
Queste sono le regole che valgono sempre:

- **Un lanciatore, lavoro per-indicatore in parallelo, ogni run in un worktree.**
  `scripts/pipeline_launch.py` legge il dossier per-indicatore e le code e
  restituisce una lista prioritizzata di lanci (produttore e verificatore
  per-indicatore, ammissione batch); il suo contratto da agente e'
  `.claude/agents/launcher.md`. Non c'e' piu' un dispatcher a uno-stadio-per-tick
  ne' il lock una-PR-aperta. Indicatori diversi toccano file diversi, ma quella
  separazione vale per i **percorsi**, non per l'indice git ne' per HEAD: un
  checkout condiviso ne ha uno solo, e due run che se li contendono si spostano
  il branch sotto i piedi. Per questo ogni run apre il proprio **git worktree**
  isolato (`scripts/pipeline_workspace.py`, keyed sul `run_id`), non solo un branch
  con nome diverso. Tre ruoli soli: ammissione (scout+hunter+promoter), produttore
  (curator+writer+reviewer), verificatore.
- **Ogni registro e' un file per record**: `content/indicators/`,
  `data/pipeline/runs/`, `data/pipeline/verifiche/`. Mai ricompattarli in un
  file unico: il conflitto tra due stadi non e' improbabile, e' impossibile, e
  deve restare cosi'.
- **Una run e' il suo `run_id`, mai il numero della PR.** La riga di diario
  viaggia dentro la pull request, quindi non puo' conoscerne il numero.
  `pipeline_log.py --write` conia l'id, `pipeline_merge.py --run-id` unisce le
  due meta'.
- **Il cancello non e' consultivo.** Ogni stadio scrive solo i percorsi di
  `pipeline_gate.STAGE_PATHS`; non allargarli per far passare qualcosa. La
  barra finale distingue directory da file, ed e' cio' che impedisce la fuga.
  Il cancello gira anche in CI sui branch `automation/*`, e la guardia
  per-agente (`scripts/agent_guard.py`, dichiarata nel frontmatter di ogni
  agente) applica lo stesso perimetro al momento del gesto.
- **Nessuno stadio aspetta un umano.** Ogni stadio fonde sul cancello locale,
  che gira la suite intera prima del merge. La CI remota non parte sulle PR
  aperte via il GitHub MCP, quindi aspettarla (`checks`) non comprava un
  verdetto indipendente ma un deadlock. Il controllo e' perimetro + cancello +
  suite, mai un'approvazione.
- **Mai `gh pr merge --auto`.** Non aspetta su questo repository: fonde subito.
  L'attesa vive in `scripts/pipeline_merge.py`.
- **La PR si apre via REST, mai con `GH_REPO`.** `gh pr create` e' GraphQL e non
  vede il remote proxato; `pipeline_merge.py --open` la apre sullo slug ricavato
  da `repo_slug`, sulla stessa REST del merge. `GH_REPO` corto-circuita
  `repo_slug`, gli rompe un test e causa rifiuti orfani su master: non impostarlo.
- **Il vivo del cruscotto passa dal sito, non da file locali.** Battiti e PR
  aperte finiscono nel SQLite che Litestream replica su GCS (`app/pipeline_state.py`),
  scritti dai POST degli agenti a `/_pipeline/beat` (segreto `PIPELINE_INGEST_TOKEN`).
  Gli agenti girano su macchine effimere separate dal server: i vecchi battiti su
  file, ignorati da git, non lo raggiungevano, ed e' per quello che `/_pipeline`
  sembrava morto. Il committato (dossier + diario) resta la storia.
- **Il rientro e' guidato dai dati, mai dal calendario.** Una curatela scade
  quando la fonte pubblica un anno nuovo (`data_year`); una rilettura quando
  le cifre dell'articolo si rinfrescano (`reviewed_vintage`).
- **Gli script della catena sono stdlib puro** e devono restarlo: un agente
  cloud li esegue su un checkout fresco, prima che esista un venv.
- Prima di cambiare modello, prompt, rubriche o hook degli agenti: il giro di
  canary di [`docs/CANARY.md`](../../docs/CANARY.md) e le eval in `evals/`.
