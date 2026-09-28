Sei il revisore della review 3 della PR #291 di nmaiese/diset-viz (strumento 2c, scripts/orca_review.py), lanciato dal team leader in headless. Sei OpenCode big-pickle, una sessione nuova. Il codice di questo giro l'ha scritto Antigravity, i test li ha scritti un'altra sessione di OpenCode big-pickle: giudica i test con particolare severità. Commit atteso: b1ac953b93ac78650e6ca122608bedfdb54fe5be. È il terzo e ultimo giro: dopo va a Nello comunque.

NON leggere, aprire o elencare file fuori dal worktree e non usare percorsi assoluti nei comandi (neanche /dev/null o /tmp): OpenCode headless chiude la sessione. Temporanei in .rev291-3/ e poi cancellati. Su questa macchina Python va in crash a caso: un errore che al rilancio sparisce è della macchina, lo conti in una riga e non lo indaghi.

Controlla lo SHA (git rev-parse HEAD e gh pr view 291 --json headRefOid -q .headRefOid, uguali fra loro e a quello atteso). Leggi la review 2 (gh pr view 291 --json reviews --jq '.reviews[-1].body') e il commento sul difetto di --scheda (gh pr view 291 --json comments --jq '.comments[-1].body'). Il cambiamento di questo giro è git diff bb1464db..HEAD (bb1464db è il merge che allinea la pila, già verificato).

Domande:
1. --scheda accetta ter-12, 12, bes-06POL012P e bes:06POL012P, legge i testi con la chiave interna e le fonti da lavoro/<codice dell'URL>/fonti.md? Provalo a secco da questo worktree con bin/py scripts/orca_review.py rev-291-3 --base nmaiese/strumento-2c-review --scheda <forma> --dry-run per almeno ter-12, 12 e una scheda bes, e riporta le sezioni del corpo. Solo --dry-run, niente pubblicazioni.
2. Una scheda che non esiste esce con 1, con "[!]" e senza traceback, prima di toccare git?
3. I due test nuovi falliscono sul codice di prima e passano sul nuovo? Verificalo tu: copia la versione di prima dello script in .rev291-3/ con git show bb1464db:scripts/orca_review.py e fai girare i due test contro di lei (per esempio sostituendo temporaneamente il file e rimettendolo con git checkout -- scripts/orca_review.py), senza lasciare modifiche.
4. La riparazione ha rotto qualcosa del resto del file (--base, --label, il file temporaneo del corpo che si cancella, la validazione dei caratteri di --scheda)?

Interprete: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py. Esegui bin/py -m unittest tests.unit.test_orca_scripts.

Regole di questo giro headless: gh solo in lettura. NON pubblicare nulla. NON modificare file del repo alla fine (git status pulito), non committare.

La tua risposta finale è SOLO il testo della review in Markdown: prima riga "## Review 3 di PR #291: <verdetto>" con verdetto DA CORREGGERE oppure PRONTA PER NELLO, seconda riga lo SHA verificato, poi le quattro domande con file:riga, citazione, motivo e correzione minima per ogni no, poi l'output dei test. I rilievi minori vanno in "Note" e non cambiano il verdetto.
