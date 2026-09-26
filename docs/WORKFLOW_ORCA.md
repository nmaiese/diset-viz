# Metodologia di Lavoro Multi-Agente con Orca

Questo documento stabilisce il protocollo di collaborazione tra **Nello (umano)** e i tre agenti AI (**Claude**, **ChatGPT/Codex**, **Gemini/Antigravity**) orchestrati all'interno della suite **Orca**.

---

## 1. Ripartizione dei Ruoli e dei Budget

| Agente | Abbonamento | Ruolo | Quando usarlo |
|---|---|---|---|
| **Claude** | $100/mese | **Chief Architect & Lead Reviewer** | • Design di nuove sezioni o modifiche strutturali complesse.<br>• Review di PR e applicazione rigorosa delle linee guida di stile e design.<br>• Audit di coerenza e refactoring ad alto impatto. |
| **Codex** | ~$25/mese | **Specialist Implementer / Worker** | • Implementazione di task specifici, classi o funzioni isolate.<br>• Generazione e aggiornamento di unit test.<br>• Script di parsing dati, trasformazioni CSV/SDMX. |
| **Gemini** | ~$25/mese | **Navigator & Context Hub** | • Ingestione di mega-contesti (dataset interi, log chilometrici, trascrizioni complete).<br>• Analisi e audit cross-file.<br>• Creazione delle specifiche dei task (`TASK.md`) e pair-programming live. |

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

---

## 3. Comandi Orca CLI Essenziali

La CLI di Orca (tramite bridge WSL in `/mnt/c/Users/Nilo/AppData/Local/Programs/orca/resources/bin/orca.exe` o alias `orca-ide`) gestisce il ciclo di vita:

### Avviare un nuovo task con un agente:
```bash
# Avvio task indipendente con Codex in un nuovo worktree:
orca worktree create --name fix-routing --no-parent --agent codex --prompt "Leggi TASK.md ed esegui l'implementazione" --json

# Avvio task di review o architettura con Claude:
orca worktree create --name review-design --no-parent --agent claude --prompt "Leggi TASK.md ed esegui la code review su app/templates/v1" --json
```

### Aggiornare lo stato e i commenti sulla Card di Orca:
```bash
# Aggiorna il commento visibile nella dashboard di Orca:
orca worktree set --worktree active --comment "Implementati i test; in attesa di review" --workspace-status in-review --json

# Stati validi: todo, in-progress, in-review, completed
```

### Inviare comandi a un terminale esistente:
```bash
orca terminal send --terminal <handle> --text "leggi il feedback aggiornato in TASK.md e correggi" --enter --json
```
