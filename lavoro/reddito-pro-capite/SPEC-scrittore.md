# Scrittore (pilota 1 del blog): articolo sul reddito pro capite per regione
Worktree divario-blog-reddito-pil, ramo divario/blog-reddito-pro-capite. Sei lo scrittore della pipeline di `docs/design_drafts/team/PIANO.md`. Mai push, merge, deploy. Commit locale in italiano, prosa, senza Co-Authored-By.
## Input (leggi in quest'ordine, non c'e altro)
`lavoro/reddito-pro-capite/brief.md` (e il tuo unico input numerico), `lavoro/reddito-pro-capite/fonti.md` (citazioni letterali ammesse), `lavoro/reddito-pro-capite/dossier-ter-901.json` e `dossier-ter-902.json`, `content/STYLE.md` (regole vincolanti), `content/esempi/lavoce-salari-sud.md` (il tuo unico modello di voce). NON leggere altre bozze del tema in altri rami o worktree, ne l'articolo `content/posts/2026-06-30-pil-pro-capite-regioni-divario-2024.md` per copiarne la struttura: esiste, non va ripetuto.
## Che cosa produrre
1. `content/posts/2026-10-05-reddito-pro-capite-regioni-non-e-il-pil.md` con il frontmatter descritto nel brief (draft: true, senza author, dataset, external_figures per i numeri non del sito).
2. `app/static/data/articles/reddito-pro-capite-regioni.csv` (le venti regioni, colonne come nella tabella del brief, valori da `data.get_indicator('901')` e `('902')`, righe con fine linea `\n`).
3. L'articolo. Forma libera, nessuna sezione predefinita. Una domanda reale, una tesi, un ancoraggio con due regioni, una digressione. Segui la lista "non IA" del brief.
## Controlli prima del commit (output corto)
`rg -n "[—–;…]" content/posts/2026-10-05-reddito-pro-capite-regioni-non-e-il-pil.md` deve essere vuoto. Verifica ogni numero del testo contro il brief e contro `data.get_indicator` (interprete: `export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python`, poi `PYTHONPATH=. bin/py`). Ogni regione con un valore nominata la prima volta ha il suo link `/regione/<chiave>`. `bin/py -m unittest tests.integration.test_blog -q` se esiste, e `bin/py -m unittest discover -s tests/unit -q` senza nuove regressioni (preesistenti: manca `requests`).
`worker_done`: tre frasi, il grafico che regge la tesi, e l'elenco dei punti in cui hai dubbi.
