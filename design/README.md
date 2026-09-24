# design/

Qui sta il progetto della **versione 1.0** del sito: il sistema di pagina e i
prototipi statici delle pagine chiave, costruiti con dati veri. La 1.0 e' in
produzione, ma **il sito non legge niente da qui**: i token stanno in
`app/static/css/ds/system.css`, i componenti in `css/ds/components.css`, le
pagine in `app/templates/v1/` e cio' che chiedono ai dati in `app/design/`. Un
prototipo che cambia qui arriva al sito solo con una PR che lo porta in `app/`.

La cartella non finisce nell'immagine di Cloud Run (il `Dockerfile` copia solo
`frontend/`, `app/`, `content/`, `scripts/`, `packs/`, `data/` e `run.py`) e
`unittest discover -s tests` non la vede. Per questo si scrive su `master` come
la documentazione.

## Che cosa c'e'

- `v1/SISTEMA.md`: griglia, tipografia, componenti, pagine e regole di
  contenuto. E' il documento da leggere prima di toccare un template della 1.0.
- `v1/tokens/tokens.json`: i valori della direzione scelta, "Cronaca". Da qui
  `tools/tokens.py` genera `src/css/tokens.css`. Un colore si cambia qui, mai
  nel CSS dei componenti.
- `v1/src/`: layout, pagine e partial Jinja dei prototipi, il foglio dei
  componenti e il poco JavaScript che serve.
- `v1/data/`: l'istantanea del contesto vero delle pagine di esempio, catturata
  dall'app. Nessuna cifra dei prototipi e' scritta a mano.
- `v1/dist/pagine/`: le pagine rese, documenti completi che si aprono con un
  doppio clic.
- `v1/screens/`: gli screenshot del sito prima e dei prototipi dopo.

## I comandi

```bash
bin/py design/v1/tools/extract.py        # cattura il contesto delle pagine di esempio
bin/py design/v1/tools/tokens.py         # tokens.json -> src/css/tokens.css
bin/py design/v1/tools/check_tokens.py   # contrasti e daltonismo, esce non zero se una soglia salta
bin/py design/v1/tools/build.py          # rende i prototipi in dist/pagine/
bin/py design/v1/tools/check_pages.py    # punteggiatura, numeri, colori, struttura
node design/v1/tools/shots.mjs prima     # screenshot della produzione
node design/v1/tools/shots.mjs dopo      # screenshot dei prototipi
node design/v1/tools/shots.mjs check     # scorrimento orizzontale e tastiera
node design/v1/tools/shots.mjs giro <base> <cartella> /,/temi        # il sito servito: pieghe, sforamenti, errori, richieste fallite
node design/v1/tools/shots.mjs tastiera <base> /,/regione/puglia     # il sito servito: salto al contenuto, focus, cassetto
```

`giro` e `tastiera` lavorano su un sito servito, locale o produzione. In locale
gunicorn va lanciato con i thread (`--worker-class gthread --threads 8`, come
nel Dockerfile): con un solo worker sincrono una connessione aperta da Chrome
senza richiesta lo tiene fermo fino al timeout.

Chrome headless non disegna dentro la sandbox di Claude Code: `shots.mjs` va
lanciato fuori sandbox, o a mano.
