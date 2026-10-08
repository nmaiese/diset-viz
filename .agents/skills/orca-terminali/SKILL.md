---
name: orca-terminali
description: "Legge, invia input e rilascia terminali Orca con handle verificati. Usala per osservare o sbloccare agente, o chiudere terminale concluso."
---

# Terminali Orca

Input nel terminale sbagliato può approvare permesso; screenshot globale ha mostrato `.env`; polling frequente ha bloccato WSL. Usa handle aggiornato, lettura limitata, niente segreti nei log e nessun retry più frequente di uno al minuto.

Fuori dai terminali Orca usa `orca-ide`; binario Linux `orca` è lettore schermo. Verifica sintassi con `orca-ide skills get orca-cli`.

## Trova e leggi

```bash
orca-ide terminal list --json
orca-ide terminal read --terminal <handle> --limit <n> --json
```

Prendi handle completo dalla lista attuale; dopo riavvio cambia. Controlla titolo/ruolo e leggi prima di scrivere. Classifica output: attivo, finito, quota, permesso o errore. Non usare screenshot intero per decidere dove scrivere.

## Invia input

```bash
orca-ide terminal send --terminal <handle> --text <testo>
orca-ide terminal send --terminal <handle> --enter
```

Testo e Invio in chiamate separate. Se testo contiene backtick o `$()`, mettilo in file e passalo con quoting sicuro; mai interpolarlo nella shell. Approva solo permesso esattamente autorizzato da Regolamento o ordine scritto; nel dubbio segnala alla direzione. Ordini agenti passano dal ponte.

Se Orca/interop non risponde (`runtime_unavailable`, timeout o `UtilAcceptVsock: accept4 failed`), fermati e segnala; non riavviare Orca o WSL da terminale.

## Rilascia e chiudi

Dopo `worker_done`, rilascia dispatch settled prima di chiudere qualsiasi altro terminale:

```bash
orca-ide orchestration worker-release --dispatch <id> --json
orca-ide terminal list --json
# Solo se handle ancora presente e release sicura:
orca-ide terminal close --terminal <handle>
```

`worker-release` si usa solo su worker settled, mai attivo o ignoto. Dopo risposta leggi `processAction` e `orca-ide terminal list --json`: non dedurre chiusura da `state=released`. `retained` con `external_terminal` di solito richiede chiusura; `released` con `closed_exited_terminal` indica terminale già chiuso. Chiudi esattamente l'handle del worker solo se compare ancora nella lista e release è sicura. Non usare `terminal close` al posto di release su worker attivo o stato ignoto. Prima verifica rapporto e output; segui anche `lancio-worker` e `scripts/orca-fine-worker.sh`. Coordinatore vecchio si chiude solo dopo primo battito del nuovo. Mai uccidere processi senza verificare PID, cwd e modello.

Se compare segreto: chiudi vista, non copiarlo né citarlo nei log; avvisa direzione perché titolare decida rotazione.
