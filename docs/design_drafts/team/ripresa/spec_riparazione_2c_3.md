Riparazione dello strumento 2c, scripts/orca_review.py (PR #291 e issue #288 di nmaiese/diset-viz), lanciata dal team leader in headless nel worktree della 2c. Il ramo ha appena ricevuto con un merge la 2b e la 2a (commit bb1464db).

Il difetto, trovato usando lo script sul pilota ter-12 (PR #293): --scheda vuole la chiave interna per i testi e il codice dell'URL per la cartella di lavoro.
- Con --scheda ter-12 il corpo della PR dice "Nessun testo precedente" e "File nuovo non trovato", perché indicator_store.filename_for riceve "ter-12" invece di "12".
- Con --scheda 12 i testi escono, ma la sezione delle fonti manca, perché lo script cerca lavoro/12/fonti.md mentre la cartella di lavoro usa il codice dell'URL, lavoro/ter-12/fonti.md (così la vogliono le skill in skills/editorial-team/).

Correggi scripts/orca_review.py e tests/unit/test_orca_scripts.py così:
1. --scheda accetta tutte le forme che accetta la guardia (scripts/editoriale/guardia.py: "ter-12, 12, bes-06POL012P o bes:06POL012P"). Riusa la stessa risoluzione del codice che usa la guardia o il sito, non scriverne una nuova a mano.
2. I testi prima e dopo si leggono con la chiave interna (12, bes:06POL012P). Le fonti si leggono da lavoro/<codice dell'URL>/fonti.md (ter-12, bes-06POL012P).
3. Una scheda che non si risolve dà "[!] ..." su stderr e return 1, come il resto del file. La validazione dei caratteri che c'è già resta.
4. Test: --scheda ter-12 e --scheda 12 producono lo stesso corpo, con testo prima, testo dopo e fonti. Una scheda che non esiste dà return 1. I test esistenti restano verdi.

Interprete: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py. Esegui bin/py -m unittest tests.unit.test_orca_scripts (non la suite intera: su questa macchina Python va in crash a caso, e un errore che non si ripete rilanciando è della macchina). Poi prova dal vero, a secco, dal worktree del pilota: cd /home/nilo/dev/sites/divarioitalia/.orca/worktrees/divarioitalia/ind-ter-12 && DIVARIO_PYTHON=... bin/py /home/nilo/dev/sites/divarioitalia/.orca/worktrees/divarioitalia/strumento-2c-review/scripts/orca_review.py ind-ter-12 --issue 292 --base nmaiese/strumento-2c-review --scheda ter-12 --dry-run, e controlla che il corpo abbia testo prima, testo dopo e fonti. Solo --dry-run: non pubblicare niente.

git diff --check pulito. Tocca solo scripts/orca_review.py e tests/unit/test_orca_scripts.py. Nessun altro file nel worktree (niente rewrite.py, patch_*.py, report.md), temporanei in /tmp. Non fare git add né commit.

Alla fine rispondi in italiano con le modifiche punto per punto, i test aggiunti per nome, l'output dei test, le prime righe di ciascuna sezione del corpo nella prova a secco e git diff --stat.
