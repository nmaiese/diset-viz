# Account con Supabase (Postgres + auth)

> **SUPERATO (Fase 5, 2026-07-31).** Il sistema account è stato implementato e la
> sua descrizione viva sta in [`ACCOUNT.md`](ACCOUNT.md). Login **Google** (non
> magic-link), preferiti, statistiche+achievements sull'account, confronti
> salvati, pagina account con export/cancellazione GDPR. Questo file resta come
> storia del piano iniziale. **Non agire su questo doc: leggi `ACCOUNT.md`.**

> **STATO (Fase 4, 2026-07-31).** Questo documento è in parte **superato**
> dall'implementazione effettiva. Cosa vale oggi, nel codice su `master`:
> - **Auth: Google OAuth**, non magic link (email rimandata finché non c'è un
>   SMTP custom: l'email di default Supabase è rate-limited). La verifica del
>   JWT lato server (`app/auth.py`) è la stessa comunque.
> - **Stato mutabile su Postgres via SQLAlchemy**: `app/db.py` (engine a due
>   dialetti, SQLite in test/CI, Postgres in produzione quando `DATABASE_URL` è
>   impostata), `app/models.py`, `migrations/` (Alembic). Migrati **sia** la
>   classifica (`app/leaderboard.py`, con `user_id` opzionale) **sia** lo stato
>   vivo della catena (`app/pipeline_state.py`) -- quest'ultimo NON è in questo
>   doc originale.
> - **Console di monitoraggio in tempo reale** (`/_pipeline/console`, sottodominio
>   `monitor.divarioitalia.it`) via **Supabase Realtime**, con **RLS** che
>   restringe le tabelle pipeline alla mail admin (`scripts/supabase_setup.sql`).
>   Sostituisce il `?token=`. Anche questo è fuori dal doc originale.
> - **Keep-alive** (`/_keepalive` + Cloud Scheduler) contro la pausa 7 giorni.
> - **Litestream** si ritira solo **dopo** aver migrato le righe reali
>   (`scripts/migrate_leaderboard_to_postgres.py`) e verificato i conteggi.
>
> **Sezione game-account rimandata.** Achievements, `player_stats`,
> `daily_results`, `saved_comparisons`, e il flusso `claim` descritti sotto NON
> sono su `master`: vivono sul branch `claude/game-user-db-achievements-5rlmrx`,
> non mergiato. Restano un piano futuro, non lo scope della Fase 4 (che tiene lo
> `user_id` opzionale sulla classifica e nient'altro sugli account di gioco). Il
> piano operativo vivo è
> `/home/nilo/.claude/plans/lavori-sul-progetto-divario-playful-peacock.md`.

## Context

Si evolve il gioco di Divario Italia da un profilo giocatore leggero (SQLite +
recovery code, già rilasciato sul branch `claude/game-user-db-achievements-5rlmrx`)
a **account veri** su **Supabase**: Postgres gestito + autenticazione **magic
link via email**. Si parte con Supabase per stare a costo quasi zero, e poiché si
usa Postgres standard con SQLAlchemy + Alembic si resta **portabili** (domani si
può migrare a Cloud SQL o self-host senza riscrivere il codice). In una fase
successiva l'utente potrà **salvare i propri dati e costruire le proprie
comparazioni** dell'atlante.

### Decisione di architettura (con alternativa)

**Si usa Supabase Auth (GoTrue) per il magic link**, non un'implementazione
propria: Supabase gestisce invio email, token, verifica e sessioni JWT. Il
**backend Flask resta l'unica autorità sui dati di gioco** (l'anti-cheat della
classifica non cambia): verifica il JWT di Supabase e parla lui con Postgres via
SQLAlchemy. Il browser NON accede a Postgres direttamente (niente RLS come
confine primario), così la logica server-authoritative resta intatta.
*Alternativa (scartata salvo tuo veto): magic link fatto in casa + provider
email + tabelle `magic_links`/`sessions` nostre. Più codice e più superficie, per
un risultato equivalente.*

Costo su gcloud: **nessun nuovo servizio GCP**. Cloud Run resta com'è; Supabase è
esterno. Si aggiungono solo dei secret e si **dismette Litestream** (lo sostituisce
Postgres).

Questo documento è il piano di implementazione: nessuna modifica al codice finché
non è approvato.

---

## Come si incastrano i pezzi

- **Identità**: il frontend usa `@supabase/supabase-js` → `signInWithOtp({email})`
  manda il magic link; al ritorno supabase-js tiene la sessione (access +
  refresh JWT).
- **API**: ogni chiamata al backend porta `Authorization: Bearer <access_token>`.
  Flask verifica il JWT (HS256 con `SUPABASE_JWT_SECRET`, oppure JWKS) ed estrae
  `sub` (UUID utente) ed email.
- **Dati**: Flask usa SQLAlchemy verso Postgres Supabase per profilo,
  statistiche, achievement, classifica e (fase futura) comparazioni. Le tabelle
  nostre sono nello schema `public`, con chiave l'UUID di `auth.users`.
- **Anti-cheat invariato**: punteggi/streak restano validati server-side dai
  token quiz firmati esistenti (`app/quiz_tokens.py`); l'account aggiunge solo
  l'identità durevole a cui attribuirli.

---

## Connessioni Postgres (specifico di Supabase / Cloud Run scale-to-zero)

Servono **due** stringhe di connessione:
- `DATABASE_URL` → **pooler Supavisor in transaction mode** (porta 6543), usato
  dall'app. Con psycopg disabilitare i prepared statements (`prepare_threshold=None`)
  o usare `NullPool`, perché il transaction pooler non li supporta. Pool piccolo
  per istanza (`pool_size` 2-3, `pool_pre_ping=True`).
- `DIRECT_URL` → connessione **diretta** (porta 5432), usata **solo da Alembic**
  per le migrazioni.
- Entrambe in TLS (`sslmode=require`) e in Secret Manager.

---

## Modello dati (schema `public`, gestito da Alembic)

Supabase Auth possiede `auth.users` (email, magic link, sessioni): **non lo
gestiamo noi**. Le nostre tabelle:

```
profiles
  auth_id      UUID PK            -- = auth.users.id (dal JWT)
  email        CITEXT             -- denormalizzata dal JWT, per comodità
  nickname     TEXT               -- pubblico, moderato (app/moderation.py)
  created_at, last_seen_at TIMESTAMPTZ

player_stats     -- come oggi, re-key su auth_id (era player_id)
achievements     -- come oggi, re-key su auth_id
daily_results    -- come oggi, re-key su auth_id
scores           -- classifica: FK auth_id nullable (anonimi restano), nickname denormalizzato

saved_comparisons             -- FASE FUTURA, schema pronto da ora
  id           BIGSERIAL PK
  auth_id      UUID FK profiles(auth_id) ON DELETE CASCADE
  title        TEXT NOT NULL
  config       JSONB NOT NULL    -- indicatori, regioni, anni, tipo grafico
  public_slug  TEXT UNIQUE       -- opzionale, condivisione
  created_at, updated_at TIMESTAMPTZ
```

I moduli `app/players.py`, `app/achievements.py`, `app/leaderboard.py` vengono
riscritti sopra l'ORM mantenendo le firme pubbliche dove possibile. Si riusa
`app/moderation.py`.

### Claim dei profili leggeri esistenti

I profili attuali (recovery code) diventano "profili di dispositivo non
rivendicati". Endpoint `POST /api/player/claim`: utente loggato (JWT) che invia
il vecchio player token → Flask trasferisce `player_stats`/`achievements`/
`daily_results` dal `player_id` all'`auth_id` e collega le righe classifica. Chi
ha già giocato non riparte da zero.

---

## Achievement (sistema esistente, come si integra)

Il sistema achievement è **già implementato** (Fase 0) e va **portato**, non
riprogettato:

- **Catalogo nel codice** (`app/achievements.py`): voci dichiarative
  (`id`, icona, titolo, descrizione, criterio come funzione pura sugli aggregati
  di `player_stats`). Aggiungere o ritoccare un traguardo è una modifica di
  codice, **senza migrazioni DB**. Set iniziale: prima risposta giusta, serie 10
  e 25 in "Chi è maggiore?", primo ordinamento perfetto, 10 perfetti di fila,
  prima Regione del giorno, 7 giornaliere di fila, tuttologo (tutti e tre i
  giochi), veterano (50 round).
- **Sblocchi in DB** (tabella `achievements`): solo gli sblocchi, non le
  definizioni. Idempotente (un traguardo già sbloccato non si ripropone).
- **Valutazione server-side** dove il risultato è già verificato: risposte
  quiz (`/api/game/compare/answer`, `/api/game/order/answer`), guess giornaliero
  (`/api/game/guess`) e submit classifica. I traguardi appena sbloccati tornano
  **inline** nella risposta e il frontend mostra un **toast** (`notifyAchievements`
  in `frontend/src/game/shared.jsx`), oltre alla **vetrina** nel profilo
  (`frontend/src/game/profile.jsx`) con stato sbloccato/da conquistare.

Cosa cambia con Supabase:
- La tabella `achievements` viene **re-keyed** da `player_id` a `auth_id`; il
  catalogo e la logica di `app/achievements.py` restano, riscritti sopra l'ORM.
- La valutazione continua negli stessi hook, attribuita all'`auth_id` quando c'è
  un JWT valido.
- Il **claim** del profilo di dispositivo trasferisce gli sblocchi già ottenuti
  sull'account, così non si perdono i traguardi conquistati da anonimi.
- **Export/cancellazione GDPR** includono gli achievement dell'utente.
- Estensione futura naturale: traguardi legati alle **comparazioni salvate**
  (es. prima comparazione creata, comparazione condivisa).

## Passi di implementazione (ordinati, ognuno rilasciabile)

### Fase A — Fondamenta dati (Supabase + ORM + migrazioni)
1. Creare il progetto Supabase, prendere `DATABASE_URL` (pooled), `DIRECT_URL`,
   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`.
2. `requirements.txt`: aggiungere `SQLAlchemy>=2`, `alembic`, `psycopg[binary]`,
   `PyJWT`. Rimuovere il ruolo di Litestream per il gioco.
3. `app/db.py`: sostituire sqlite3 grezzo con `Engine`/`Session` SQLAlchemy
   (letto da `DATABASE_URL`, pool piccolo, no prepared statements). Sessione
   per-request + teardown in `app/__init__.py`.
4. `app/models.py`: modelli ORM (profiles, player_stats, achievements,
   daily_results, scores, saved_comparisons).
5. `migrations/` Alembic (usa `DIRECT_URL`); prima migrazione crea lo schema.
6. Riscrivere `app/players.py`/`app/achievements.py`/`app/leaderboard.py` sopra
   l'ORM (stesse firme). Riadattare `tests/test_players.py` (da scrivere) e
   `tests/integration/test_leaderboard.py` a Postgres di test.

### Fase B — Autenticazione magic link (Supabase Auth)
7. Backend: `app/auth.py` che verifica il Bearer JWT (`SUPABASE_JWT_SECRET`),
   estrae `auth_id`/email, fa upsert del `profiles` al primo accesso, espone
   l'utente (es. `flask.g.user`). Helper `require_user()` per gli endpoint.
8. Endpoint: `GET /api/auth/me`, `PATCH /api/player/nickname` (moderato),
   `POST /api/player/claim`. Gli hook stats/achievement negli endpoint di gioco
   passano dall'`auth_id` quando c'è un JWT valido (in aggiunta, per la
   transizione, al player token esistente).
9. Frontend: aggiungere `@supabase/supabase-js`; esporre `SUPABASE_URL`/anon key
   ai template via il context processor `inject_site_config` (`app/__init__.py`)
   così non serve rebuild per cambiarli. `shared.jsx`: client Supabase, login via
   `signInWithOtp`, allegare `Authorization: Bearer` a tutte le fetch, gestire il
   ritorno dal magic link. `profile.jsx`: UI login/logout e stato account.
10. **CSP**: aggiungere `https://<project>.supabase.co` a `connect-src` (e
    `script-src` se serve) in `_build_content_security_policy` (`app/__init__.py`).
11. Supabase Auth: configurare **SMTP custom** (Resend/Postmark/SES) per superare
    i limiti dell'email di default, il redirect URL e il template email.

### Fase C — GDPR e comparazioni salvate
12. `GET /api/account/export` e `DELETE /api/account` (diritto all'oblio,
    `ON DELETE CASCADE` già pronto; cancellare anche l'utente lato Supabase Auth
    via admin API). Aggiornare privacy e cookie policy (email + sessione).
13. Comparazioni: `app/comparisons.py` + `/api/comparisons` (CRUD per utente),
    pulsante "Salva comparazione" nell'atlante (`frontend/src/main.jsx`) e pagina
    "Le mie comparazioni". Condivisione opzionale via `public_slug`.

---

## Sicurezza

- JWT verificato lato server a ogni richiesta protetta; niente password da noi.
- Magic link, invio email e refresh gestiti da Supabase Auth (custom SMTP in
  produzione).
- Access token gestito da supabase-js sul client; CSP già restrittiva, da
  estendere solo al dominio Supabase. (Se in futuro si vuole il massimo contro
  XSS, si può passare a sessione via cookie HttpOnly con gli helper SSR di
  Supabase, ma non è necessario ora.)
- Segreti (`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_JWT_SECRET`) solo in Secret
  Manager; `SUPABASE_URL`/anon key sono pubblici. TLS verso Postgres.

---

## Config e deploy (gcloud invariato come servizi)

- Env/segreti nuovi su Cloud Run: `DATABASE_URL`, `DIRECT_URL`,
  `SUPABASE_JWT_SECRET` (secret); `SUPABASE_URL`, `SUPABASE_ANON_KEY` (env
  pubbliche). Aggiornare `app/config.py`, `.env.example`, `DEPLOY.md`.
- `cloudbuild.yaml`: step `alembic upgrade head` (con `DIRECT_URL`) prima del
  deploy.
- `Dockerfile`: rimuovere Litestream e `LEADERBOARD_DB`/`LITESTREAM_REPLICA_URL`;
  il bucket GCS della classifica si può dismettere dopo la migrazione dei dati.
- Nessun nuovo servizio GCP, nessun VPC connector (Supabase è pubblico su TLS).

---

## Verifica end-to-end

1. **Migrazioni**: `alembic upgrade head`/`downgrade` su un Postgres usa-e-getta
   (Docker `postgres` o `supabase start` locale); verificare tabelle e vincoli.
2. **Test**: la strategia cambia (non più SQLite temporaneo). Codice che tocca il
   DB gira contro un **Postgres di test** (testcontainers o Supabase locale) con
   Alembic applicato e truncation tra i test; logica pura (criteri achievement,
   moderazione) resta senza DB. Nuovi test: verifica JWT (token valido → utente,
   scaduto/manomesso → 401), `claim`, wiring stats con JWT, export/cancellazione.
3. **Flussi manuali**: `signInWithOtp` in dev (link nei log/inbox), ritorno dal
   magic link, `GET /api/auth/me`, giocare un round e vedere le stats
   sull'account, `claim` di un profilo di dispositivo, logout.
4. **Regressioni**: `python -m unittest discover -s tests`, `npm run build`,
   `git diff --check`, `npm audit`; atlante, blog, qualità della vita e `/legacy`
   intatti; CSP aggiornata non rompe GTM/AdSense.

---

## File principali coinvolti

- Nuovi: `app/models.py`, `migrations/` (Alembic), `app/auth.py`,
  `app/comparisons.py` (fase C), `tests/test_auth.py`.
- Riscritti/modificati: `app/db.py` (SQLAlchemy), `app/players.py`,
  `app/achievements.py`, `app/leaderboard.py` (ORM), `app/views.py` (endpoint
  `/api/auth/*`, `/api/player/claim`, hook), `app/__init__.py` (init DB, sessione
  per-request, utente da JWT, CSP, config Supabase nei template), `app/config.py`,
  `requirements.txt`, `Dockerfile`, `cloudbuild.yaml`, `.env.example`, `DEPLOY.md`.
- Frontend: `frontend/package.json` (+`@supabase/supabase-js`),
  `frontend/src/game/shared.jsx`, `frontend/src/game/profile.jsx`,
  `frontend/src/main.jsx` (fase C, comparazioni).
- Riusati: `app/moderation.py`, `app/quiz_tokens.py`, `_rate_limit_ok`.

---

## Nodi da confermare prima della Fase B

- Provider SMTP per Supabase Auth (Resend/Postmark/SES).
- Verifica JWT via secret condiviso (HS256) o via JWKS.
- Testo di privacy e cookie policy per email + sessione account.
