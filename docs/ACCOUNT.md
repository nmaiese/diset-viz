# Account utente (Supabase) — come funziona davvero

Questo documento possiede il sistema account, rilasciato con la **Fase 5** della
rifondazione. Sostituisce un piano storico (magic-link piu' un profilo giocatore
su SQLite) che stava in `docs/archive/AUTH_SUPABASE.md`, cancellato il 5 settembre
2026 con tutta `docs/archive/`: quello che gira è qui sotto.

## In una riga

Login **Google** (Supabase Auth), backend mutabile su **Supabase Postgres**, e
un insieme di funzioni per l'utente registrato: **preferiti** indicatore,
**statistiche e traguardi** dei minigiochi legati all'account, **confronti
salvati**, una **pagina account** con export e cancellazione (GDPR). Il gioco e
il sito restano **usabili senza registrazione**: l'account è un extra.

## Le due autorità, e l'invariante che le tiene

- **Il browser** parla con Supabase per l'**identità** (login Google) e per la
  **console Realtime** della catena (admin). Il client è `@supabase/supabase-js`,
  caricato **on-demand** (una pagina anonima non lo scarica).
- **Il backend Flask** è l'**unica autorità sui dati**. Verifica il Bearer JWT
  di Supabase (`app/auth.py`, ES256 via JWKS) e parla lui con Postgres via
  SQLAlchemy (`app/db.py`).

**Invariante di sicurezza (non negoziabile).** L'`auth_id` viene **sempre** dal
JWT verificato (`auth.current_user`), **mai** dal body della richiesta. Il ruolo
Postgres dell'app è `postgres`, che ha **BYPASSRLS**: quindi la RLS **non è il
confine** per i dati account, è difesa in profondità. Il confine vero è il
`WHERE auth_id = ?` in ogni modulo dati (`favorites.py`, `player_stats.py`,
`achievements.py`, `comparisons.py`, `account.py`). Un endpoint che accettasse
`auth_id` dal client sarebbe una fuga completa. Le policy RLS ci sono comunque
(`scripts/supabase_setup.sql`), per il caso in cui un domani il browser leggesse
direttamente.

## Dove vive la verifica JWT (una trappola già pagata)

`app/auth.py` verifica un JWT **ES256** (chiave asimmetrica del progetto, via
JWKS). PyJWT **da solo non fa** ES256/RS256: serve `cryptography`, ed è in
`requirements.txt` come `PyJWT[crypto]`. Senza, la verifica fallisce e **ogni
richiesta autenticata cade a 401** — in produzione, mentre in locale passa
perché `cryptography` è già nel venv. È successo: se l'auth server "non
attacca" in prod ma i test verdi, guarda qui prima.

## Schema (tutto chiave `auth_id`, RLS own-rows)

Migrazioni Alembic `migrations/versions/0003..0006`, modelli in `app/models.py`:

| Tabella | Cosa | Modulo |
| --- | --- | --- |
| `profiles` | account: email, nickname, timestamps. Upsert al login. | `app/accounts.py` |
| `favorites` | indicatori preferiti (PK auth_id+indicator_id). | `app/favorites.py` |
| `player_stats` | aggregati per (utente, modalità: compare/order/daily). | `app/player_stats.py` |
| `daily_results` | storico Regione del giorno per data (streak). | `app/player_stats.py` |
| `achievements` | sblocchi (le definizioni sono in codice). | `app/achievements.py` |
| `saved_comparisons` | confronti salvati (config JSON, **niente public_slug**). | `app/comparisons.py` |
| `scores` | classifica: `user_id` opzionale (Fase 4). | `app/leaderboard.py` |

## Endpoint (tutti authed, 401 se anonimo salvo dove detto)

- `GET /api/auth/me` — identità dal JWT + upsert profilo (best-effort). Anonimo
  torna `{"user": null}`.
- `GET/POST /api/favorites`, `DELETE /api/favorites/<id>` — preferiti.
- `GET /api/player/me` — stats + vetrina traguardi. `POST /api/player/merge` —
  fonde i progressi locali nell'account (una volta). `PATCH /api/player/nickname`.
- `GET/POST /api/comparisons`, `DELETE /api/comparisons/<id>` — confronti salvati.
- `GET /api/account/export` (portabilità), `DELETE /api/account` (oblio: righe +
  utente Supabase via admin API con `SUPABASE_SECRET_KEY`).
- Hook su `/api/game/compare|order/answer` e `/api/game/guess`: se loggato,
  registrano stats e valutano achievement, sblocchi **inline** nella risposta.

## Frontend

- **`frontend/src/shared/supabase.js`** — client (import dinamico), `getUser`,
  `getAccessToken`, `signInWithGoogle`, `syncProfile`, `mergeLocalStatsOnce`.
- **`frontend/src/site/auth.js`** — entry vanilla nel masthead di **ogni pagina
  SSR** (`blog_base.html`): controllo login/account, stella preferiti sulle pagine
  indicatore, pagina `/account`. Ottimizzato: niente supabase-js per gli anonimi.
- **`frontend/src/shared/AuthControl.jsx`** — controllo login React per l'atlante.
- **Atlante** (`main.jsx`): filtro "Solo preferiti" (`?fav=1`), confronti salvati
  in `CompareView`.
- **Giochi** (`game/`): toast traguardi (`notifyAchievements`), scelta salva a 3
  opzioni, vetrina traguardi nell'hub, merge al login.

Gli achievements sono **login-only**: le stats anonime stanno in localStorage e
il server non le vede, quindi non c'è un secondo percorso di valutazione non
fidato.

## Cache dei bundle (una trappola)

Gli entry (`index.js`, `game.js`, `site.js`) hanno **nome fisso** ma importano
chunk con **hash** che cambiano a ogni build. Con la cache del browser, un entry
vecchio importa chunk spariti e la SPA resta bianca (fallback SEO). Il fix è
`asset_url()` (`app/__init__.py`): un `?v=<hash-contenuto>` sugli entry, URL
unico per rilascio. Usalo (non `url_for('static')` diretto) per ogni asset a nome
fisso che cambia.

## Config / deploy

Segreti (Secret Manager) su Cloud Run: `SUPABASE_JWT_SECRET` (vuoto -> JWKS, che
è il caso attuale), `SUPABASE_SECRET_KEY` (solo per la cancellazione account).
Env pubbliche: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `MONITOR_ADMIN_EMAIL`.
Le tabelle account si creano con `alembic upgrade head`; la RLS con
`scripts/supabase_setup.sql`. Dettagli operativi in [`DEPLOY.md`](../DEPLOY.md),
sezione "Fase 4".

## Cosa resta fuori (per scelta)

- **Email/magic-link**: rimandati finché non c'è un SMTP custom. Solo Google.
- Il confronto salvato ripristina indicatore + regioni, l'anno torna all'ultimo.
