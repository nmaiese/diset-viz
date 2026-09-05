FROM node:22-slim AS frontend-build

WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY content/ content/
# `scripts/` serve **a runtime**, non solo alla catena editoriale, e la ragione
# e' una sola riga: `app/indicator_texts.py` importa `scripts.indicator_store`,
# che possiede il formato degli articoli in `content/indicators/`. Lo store sta
# li' e non in `app/` perche' lo leggono anche gli script della catena, che sono
# stdlib puri e non possono importare `app/__init__.py`, il quale importa Flask.
#
# Senza questa riga l'immagine non parte affatto: ModuleNotFoundError su
# `scripts` al primo import, cioe' il sito giu' invece di una pagina sbagliata.
# `tests/test_app.py` lo sorveglia, perche' e' un guasto che si vede solo in
# produzione e la suite qui gira senza container.
COPY scripts/ scripts/
# `packs/` per la stessa ragione: `app/indicator_texts.py` importa
# `packs.context` per derivare le fonti visibili in pagina dagli identificatori
# di corpus citati dalle sezioni. Senza questa riga l'immagine non parte.
#
# L'import va in quel verso e non nell'altro: `packs/context.py` e' stdlib puro
# e non conosce `app`, mentre `packs/build.py`, che invece importa `app`, non
# entra mai nel giro di rendering. La direzione e' la ragione per cui non c'e'
# un ciclo.
COPY packs/ packs/
# `data/corpus/` e' dentro `data/`, che gia' si copia qui sotto: e' li' che
# stanno le affermazioni da cui le fonti si derivano.
# `data/` serve a runtime: `app/publisher.py` legge `data/source_state.json` per
# la data dell'ultimo aggiornamento delle fonti. Porta anche la storia committata
# della catena (diari e verifiche in `data/pipeline/`), che dal 5 settembre 2026
# nessuna rotta legge piu': resta come archivio. Sono ~2 MB di file versionati.
# L'effimero (cache, sqlite) e' gitignored, quindi non entra nel context di Cloud
# Build. `test_app.py` sorveglia che questa COPY resti, perche' e' un buco che si
# vede solo in produzione.
COPY data/ data/
COPY run.py .
COPY --from=frontend-build /build/app/static/dist app/static/dist

EXPOSE 8080

# timeout FINITO (60s): un worker bloccato viene terminato e riavviato invece di
# restare appeso per sempre (--timeout 0 disabilitava del tutto il watchdog).
# 1 worker: la cache in-process (CACHE_TYPE=simple) e la tabella da ~110k righe
# di get_rows() venivano duplicate per ogni worker, portando il container sopra
# il limite di memoria Cloud Run. Gli 8 thread coprono comunque la concorrenza.
#
# Lo stato mutabile (classifica, vivo della catena) vive su Supabase Postgres
# (DATABASE_URL), non piu' su SQLite: Litestream e' stato ritirato con la Fase 4.
CMD ["sh", "-c", "gunicorn run:app -b 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 60 --graceful-timeout 30"]
