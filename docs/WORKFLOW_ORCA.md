# Metodologia di Lavoro Multi-Agente con Orca

Questo documento stabilisce il protocollo di collaborazione tra **Nello (umano)** e gli agenti AI orchestrati all'interno della suite **Orca**.

Le ultime sezioni sono state scritte la sera del 27 settembre 2026, e contengono cose
**misurate** quella notte, non intenzioni. Le misure sono datate per poter essere
smentite: una riga senza data è un'opinione, e in questo documento le opinioni sono
poche.

---

## 1. Routing dei Ruoli

La fonte di verità è `AGENT_ROUTING` in `scripts/orca_dispatch.py`. L'help della
CLI viene generato dalla stessa mappa.

| Ruolo richiesto | Agente Orca | Quando usarlo |
|---|---|---|
| `worker` | **Codex** | Implementazione, test e script deterministici. |
| `researcher` | **Antigravity** | Ricerca, ricognizione e audit cross-file. |
| `architect` | **Codex** | Disegno tecnico e modifiche strutturali. |

Il protocollo generale di Orca e le informazioni sui provider appartengono a
`~/dev/dev-tools/docs/orca.md`: qui non si duplicano. Un vincolo operativo resta
in capo a chi lancia i task: Ollama Cloud accetta una sola richiesta concorrente,
quindi i task che lo usano vanno avviati in sequenza, senza lock fittizi nel repo.

La tabella è un **piano di ruoli**, non una misura di disponibilità. Un agente con
quota esaurita fallisce con un messaggio che sembra un altro problema, quindi la
disponibilità si verifica **prima** di assegnare, con
`~/dev/dev-tools/scripts/agent-probe.sh` (dieci secondi); i numeri di quota vivono
in `~/dev/dev-tools/docs/opencode-quota.md` e `opencode-modelli.md` e qui non si
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
  avviato come worktree nativo e scheda visibile via `orca-ide worktree create`
  o `bin/py scripts/orca_dispatch.py`.
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
# Crea il worktree, avvia l'agente corretto e poi scrive TASK.md nel path reale.
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

## 6. Antigravity in orchestrazione, misurato e diagnosticato il 28 settembre 2026

Prima diagnosi (sbagliata, corretta qui): `worker-start --agent antigravity` sembrava fallire
sempre con `agent_prompt_blocked`, indipendente dal modello. Non è il modello. Letto lo schermo
del terminale con `orca terminal read --terminal <handle> --screen --json` **prima** di rilasciarlo
(non dopo: il rilascio chiude il terminale e la prova sparisce), la causa reale è una catena di tre
problemi distinti, tutti aggirabili:

1. **Il dialogo di primo avvio non e' testuale.** La prima volta che Antigravity CLI gira in un
   worktree chiede "Do you trust the contents of this project?" con un menu a frecce
   (`> Yes, I trust this folder` / `No, exit`). L'iniezione del prompt di Orca manda testo, il menu
   lo scarta, e il turno fallisce con `agent_prompt_blocked` prima ancora di vedere la spec. Si
   sblocca con un solo invio: `orca terminal send --terminal <handle> --enter --json`. Spiega perché
   a Nello era già andata bene altrove: quel worktree aveva già superato il dialogo.
2. **Anche a fiducia concessa, l'invio automatico non conferma la sottomissione.** Un secondo
   `worker-start --terminal <handle-ora-fidato>` incolla la spec nella casella di input
   ("`[Pasted text #1 +82 lines]`"), ma il turno non parte da solo: serve un altro
   `orca terminal send --terminal <handle> --enter --json` per premere davvero Invio. Senza
   quel secondo invio manuale il dispatch fallisce di nuovo con lo stesso `agent_prompt_blocked`,
   e la capability di quel dispatch viene revocata nello stesso istante: anche riuscendo a far
   partire il turno dopo, il canale per mandare `worker_done` è già morto.
3. **`orca-ide` non è sul `PATH` del sotto-processo Bash di Antigravity.** Il worker lo scopre da
   solo (`which orca-ide` fallisce, poi `find /`, poi `export PATH=$HOME/.local/bin:$PATH`) e alla
   fine lo richiama per percorso assoluto: funziona, ma consuma turni. Anche cosi', l'ultimo
   `orca-ide orchestration send --type worker_done` e' rimasto a `running` senza mai consegnare
   il messaggio (capability già revocata al punto 2), e il worker ha scritto in chiaro "notificato
   il coordinatore" senza aver verificato l'esito del comando: non fidarsi della narrazione di un
   worker sul proprio `worker_done`, il canale autorevole è `orca orchestration check`.

In sintesi: **antigravity funziona in orchestrazione**, ma non al primo avvio di un worktree nuovo
e non senza un intervento manuale per far ripartire la sottomissione dopo il trust dialog. Finché
questi tre punti non sono risolti lato Orca, il ripiego pulito resta l'headless fuori
orchestrazione, come `~/dev/dev-tools/docs/orca.md` già indicava: `agy --model <id>
--dangerously-skip-permissions -p "<prompt>"`. Ha fatto ricerca web reale (fonti verificabili
nell'output) e prodotto un'analisi di 700+ parole in un turno, senza toccare file: l'output va
salvato da chi coordina, l'headless non scrive nel repo.

Un gotcha separato su `opencode run`: il messaggio posizionale deve stare **prima** dei flag `-f`,
altrimenti il parser tratta il testo del prompt come un nome di file e fallisce con
`File not found: <tutto il prompt>`.

## 7. Cosa richiede mano umana

Ci sono cose che nessun agente deve fare: il container GTM (tag morti, hostname di
produzione), la regola per il traffico interno in GA4 e la creazione di dimensioni
e metriche, Bing Webmaster Tools, il deploy, e le decisioni che sono di Nello
(Google-Extended e il merge).
