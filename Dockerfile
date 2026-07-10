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
COPY run.py .
COPY --from=frontend-build /build/app/static/dist app/static/dist

EXPOSE 8080

# timeout FINITO (60s): un worker bloccato viene terminato e riavviato invece di
# restare appeso per sempre (--timeout 0 disabilitava del tutto il watchdog).
# 1 worker: la cache in-process (CACHE_TYPE=simple) e la tabella da ~110k righe
# di get_rows() venivano duplicate per ogni worker, portando il container sopra
# il limite di memoria Cloud Run. Gli 8 thread coprono comunque la concorrenza.
CMD ["sh", "-c", "gunicorn run:app -b 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 60 --graceful-timeout 30"]
