---
paths:
  - "app/**"
---

# Le rotte, e le regole che non si vedono rompendole

- `/` — atlante React/Vite (sorgente in `frontend/`, build in `app/static/dist/`).
- `/blog`, `/blog/<slug>` — blog server-rendered (Jinja) dai Markdown in
  `content/posts/`.
- `/qualita-della-vita`, `/classifica`, `/metodologia`, `/province` — pagine
  qualità della vita, regionali e provinciali.
- `/indicatore/<slug>/<acronimo>-<id>` — ogni indicatore, di ogni famiglia
  (`ter`, `bes`, `ims`, `eur`, `dem`). Keyword-first per la SEO: lo slug umano
  guida, il codice risolve. Il codice è l'ultimo segmento e porta l'id, quindi
  la pagina sopravvive a un cambio di nome; uno slug sbagliato fa 301 verso il
  canonico, le URL legacy fanno 301 qui. **Un template per tutte le famiglie**
  (`app/templates/indicator_page.html`) su un view model
  (`app/indicator_view.py`): leggere `docs/INDICATOR_PAGES.md` prima di toccare
  l'uno o l'altro.
- `/divari-regionali` — l'hub editoriale sul divario, da `app/divari.py`. Non
  è una seconda tassonomia: argomenta una tesi e la misura, quindi **ogni
  numero e ogni quota nella sua prosa è ricalcolata dal catalogo al render**.
  Mai una cifra hardcoded in quel template. Riusa la mappa della homepage via
  `_map_panel.html` (`_map_hero` in `app/views.py`); le medie delle partizioni
  sono medie semplici dei valori regionali, limite che la pagina dichiara.
- `/confronto` — la casa canonica del confronto: pagina server-rendered che
  monta la vista compare della SPA con `window.__diInitialView`. Lo stato SPA
  `/atlante?view=confronto` funziona ancora ma niente ci punta: uno strumento,
  una URL pubblica. Una vista path-scoped si aggiunge impostando quel flag nel
  template, mai insegnando a `frontend/src/main.jsx` le rotte Flask.
- `/ricerca?q=` — ricerca interna, server-rendered, **`noindex, follow` di
  proposito** (uno spazio `?q=` illimitato sarebbe pagine sottili duplicate).
  L'header sta nella view perché `add_security_headers` timbra `index, follow`
  su ciò che non dichiara altro. Fuori dalla sitemap e deliberatamente NON nel
  disallow di robots.txt: una pagina disallow non si fa mai leggere il noindex.
- `/legacy` — la dashboard D3 originale: non romperla (`tests/integration/test_app.py`).
- `/account` — pagina account (noindex), si popola lato client col Bearer.
- `/api/*` — catalogo, ricerca, indicatori, qualità della vita, **e l'account**:
  `/api/auth/me`, `/api/favorites`, `/api/player/{me,merge,nickname}`,
  `/api/comparisons`, `/api/account/{export,delete}`. Tutti gli endpoint account
  sono authed (401 anonimo) e ricavano l'`auth_id` **solo dal JWT verificato**,
  mai dal body: la RLS è difesa in profondità (il backend gira BYPASSRLS), il
  confine è il `WHERE auth_id`. Leggere `docs/ACCOUNT.md` prima di toccarli.
- `/_pipeline/console` — console catena in tempo reale (Supabase Realtime), su
  `monitor.divarioitalia.it`, ristretta alla mail admin via RLS.

Strato dati: `app/data.py` (legge `app/static/data/Assoluti_Regione.csv`).
Strato blog: `app/blog.py` (legge `content/posts/*.md`).

## Nomi delle fonti: una sola verità

**`app/sources.py` è l'unica fonte per etichette e URL delle famiglie.** Le
etichette utente sono nomi piani institution-first, mai un acronimo interno
nudo, e nessuna etichetta o URL di indicatore va hardcodata altrove. Le
famiglie servite dallo strato esterno stanno in `sources.EXTERNAL_FAMILIES`;
aggiungerne una tocca tre specchi (`app/sources.py`, `discovery.FEED_FAMILY`,
`promote_candidates.PROMOTION_PARSERS`) e `tests/integration/test_discovery.py` li tiene
allineati. Mai hardcodare un prefisso: il codice che lo fece pubblicò una
serie Istat sotto il nome di Eurostat.

## SEO tecnica, da non regredire

Host canonico apex, 404 pubblica con `noindex`, `X-Robots-Tag` su API e dati,
HSTS, sitemap di sole URL canoniche pubbliche, JSON-LD solo dove la pagina
visibile lo sostiene.
