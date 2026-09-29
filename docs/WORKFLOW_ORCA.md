# Metodologia di Lavoro Multi-Agente con Orca

Questo documento stabilisce il protocollo di collaborazione tra **Nello (umano)** e gli agenti AI orchestrati all'interno della suite **Orca**.

Le ultime sezioni sono state scritte la sera del 27 settembre 2026, e contengono cose
**misurate** quella notte, non intenzioni. Le misure sono datate per poter essere
smentite: una riga senza data è un'opinione, e in questo documento le opinioni sono
poche.

---

## 1. Routing dei Ruoli

`worker`, `researcher` e `architect` sono alias delle attività `implementazione`,
`ricerca` e `architettura` di `~/dev/dev-tools/agents/ruoli.tsv`, che è la fonte unica:
quale agente esegua l'attività lo sceglie `~/dev/dev-tools/scripts/orca-lancia.sh`, il
primo con quota. `AGENT_ROUTING` non esiste più: la mappa alias-attività è
`ROLE_TO_ATTIVITA` in `scripts/orca_dispatch.py`, e l'help della CLI la stampa.

Il protocollo generale di Orca e le informazioni sui provider appartengono a
`~/dev/dev-tools/docs/orca.md`: qui non si duplicano. Un vincolo operativo resta
in capo a chi lancia i task: Ollama Cloud accetta una sola richiesta concorrente,
quindi i task che lo usano vanno avviati in sequenza, senza lock fittizi nel repo.

Il ruolo è un **piano**, non una misura di disponibilità. Un agente con
quota esaurita fallisce con un messaggio che sembra un altro problema, quindi la
disponibilità si verifica **prima** di assegnare, con
`~/dev/dev-tools/scripts/agent-probe.sh` (fino a circa sei minuti, le tre sonde
ollama girano in serie). I numeri di quota vivono in
`~/dev/dev-tools/docs/opencode-quota.md` e `opencode-modelli.md` e qui non si
copiano.

**Il canale che dice la verità sullo stato degli agenti** è
`bin/py scripts/tool_failures.py`: elenca i guasti ripetuti nelle ultime 48 ore. Se
un agente fallisce sempre per lo stesso motivo, lo dice lì, e quella riga va letta
prima di riassegnargli il task.

---

## 2. Il Protocollo "Live Task Spec" (Sostituto degli Artifacts)

Per superare la volatilità delle chat con un metodo pratico integrato in Orca e
da terminale:

1. **Il file di lavoro vive nel worktree (`TASK.md`)**:
   Ogni nuovo task aperto in un worktree viene avviato con un file `TASK.md` nella radice del progetto.
2. **Editing Live in Orca**:
   Orca apre `TASK.md` nel pannello editor accanto ai terminali.
   * **Nello può modificarlo in qualsiasi momento** (aggiungendo vincoli, note o spuntando criteri di accettazione) e salvare con `Ctrl+S`.
   * L'agente nel terminale rilegge `TASK.md` prima di ogni iterazione, assorbendo il feedback live in tempo reale.
3. **Template standard di `TASK.md`**:

```markdown
# Task: [Titolo del Task]

> Status: in-progress | in-review | completed
> Assegnato a: [Codex | Antigravity] ([worker | researcher | architect])
> Branch: [nome-branch]

## Obiettivo
[Descrizione in 1-2 frasi di cosa deve essere realizzato]

## Requisiti
- R1. [Cosa fare, non come farlo]
- R2. [Vincoli di integrità o di stile]

## Criteri di Accettazione (Checklist)
- [ ] [Verifica 1: comando test o riscontro oggettivo]
- [ ] [Verifica 2: build frontend o risposta HTTP]

## Note e Feedback Live di Nello
<!-- Scrivi qui feedback live mentre l'agente lavora. Salva con Ctrl+S -->

## Log Decisioni Agente
- [Data/Ora]: [Decisione architetturale o passaggio completato]
```

`TASK.md` sta nella radice del worktree ed è escluso da Git: serve a note live e
log delle decisioni, non entra nel ramo.

---

## 3. Un worktree per agente, e niente di più

La regola che tiene insieme tutto il resto, e che nasce da un guasto misurato.

La sera del 27 settembre 2026, `scripts/tool_failures.py` elencava **49 guasti
ripetuti in 48 ore**, raccolti in 8 firme diverse, e 40 dei 49 erano la stessa
frase:

> This agent is isolated in the worktree `.claude/worktrees/wf_...`, but this command ...

Tutti agenti dentro worktree secondari, che si erano messi a scrivere o a leggere
fuori dal proprio worktree: il `cd` in un altro worktree, uno script in
`/tmp` di un'altra sessione, un `cat >` in una scratchpad altrui. Sono 40 occasioni
in cui un agent ha speso un turno e prodotto niente, e le altre 9 sono un
`sed -i` su un file fuori worktree, un traceback e due `ruff` per import non
ordinati: la stessa disattenzione, con meno danni.

Ne segue:

- **Visibilità Totale delle Conversazioni in Orca**: ogni task o sub-task viene
  avviato come worktree nativo e scheda visibile via `bin/py scripts/orca_dispatch.py`
  o `~/dev/dev-tools/scripts/orca-lancia.sh`.
- **Un task, un worktree, un agente.** Due agenti nello stesso checkout non si
  coordinano, e Orca non li blocca.
- **Un agente non esce dal suo worktree.** Se serve un file di lavoro, quello è il
  `TASK.md` del suo worktree. Se serve uno script, è dentro il suo worktree e si
  cancella prima del commit, oppure in `/tmp` con un nome suo.
- **`cd` in un altro worktree è il modo più economico di sprecare un turno.**
- **L'interprete è `bin/py`, e va puntato a mano.** In un worktree nuovo `.venv` non
  esiste, e `python3` qui è una funzione di shell che cade su un interprete senza
  dipendenze. Senza questo, `bin/py` esce con `127` e l'agente la prende per un
  problema del progetto:

  ```bash
  export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python
  bin/py -c "import app; print(app.__file__)"
  ```

  La risposta deve contenere il percorso **del worktree dell'agente**: l'ambiente
  delle dipendenze è lo stesso, ma se il codice importato è quello di un altro
  checkout il verdetto dei test è su un altro codice.

---

## 4. Comandi Orca CLI Essenziali

In WSL il comando è sempre `orca-ide`, mai `orca`, che è il lettore di schermo
GNOME. Il protocollo completo è in `~/dev/dev-tools/docs/orca.md`; qui restano
solo i comandi propri di questo repository.

```bash
# Crea il worktree (orca-worktree.sh), scrive TASK.md e lancia l'agente con orca-lancia.sh.
bin/py scripts/orca_dispatch.py <slug> --title "Titolo" --objective "Obiettivo" --role worker

# Pubblica il ramo verificato e apre una PR in bozza.
bin/py scripts/orca_review.py <slug> --issue <numero>

# Rimuove un worktree pulito e tratta il ramo senza forzare un ramo non fuso.
bin/py scripts/orca_clean.py <slug>
```

`ORCA_CLI_COMMAND` può indicare il binario esportato da Orca; in sua assenza gli
script cercano solo `orca-ide`. Le create usano `origin/master`, `--setup skip` e
un prompt su una sola riga. Se Orca risponde `runtime_unavailable` o va in timeout,
il dispatcher controlla `orca-ide worktree list` e non riprova la create.

Quando partono più worker, le create vanno lanciate **in sequenza**: avvii
simultanei possono produrre `terminal_handle_stale`. Attendere che ogni create sia
terminata prima di iniziare la successiva.

La scheda del worktree in Orca dice a che punto è il lavoro, e va aggiornata a ogni
passaggio (stati: `todo`, `in-progress`, `in-review`, `completed`):

```bash
orca-ide worktree set --worktree active --comment "Implementati i test; in attesa di review" --workspace-status in-review --json
```

### Tre cose osservate qui, da non scambiare per errori propri

- **`index.lock: Read-only file system` al momento del commit, e solo lì.** È la
  sandbox di Codex (`-s workspace-write`): monta in sola lettura la cartella git del
  worktree, che sta in `.git/worktrees/<nome>` del checkout principale, anche con
  `--add-dir .git`. Il 27/09 un Codex in sandbox ha finito il lavoro, verificato 425
  test, e si è fermato solo lì, lasciando le modifiche integre e non staged. Non si
  aggira il lock: il commit lo fa chi coordina, fuori dalla sandbox, dopo aver
  rieseguito i test. La specifica deve dire all'agente di fermarsi e riferire.
- **Una specifica può chiedere un impossibile, e l'agente che la segue alla lettera
  si blocca invece di fingere.** Il caso è reale: la specifica chiedeva un allarme
  quando la quota di testo mascherato scendeva sotto quella non mascherata, cioè un
  test che verifica `quota_senza_numeri < quota`. L'agente ha dimostrato che la
  disuguaglianza è impossibile — mascherare i numeri può solo far salire la quota,
  perché trasforma sequenze diverse in una sequenza sola — e si è fermato a
  riportarlo, invece di produrre un test con un doppione finto che sarebbe passato
  senza provare niente. È il comportamento giusto: la specifica è un contratto da
  discutere, non un ordine da eseguire.
- **La specifica va riscritta, non rattoppata.** Dopo l'equivoco, la correzione non
  è stata un test più tollerante: è stato un discriminante diverso e vero, e la
  specifica è stata riscritta prima di rilanciare l'agente. Rilanciare con la stessa
  specifica, o solo addolcita, produce un altro blocco o un test falso.

---

## 5. Cosa non fa un agente, in ogni caso

- **Push del ramo e PR in bozza sì**, tramite `scripts/orca_review.py`, così Nello
  può controllare il lavoro.
- **Niente merge.** Lo fa Nello; `master` si distribuisce automaticamente.
- **Niente segreti.** Nessuna lettura di `.env`, chiavi o credenziali, nessuna
  scrittura di `auth.json`.
- **Niente deploy.**
- **Niente `Co-Authored-By`** nei messaggi di commit.

### Chi ha fatto cosa, su GitHub

Dal 28/09 ogni worker lanciato con `orca-lancia.sh` di dev-tools parte da un wrapper
che esporta `AGENT_ID=<agente>-<modello>` (per esempio `codex-gpt-5.6-sol`,
`opencode-big-pickle`) e lo usa come autore e committer git, con l'email
`n.maiese+<agente>@gmail.com`. Il ramo `nmaiese/firma-agenti` è nato così: un commit
di `opencode-big-pickle`. Per il resto l'account resta uno solo, quindi:

- `scripts/orca_review.py` chiude il corpo della PR con `— <AGENT_ID>`, o con il
  valore di `--firma` se lo passa chi coordina. Issue, review e commenti scritti con
  `gh` finiscono con la stessa riga (la regola sta negli `AGENTS.md` globali degli
  agenti, sorgente in dev-tools `agents/AGENTS.md`).
- Quando chi coordina committa il diff di un worker (per esempio dopo una sandbox di
  Codex), lo fa con `git commit --author="<AGENT_ID> <n.maiese+<agente>@gmail.com>"`.
- Per affidare un'issue a un agente si usa la label `agent:<nome>`: su GitHub
  l'assegnatario può essere solo un utente, e l'account è quello di Nello.

## 6. Antigravity in orchestrazione, misurato e diagnosticato il 28 settembre 2026

*Storico 28/09/2026. Dal 29/09 headless vietato da una guardia; misure restano come dato.*

> Aggiornamento della sera del 28/09, dopo le prove in `~/dev/dev-tools/docs/orca.md`
> ("Lanciare un worker e sapere se la spec è arrivata"): con il worktree già fidato
> (`orca-preflight.sh --scrivi-trust`) `worker-start --agent antigravity` consegna
> senza inviare a mano. Il lanciatore `orca-lancia.sh` fa già tutto; questa sezione
> resta come diagnosi di com'è nato il problema.

Prima diagnosi (sbagliata, corretta qui): `worker-start --agent antigravity` sembrava fallire
sempre con `agent_prompt_blocked`, indipendente dal modello. Non è il modello. Letto lo schermo
del terminale con `orca-ide terminal read --terminal <handle> --screen --json` **prima** di rilasciarlo
(non dopo: il rilascio chiude il terminale e la prova sparisce), la causa reale è una catena di tre
problemi distinti, tutti aggirabili:

1. **Il dialogo di primo avvio non e' testuale.** La prima volta che Antigravity CLI gira in un
   worktree chiede "Do you trust the contents of this project?" con un menu a frecce
   (`> Yes, I trust this folder` / `No, exit`). L'iniezione del prompt di Orca manda testo, il menu
   lo scarta, e il turno fallisce con `agent_prompt_blocked` prima ancora di vedere la spec. Si
   sblocca con un solo invio: `orca-ide terminal send --terminal <handle> --enter --json`. Spiega perché
   a Nello era già andata bene altrove: quel worktree aveva già superato il dialogo.
2. **Anche a fiducia concessa, l'invio automatico non conferma la sottomissione.** Un secondo
   `worker-start --terminal <handle-ora-fidato>` incolla la spec nella casella di input
   ("`[Pasted text #1 +82 lines]`"), ma il turno non parte da solo: serve un altro
   `orca-ide terminal send --terminal <handle> --enter --json` per premere davvero Invio. Senza
   quel secondo invio manuale il dispatch fallisce di nuovo con lo stesso `agent_prompt_blocked`,
   e la capability di quel dispatch viene revocata nello stesso istante: anche riuscendo a far
   partire il turno dopo, il canale per mandare `worker_done` è già morto.
3. **`orca-ide` non è sul `PATH` del sotto-processo Bash di Antigravity.** Il worker lo scopre da
   solo (`which orca-ide` fallisce, poi `find /`, poi `export PATH=$HOME/.local/bin:$PATH`) e alla
   fine lo richiama per percorso assoluto: funziona, ma consuma turni. Anche cosi', l'ultimo
   `orca-ide orchestration send --type worker_done` e' rimasto a `running` senza mai consegnare
   il messaggio (capability già revocata al punto 2), e il worker ha scritto in chiaro "notificato
   il coordinatore" senza aver verificato l'esito del comando: non fidarsi della narrazione di un
   worker sul proprio `worker_done`, il canale autorevole è `orca-ide orchestration check`.

4. **Il prompt può arrivare prima che l'interfaccia sia pronta.** Visto lo stesso giorno in un
   worktree già fidato, quindi senza dialogo: il dispatch è finito `outcome_unknown` e lo schermo
   mostrava la casella di input vuota, la spec persa. Anche qui la prova si legge a schermo prima
   di rilasciare. Rimedio: `worker-stop` e nuovo lancio con `orca-lancia.sh`, non un secondo tentativo alla cieca.

In sintesi: **antigravity funziona in orchestrazione**, ma non al primo avvio di un worktree nuovo
e non senza un intervento manuale per far ripartire la sottomissione dopo il trust dialog. Il
lancio passa da `orca-lancia.sh`, non da un ripiego headless: per antigravity vedi
`~/dev/dev-tools/docs/orca.md`, sezione antigravity. In headless aveva fatto ricerca web reale
(fonti verificabili nell'output) e prodotto un'analisi di 700+ parole in un turno, senza toccare
file: l'output andava salvato da chi coordinava.

Un gotcha separato su `opencode run`: il messaggio posizionale deve stare **prima** dei flag `-f`,
altrimenti il parser tratta il testo del prompt come un nome di file e fallisce con
`File not found: <tutto il prompt>`.

Un secondo gotcha, più insidioso perché non dà errore: **`opencode run` lanciato in background
aspetta la fine dello stdin.** Se lo stdin è un socket o una pipe che nessuno chiude, come nei
comandi in background di Claude Code, il processo carica la configurazione, scrive `init` nel log
e resta fermo per sempre: nessuna sessione, nessuna connessione, pochi secondi di CPU. Il 28
settembre due lavori sono rimasti così 14 minuti. Si lancia sempre con `< /dev/null` e dentro un
`timeout`, e si controlla presto `~/.local/share/opencode/log/opencode.log`: se dopo `init` non
compare `session.id`, il processo è bloccato. Stesso accorgimento per `agy -p`.

Un terzo, visto alla prima review vera sulla issue #285: **`opencode run -f` rifiuta i file fuori
dalla cartella di lavoro.** Un diff salvato in `/tmp` e passato con `-f /tmp/diff.txt` produce
`permission requested: external_directory (/tmp/*); auto-rejecting`. Il wrapper esce comunque con
0 e il parere non c'è, quindi non basta guardare il codice d'uscita. I file da allegare vanno
scritti dentro il worktree, per esempio in `lavoro/`, e cancellati dopo.

Due guasti di Orca visti lo stesso giorno, durante la fase 1 del team editoriale:
- **`--agent claude --model haiku` non ha ricevuto la consegna.** L'agente è partito, la casella
  di input è rimasta vuota e il dispatch è rimasto `start_unknown` per cinque minuti. Allo
  schermo c'era anche l'errore di un hook `SessionStart` di tipo prompt, che però compare anche
  sui worker sonnet che funzionano. Con un caso solo non si sa se il guasto dipenda da haiku.
  Rimedio: `worker-stop`, `worker-release`, poi di nuovo con `--task <id> --retry-of <dispatch>`
  su sonnet, che è partito subito. Si controlla sempre lo schermo nel primo minuto.
- **`worktree create` può chiudere la connessione** ("The Orca runtime closed the connection
  before responding") e creare lo stesso il worktree, sia in git sia in Orca. Prima di
  riprovare si guarda `git worktree list`, e si aspetta che `orca-ide worktree show --worktree
  branch:<ramo>` lo trovi, perché la registrazione in Orca arriva qualche secondo dopo quella in
  git. Riprovare subito non dà errore: crea un doppione con il suffisso `-2` (`rev-285-2-2`).

**Antigravity e OpenCode come worker veri, misurati il 28 settembre sugli strumenti del team
editoriale.** Nessuno dei due riceve la consegna da solo, ma tutti e due lavorano bene una volta
sbloccati.
- **Antigravity** (`--agent antigravity --model gemini-3.1-pro-high`, PR #291). Si sono ripresentati
  identici i difetti 1 e 2: il dialogo di fiducia su un worktree nuovo, poi la spec incollata e non
  inviata. Si sblocca con due `terminal send --enter`, e da lì lavora nel terminale Orca. Il
  dispatch però è già `failed`, quindi il suo `worker_done` resta appeso: la fine si legge dallo
  schermo (niente più "Generating") e dai file. Ha un'abitudine da sapere: lascia nella radice del
  worktree i suoi script di lavoro (`patch_*.py`, `report.md`), anche quando la spec lo vieta. Il
  team leader li toglie prima del `git add`, che va sempre fatto per percorsi espliciti. In
  headless (`agy -p` con `< /dev/null`) ha fatto due riparazioni buone, con i test chiesti.
- **OpenCode** (`--agent opencode`, modello dalla sua configurazione, oggi `opencode/big-pickle`,
  PR #290 e #291). Il terminale parte vuoto e il dispatch resta `dispatched`. Il preambolo di Orca
  (`orchestration dispatch-show --task <id> --preamble`) non contiene la capability, quindi il
  `worker_done` non arriva. La spec si passa con `terminal send --text` più `--enter`, e la fine si
  legge dalla review pubblicata sulla PR. Big-pickle, gratuito, ha fatto una review di qualità
  alta: ha misurato che la guardia bocciava 90 articoli corretti su 381, cosa che il suo autore non
  aveva visto.

I crediti del provider `huggingface` (GLM-5.3-Flash) sono 0,10 dollari al mese e finiscono senza
preavviso a metà di un lavoro, con `Payment Required: You have depleted your monthly included
credits`. Non va messo su un passaggio che il flusso aspetta.

**Codex che si aggiorna da solo si mangia la consegna**, visto la sera del 28 settembre sulle review
2 di #289 e #290. Al primo avvio dopo un rilascio nuovo Codex mostra il dialogo "Update available"
con "1. Update now" già selezionato. L'invio con cui Orca manda la spec sceglie l'aggiornamento:
Codex si aggiorna (0.157.1 → 0.158.0), stampa "Please restart Codex" ed esce alla shell. Il
dispatch resta `pending` e nessun `worker_done` arriva mai. Sull'altro terminale lanciato insieme la
spec non è arrivata affatto, e il dispatch è andato `failed` con Codex fermo sul prompt vuoto. In
tutti e due i casi si è perso mezz'ora di attesa. Il rimedio è controllare lo schermo nel primo
minuto, come per haiku. Rilanciare Codex a mano nel terminale con
`--dangerously-bypass-approvals-and-sandbox` viene negato dal classificatore dei permessi di Claude
Code, ed è giusto così: un agente senza sandbox lo avvia Orca, non il team leader.

**Le quote dei provider, misurate con un ping per modello la sera del 28 settembre** (`opencode run
"Rispondi soltanto con la parola OK." -m <modello> < /dev/null`, `agy --model <id> -p ...`). Rispondono:
Antigravity `gemini-3.1-pro-high` e `gemini-3.8-flash-high`, Zen `opencode/big-pickle`,
`opencode/nemotron-3-ultra-free` e `opencode/mimo-v2.6-flash-free`, e su ollama-cloud `gpt-oss:120b`,
`nemotron-3-ultra` e `gemma4:31b`. Non rispondono: `google/*` (crediti prepagati finiti), `zai/*`,
`moonshotai/*` e `minimax/*` (saldo), `groq/*` (chiave non valida), i modelli ollama-cloud fuori dal
piano gratuito (`kimi-k3`, `kimi-k2.6`, `deepseek-v4-pro`, `glm-5.3`, `minimax-m2.7`,
`mistral-large-3`) e quelli ritirati il 25 settembre (`qwen3.5:397b`, `deepseek-v4-flash`,
`glm-5.1`). I provider con credito finito rispondono dopo circa 75 secondi, non subito: il ping va
fatto con un `timeout`, altrimenti si scambia l'attesa per lavoro.

*Storico 28/09/2026. Dal 29/09 headless vietato da una guardia; misure restano come dato.*

**I ruoli in headless, misurati la stessa sera sul pilota ter-12 e sulle review degli strumenti.**
- **`opencode run` muore su ogni accesso fuori dalla cwd.** Leggere `/tmp`, la libreria standard
  di Python o un file che un webfetch ha salvato in `/tmp` chiede il permesso `external_directory`.
  In headless il permesso viene rifiutato da solo ("auto-rejecting"), e il run finisce con exit 0
  senza risposta. Due giri di review si sono persi così. La consegna deve dire "non leggere niente
  fuori dal worktree, temporanei in `.<nome>/` dentro il worktree".
- **Due `opencode run` partiti nello stesso istante** si contendono il database di OpenCode, e uno
  muore con "Error: Unexpected error / database is locked". Partiti a qualche secondo di distanza,
  convivono.
- **Le citazioni dello scout si verificano scaricando l'URL.** Antigravity pro-high ha dato 8
  citazioni letterali su 8. OpenCode nemotron-3-ultra-free ne ha date 1 su 18: le altre erano
  parafrasi o frasi composte, e un URL rispondeva 403. Il controllo si fa con uno script che scarica
  la pagina o il PDF (`uv run --with pypdf`) e cerca la citazione normalizzata.
- **Il grafico ha dichiarato due ritagli "con la figura in primo piano"** che mostravano le fonti e
  la licenza. La resa l'ha verificata davvero il leader, con Playwright su Chrome
  (`uv run --with playwright`, `channel="chrome"`): screenshot del solo elemento `figure`, a 375 e
  768 px, tema chiaro e scuro, più `scrollWidth`. Un'affermazione su un'immagine si controlla
  aprendo l'immagine.
- **Il secondo parere di gpt-oss:120b è debole sulla sostanza.** Sulla domanda 1 ha detto di no,
  ma non ha visto che l'attacco del pilota era sbagliato nei fatti ("scende in tutte le regioni",
  mentre nel 2025 sei regioni salgono). Sulla domanda 3 ha dato l'italiano per buono. Serve come
  lettura in più, non come controllo.
- **Per OpenCode headless anche `/dev/null` è fuori dal worktree.** Un `cat -A /dev/null` ha
  chiuso una review a metà. La consegna dice "niente percorsi assoluti, neanche /dev/null o
  /tmp".
- **Antigravity ha scritto nel resoconto una prova a secco che non aveva fatto**, con un commit
  che non esiste e un'intestazione di tabella che il file non ha. Il codice era giusto, il
  resoconto no. Il leader rifà sempre la prova che il resoconto dichiara.

## 7. Cosa richiede mano umana

Ci sono cose che nessun agente deve fare: la regola per il traffico interno in GA4
(l'API non espone i filtri dati), Bing Webmaster Tools, il deploy, e le decisioni che
sono di Nello (Google-Extended e il merge).

Il container GTM e la property GA4 non sono piu' in questa lista dal 29 settembre
2026: il service account `ga4-mcp@nil-automata.iam.gserviceaccount.com` ha `Pubblica`
sul container e `canEdit` sulla property, e le modifiche si fanno via API da chi
coordina, con Nello che le ha chieste. Una modifica a GTM si pubblica come versione
nuova con note, cosi' il ritorno indietro e' ripubblicare la precedente.
