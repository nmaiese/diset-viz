# Deploy di Divario Italia

App Flask + React stateless. Produzione consigliata su Google Cloud Run con
immagine Docker costruita da Cloud Build.

## Variabili d'ambiente

Sono variabili pubbliche, quindi non serve Secret Manager:

| Variabile | Esempio | A cosa serve |
|---|---|---|
| `SITE_URL` | `https://divarioitalia.it` | URL canonico per sitemap, canonical e blog |
| `GOOGLE_TAG_MANAGER_ID` | `GTM-PZ45BG7D` | Contenitore per Analytics, CMP e altri tag |
| `GA_MEASUREMENT_ID` | `G-THTPZZ02QH` | Measurement ID GA4 da usare nei tag GTM |
| `ADSENSE_CLIENT` | `ca-pub-6806451730012282` | Google AdSense e `/ads.txt` |
| `ADSENSE_SLOT_BANNER` | `1234567890` | Slot opzionale per banner futuri |
| `GOOGLE_SITE_VERIFICATION` | `...` | Verifica Search Console |
| `BING_SITE_VERIFICATION` | `...` | Verifica Bing Webmaster Tools |

Impostale sul servizio Cloud Run con `--update-env-vars`, mai con
`--set-env-vars` in automazione:

```bash
gcloud run services update diset-viz --region europe-west1 \
  --update-env-vars SITE_URL=https://divarioitalia.it,GOOGLE_TAG_MANAGER_ID=GTM-PZ45BG7D,GA_MEASUREMENT_ID=G-THTPZZ02QH,ADSENSE_CLIENT=ca-pub-6806451730012282
```

Il template imposta il default di Google Consent Mode prima di qualunque script
Google, poi carica Google Tag Manager e, se configurato, il loader AdSense nel
`<head>`. Non ci sono tag nativi GA4, dispatcher GA4 Custom HTML, banner CMP
locale o tag Funding Choices nel codice del sito.

La strategia completa, inclusi eventi e configurazione GTM/GA4, è in
[`docs/tracking_spec.md`](docs/tracking_spec.md).

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

Verifiche HTTP minime dopo il deploy:

```bash
curl -I https://divarioitalia.it/
curl -I https://divarioitalia.it/blog
curl -I https://divarioitalia.it/qualita-della-vita
curl -I https://divarioitalia.it/qualita-della-vita/classifica
curl -I https://divarioitalia.it/qualita-della-vita/province
curl -I https://divarioitalia.it/robots.txt
curl -I https://divarioitalia.it/sitemap.xml
curl -I https://divarioitalia.it/ads.txt
```

`/qualita-della-vita/province` esiste solo se i file BES provinciali sono
presenti. Se la pagina risponde 404 in un ambiente pulito, rigenera o includi gli
artefatti descritti in [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md).
