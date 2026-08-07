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
  restituisce una lista prioritizzata di lanci (verificatore e reader-editor
  per-indicatore, ammissione batch). **Non ha piu' un agente lanciatore**:
  `launcher.md` era un workflow scritto in prosa, e il coordinamento in un
  workflow costa zero token. La scrittura degli articoli non passa piu' di qui,
  la fa `.claude/workflows/produci-indicatori.js`. Non c'e' un dispatcher a uno-stadio-per-tick
  ne' il lock una-PR-aperta. Indicatori diversi toccano file diversi, ma quella
  separazione vale per i **percorsi**, non per l'indice git ne' per HEAD: un
  checkout condiviso ne ha uno solo, e due run che se li contendono si spostano
  il branch sotto i piedi. Per questo ogni run apre il proprio **git worktree**
  isolato (`scripts/pipeline_workspace.py`, keyed sul `run_id`), non solo un branch
  con nome diverso. Tre ruoli, non piu' quattro: ammissione
  (scout+hunter+promoter+curator), verificatore, reader-editor. La composizione
  non si ricopia: la mappa da vecchio stadio a ruolo vivo e'
  `pipeline_launch.ROLE_OF_STAGE`, e sia `pipeline_status` sia
  `pipeline_monitor` la importano. **Il produttore non
  esiste piu' come agente**: scrivere un articolo e' passato all'officina, dove
  lo fanno quattro tipi con pochi strumenti dentro un workflow, a un ventesimo
  del costo. Ammissione a monte e i due critici a valle restano agenti perche'
  esercitano un giudizio che nessun workflow puo' rendere deterministico. I due
  per-indicatore lavorano **l'indicatore che il piano gli passa e nessun
  altro**: e' cio' che
  rende sicuro aprirne piu' d'uno per tick, perche' bersagli distinti scrivono
  file dal nome distinto. Una sessione che si scegliesse un lotto dalla propria
  coda sceglierebbe gli stessi record dell'altra.
- **Ogni registro e' un file per record**: `content/indicators/`,
  `data/pipeline/runs/`, `data/pipeline/verifiche/`, `data/pipeline/letture/`. Mai ricompattarli in un
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
- **La PR si apre via REST, e `GH_REPO` e' ignorato.** `gh pr create` e' GraphQL e
  non vede il remote proxato; `pipeline_merge.py --open` la apre sullo slug
  ricavato da `repo_slug`, sulla stessa REST del merge. `repo_slug` ricava lo slug
  **sempre** dal remote: `GH_REPO` non e' piu' un override (da environment
  ereditato apriva o fondeva sul repo sbagliato, i rifiuti orfani su master).
- **Il vivo del cruscotto passa dal sito, non da file locali.** Battiti e PR
  aperte finiscono su Supabase Postgres (`app/pipeline_state.py` via `app/db.py`;
  Litestream ritirato con la Fase 4), scritti dai POST degli agenti a
  `/_pipeline/beat` (segreto `PIPELINE_INGEST_TOKEN`).
  Gli agenti girano su macchine effimere separate dal server: i vecchi battiti su
  file, ignorati da git, non lo raggiungevano, ed e' per quello che `/_pipeline`
  sembrava morto. Il committato (dossier + diario) resta la storia.
- **Il rientro e' guidato dai dati, mai dal calendario.** Una curatela scade
  quando la fonte pubblica un anno nuovo (`data_year`); una rilettura quando
  le cifre dell'articolo si rinfrescano (`reviewed_vintage`).
- **Gli script della catena sono stdlib puro** e devono restarlo: un agente
  cloud li esegue su un checkout fresco, prima che esista un venv.
- **Un file di agente e' un contratto, non una cronaca.** Quattro cose e basta:
  che cosa **ricevi**, che cosa **restituisci**, che cosa ti e' **vietato**,
  e la regola operativa che nessuno strumento puo' imporre al posto tuo. Il
  perche' storico (quanto e' costata una run, quale difetto ha trovato una
  lettura) sta nei commenti del workflow e nei documenti, con un puntatore: e'
  contesto che il modello rilegge a ogni turno di ogni invocazione, e che un
  lettore umano legge una volta sola. Due corollari che sono gia' costati:
  **il background operativo si scrive dove il codice lo genera** (per lo
  scrittore e' il pacchetto, che non puo' divergere dalla voce), mai in copia
  nel prompt, perche' la copia diverge e l'ha gia' fatto; e **una restrizione
  che non funziona non si dichiara**, come `disallowedTools: advisor`, che non
  blocca niente perche' l'advisor non e' un tool di quella lista. Il divieto
  che regge e' un hook (`.claude/hooks/no_advisor.py`).
- Prima di cambiare modello, prompt, rubriche o hook degli agenti: il giro di
  canary di [`docs/CANARY.md`](../../docs/CANARY.md) e le eval in `evals/`.
