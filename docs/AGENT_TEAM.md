# Agent Team editoriale

L'Agent Team nativo di Claude Code è il runtime di riferimento per le run
**presidiate**: un lead che coordina teammate paralleli, che si parlano e
condividono una lista di task (piano di platform, `docs/30-piano.md` §D8 e
§6.5). Il workflow `indicatore-lite` resta la baseline **schedulata** finché la
regola di promozione in fondo non decide.

## Architettura

La sessione principale è l'editor-in-chief e coordina cinque sessioni autonome.
Le definizioni vivono nel plugin `motore` di `~/dev/platform/plugin/agents/`;
il tipo porta il prefisso `motore:`, il nome del teammate resta senza prefisso
perché i subject dei task e il monitor usano quello.

| teammate | tipo | responsabilità | scrive file |
| --- | --- | --- | --- |
| `data-editor` | `motore:data-editor` | evidenza quantitativa e limiti | no |
| `source-researcher` | `motore:source-researcher` | fonti e contesto verificabile | no |
| `search-strategist` | `motore:search-strategist` | intento, titolo e copertura | no |
| `data-journalist` | `motore:data-journalist` | angolo e bozza strutturata | no |
| `skeptical-editor` | `motore:skeptical-editor` | stress test e verdetto | no |

Solo il lead esegue `lab.dossier`, salva gli artefatti, lancia
`lab.controlla`, pubblica e avvia i test. L'exit code 0 di `lab.controlla`
non basta: `non_trovate` e `link_inesistenti` devono essere zero,
`bloccanti` deve essere vuoto e la pubblicazione deve usare esclusivamente il
percorso `bozza_salvata` restituito dal controllo. I teammate comunicano
direttamente e usano la lista task condivisa. Non sono ammessi team annidati o
subagenti. Il frontmatter `skills` non viene applicato ai teammate: il prompt
di spawn ordina a ciascuno di invocare le skill nominate nella sua definizione.

## Avvio

Aprire una sessione Claude Code nuova e invocare:

`/redazione-indicatore ter-6`

La skill `motore:redazione-indicatore` (nel plugin, `skills/redazione-indicatore/SKILL.md`)
contiene protocollo, nomi, task e criteri di uscita. Il progetto abilita i team
con `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` e usa
la modalità `in-process`, compatibile anche con terminale integrato e Windows
Terminal.

Una sessione gestisce un solo indicatore. Il team non è ripristinato da
`/resume`: dopo una ripresa il lead deve creare nuovi teammate e riagganciare i
task rimasti.

## Memoria selettiva

Solo `source-researcher` e `skeptical-editor` dichiarano `memory: project`.
Le definizioni stanno nel plugin, le memorie restano **in questo repo**,
versionate:

- `.claude/agent-memory/source-researcher/`
- `.claude/agent-memory/skeptical-editor/`

Claude Code garantisce la memoria nativa quando la definizione gira come
subagente: abilita gli strumenti della memoria e carica l'inizio di
`MEMORY.md`. Nel percorso Agent Team la documentazione garantisce invece
`tools`, `model` e corpo della definizione, ma non documenta `memory`.
Per questo il contratto non dipende da un comportamento implicito: il teammate
legge il file con `Read`, propone `memory_candidates` e il lead è l'unico che
promuove le voci. Gli strumenti generici `Write`, `Edit` e `Bash` restano
fuori dall'allowlist dei teammate, e `tests/integration/test_docs_match_the_code.py`
lo verifica sulle definizioni del plugin.

La memoria conserva percorsi di ricerca, qualità delle fonti, endpoint,
comparabilità, difetti ricorrenti e falsi positivi. Non conserva fatti correnti,
classifiche, conclusioni del singolo articolo o preferenze stilistiche. Ogni
voce ha data di verifica, data di ricontrollo, ambito, prova e limiti.

## Routine cloud

Una Routine crea una nuova sessione e clona la branch predefinita a ogni run.
Quindi la memoria di progetto è disponibile nel cloud, ma un aggiornamento
prodotto dalla run diventa visibile alle run future solo dopo il merge della
relativa PR. La Routine non deve scrivere direttamente sulla branch predefinita (`master`
in questa repository) e non deve usare la pipeline baseline come fallback
silenzioso. Nel cloud il plugin `motore` va reso disponibile alla sessione
(marketplace `platform` su GitHub `nmaiese/platform`, dichiarato in `.claude/settings.json`; in locale `settings.local.json` può puntare alla cartella `~/dev/platform`; in alternativa `--plugin-dir`):
senza plugin i tipi `motore:*` non esistono e la run va fermata.

Prompt operativo:

```text
Nel repository nmaiese/diset-viz esegui una run editoriale per un solo
indicatore usando un vero Agent Team Claude Code.

Prima di iniziare:
1. verifica che il plugin motore sia caricato (la skill
   motore:redazione-indicatore e i tipi motore:data-editor, motore:source-researcher,
   motore:search-strategist, motore:data-journalist, motore:skeptical-editor
   devono risolversi) e che esistano le memorie in
   .claude/agent-memory/source-researcher/ e .claude/agent-memory/skeptical-editor/;
2. verifica che autoMemoryEnabled sia true;
3. se manca qualcosa, ferma la run e spiega che cosa manca. Non usare
   indicatore-lite come fallback.

Invoca /redazione-indicatore <codice> e segui integralmente quella skill.
Crea i cinque teammate con i tipi e i nomi dichiarati. Ricercatore e revisore
devono consultare la propria memoria, verificare di nuovo ogni fatto e
restituire memory_candidates. Solo il lead può modificare i MEMORY.md, dopo
aver verificato prova, durata e ambito del candidato.

Non scrivere né pubblicare direttamente sulla branch predefinita (`master`).
Lavora sulla branch claude/
della run e apri una PR revisionabile. Prima di chiudere la sentinella inserisci
nell'esito articoli/fermati e il consuntivo memoria con consultata, candidati,
promossi, scartati e aggiornata. Esegui i controlli e i test richiesti dalla
skill; una run verde senza esito editoriale esplicito non è un successo.
```

Sostituire `<codice>` con l'indicatore assegnato alla Routine.

## Monitoraggio

I subject dei task seguono il contratto:

`[redazione:<ruolo>:<fase>] <codice> - <titolo>`

Gli hook nativi `TaskCreated` e `TaskCompleted` passano per
`.claude/hooks/team_monitor.py` (che resta in questo repo), e li converte nel
contratto già usato da `/_pipeline/beat`. Non legge né modifica
`~/.claude/teams`, perché quella directory è stato interno e transitorio del
runtime.

La task `[redazione:lead:chiusura]` è la sentinella. Prima di completarla il lead
scrive nella descrizione il JSON `articoli`/`fermati` e il consuntivo
`memoria`; il completamento invia il consuntivo, aggiorna la storia
dell'indicatore e chiude la run nella dashboard. Nel dettaglio dell'esito sono
visibili memoria consultata, candidati, promossi, scartati e file aggiornati.
Un hook asincrono riposta il battito ogni due minuti finché la sentinella resta
aperta, senza consumare turni del team.

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
