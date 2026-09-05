# CLAUDE.md

Guida per Claude Code (e per gli altri agenti) che lavorano in questo repo.

Questo file è un **router**. Porta ciò che è vero ovunque e abbastanza corto da
valere la ripetizione; tutto ciò che ha profondità sta nel documento che
possiede l'argomento, e le regole con uno scope in `.claude/rules/` si caricano
da sole dove si applicano. Una regola copiata in due posti va fuori sincrono
senza che nessuno se ne accorga, e questo progetto lo ha già pagato.

**Se un argomento qui sotto ha un documento, leggi il documento. Non agire sul riassunto.**

## Lo stato non è qui

Questo repo dice **come funziona il sito**. A che punto siamo, che cosa stiamo
facendo, che cosa viene dopo e perché lo stiamo facendo stanno in un posto solo,
`QUADRO.md` del repo `nmaiese/redazione-ai`, che l'hook di avvio ti mette già in
contesto quando è agganciato.

Quindi: **nessun documento di questo repo porta caselle di spunta, avanzamenti,
"prossimo passo" o date di piano.** Se ti viene da scrivere lo stato in `docs/`,
va nel Quadro. Il 5 settembre nove posti dicevano che cosa c'era da fare, e si
contraddicevano.

Le **PR** servono per il codice del sito (`app/`, `frontend/`, `scripts/`,
`config/`, `tests/`) e per gli articoli (`content/`): lì il merge è il gate
umano, e per divarioitalia il merge è la pubblicazione. La **documentazione non
passa da PR**: `docs/`, `CLAUDE.md`, `README.md` e `.claude/` si scrivono
direttamente su `master`.

## La mappa

| se stai lavorando su... | leggi |
| --- | --- |
| account utente, login Google, preferiti, statistiche/achievements, confronti salvati, GDPR | [`docs/ACCOUNT.md`](docs/ACCOUNT.md) |
| una pagina indicatore, la sua prosa, le sue guardie | [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md) |
| che cosa si può citare in un articolo | [`docs/SECONDARY_SOURCES.md`](docs/SECONDARY_SOURCES.md) |
| **scrivere un articolo indicatore**: brief, verifica, pubblicazione | il repo `redazione-ai` (`REDAZIONE.md` e `siti/divarioitalia.md`) |
| aggiungere indicatori, temi o un dataset regionale | [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) |
| **famiglie di indicatori**: stessa misura, dimensioni diverse (genere, età, regione/provincia) | [`docs/FAMIGLIE_INDICATORI.md`](docs/FAMIGLIE_INDICATORI.md) |
| **a che punto è la prosa dell'atlante**: lo stato dei 634 indicatori | `app/editorial_state.py` (il criterio, uno solo), `app/indicator_universe.py` (la passata, una sola) |
| dati provinciali | [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md) |
| freschezza dei dati e monitoraggio delle fonti | [`docs/DATA_FRESHNESS.md`](docs/DATA_FRESHNESS.md), [`docs/SOURCE_MONITORING.md`](docs/SOURCE_MONITORING.md) |
| fonti verticali esterne | [`docs/EXTERNAL_SOURCES.md`](docs/EXTERNAL_SOURCES.md) |
| la voce editoriale, blog e pagine indicatore | [`content/STYLE.md`](content/STYLE.md) |
| priorità e lacune sulle domande che un motore o un assistente può porre | [`docs/LLM_QUERY_MAP.md`](docs/LLM_QUERY_MAP.md) |
| tracciamento, consenso, versione GTM | [`docs/tracking_spec.md`](docs/tracking_spec.md) |
| deploy su Cloud Run | [`DEPLOY.md`](DEPLOY.md) |

## Che cos'è

**Divario Italia** (divarioitalia.it) è un atlante Flask + React degli
indicatori territoriali Istat, più un blog server-rendered per la SEO e una
sezione qualità della vita per regioni e province. L'atlante sta a `/`
(sorgente in `frontend/`, build in `app/static/dist/`); ogni indicatore di ogni
famiglia a `/indicatore/<slug>/<acronimo>-<id>`, servito da **un template su un
view model**; il blog a `/blog`; l'hub editoriale a `/divari-regionali`; il
confronto a `/confronto`; la ricerca a `/ricerca`; la dashboard D3 originale a
`/legacy` (non va rotta); l'API JSON sotto `/api/`. Le verità rotta per rotta
(canonico, noindex e perché, che cosa si ricalcola al render) stanno in
`.claude/rules/app.md`.

**I nomi delle fonti hanno una sola fonte di verità, `app/sources.py`**, detto
qui perché romperla è invisibile: le etichette pubbliche sono nomi in chiaro
istituzione-prima, mai un acronimo interno nudo, e nessuna etichetta di famiglia
o URL di indicatore va hardcodata altrove. Il codice che lo faceva ha pubblicato
una serie Istat sotto il nome di Eurostat.

Strato dati: `app/data.py` (legge `app/static/data/Assoluti_Regione.csv`).
Strato blog: `app/blog.py` (legge `content/posts/*.md`).

## Chi scrive gli articoli

Non questo repo. La redazione vive in `nmaiese/redazione-ai`: `motore/` calcola
il dossier e il brief, tre agent scrivono e verificano, `motore pubblica` scrive
in `content/indicators/` di qui e `motore pr` apre la PR. Il contratto del pezzo
è `REDAZIONE.md` di quel repo, le regole del sito `siti/divarioitalia.md`.

Qui restano solo gli agganci: `content/indicators/` dove i pezzi atterrano,
`content/STYLE.md` per la voce, e le regole con scope in `.claude/rules/`
(`app.md`, `data.md`, `editorial.md`, `frontend.md`, e le tre `motore-*.md`).

## Comandi

**L'interprete Python di questo progetto è `bin/py`, sempre.** Non `python3`
(qui è una funzione di shell che senza `$VIRTUAL_ENV` cade su un interprete senza
dipendenze), non `.venv/bin/python` (in molti worktree non esiste). `bin/py`
risolve in un posto solo (`$DIVARIO_PYTHON`, poi `.venv/bin/python` del repo, poi
`$VIRTUAL_ENV`) e fallisce dicendo perché. Senza venv: `export DIVARIO_PYTHON=...`.

```bash
bin/py scripts/tool_failures.py                  # i guasti che si ripetono

# build della SPA (obbligatoria dopo ogni modifica in frontend/)
cd frontend && npm run build && cd ..

# in locale (dalla radice del repo)
.venv/bin/gunicorn run:app -b 127.0.0.1:5050

# test, audit, spazi
bin/py -m unittest discover -s tests -v          # tutta la suite, prima di commit/push
bin/py -m unittest discover -s tests/unit -v      # solo i veloci (<1s), durante lo sviluppo
bin/py -m unittest discover -s tests/integration -v  # la parte pesante: Flask/HTTP e catena e2e
cd frontend && npm audit --audit-level=low
git diff --check
```

`tests/` è pacchetto Python (ha `__init__.py`) apposta: così `tests/conftest.py`
si aggancia sotto `unittest`. In `tests/integration/` va ciò che ha bisogno di un
giro reale (client Flask, catena e2e, tutti gli articoli committati); il resto in
`tests/unit/`. Un file che mescola le due cose va spaccato, non spostato.

Dopo aver toccato `frontend/src/*`, rebuild prima di provare l'app servita.
Dopo aver cambiato i dati, **riavvia gunicorn**: i loader cachano per la vita
del processo (`lru_cache`, non un TTL). Il deploy è Cloud Run via Cloud Build
(`DEPLOY.md`): la build fa `pip install`, `npm ci`, `npm run build`.

## Scrittura, leggi [`content/STYLE.md`](content/STYLE.md)

Una voce sola per blog e pagine indicatore, posseduta da `content/STYLE.md`.
Gli assoluti: niente em-dash `—`, niente en-dash `–`, niente `;`, niente `…`;
solo numeri veri e verificati, mai una fonte inventata; link canonici agli
indicatori (`/indicatore/<slug>/ter-105`, mai `/?indicator=`). Le guardie che
fermano un pezzo sono le tre di `motore verifica` nel repo della redazione:
una cifra che non sta nel dossier, un link interno che non esiste, una fonte che
non risponde. Non c'è una rubrica a punti e non c'è un lint della prosa.

## Dati, leggi [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md)

Temi, punteggi di tema, profili regionali e macro-aree sono tutti **derivati**
dai dati e ricalcolati a runtime; il cablaggio (versi in `CURATED_DIRECTION`,
mappa dei temi in `config/theme_categories.csv`, separazione provinciale) sta in
`.claude/rules/data.md`. Il guasto silenzioso da sapere ovunque: un tema non
mappato tiene il suo indicatore nel catalogo e lo toglie da ogni totale di
macro-area, senza che niente fallisca.

## Vincoli

- Non rompere `/legacy` né lo schema dati (`tests/integration/test_app.py` guarda entrambi).
- Tenere intatta la SEO tecnica (la lista è in `.claude/rules/app.md`).
- Tenere l'identità cartografica: navy `#15233b`, carta `#fbfaf7`, un solo
  accento `#e4572e`, font Archivo / Inter / Space Mono.
- Non committare segreti (`.gitignore` esclude già `client_secret_*.json`).
- Messaggi di commit: nessun trailer `Co-Authored-By`.
