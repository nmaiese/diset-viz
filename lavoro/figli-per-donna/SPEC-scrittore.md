# Scrittore (pilota 2 del blog): articolo sul numero medio di figli per donna per regione
Worktree divario-blog-figli-per-donna, ramo divario/blog-figli-per-donna. Sei lo scrittore della pipeline di `docs/design_drafts/team/PIANO.md`. Mai push, merge, deploy. Commit locale in italiano, prosa, senza Co-Authored-By.
## Input (leggi in quest'ordine, non c'e altro)
`lavoro/figli-per-donna/brief.md` (e il tuo unico input numerico), `lavoro/figli-per-donna/fonti.md` (citazioni letterali ammesse), `lavoro/figli-per-donna/dossier-ter-922.json`, `content/STYLE.md` (regole vincolanti), `content/esempi/lavoce-salari-sud.md` (il tuo unico modello di voce). Per il frontmatter puoi guardare `content/posts/2026-09-29-casa-affitti-mercato.md`. NON leggere altri pezzi per copiarne struttura o frasi.
## Che cosa produrre
1. `content/posts/2026-10-06-figli-per-donna-regioni-italia.md` con il frontmatter descritto nel brief (draft: true, senza author, dataset, external_figures per i numeri non del sito).
2. `app/static/data/articles/figli-per-donna-regioni.csv` (venti regioni, valori 2010 e 2025, variazione, posti; da `data.get_indicator('922')`; righe con fine linea `\n`).
3. L'articolo: forma libera, nessuna sezione predefinita, una domanda reale, una tesi, un ancoraggio con due regioni, una digressione, link `/regione/<chiave>` alla prima menzione di una regione con un valore, marcatori `<!-- figura: nome -->` dove servono i due grafici del brief.
## Controlli prima del commit (output corto)
`rg -n "[—–;…]" content/posts/2026-10-06-figli-per-donna-regioni-italia.md` vuoto. Ogni numero del testo contro il brief e contro `data.get_indicator('922')` (interprete: `export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python`, poi `PYTHONPATH=. bin/py`). Ogni correlazione o confronto citato misurato. `bin/py -m unittest tests.integration.test_blog -q` se esiste (togli `draft` solo per provare, poi rimettilo).
`worker_done`: tre frasi, i due grafici che reggono la tesi, e i punti in cui hai dubbi.
