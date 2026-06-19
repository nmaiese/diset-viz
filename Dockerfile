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

CMD ["sh", "-c", "gunicorn run:app -b 0.0.0.0:${PORT:-8080} --workers 2 --threads 8 --timeout 0"]
