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
| `ADSENSE_CLIENT` | `ca-pub-6806451730012282` | Loader e meta tag Google AdSense (`/ads.txt` e' versionato nell'app) |
| `ADSENSE_SLOT_BANNER` | `1234567890` | Slot opzionale per banner futuri |
| `GOOGLE_SITE_VERIFICATION` | `...` | Verifica Search Console |
| `BING_SITE_VERIFICATION` | `...` | Verifica Bing Webmaster Tools |

Impostale sul servizio Cloud Run con `--update-env-vars`, mai con
`--set-env-vars` in automazione:

```bash
gcloud run services update diset-viz --region europe-west1 \
  --update-env-vars SITE_URL=https://divarioitalia.it,GOOGLE_TAG_MANAGER_ID=GTM-PZ45BG7D,GA_MEASUREMENT_ID=G-THTPZZ02QH,ADSENSE_CLIENT=ca-pub-6806451730012282
```

### Quiz "Quanto conosci l'Italia?" — SECRET_KEY e classifica

**Stato attuale (implementato su `nil-automata` / servizio `diset-viz`):**

- `SECRET_KEY` è un secret Secret Manager (`diset-viz-secret-key`), collegato al
  servizio con `--update-secrets` e leggibile dalla service account di runtime
  (`209597210585-compute@developer.gserviceaccount.com`, ruolo
  `roles/secretmanager.secretAccessor` sul secret). Mai un valore statico in
  chiaro nel repo o nei log.
- La classifica persiste con **Litestream**: il file SQLite vive nel filesystem
  locale effimero del container (`/data/leaderboard.sqlite3`, `LEADERBOARD_DB`
  impostata come default nel `Dockerfile`) e viene replicato in continuo sul
  bucket `gs://nil-automata-diset-viz-leaderboard/leaderboard`
  (`LITESTREAM_REPLICA_URL`, già impostata sul servizio). All'avvio del
  container Litestream ripristina l'ultima replica se il file locale non
  esiste (`-restore-if-db-not-exists` nel `CMD` del `Dockerfile`), poi fa da
  supervisore del processo gunicorn (`-exec`). Nessun impatto sulla
  scalabilità: non serve un volume condiviso né `--max-instances 1`, ogni
  container ha la propria copia locale del file.
- La service account di runtime ha `roles/storage.objectAdmin` sul bucket
  (necessario per scrivere le repliche).

| Variabile | Valore attuale | A cosa serve |
|---|---|---|
| `SECRET_KEY` | secret Manager `diset-viz-secret-key:latest` | Firma i token di sessione del quiz. |
| `LEADERBOARD_DB` | `/data/leaderboard.sqlite3` (default da `Dockerfile`) | Percorso locale del file SQLite nel container. |
| `LITESTREAM_REPLICA_URL` | `gs://nil-automata-diset-viz-leaderboard/leaderboard` | Destinazione della replica continua Litestream. |

### Cruscotto della catena `/_pipeline` — token e vivo

Il cruscotto interno mostra lo stato **vivo** della catena editoriale (ruoli in
volo e PR aperte). Il vivo non puo' passare da file locali: gli agenti girano su
macchine effimere separate dal server. Passa invece dallo **stesso** SQLite della
leaderboard (`LEADERBOARD_DB`, gia' replicato su GCS da Litestream): gli agenti
fanno un POST a `/_pipeline/beat`, il sito scrive quella tabella (`pipeline_activity`),
`/_pipeline` la legge. Due variabili nuove:

| Variabile | Dove | A cosa serve |
|---|---|---|
| `PIPELINE_TOKEN` | env Cloud Run (o Secret Manager) | Se impostata, `/_pipeline` serve solo con `?token=` giusto, altrimenti 404. Vuota = aperta (solo locale). |
| `PIPELINE_INGEST_TOKEN` | **Secret Manager**, su Cloud Run **e** nell'ambiente agenti `divarioitalia` | Il segreto con cui gli agenti autenticano il POST dei battiti (header `X-Pipeline-Key`). Vuoto = ingest spento (404). |

L'ambiente agenti vuole anche `PIPELINE_INGEST_URL=https://divarioitalia.it`, cosi'
`pipeline_monitor.py --beat-open/--beat-close` e `pipeline_inflight.py --post` sanno
dove postare. Nessuna credenziale GCP sugli agenti: scrivono solo via l'endpoint.

**Caveat.** La tabella del vivo condivide il file SQLite della leaderboard, quindi
eredita la stessa assunzione: Litestream e' single-writer, e il modello regge
perche' il traffico e' basso e `--min-instances=0` tiene di norma un solo
container attivo. Sotto scale multi-istanza il vivo puo' risultare per-istanza
finche' non arriva il prossimo restore; e' un limite accettato, non un bug nuovo.

Per ricreare il setup da zero (nuovo progetto o servizio):

```bash
# secret
python3 -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets create diset-viz-secret-key --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding diset-viz-secret-key \
  --member="serviceAccount:RUNTIME_SA" --role="roles/secretmanager.secretAccessor"

# bucket per la classifica
gsutil mb -l europe-west1 -b on gs://IL_TUO_BUCKET
gsutil iam ch serviceAccount:RUNTIME_SA:roles/storage.objectAdmin gs://IL_TUO_BUCKET

# collega tutto al servizio
gcloud run services update diset-viz --region europe-west1 \
  --update-secrets=SECRET_KEY=diset-viz-secret-key:latest \
  --update-env-vars=LITESTREAM_REPLICA_URL=gs://IL_TUO_BUCKET/leaderboard
```

`RUNTIME_SA` è la service account del servizio Cloud Run (visibile con
`gcloud run services describe diset-viz --region europe-west1 --format="value(spec.template.spec.serviceAccountName)"`,
di default la compute service account del progetto).

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
