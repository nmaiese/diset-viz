---
name: lancio-e-cancello-divario
description: Come si lancia, si controlla e si chiude un worker Orca sul repo divarioitalia, e come un ramo passa in produzione (il merge su master e il deploy). Usala sempre quando devi lanciare o rilanciare un worker o una review con orca-lancia.sh, controllare un terminale fermo per quota o permesso, portare un ramo di divarioitalia in produzione (PR, merge, deploy, rollback, prova dal sito vivo), ripulire i worktree finiti, o scrivere la spec di un worker su un modello gratuito. Non serve per una singola modifica fatta a mano o per una domanda sul codice.
---

# Lancio dei worker e cancello di produzione, divarioitalia

Questa procedura esiste perche gli stessi errori si sono ripetuti in una sera: un lancio con la RAM sotto soglia, un worker fermo per quota per ore senza che nessuno lo vedesse, un terminale chiuso mentre il worker lavorava, una review rimasta muta, un test instabile scambiato per regressione, una spec a un modello gratuito con dati personali. Il merge su master pubblica il sito: il cancello esiste per questo.

## 1. Prima di ogni lancio
- RAM: `free -m` e leggi la colonna **available**. Sotto 1,5 GB niente lancio finche non pulisci. Swap oltre il 50%: stesso (soglie della direzione, 3/10). Un lancio alla volta.
- Percorsi sempre assoluti: il guard rifiuta `orca-lancia.sh` o `orca-worktree.sh` se non risolvono in `~/dev/dev-tools/scripts/`. Mai headless (`codex exec`, `opencode run`, `claude -p`), mai `orca-ide terminal create` a mano.
- Worktree: `~/dev/dev-tools/scripts/orca-worktree.sh <nome> --repo id:d2ae0385-1020-40e5-8859-7fbd55a33e03 --base-branch <ramo o origin/master>`. Rinomina il ramo con `git branch -m divario/<compito>` e tieni il worktree con lo stesso nome. Il ramo di partenza e quello che serve: un worker su un ramo vecchio vede test vecchi.
- Lancio: `~/dev/dev-tools/scripts/orca-lancia.sh --agent <agente> [--model <m>] | --attivita <x> --worktree <nome> --spec-file <file> [--sola-lettura]`. Una spec per file. Per review e red team `--sola-lettura` e poi controlla che `git status --porcelain` resti vuoto.
- Modello: implementazione Codex (se ha quota), Claude sonnet per il resto, review e red team di un'altra famiglia dall'autore. Se un fornitore e esaurito, riassegna subito a un altro, non aspettare. I nomi esatti dei modelli stanno in `~/dev/dev-tools/agents/ruoli.tsv` e `~/dev/dev-tools/docs/opencode-modelli.md`.
- Modelli gratuiti (big-pickle, nemotron, longcat): mai dati personali. Cioe nessun nome, email, cognome o gestore del titolare, nessun `.env`, nessun messaggio del titolare, nessun analytics non aggregato. Scrivi nella spec la riga "dati personali: nessuno" solo dopo averlo verificato. Se serve cercare un cognome o un indirizzo, il pattern si costruisce per concatenazione dentro il test (mai in chiaro nella spec) e la verifica e a pagamento o in CI.

## 2. Mentre il worker lavora
A ogni battito (`/home/nilo/dev/trade5/.venv/bin/t5 ponte battito C-DIV "testo"`, ogni passo, RAM e swap compaiono da soli) leggi la coda di ogni terminale con `orca-ide terminal read --terminal <handle> --json | jq -r '.result.terminal.tail[]?'` e classifica: al lavoro, finito, fermo per quota ("usage limit reached"), fermo su richiesta di permesso, fermo per errore. Quota: chiudi e rilancia lo stesso compito su un altro modello. Permesso dentro il suo worktree senza push, segreti, rete esterna o cancellazioni: rispondi tu. Altrimenti nega e scrivilo.
- Il `worker_done` arriva con `orca-ide orchestration check --run <id> --json | jq '.result.messages[]?'`. A volte non compare: in quel caso leggi il terminale. Quando lo aspetti in un monitor, conta i messaggi con un confronto numerico (`[ "${g:-0}" -ge 1 ]`), mai con una stringa.
- **Chiudi un terminale solo dopo aver visto il `worker_done` e il commit** (`git log`, `git status`). Chiuderlo prima uccide il worker a meta.
- Un worker non e finito se i file esistono ma non c'e commit. Rilancia una ripresa con una spec che dice cosa c'e gia su disco.

## 3. Cancello di produzione
Test verdi (la suite di integration ha un errore preesistente `test_verify_pezzi_trend` per `PIL` mancante e un test instabile sulla home, `test_la_testata_della_home_ha_la_mappa_coi_dati`, che pesca un indicatore a caso: rilancia la sola job prima di cercare una regressione). Una review di un'altra famiglia con rilievi numerati e chiusi uno per uno. Red team a contesto pulito (sola lettura, non gli dici le tue conclusioni). Massimo due giri di review (regola della direzione): se dopo il secondo resta un bloccante scrivi alla direzione, che decide. Prova funzionale e piano di rollback scritto prima del merge: la revisione Cloud Run attuale (`gcloud run services describe diset-viz --region europe-west1 --project nil-automata --format='value(status.latestReadyRevisionName)'`).

## 4. Merge, deploy e prova dal vivo
`git push -u origin <ramo>`, `gh pr create --base master --head <ramo>` (descrizione in italiano, prosa), aspetta la CI python e frontend (circa 11 minuti), `gh pr merge <n> --merge`. Il deploy di Cloud Build dura 10-19 minuti: aspetta che `status.latestReadyRevisionName` cambi. Poi prova dal sito vivo con `curl` (Cloudflare da 403 allo user agent di Python):
- le pagine principali rispondono 200 (home, regione, provincia, scheda, /privacy, /chi-siamo, /blog, /sitemap.xml)
- cognome, gestore e email personale: zero su tutte le pagine e feed, tranne /privacy (intestatario)
- l'effetto atteso della modifica (conteggio sitemap, `x-robots-tag`, canonical) su un campione
Se una prova fallisce: rollback immediato alla revisione precedente (`gcloud run services update-traffic diset-viz --to-revisions <rev>=100 ...`) e rapporto. Scrivi nel rapporto commit di merge, revisione nuova, comandi e output.

## 5. Dopo
Chiudi i terminali finiti, poi i worktree puliti con `orca-ide worktree rm --worktree path:<percorso>` (mai `git worktree remove -f`). Metti un tag `parcheggio/<nome>` sul commit prima: `rm` cancella anche il ramo locale se e unito. Mai toccare worktree di altri coordinatori. Nessun ramo non unito si perde. Scrivi nel battito che cosa e in corso o "coda vuota".
