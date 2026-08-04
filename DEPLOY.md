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

> **SUPERATO dalla Fase 4 (2026-07-31).** La classifica e lo stato vivo della
> catena NON stanno piu' su SQLite + Litestream: sono su **Supabase Postgres**
> (vedi la sezione "Fase 4" piu' sotto). `SECRET_KEY` resta (firma i token quiz).
> Litestream, `LEADERBOARD_DB` in produzione e `LITESTREAM_REPLICA_URL` sono
> **ritirati**: il testo qui sotto vale solo come storia. Il file SQLite locale
> serve ancora solo in sviluppo (con `DATABASE_URL` vuota).

**Stato storico (pre-Fase 4, non piu' in produzione):**

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

**Attivo in produzione dal 2026-07-31** (Fase 4, sotto): lo stato vivo della
catena editoriale (ruoli in volo, PR aperte) sta su **Supabase Postgres**, non
su file locali ne' su SQLite/Litestream. Esistono **due percorsi dati
distinti**, non uno:

- `/_pipeline?token=...` (server-rendered) legge da Postgres via l'ORM
  (`app/db.py`/`app/pipeline_state.py`), scritto dal POST degli agenti a
  `/_pipeline/beat`, autenticato **solo** dall'header `X-Pipeline-Key`
  (`PIPELINE_INGEST_TOKEN`). Dal 2026-08-04 lo stesso POST porta anche lo
  **snapshot di lifecycle per indicatore** (`pipeline_outcomes`, azione
  `outcome`), scritto dal passo di merge a ogni PR fusa: il cruscotto lo
  sovrappone al dossier committato, cosi' `pubblicata`/`verificato`/prossimo
  passo sono aggiornati senza aspettare il redeploy dell'immagine (vedi
  `scripts/pipeline_merge.py::emit_outcomes`,
  `scripts/pipeline_monitor.py::_apply_outcomes`). Non tocca la pagina pubblica
  dell'articolo, che resta legata al deploy.
- `monitor.divarioitalia.it/_pipeline/console` **non passa da Flask**:
  `frontend/src/monitor/main.js` parla direttamente a Supabase dal browser
  (`pipeline_activity` via client JS + sottoscrizione Realtime), filtrato da
  **Row Level Security** sul login Google (`MONITOR_ADMIN_EMAIL`), non dal
  token. Questo percorso resta vuoto senza errore se RLS+Realtime non sono
  stati applicati (`scripts/supabase_setup.sql`, punto 4 piu' sotto) — non
  basta che gli agenti scrivano.

| Variabile | Dove | A cosa serve |
|---|---|---|
| `PIPELINE_TOKEN` | env Cloud Run (o Secret Manager) | Se impostata, `/_pipeline` serve solo con `?token=` giusto, altrimenti 404. Vuota = aperta (solo locale). |
| `PIPELINE_INGEST_TOKEN` | **Secret Manager**, su Cloud Run **e** nell'ambiente agenti `divarioitalia` | Il segreto con cui gli agenti autenticano il POST dei battiti (header `X-Pipeline-Key`). Vuoto = ingest spento (404). |

L'ambiente agenti vuole anche `PIPELINE_INGEST_URL=https://divarioitalia.it`, cosi'
`pipeline_monitor.py --beat-open/--beat-close` e `pipeline_inflight.py --post` sanno
dove postare. Nessuna credenziale GCP sugli agenti: scrivono solo via l'endpoint.
Nessun'altra variabile serve li': `gh api` (apertura PR) usa l'auth gia'
presente nel sandbox cloud dell'agente, non un token in env.

### Fase 4 — Backend mutabile su Supabase

Lo stato mutabile (classifica + vivo della catena) e' su ORM SQLAlchemy: SQLite
solo quando `DATABASE_URL` e' vuota (sviluppo locale), Postgres di Supabase
altrimenti. **Attivo in produzione**, Litestream **ritirato**: quanto segue
descrive come e' stato acceso, non un passo ancora da fare.

**Cronaca dell'accensione** (gia' fatta, i passi restano come riferimento se
si dovesse rifare da un nuovo progetto Supabase):

1. **Secret Manager** (segreti): `DATABASE_URL` (pooler 6543, transaction mode,
   `sslmode=require`), `DIRECT_URL` (diretta 5432, per Alembic), `SUPABASE_JWT_SECRET`.
   Collega al servizio con `--update-secrets`, come `SECRET_KEY`.
2. **Env pubbliche** su Cloud Run: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
   (`--update-env-vars`). Opzionale `MONITOR_ADMIN_EMAIL` (default gia' giusto).
3. **Schema**: `DIRECT_URL=... alembic upgrade head` (crea `scores`,
   `pipeline_activity`, `pipeline_tokens`). Da fare una volta a mano, o come step
   `alembic upgrade head` in `cloudbuild.yaml` prima del deploy (richiede
   `availableSecrets` con `DIRECT_URL`: aggiungerlo solo quando il secret esiste,
   altrimenti il build fallisce). Lo step va **solo sul deploy, mai sul test**:
   se `DATABASE_URL`/`DIRECT_URL` finiscono nell'env dello step di test, la suite
   punterebbe a Postgres e il gate cadrebbe.
4. **RLS + Realtime**: esegui `scripts/supabase_setup.sql` nel SQL editor del
   progetto (attiva la RLS, la policy admin sulle tabelle pipeline, la publication
   Realtime). Senza, la console resta vuota **senza errore**.
5. **Migrazione righe** (PRIMA di togliere Litestream):
   ```bash
   gsutil cp gs://nil-automata-diset-viz-leaderboard/leaderboard <lb>.sqlite3
   DATABASE_URL=<pooler> .venv/bin/python scripts/migrate_leaderboard_to_postgres.py --source <lb>.sqlite3
   ```
   Confronta i conteggi riga stampati.
6. **Keep-alive**: imposta `KEEPALIVE_TOKEN` (Secret Manager) sul servizio, poi un
   Cloud Scheduler che colpisce `GET /_keepalive` con l'header, ogni poche ore
   (tiene sveglio Supabase contro la pausa 7 giorni; senza header 404):
   ```bash
   gcloud scheduler jobs create http diset-viz-keepalive --location europe-west1 \
     --schedule "0 */6 * * *" --uri https://divarioitalia.it/_keepalive --http-method GET \
     --update-headers "X-Keepalive-Key=<KEEPALIVE_TOKEN>"
   ```
7. **Console**: `monitor.divarioitalia.it` (domain mapping Cloud Run + DNS) ->
   `/_pipeline/console`, login Google ristretto alla mail admin via RLS.
8. **Solo dopo** la verifica delle righe: rimuovi Litestream dal `Dockerfile`
   (stage, binario, `LEADERBOARD_DB`, `LITESTREAM_REPLICA_URL`, `litestream.yml`),
   e dismetti il bucket GCS.

Le migrazioni successive alla Fase 4 aggiungono tabelle con lo stesso passo 3
(`DIRECT_URL=... alembic upgrade head`) e vogliono lo stesso passo 4
(`scripts/supabase_setup.sql`, idempotente) rieseguito: `0007_pipeline_outcomes`
(2026-08-04) crea `pipeline_outcomes`, lo snapshot di lifecycle per indicatore
del cruscotto (vedi sopra). Finche' i due passi non sono rifatti in produzione,
l'overlay degrada in sicurezza a mappa vuota e la board mostra il solo dossier
committato, come prima di questa migrazione.

| Variabile | Dove | A cosa serve |
|---|---|---|
| `DATABASE_URL` | Secret Manager | Postgres app (pooler 6543 transaction). Vuota = SQLite. |
| `DIRECT_URL` | Secret Manager | Postgres diretto (5432), solo Alembic. |
| `SUPABASE_JWT_SECRET` | Secret Manager | Verifica HS256 dei JWT (vuoto -> JWKS, caso attuale). |
| `SUPABASE_SECRET_KEY` | Secret Manager | Solo per la cancellazione account (admin API Supabase). |
| `SUPABASE_URL` | env Cloud Run | Progetto Supabase (browser: auth + Realtime). |
| `SUPABASE_ANON_KEY` | env Cloud Run | Chiave anon pubblica (protetta da RLS). |
| `MONITOR_ADMIN_EMAIL` | env Cloud Run | Sola mail ammessa alla console. |

Nota (Fase 5): la verifica JWT e' **ES256 via JWKS** e richiede `cryptography`
(in `requirements.txt` come `PyJWT[crypto]`): senza, ogni richiesta autenticata
cade a 401 in produzione. Il sistema account (login, preferiti, stats,
achievements, confronti, GDPR) e' documentato in [`docs/ACCOUNT.md`](docs/ACCOUNT.md);
le tabelle sono le migrazioni Alembic `0003..0006` + la RLS di
`scripts/supabase_setup.sql`.

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
