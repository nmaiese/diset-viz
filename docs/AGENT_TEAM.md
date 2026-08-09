# Agent Team editoriale

Questo branch affianca a `indicatore-lite` un esperimento basato sugli Agent
Team nativi di Claude Code. Non sostituisce ancora la pipeline corrente.

## Architettura

La sessione principale è l'editor-in-chief e coordina cinque sessioni autonome:

| teammate | responsabilità | scrive file |
| --- | --- | --- |
| `data-editor` | evidenza quantitativa e limiti | no |
| `source-researcher` | fonti e contesto verificabile | no |
| `search-strategist` | intento, titolo e copertura | no |
| `data-journalist` | angolo e bozza strutturata | no |
| `skeptical-editor` | stress test e verdetto | no |

Solo il lead esegue `lab.dossier`, salva gli artefatti, lancia
`lab.controlla`, pubblica e avvia i test. I teammate comunicano direttamente e
usano la lista task condivisa. Non sono ammessi team annidati o subagenti.

## Avvio

Aprire una sessione Claude Code nuova e invocare:

`/redazione-indicatore ter-6`

La skill `redazione-indicatore` contiene protocollo, nomi, task e criteri di
uscita. Il progetto abilita l'esperimento con
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` e usa la modalità `in-process`,
compatibile anche con terminale integrato e Windows Terminal.

Una sessione gestisce un solo indicatore. Il team non è ripristinato da
`/resume`: dopo una ripresa il lead deve creare nuovi teammate e riagganciare i
task rimasti.

## Monitoraggio

I subject dei task seguono il contratto:

`[redazione:<ruolo>:<fase>] <codice> - <titolo>`

Gli hook nativi `TaskCreated` e `TaskCompleted` passano per
`.claude/hooks/team_monitor.py`, che li converte nel contratto già usato da
`/_pipeline/beat`. Non legge né modifica `~/.claude/teams`, perché quella
directory è stato interno e transitorio del runtime.

La task `[redazione:lead:chiusura]` è la sentinella. Il suo completamento invia
il consuntivo e chiude la run nella dashboard.

Se `PIPELINE_INGEST_URL` o `PIPELINE_INGEST_TOKEN` non sono presenti, il team
continua senza telemetria. Per ispezionare i payload senza rete:

```bash
TEAM_MONITOR_STDOUT=1 python3 .claude/hooks/team_monitor.py <<'JSON'
{"hook_event_name":"TaskCreated","session_id":"abc12345","team_name":"session-abc12345","cwd":".","task_id":"task-1","task_subject":"[redazione:data-editor:ricerca] ter-6 - prova"}
JSON
```

## Regola di promozione

Mantenere `indicatore-lite` come baseline fino a cinque canary diversi per
struttura dei dati. Confrontare qualità, rilievi gravi, costo, turni, tempo e
percentuale di articoli fermati. Il team diventa default solo se migliora la
qualità senza introdurre regressioni nei controlli deterministici o nella
dashboard.

Canary iniziali: `ter-6`, `ter-13`, `ter-167`, `bes-SDG-310` e un indicatore
provinciale il cui livello predefinito è provincia.
