---
name: lancio-e-cancello-divario
description: Dettagli specifici di Divario Italia per lanciare o rilanciare worker Orca, aprire PR, verificare CI, fare merge, deploy Cloud Run, prova dal vivo e rollback. Usala con lancio-worker e cancello-merge; non serve per modifiche locali senza ciclo Orca.
---

# Lancio e cancello Divario Italia

Per ciclo dei worker, modelli, RAM e pulizia leggi la skill comune `/mnt/c/Users/Nilo/orca/specs/skills_societa/lancio-worker/SKILL.md`. Per review, autorizzazioni, numero di giri, ordine del merge e cancello di produzione leggi `/mnt/c/Users/Nilo/orca/specs/skills_societa/cancello-merge/SKILL.md` e il più recente `/mnt/c/Users/Nilo/orca/specs/REGOLAMENTO_coordinatori.md`. La scheda del coordinatore è `/mnt/c/Users/Nilo/orca/specs/ruoli/C-DIV-coord-divario.md`. Se una copia locale contrasta con il REGOLAMENTO, prevale quest'ultimo.

Per creare un worktree Divario usa `~/dev/dev-tools/scripts/orca-worktree.sh <nome> --repo id:d2ae0385-1020-40e5-8859-7fbd55a33e03 --base-branch origin/master`; sostituisci `origin/master` con il ramo richiesto dalla spec. Nel solo worktree nuovo, se necessario, rinomina il ramo `divario/<compito>` con `git -C <worktree> branch -m divario/<compito>`. Verifica base e ramo prima del lancio: un worker su una base vecchia vede test vecchi.

## Prove del repository

- Usa sempre `bin/py` con l'interprete del progetto: `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m unittest discover -s tests -v`. Il router `CLAUDE.md` possiede gli altri comandi. Dopo modifiche a `frontend/src/`, esegui la build frontend; verifica le job CI Python e frontend prima del cancello. Un modulo non importato per dipendenza mancante non è un test passato.
- Problemi già osservati: `test_verify_pezzi_trend` può fermarsi per `PIL` mancante; `test_la_testata_della_home_ha_la_mappa_coi_dati` è instabile perché sceglie un indicatore variabile. Verifica ambiente, job e confronto con `origin/master` prima di attribuire un fallimento al ramo. Registra separatamente baseline, regressioni nuove e test non eseguiti; non dichiarare CI verde senza output corrente.

## Cancello e deploy

- Il push GitHub di divarioitalia richiede ok scritto della direzione, anche sul ramo di lavoro: solo fast-forward, mai force. Merge in produzione solo dopo cancello e ok scritto; uno alla volta. Due merge ravvicinati fecero vincere la build vecchia: attendi deploy e prova del primo prima del secondo.
- Prima del merge annota **la revisione che serve il 100% del traffico**, non soltanto `latestReadyRevisionName`: `gcloud run services describe diset-viz --region europe-west1 --project nil-automata --format='json(status.traffic,status.latestReadyRevisionName)'`. Conserva revisione e piano di rollback nel rapporto.
- Dopo deploy, verifica che nuova revisione serva il 100% e prova contenuto vivo con `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.prova_dal_vivo --da <commit prima> --a <commit dopo>`. Il comando confronta frasi nuove di `content/` sul sito; `nessun_file` non prova una modifica di solo codice. Controlla anche tre pagine a campione e l'effetto atteso. Un HTTP 200 non bastò a mostrare il testo nuovo nella build sbagliata.
- Nel controllo vivo verifica cognome del titolare, nome del gestore ed email personale assenti da pagine pubbliche e feed fuori da `/privacy`. Non scrivere i valori personali nella skill, nei comandi di esempio o nel rapporto.
- Nei controlli HTTP usa User-Agent `DivarioCheck/1.0`; `prova_dal_vivo` lo imposta già. Nei controlli browser blocca richieste analytics e ads, per non sporcare misure e impressioni: i controlli Dev hanno già sporcato o rischiato di sporcare dati. Documenta i blocchi applicati.
- Se la prova fallisce, riporta la revisione annotata al 100% con `gcloud run services update-traffic diset-viz --to-revisions <revisione-precedente>=100 --region europe-west1 --project nil-automata`, poi verifica traffico e riferisci l'esito. Segui `cancello-merge` per eventuale revert del codice: non riscrivere la storia Git.
