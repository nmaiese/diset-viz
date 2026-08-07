"""L'officina: dove un articolo si scrive, si controlla e si pubblica.

Due moduli soltanto, e nessun agente-file.

- `lint`     l'unico cancello editoriale. Deterministico, nessun modello.
- (il workflow di scrittura vive in `.claude/workflows/`, perche' e' uno
  script che il runtime esegue, non codice del sito.)

Perche' esiste come pacchetto e non come l'ennesimo script: le guardie
numeriche che contano vivevano **dentro la suite di test**, quindi l'unico modo
di controllare un articolo era eseguire millecentosessanta test. E' una delle
ragioni per cui pubblicare 750 parole costava trentotto dollari.
"""
