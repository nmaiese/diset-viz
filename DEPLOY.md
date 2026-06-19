# Deploy di Divario Italia

App Flask + React stateless. Produzione consigliata su Google Cloud Run con
immagine Docker costruita da Cloud Build.

## Variabili d'ambiente

Sono variabili pubbliche, quindi non serve Secret Manager:

| Variabile | Esempio | A cosa serve |
|---|---|---|
| `SITE_URL` | `https://divarioitalia.it` | URL canonico per sitemap, canonical e blog |
| `GA_MEASUREMENT_ID` | `G-THTPZZ02QH` | Google Analytics 4 |
| `ADSENSE_CLIENT` | `ca-pub-XXXXXXXXXXXXXXXX` | Google AdSense e `/ads.txt` |
| `ADSENSE_SLOT_BANNER` | `1234567890` | Slot opzionale per banner futuri |
| `FORCE_FUNDING_CHOICES_CMP` | `true` | Forza Funding Choices a procedere con il messaggio quando Google lo rende eleggibile |
| `ENABLE_CONSENT_BANNER` | `true` | Banner consenso cookie |
| `GOOGLE_SITE_VERIFICATION` | `...` | Verifica Search Console |
| `BING_SITE_VERIFICATION` | `...` | Verifica Bing Webmaster Tools |

Impostale sul servizio Cloud Run con `--update-env-vars`, mai con
`--set-env-vars` in automazione:

```bash
gcloud run services update diset-viz --region europe-west1 \
  --update-env-vars SITE_URL=https://divarioitalia.it,GA_MEASUREMENT_ID=G-THTPZZ02QH,ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX,FORCE_FUNDING_CHOICES_CMP=true,ENABLE_CONSENT_BANNER=true
```

## Primo deploy

```bash
gcloud auth login
gcloud config set project IL_TUO_PROGETTO
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud run deploy diset-viz \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --memory 512Mi
```

## Deploy automatico

Configura un trigger Cloud Build sul repository GitHub, branch `^master$`, build
config `cloudbuild.yaml`. Il file:

1. costruisce l'immagine dal `Dockerfile`, incluso il frontend React,
2. la pubblica su Artifact Registry in `europe-west1`,
3. aggiorna Cloud Run senza toccare le env var del servizio.

## Verifica

```bash
.venv/bin/python -m unittest discover -s tests -v
cd frontend && npm run build
gcloud run services describe diset-viz --region europe-west1 \
  --format='value(status.url,status.latestReadyRevisionName)'
```
