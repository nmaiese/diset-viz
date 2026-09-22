---
paths:
  - "app/**"
---

# Le rotte, e le regole che non si vedono rompendole

- `/` — la home, **server-rendered** (`app/templates/home.html`): la mappa viva,
  i quattro percorsi d'ingresso, una storia dai dati, il confronto, i temi, la
  qualita' della vita, le analisi, i quiz. Non e' l'atlante, e non lo e' piu'
  da quando la home e' stata rifatta sul design system 2026.
- `/atlante` — l'atlante React/Vite (sorgente in `frontend/`, build in
  `app/static/dist/`), montato da `app/templates/app.html`. Insieme a
  `/confronto` sono le due sole pagine che caricano il bundle della SPA, e si
  migrano sempre insieme. **La testata non e' loro**: la rende Flask con
  `_ds_header.html` sopra `#root`, come su ogni altra pagina, e il body porta
  `class="ds sitechrome"` perche' `chrome.css` e' scoped sotto quella classe.
  A React restano la barra del telefono e il pulsante di ritorno. Una testata
  disegnata dentro la SPA sono due identita' sullo stesso dominio, ed e' gia'
  successo.
- `/temi`, `/tema/<slug>` — l'indice dei temi e la pagina di un tema.
- `/regioni`, `/regione/<key>` — l'indice delle regioni e il profilo di una.
- `/provincia/<key>` — il profilo di una delle 103 province misurate dal BES:
  posizione, punteggio, le dodici dimensioni, **i valori veri di tutti i 67
  indicatori** con unita', anno e posizione fra le province, dove e' prima e
  dove e' ultima fra le province della sua regione, gli indicatori che la
  tirano su e giu', le vicine in classifica. I valori li legge
  `province_profile.indicatori`, da `bes_data.get_bes_rows("provincia")`: per
  un anno la pagina ha mostrato solo punteggi standardizzati, e chi cercava
  "speranza di vita provincia di Lecce" trovava una pagina senza il numero di
  anni. Il confronto dentro la regione e' sempre fra province, mai con il
  valore regionale. Non c'e' un indice `/province`: l'indice e'
  la classifica, `/qualita-della-vita/classifica/province`, e il percorso passa
  di li'. Il profilo lo monta `app/province_profile.py`, che non calcola niente
  di nuovo: mette in forma il payload di `quality_life_bes.build_bes_territory`.
- `/catalogo-dati` — l'elenco piatto di ogni indicatore indicizzabile.
- `/chi-siamo`, `/contatti`, `/termini`, `/privacy` — le quattro pagine di
  fiducia. Stanno nel contratto di `PUBLIC_DISCOVERABILITY_EXPECTATIONS`, dove
  fino al 22 settembre 2026 non c'erano: l'audit contro produzione non si
  sarebbe accorto se una fosse tornata 404. L'indirizzo a cui si risponde e il
  nome della piattaforma dei consensi stanno in `app/publisher.py`, accanto
  all'identita' che dichiarano, e il `mailto:` va in chiaro: un indirizzo che
  solo JavaScript sa comporre non e' un contatto.
- `/blog`, `/blog/<slug>` — blog server-rendered (Jinja) dai Markdown in
  `content/posts/`.
- `/blog/feed.xml` — il feed RSS 2.0 del blog, con `/feed.xml` e `/rss.xml` che
  ci arrivano con un 301. Le date vanno in RFC 822, non nell'ISO della sitemap.
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
