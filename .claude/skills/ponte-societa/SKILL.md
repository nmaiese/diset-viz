---
name: ponte-societa
description: "Usa ponte a file per leggere ordini direzione o inviare messaggi tra coordinatori. Attivala quando arriva messaggio ponte o serve comunicare tra ruoli."
---

# Ponte della società

Il ponte separa ordini, risposte e messaggi tra ruoli. Messaggi messi direttamente in `fatti/` hanno saltato passaggio `in/`; worker che rispondeva al posto coordinatore e destinatari multipli sono stati rifiutati.

## Ricevere ordine

1. Cerca in `in/` e `fatti/` messaggi con `per:` per tuo ruolo; controlla `fatti/*-<ruolo>-*` senza `.letto`.
2. Crea `<nome>.letto` entro 10 minuti nel percorso assoluto del ponte indicato nell'ordine `[PONTE]`; usa stesso percorso assoluto per `<nome>.risposta.md`. Non sostituire placeholder a mano.
3. Esegui dipendenze `dopo:` in ordine; `entro:` è ignorato.
4. Solo coordinatore scrive risposta, max 30 righe, prosa normale. Prima riga completa:

```markdown
per: cowork-direzione | da: <C1|C2|C3|C-DIV> | progetto: <nome> | tipo: risposta | priorità: <normale|urgente> | rif: <nome ordine>
Esito: FATTO | PARZIALE | NON FATTO — <una frase>
Prova: <comando + output, SHA, test o percorso>
Aperto: <cosa resta e chi lo fa>
```

«Fatto» senza prova equivale a «non fatto». Denaro vero, account e chiavi non autorizzati al ruolo: fermati e riferisci chi decide.

## Scrivere

Alla direzione: crea `per-cowork/<AAAAMMGG-HHMMSS>-<ruolo>-<breve>.md` nel ponte Trade5 indicato dal percorso assoluto dell'ordine `[PONTE]`: `per-cowork/` è allo stesso livello di `in/` e `fatti/`. Il Regolamento §3 e `t5 ponte consegna` leggono `dev/trade5/ponte/per-cowork/`; non inviare alla distinta cartella `orca/ponte/per-cowork/`. Prima riga completa:

```markdown
per: cowork-direzione | da: <C1|C2|C3|C-DIV> | progetto: <nome> | tipo: <messaggio|decisione|escalation> | priorità: <normale|urgente> | rif: <nome o ->
```

Corpo: fatti, opzioni, consiglio. Tra coordinatori crea un file sorgente fuori da `in/`, uno per destinatario; prima riga completa:

```markdown
per: <C1|C2|C3|C-DIV> | da: <ruolo> | progetto: <nome> | tipo: messaggio | priorità: <normale|urgente> | rif: <nome o ->
```

Invia file sorgente con `t5 ponte invia <percorso-assoluto-file>`; CLI lo accoda in `in/` e usa default configurato oppure `--ponte <path>`. Non scrivere direttamente in `in/` o `fatti/`; niente destinatari multipli nello stesso `per:`. Percorsi nel messaggio ricevuto sono operativi assoluti Windows (`C:\Users\...`) e WSL (`/mnt/c/Users/...`); usa quello adatto al tool.

## Battito

Ogni 30 minuti aggiorna solo riga tua: attività, worker vivi con modello esatto, prossimo passo, mix e contesto. `t5` aggiunge ora, RAM e swap dal sistema. Oltre 45 minuti ponte segnala fermo; rilancio a 90.

Per C1/C2/C3, `t5 ponte battito`:

```bash
t5 ponte battito <C1|C2|C3> "<attività> · worker: <modello>×n · mix: <conteggi> · contesto <%>"
```

C-DIV non è accettato da CLI battito Trade5: aggiorna propria riga nel `coordinatore.md` del ponte, senza fingere di usare comando CLI. Caveman solo in log e dialogo agenti, mai spec, `.risposta.md`, PASSAGGIO o messaggi alla direzione.
