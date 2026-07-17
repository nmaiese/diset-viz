FROM node:22-slim AS frontend-build

WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM litestream/litestream:0.5.14 AS litestream

FROM python:3.12-slim

WORKDIR /app

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
# Filesystem del container Cloud Run effimero: la classifica del quiz vive qui
# e Litestream la ripristina da GCS a ogni avvio (vedi CMD sotto e DEPLOY.md).
ENV LEADERBOARD_DB=/data/leaderboard.sqlite3

COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream
COPY litestream.yml /etc/litestream.yml

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY content/ content/
COPY run.py .
COPY --from=frontend-build /build/app/static/dist app/static/dist

RUN mkdir -p /data

EXPOSE 8080

# timeout FINITO (60s): un worker bloccato viene terminato e riavviato invece di
# restare appeso per sempre (--timeout 0 disabilitava del tutto il watchdog).
# 1 worker: la cache in-process (CACHE_TYPE=simple) e la tabella da ~110k righe
# di get_rows() venivano duplicate per ogni worker, portando il container sopra
# il limite di memoria Cloud Run. Gli 8 thread coprono comunque la concorrenza.
#
# Litestream fa da supervisore del processo gunicorn (-exec): all'avvio
# ripristina leaderboard.sqlite3 dall'ultima replica su GCS se il file locale
# non esiste (-restore-if-db-not-exists), poi lo replica in continuo mentre
# l'app gira. Nessun impatto sulla scalabilità: non serve un volume condiviso
# né limitare le istanze, ogni container ha la propria copia locale del file.
CMD ["sh", "-c", "litestream replicate -config /etc/litestream.yml -restore-if-db-not-exists -exec \"gunicorn run:app -b 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 60 --graceful-timeout 30\""]
