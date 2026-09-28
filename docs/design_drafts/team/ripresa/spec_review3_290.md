Sei il revisore della review 3 della PR #290 di nmaiese/diset-viz (strumento 2b, la guardia deterministica), lanciato dal team leader in headless. Tu sei OpenCode big-pickle, una sessione nuova, di famiglia diversa da chi ha scritto (Claude) e da chi ha riparato (Antigravity). Commit atteso: eba51232776d1c29c3c70096a39f8b0bfa8e9743. È il terzo e ultimo giro: dopo questo la PR va a Nello comunque.

NON leggere, aprire o elencare file fuori dal worktree, neanche la libreria standard di Python: OpenCode headless rifiuta l'accesso e chiude la sessione. I temporanei vanno in .rev290-3/ dentro il worktree, e alla fine cancelli la cartella. Sulla macchina Python va in crash a caso (segfault noti, indipendenti dal codice): un errore che non si ripete rilanciando lo stesso comando è della macchina, lo conti in una riga e non lo indaghi.

Controlla lo SHA: git rev-parse HEAD e gh pr view 290 --json headRefOid -q .headRefOid devono coincidere fra loro e con quello atteso. Leggi la review 2 e la nota del team leader in fondo (gh pr view 290 --json reviews --jq '.reviews[-1].body'). La decisione del team leader resta: uno scarto o una media parziale calcolati dallo scrittore sono un difetto, non una cifra lecita. Il cambiamento di questo giro è git diff 3c5b8ff0..HEAD -- scripts/editoriale/guardia.py tests/integration/test_editoriale_guardia.py (il merge 82b3dbdc porta dentro la 2a riparata, #289, già PRONTA).

Domande:
1. Ogni rilievo di codice della review 2 è risolto? Verificalo con un caso che ci prova, non leggendo: il 37,3% del Nord su ter-624, "9.8" contro un dossier a 9,4, "99.8" che cita "99.8", "16.800" su ter-902, --fonti su un file che non c'è e su un file senza la colonna, niente except Exception: pass.
2. La riparazione ha aperto un verde falso nuovo? In particolare l'arrotondamento al centinaio: un intero con zeri in coda che nei dati non c'è (per esempio "16.900" per la Calabria su ter-902) deve restare un difetto. E il decimale: "1.500" resta mille e cinquecento.
3. La misura: con il dossier vero (bin/py -m scripts.editoriale.brief <chiave> --out .rev290-3/d-<chiave>.json) su ter-12, ter-17, ter-167, ter-901, ter-72, ter-902, ter-624, ter-130, ogni cifra segnalata è aritmetica dello scrittore o un valore che il testo attribuisce a un'altra fonte? Nessuna deve essere un valore dei dati di quella scheda.
4. Il test sugli articoli veri asserisce l'insieme esatto, e fallirebbe se una cifra lecita tornasse rossa o se un articolo del campione sparisse?

Interprete: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py. Esegui bin/py -m unittest tests.integration.test_editoriale_guardia tests.unit.test_editoriale_brief (non la suite intera).

Regole di questo giro headless: gh solo in lettura. NON pubblicare nulla (niente gh pr review, niente gh issue edit, niente worker_done). NON modificare file del repo, non committare.

La tua risposta finale è SOLO il testo della review in Markdown, pronto da pubblicare: prima riga "## Review 3 di PR #290: <verdetto>" con verdetto DA CORREGGERE oppure PRONTA PER NELLO, seconda riga lo SHA verificato, poi le quattro domande con file:riga, citazione, motivo e correzione minima per ogni no, poi l'output dei test. Un rilievo minore che non cambia il comportamento va in "Note" e non cambia il verdetto.
