## Revisione automatica — PR #291 (worker Orca, famiglia diversa dall'autore)

SHA verificato: `8c71db94edd77651d594e40581c9c090bc5812d2` (`git rev-parse HEAD` == `gh pr view 291 --json headRefOid`).

### Risposte alle domande della issue

1. **Fa quello che chiede #288?** Sì, funzionalmente: `--base` propagato sia al conteggio commit (`git rev-list --count origin/<base>..HEAD`) sia a `gh pr create --base`; `--label` ripetibile (`action="append"`); la PR resta sempre `--draft`; `--scheda` compone il corpo con SHA, testo di TASK.md, testo prima (da `origin/<base>`) e nuovo (da `indicator_store.read`/`rendi`), fonti da `lavoro/<chiave>/fonti.md`, `Closes #n`; il corpo passa con `--body-file`; `--dry-run` stampa i comandi senza eseguire `git push`/`gh pr create`. Verificato con esecuzione reale (vedi sotto).

2. **Casi rotti — verificati uno per uno:**
   - Base diversa da `master`: OK, testato dal vivo (`--base nmaiese/strumento-2b-guardia`), sia nel conteggio commit sia nel comando `gh pr create`.
   - Scheda senza articolo su `origin/<base>`: gestito senza eccezioni, produce `_Nessun testo precedente o file non trovato in origin/<base>_` / `_File nuovo non trovato_` (testato dal vivo con `--scheda ter-12`, che non esiste).
   - `fonti.md` assente: gestito, la sezione "Fonti nuove" viene semplicemente omessa (`if fonti_file.is_file()`).
   - Label vuota: non è un problema dello script (nessuna validazione, ma `gh` la rifiuterebbe a valle); non bloccante.
   - **File temporaneo del corpo che resta in giro: CONFERMATO, bug reale.** `scripts/orca_review.py:196` chiama `tempfile.mkstemp()` **incondizionatamente**, anche quando `dry_run=True` e anche nel percorso normale il file non viene mai cancellato dopo `gh pr create` (nessun `os.remove`/`finally`). Riprodotto dal vivo: un `--dry-run` con `--scheda ter-12` ha lasciato un file da 283 byte in `/tmp` (contenuto reale del corpo PR) mai referenziato da nessun comando stampato, perché il comando stampato in dry-run usa il placeholder letterale `"PR_BODY.md"` (riga 212) che non esiste. Quindi il dry-run non è più "senza effetti collaterali": scrive comunque un file reale e lo abbandona, e il comando stampato non corrisponde a cosa è successo davvero su disco.
   - **Non nella lista della issue ma trovato testando:** `--scheda` con una chiave che contiene `__` (il separatore di `indicator_store.filename_for`) fa risalire un'eccezione `StoreError` non gestita fino a un traceback grezzo, invece del pattern `_print_failure` + `return 1` usato ovunque nel resto del file. Riprodotto dal vivo chiamando `_task_body` con `scheda="indicatore__con__separatore"`.

3. **I test coprono davvero, o passano per costruzione?** In parte per costruzione. I 4 test nuovi verificano solo i comandi stampati/i valori nella lista argomenti (`--base`, `--label`, contenuto del corpo mockato), mai gli effetti collaterali reali: nessun test controlla che il file temporaneo venga creato con contenuto corretto né che venga ripulito, quindi il leak del punto precedente sopravvive a 16 test verdi. `test_scheda_compone_corpo` mocka `indicator_store.filename_for/analizza/read/rendi` per intero: non testa la StoreError su chiave malformata né il ramo `ImportError` di `indicator_store`.

4. **Sicurezza.** I comandi sono costruiti come liste di argomenti passate a `subprocess.run` senza `shell=True`, quindi niente shell injection classica. `base`/`scheda`/`labels` (input non fidato lato CLI) finiscono come singoli argomenti in `git rev-list`, `git show`, `gh pr create` senza validazione: un valore che comincia per `-` verrebbe interpretato come opzione da `git`/`gh` (basso rischio, tool locale). Più concreto: `scheda` è interpolato senza sanitizzazione nel percorso `worktree_path / "lavoro" / scheda / "fonti.md"` (riga 147); una chiave con `..` potrebbe far uscire la lettura dal worktree e finire nel corpo di una PR pubblica. Il file temporaneo del corpo (bug del punto 2) è creato con `tempfile.mkstemp` (permessi utente, non world-readable), quindi non è di per sé un problema di sicurezza, solo di pulizia.

### Test eseguiti

- `bin/py -m unittest tests.unit.test_orca_scripts` con `DIVARIO_PYTHON=.venv/bin/python`: **16 test, tutti verdi**.
- `bin/py scripts/orca_review.py rev-291-1 --dry-run --base nmaiese/strumento-2b-guardia --label run:team --label infra --scheda ter-12`: comandi stampati corretti (`--base`, doppio `--label`, `--body-file PR_BODY.md`), ma ha lasciato un file temporaneo reale in `/tmp` (rimosso a mano dopo l'ispezione).

### Secondo parere (opencode headless, gpt-oss:120b, non bloccante)

Accordo: segnala lo stesso leak concettuale attorno al file temporaneo e l'incoerenza del placeholder `PR_BODY.md` in dry-run; segnala anche la `sys.path.insert` senza cleanup (riga 30) — minore ma legittimo, può contaminare import successivi nello stesso processo.

Disaccordo: ha sostenuto che `open(body_fd, "w")` (riga 197) sia un bug perché "open si aspetta un path, non un file descriptor" e che quindi tutta la PR fallirebbe con `TypeError`. È falso: `open()` in Python accetta un intero come file descriptor (comportamento documentato, equivalente a `os.fdopen`); i 16 test verdi e la mia esecuzione reale del dry-run lo confermano empiricamente — nessun `TypeError`. Ho scartato questo rilievo.

### Verdetto: **DA CORREGGERE**

SHA revisionato: `8c71db94edd77651d594e40581c9c090bc5812d2`.

Correzioni minime richieste prima del merge:
1. `scripts/orca_review.py:196-198` — creare il file temporaneo solo quando serve davvero (non in `dry_run`) e cancellarlo con `finally`/`os.remove` dopo `gh pr create` (successo o fallimento). In `dry_run`, il comando stampato dovrebbe riferirsi a un percorso reale o a un placeholder esplicito senza scrivere nulla su disco.
2. `scripts/orca_review.py:113` — avvolgere `indicator_store.filename_for(scheda)` in un `try/except StoreError` e restituire un messaggio `[!] ...` + `return 1`, coerente col resto del file, invece di lasciar risalire il traceback.
3. Opzionale ma consigliato: validare/normalizzare `scheda` prima di comporre `worktree_path / "lavoro" / scheda / "fonti.md"` per evitare traversal di percorso.
