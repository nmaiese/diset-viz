---
name: lancio-worker
description: "Gestisce assegnazione, attesa, verifica e chiusura dei worker Orca. Usala quando un coordinatore lancia o chiude un worker."
---

# Lancio e chiusura worker

Il coordinatore assegna, verifica e chiude; il worker esegue spec. Base errata ha prodotto file giocattolo, rapporti «tutto verde» falsi: verifica base, diff e prova dichiarata.

## Prima del lancio

1. Coordinatore fa lettura, grep e controllo stato; worker serve per implementazione, review o ricerca lunga.
2. Verifica RAM: `free -m`, available ≥ 1,5 GB e swap ≤ 50%; altrimenti non lanciare.
3. Scegli modello con `modelli-societa`; rispetta mix provider circa 40% e review di famiglia diversa.
4. Prepara spec nel worktree coordinatore: obiettivo, repo/base, file attesi, passi, esclusioni, criterio osservabile e rapporto ≤30 righe con prove.
5. Crea worktree da `main` aggiornato. Worker controlla subito file attesi; se mancano, si ferma. Mai `git reset` su lavoro esistente, rami remoti, push di cancellazioni o `--force`.

## Lancio

Esegui da worktree del repo giusto; altrimenti launcher può scegliere repo errato.

```bash
~/dev/dev-tools/scripts/orca-lancia.sh --agent <codex|claude|opencode|antigravity|grok> \
  [--model <modello-esatto>] --effort <livello> [--ok-direzione] --worktree <nome> --spec-file <percorso>
# In alternativa: --attivita <nome> al posto di --agent (modello da agents/ruoli.tsv).
```

Scegli l'effort dalla tabella di `docs/MODELLI.md` §7b.

Per `agy`, launcher rifiuta `--effort` e non seleziona il modello con `--model`: modello ed effort stanno nelle impostazioni Antigravity. Anche OpenCode rifiuta `--effort`. Se spec usa modello gratuito, dichiara `dati personali: nessuno`. Modello in `docs/MODELLI.md`. Worktree non visibile? Controlla `git worktree list` e `orca-ide worktree list`; non duplicare stesso nome.

## Attesa e verifica

Usa attese brevi, così coordinatore resta reattivo al ponte. Exit 3 segnala domanda/escalation da gestire; exit 4 segnala timeout o Dispatch fermo: rileggi stato e riarmi con stesso dispatch e handle verificati. Per un'attesa lunga, esegui giri brevi dalla sessione del coordinatore e riarmali con Monitor prima della sua scadenza (~28 minuti); non staccare il processo dal terminale Orca.

```bash
~/dev/dev-tools/scripts/orca-attendi.sh --attesi 1 --dispatch <id> --terminal <handle-del-coordinatore> --timeout-ms 170000
orca-ide terminal read --terminal <handle-worker> --limit 80 --json
orca-ide orchestration check --run <id> --json
```

Leggi terminale al battito per distinguere lavoro, quota, permesso o errore. `worker_done` comunica esito, non chiude ciclo di rilascio. Quando arriva: leggi rapporto e diff, ripeti una prova dichiarata; poi gate `cancello-merge`.

## Chiusura

```bash
~/dev/dev-tools/scripts/orca-fine-worker.sh --worktree <percorso>
# Solo dopo gate superato, se merge autorizzato:
~/dev/dev-tools/scripts/orca-fine-worker.sh --worktree <percorso> --unisci
```

`orca-fine-worker.sh` e `orca-chiudi.sh` rimuovono worktree soltanto nel repo dev-tools che contiene gli script. Per Trade5/Divario, dopo `worker_done` ricevuto con `orca-attendi.sh`, verifica con `orca-ide orchestration worker-show --dispatch <id> --json` che Dispatch sia concluso e terminale/worktree corrispondano al worker esatto. Controlla `git -C <worktree> status --porcelain --untracked-files=all`, HEAD, ramo e file ignorati da conservare. Se i commit non sono uniti, conserva il ramo e crea prima un tag `parcheggio/<nome>` sul suo HEAD. Poi `orca-ide orchestration worker-release --dispatch <id> --json`; se il terminale esterno risulta `retained`, chiudi solo il suo handle con `orca-ide terminal close --terminal <handle> --json`. Se il worktree esiste ancora ed è pulito, usa `orca-ide worktree rm --worktree path:<percorso-assoluto> --json`, senza `--force`, e verifica l'assenza con `git worktree list` e inventario Orca. Se identità, stato o inventario non sono verificabili, conserva il worktree. `--unisci` di `orca-fine-worker.sh` esegue `git merge --no-ff` in dev-tools `main`: solo dopo gate superato. Dopo cleanup, `git -C <repo> branch -d <ramo>` solo se unito; `-D` solo su ordine esplicito direzione dopo verifica tag. Niente `cd && git`.
