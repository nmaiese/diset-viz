# Metodologia di Lavoro Multi-Agente con Orca

Questo documento stabilisce il protocollo di collaborazione tra **Nello (umano)** e gli agenti AI orchestrati all'interno della suite **Orca**.

Le ultime sezioni sono state scritte la sera del 27 settembre 2026, e contengono cose
**misurate** quella notte, non intenzioni. Le misure sono datate per poter essere
smentite: una riga senza data è un'opinione, e in questo documento le opinioni sono
poche.

---

## 1. Ripartizione dei Ruoli e dei Budget

| Agente | Abbonamento | Ruolo | Quando usarlo |
|---|---|---|---|
| **Claude** | $100/mese | **Chief Architect & Lead Reviewer** | • Design di nuove sezioni o modifiche strutturali complesse.<br>• Review di PR e applicazione rigorosa delle linee guida di stile e design.<br>• Audit di coerenza e refactoring ad alto impatto. |
| **Codex** | ~$25/mese | **Specialist Implementer / Worker** | • Implementazione di task specifici, classi o funzioni isolate.<br>• Generazione e aggiornamento di unit test.<br>• Script di parsing dati, trasformazioni CSV/SDMX. |
| **Gemini** | ~$25/mese | **Navigator & Context Hub** | • Ingestione di mega-contesti (dataset interi, log chilometrici, trascrizioni complete).<br>• Analisi e audit cross-file.<br>• Creazione delle specifiche dei task (`TASK.md`) e pair-programming live. |

La tabella è un **piano di ruoli**, non una misura di disponibilità. Un agente con
quota esaurita fallisce con un messaggio che sembra un altro problema, quindi la
disponibilità si verifica **prima** di assegnare, e i numeri vivono fuori da qui, in
`~/dev/dev-tools/docs/opencode-quota.md` e `opencode-modelli.md`, che li tengono
aggiornati. Qui non si copiano: due copie di un numero di quota vanno fuori
sincrono, e quella è la lezione che questo repository ha già pagato.

**Il canale che dice la verità sullo stato degli agenti** è
`bin/py scripts/tool_failures.py`: elenca i guasti ripetuti nelle ultime 48 ore. Se
un agente fallisce sempre per lo stesso motivo, lo dice lì, e quella riga va letta
prima di riassegnargli il task.

---

## 2. Il Protocollo "Live Task Spec" (Sostituto degli Artifacts)

Per superare la volatilità delle chat e sostituire gli Artifacts di Claude con un metodo pratico integrato in Orca e da terminale:

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
> Assegnato a: [Claude | Codex | Gemini]
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

`TASK.md` sta nella radice del worktree, quindi **finisce nel ramo**: decidere se
entra nel merge o se si cancella prima del merge è di Nello, e questa volta è una
decisione aperta, non una convenzione.

---

## 3. Un worktree per agente, e niente di più

La regola che tiene insieme tutto il resto, e che nasce da un guasto misurato.

La sera del 27 settembre 2026, `scripts/tool_failures.py` elencava **49 guasti
ripetuti in 48 ore**, raccolti in 8 firme diverse, e 40 dei 49 erano la stessa
frase:

> This agent is isolated in the worktree `.claude/worktrees/wf_...`, but this command ...

Tutti agenti Claude dentro `.claude/worktrees/`, che si erano messi a scrivere o a
leggere fuori dal proprio worktree: il `cd` in un altro worktree, uno script in
`/tmp` di un'altra sessione, un `cat >` in una scratchpad altrui. Sono 40 occasioni
in cui un agent ha speso un turno e prodotto niente, e le altre 9 sono un
`sed -i` su un file fuori worktree, un traceback e due `ruff` per import non
ordinati: la stessa disattenzione, con meno danni.

Ne segue:

- **Visibilità Totale delle Conversazioni in Orca**: Nessun agente o sub-agente (Codex, Gemini, Claude, OpenCode) deve essere avviato come processo background invisibile sotto AGY (`invoke_subagent`). Ogni task o sub-task deve essere spawnato come un worktree nativo e una scheda di terminale visibile nella dashboard GUI/TUI di Orca via `orca-ide worktree create` o `bin/py scripts/orca_dispatch.py`.
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

**Il comando non è `orca`.** In WSL, fuori da un terminale Orca, `orca` risolve
`/usr/bin/orca`, che è il lettore di schermo GNOME, e lo avvia. In un terminale
Orca, e in WSL, il binario è quello che Orca esporta:

```bash
echo "$ORCA_CLI_COMMAND"   # orca-ide
```

Nell'esempi sotto, `orca` sta per il valore di quella variabile.

### Avviare un nuovo task con un agente

Puoi usare l'helper automatico del repository:

```bash
# Inizializza worktree, TASK.md e avvia l'agente Orca appropriato (worker=codex, researcher=gemini, architect=claude):
bin/py scripts/orca_dispatch.py <slug> --title "Titolo Task" --objective "Descrizione" --role worker
```

Oppure direttamente via CLI Orca:

```bash
# Avvio task indipendente con Codex in un nuovo worktree.
# --setup skip evita di lanciare gli hook di setup del repo in un worktree
# che serve solo a un lavoro di testo o di codice isolato.
orca worktree create --name fix-routing --no-parent --base-branch master \
  --setup skip --agent codex --prompt "Leggi TASK.md ed esegui l'implementazione" --json
```

`--agent` mette l'agente **nel primo terminale** e va preferito: evita il terminale
di fallback a vuoto che si crea con un worktree nudo. Non va poi creato un secondo
terminale per lo stesso agente.

**Prima di inviare qualsiasi prompt a un agente, va aspettato che la TUI sia pronta.**
Un prompt scritto in una TUI che sta ancora partendo va perso, e si scopre solo
perché il task non parte:

```bash
orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json
# si legge satisfied: true, non il fatto che abbia stampato qualcosa
```

### Lavoro headless, quando la TUI non serve

`--agent` avvia il launcher configurato, e non ha flag per modello o ragionamento.
Quando il lavoro è una specifica chiusa e il risultato è un file, si usa il
programma in modalità headless dentro il terminale:

```bash
orca worktree create --name lead-ter-13 --no-parent --base-branch master --setup skip --json
orca terminal create --worktree path:<percorso-del-worktree> --title "codex" \
  --command 'codex exec --skip-git-repo-check "Leggi TASK.md ed esegui il task"' --json
```

Il vantaggio non è la comodità, è la verificabilità: l'output finisce in un file,
l'agente non ha uno stato interattivo da tenere, e il risultato del turno è il
commit.

### Aggiornare lo stato e i commenti sulla Card di Orca:

```bash
# Aggiorna il commento visibile nella dashboard di Orca:
orca worktree set --worktree active --comment "Implementati i test; in attesa di review" --workspace-status in-review --json

# Stati validi: todo, in-progress, in-review, completed
```

### Inviare comandi a un terminale esistente:

```bash
orca terminal send --terminal <handle> --text "leggi il feedback aggiornato in TASK.md e correggi" --enter --wait-submit 10 --json
```

`--wait-submit` dà la prova che il prompt è stato **consegnato**; non prova che
l'agente sia partito. Su silenzio non si reinserisce: si legge il terminale.

### Due difetti della CLI, da non scambiare per errori propri

- **`runtime_unavailable` dopo aver già applicato la modifica.** La creazione di un
  worktree è stata osservata rispondere `runtime_unavailable` *avendo* creato il
  worktree, due volte in una notte. Prima di ripetere il comando, `orca worktree
  list`: se il worktree c'è già, non va ricreato, e il secondo tentativo produce un
  duplicato da pulire.
- **L'id di un worktree è un indirizzo in due parti**, `<repoId>::<percorso>`, e va
  copiato per intero. Il solo `repoId` non basta. Il selettore `path:<percorso>`
  funziona e va bene quando si ragiona con i path di WSL.
- **`index.lock: Read-only file system` al momento del commit, e solo li.** Il
  filesystem di questa macchina passa da sola lettura a scrivibile senza avviso.
  Il caso osservato: l'agente aveva finito tutto, verificato 413 test di unità e 1335
  della suite completa, e si è fermato unicamente perché non poteva scrivere
  l'indice. Le modifiche erano integre e non staged. La risposta non è aggirare il
  lock: è controllare `findmnt` sul path del progetto, e se è tornato scrivibile
  committare a mano, rieseguendo prima il test. Il contratto della specifica deve
  dire all'agente di fermarsi e riferire in questo caso, non di riprovare all'infinito.

### Due cose che una specifica può sbagliare, e che un agente onesto fa notare

- **Una specifica può chiedere un impossibile, e l'agente che lo segue alla lettera
  si blocca invece di fingere.** Il caso è reale: la specifica chiedeva un allarme
  quando la quota di testo mascherato scendeva sotto quella non mascherata, cioè un
  test che verifica `quota_senza_numeri < quota`. L'agente ha dimostrato che la
  disuguaglianza è impossibile — mascherare i numeri può solo far salire la quota,
  perché trasforma sequenze diverse in una sequenza sola — e si è fermato a
  riportarlo, invece di produrre un test con un doppione finto che sarebbe passato
  senza provare niente. È il comportamento giusto, ed è un motivo per cui vale la
  pena che un agente legga la specifica come un contratto da discutere e non come
  un ordine da eseguire. Ma è anche un motivo per non fidarsi del proprio primo
  ragionamento: l'errore era nella specifica, cioè nella mia testa.
- **La specifica va riscritta, non rattoppatata.** Dopo l'equivoco, la correzione non
  è stata un test più tollerante: è stato un discriminante diverso e vero, e la
  specifica è stata riscritta prima di rilanciare l'agente. Rilanciare con la stessa
  specifica, o con la specifica solo addolcita, avrebbe prodotto un altro blocco o
  un test falso.

---

## 5. Cosa non fa un agente, in ogni caso

- **Niente push, niente PR, niente merge.** Su questo repository il merge è la
  pubblicazione, e la coda di `content/` e `app/` passa da PR con gate umano. Un
  agente lascia il ramo e il commit, e la decisione di pubblicare è di Nello.
- **Niente segreti.** Nessuna lettura di `.env`, chiavi o credenziali, nessuna
  scrittura di `auth.json`.
- **Niente deploy.**
- **Niente `Co-Authored-By`** nei messaggi di commit.

## 6. Cosa richiede mano umana

Ci sono cose che nessun agente deve fare, e vale la pena tenerle scritte per non
perderle: il container GTM (tag morti, hostname di produzione), la regola per il
traffico interno in GA4 e la creazione di dimensioni e metriche, Bing Webmaster
Tools, il deploy, e le decisioni che sono di Nello (Google-Extended, il merge, il
push).
