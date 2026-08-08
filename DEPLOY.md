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
| `ADSENSE_CLIENT` | `ca-pub-6806451730012282` | Loader e meta tag Google AdSense (`/ads.txt` è versionato nell'app) |
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
> catena NON stanno più su SQLite + Litestream: sono su **Supabase Postgres**
> (vedi la sezione "Fase 4" più sotto). `SECRET_KEY` resta (firma i token quiz).
> Litestream, `LEADERBOARD_DB` in produzione e `LITESTREAM_REPLICA_URL` sono
> **ritirati**: il testo qui sotto vale solo come storia. Il file SQLite locale
> serve ancora solo in sviluppo (con `DATABASE_URL` vuota).

**Stato storico (pre-Fase 4, non più in produzione):**

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

### Cruscotto della catena `/_pipeline`

Il cruscotto guarda **le run del workflow** (`.claude/workflows/indicatore-lite.js`),
non piu' un indicatore che attraversa stadi: la catena editoriale autonoma e' stata
ritirata, e con lei le tabelle `pipeline_activity`, `pipeline_tokens` e
`pipeline_outcomes`, che dal 2026-08-08 non esistono piu' (migrazione
`0008_cruscotto_workflow`). Al loro posto due tabelle su Supabase Postgres:

- **`pipeline_run`**, una riga per workflow;
- **`pipeline_agente`**, una riga per agente dentro quel workflow.

**La regola del modello dati**, da non rompere: il **battito** (che arriva
mentre la run gira) e il **consuntivo** (che arriva a run finita) scrivono
colonne **disgiunte**. Vengono da due sorgenti diverse e arrivano in ordine non
garantito, quindi se scrivessero le stesse colonne la seconda cancellerebbe
quello che ha detto la prima, proprio sulla run che qualcuno sta guardando. Sta
in `app/pipeline_store.py`.

Chi scrive: **`lab/cruscotto.py`**, un processo che gira **di fianco** al
workflow, legge i trascritti che il runtime scrive comunque e POSTa a
`/_pipeline/beat`. Nessun agente della catena batte, e nessun prompt lo sa: i
turni sono il costo di quell'architettura, e il monitoraggio non ne aggiunge.

    bin/py -m lab.cruscotto --segui --per 5400 &   # PRIMA del workflow

Il consuntivo lo posta da se', quando vede comparire
`<sessione>/workflows/<runId>.json`, che il runtime scrive **solo a run finita**.

Chi legge: `monitor.divarioitalia.it/_pipeline/console`. Due percorsi dati, come
prima: il vivo arriva in push da **Supabase Realtime** letto diritto dal browser
(filtrato da RLS sulla mail Google, non da un token), e la storia gia' montata
da `/_pipeline/api/runs` e `/_pipeline/api/indicatori`, fetchate col Bearer del
login. Il percorso Realtime resta vuoto **senza errore** se RLS e Realtime non
sono stati applicati (`scripts/supabase_setup.sql`, punto 4 piu' sotto): non
basta che il lettore scriva.

**Un totale di costo e' un pavimento.** Un trascritto reale ha registrato
`output_tokens: 2` sulla richiesta che restituiva una bozza intera: il
trascritto e' incompleto, non lo e' la misura. Le righe portano
`costo_pavimento`, e la console lo dice invece di mostrare il totale come esatto.

| Variabile | Dove | A cosa serve |
|---|---|---|
| `PIPELINE_TOKEN` | env Cloud Run (o Secret Manager) | Se impostata, `/_pipeline` serve solo con `?token=` giusto, altrimenti 404. Vuota = aperta (solo locale). |
| `PIPELINE_INGEST_TOKEN` | **Secret Manager**, su Cloud Run **e** nell'ambiente agenti `divarioitalia` | Il segreto con cui `lab/cruscotto.py` autentica il POST (header `X-Pipeline-Key`). Vuoto = ingest spento (404). |
| `PIPELINE_INGEST_URL` | ambiente agenti `divarioitalia` | Dove postare: `https://divarioitalia.it`. Senza, il lettore legge e lo dice nel log invece di girare a vuoto. |

Nessuna credenziale GCP sugli agenti: scrivono solo via l'endpoint.

**Attenzione all'ordine, quando si cambia il cruscotto.** Il lettore puo' girare
sul ramo di lavoro, ma il POST arriva all'immagine Cloud Run costruita da
`master`: finche' il codice non e' fuso e ridistribuito, l'ingest nuovo non
esiste e la run gira lasciando il cruscotto vuoto. La sequenza e': merge su
`master`, redeploy, `alembic upgrade head`, `scripts/supabase_setup.sql`, poi la
run.

### Fase 4 — Backend mutabile su Supabase

Lo stato mutabile (classifica + vivo della catena) è su ORM SQLAlchemy: SQLite
solo quando `DATABASE_URL` è vuota (sviluppo locale), Postgres di Supabase
altrimenti. **Attivo in produzione**, Litestream **ritirato**: quanto segue
descrive come è stato acceso, non un passo ancora da fare.

**Cronaca dell'accensione** (già fatta, i passi restano come riferimento se
si dovesse rifare da un nuovo progetto Supabase):

1. **Secret Manager** (segreti): `DATABASE_URL` (pooler 6543, transaction mode,
   `sslmode=require`), `DIRECT_URL` (diretta 5432, per Alembic), `SUPABASE_JWT_SECRET`.
   Collega al servizio con `--update-secrets`, come `SECRET_KEY`.
2. **Env pubbliche** su Cloud Run: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
   (`--update-env-vars`). Opzionale `MONITOR_ADMIN_EMAIL` (default già giusto).
3. **Schema**: `DIRECT_URL=... alembic upgrade head` (crea `scores`,
   `pipeline_run`, `pipeline_agente`). Da fare una volta a mano, o come step
   `alembic upgrade head` in `cloudbuild.yaml` prima del deploy (richiede
   `availableSecrets` con `DIRECT_URL`: aggiungerlo solo quando il secret esiste,
   altrimenti il build fallisce). Lo step va **solo sul deploy, mai sul test**:
   se `DATABASE_URL`/`DIRECT_URL` finiscono nell'env dello step di test, la suite
   punterebbe a Postgres e il gate cadrebbe.
4. **RLS + Realtime**: esegui `scripts/supabase_setup.sql` nel SQL editor del
   progetto (attiva la RLS, la policy admin sulle tabelle pipeline, la publication
   Realtime sulle due tabelle del cruscotto). Senza, la console resta vuota
   **senza errore**. **Questo passo non lo puo' fare un agente**: va incollato a
   mano nel SQL editor del progetto, e va rifatto ogni volta che le tabelle del
   cruscotto cambiano nome.
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

Le migrazioni successive alla Fase 4 vogliono gli stessi passi 3
(`DIRECT_URL=... alembic upgrade head`) e 4 (`scripts/supabase_setup.sql`,
idempotente). L'ultima e' `0008_cruscotto_workflow` (2026-08-08): droppa le tre
tabelle della catena editoriale autonoma ritirata e crea `pipeline_run` e
`pipeline_agente`. **Il drop e' irreversibile per le righe che c'erano dentro**:
il `downgrade()` ricrea le tabelle vuote, e sono comunque righe di un modello
che il cruscotto nuovo non sa leggere. Finche' i due passi non sono rifatti in
produzione il cruscotto resta vuoto, e senza il passo 4 resta vuoto **senza dare
errore**.

| Variabile | Dove | A cosa serve |
|---|---|---|
| `DATABASE_URL` | Secret Manager | Postgres app (pooler 6543 transaction). Vuota = SQLite. |
| `DIRECT_URL` | Secret Manager | Postgres diretto (5432), solo Alembic. |
| `SUPABASE_JWT_SECRET` | Secret Manager | Verifica HS256 dei JWT (vuoto -> JWKS, caso attuale). |
| `SUPABASE_SECRET_KEY` | Secret Manager | Solo per la cancellazione account (admin API Supabase). |
| `SUPABASE_URL` | env Cloud Run | Progetto Supabase (browser: auth + Realtime). |
| `SUPABASE_ANON_KEY` | env Cloud Run | Chiave anon pubblica (protetta da RLS). |
| `MONITOR_ADMIN_EMAIL` | env Cloud Run | Sola mail ammessa alla console. |

Nota (Fase 5): la verifica JWT è **ES256 via JWKS** e richiede `cryptography`
(in `requirements.txt` come `PyJWT[crypto]`): senza, ogni richiesta autenticata
cade a 401 in produzione. Il sistema account (login, preferiti, stats,
achievements, confronti, GDPR) è documentato in [`docs/ACCOUNT.md`](docs/ACCOUNT.md);
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
