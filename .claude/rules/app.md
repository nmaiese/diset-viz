---
paths:
  - "app/**"
---

# Le rotte, e le regole che non si vedono rompendole

- `/` — la home, **server-rendered** (`app/templates/v1/home.html` con un
  partial per fascia in `app/templates/v1/home/`, e `home.html` come ripiego):
  la testata con la ricerca e, da 960 px, la mappa per andare a una regione;
  le porte del sito; un indicatore in evidenza **diverso a ogni visita**
  (`app/home_pick.py`, per regione o per provincia), con tutti e due i livelli
  nello stesso pannello quando tutti e due stanno nel pool; regioni e province
  con un territorio estratto a caso e l'anteprima della sua scheda; i temi; la
  qualita' della vita come porta, senza classifica; il quiz; le storie; fonti
  e metodo. Per questo **non sta nella cache di pagina**: rimetterci
  `@cache.cached` mostrerebbe lo stesso indicatore e gli stessi territori a
  tutti per cinque minuti. Le anteprime dei territori
  (`home.territory_previews`) escono dalle stesse funzioni delle pagine
  regione e provincia e si calcolano una volta per processo: costano circa
  un secondo alla prima home di ogni istanza. `?indicatore=<codice>&livello=`
  fissa la scelta (e `?indicator=<id>` del selettore di prima) se quella coppia
  sta nel pool, se no si torna al caso. Il canonico resta `/`. Non e'
  l'atlante.
- `/atlante` — l'atlante React/Vite (sorgente in `frontend/`, build in
  `app/static/dist/`), montato da `app/templates/app.html`. Insieme a
  `/confronto` sono le due sole pagine che caricano il bundle della SPA, e si
  migrano sempre insieme. **La testata non e' loro**: la rende Flask con
  `_ds_header.html` sopra `#root`, come su ogni altra pagina, e il body porta
  `class="ds sitechrome"` perche' `chrome.css` e' scoped sotto quella classe.
  Anche briciole (`_breadcrumb.html`) e piede (`_ds_footer.html`, lo stesso di
  ogni pagina) li rende Flask, fuori da `#root`, e il bersaglio di "Vai al
  contenuto" e' il `div#contenuto` attorno a briciole e `#root`. A React resta
  solo il pulsante di ritorno: la barra del telefono, la barra di contesto e il
  selettore "Per indicatore, Per regione, Confronta" se ne sono andati il 24
  settembre 2026, con `window.__diNav`. Una testata
  disegnata dentro la SPA sono due identita' sullo stesso dominio, ed e' gia'
  successo.
- `/temi`, `/tema/<slug>` — l'indice dei temi e la pagina di un tema. La
  pagina tema legge il catalogo dell'atlante, che e' regionale, e in fondo ha
  la sezione "Per provincia" con le schede del tema che hanno i valori delle
  province, aperte sulle province (`indicator_view.province_indicators_by_theme`,
  col tema della scheda, lo stesso della sua briciola): senza, le schede
  solo provinciali non stavano in nessun tema.
- `/regioni`, `/regione/<key>` — l'indice delle regioni e il profilo di una.
  La tabella "Tutti gli indicatori" ha la colonna Andamento, la serie della
  regione da `_region_series()`: una voce per processo (`synchronized_cache`,
  circa 55 ms alla prima pagina e 1,3 MB), mai una lettura per riga.
- `/provincia/<key>` — il profilo di una delle 107 province misurate dal BES:
  posizione, punteggio, le dodici dimensioni, **i valori veri di tutti i 67
  indicatori** con unita', anno e posizione fra le province, dove e' prima e
  dove e' ultima fra le province della sua regione, gli indicatori che la
  tirano su e giu', le vicine in classifica, e accanto a ogni variazione la
  sparkline della serie della provincia. I valori li legge
  `province_profile.indicatori`, da `bes_data.get_bes_rows("provincia")`: per
  un anno la pagina ha mostrato solo punteggi standardizzati, e chi cercava
  "speranza di vita provincia di Lecce" trovava una pagina senza il numero di
  anni. Il confronto dentro la regione e' sempre fra province, mai con il
  valore regionale. Il profilo lo monta `app/province_profile.py`, che non calcola niente
  di nuovo: mette in forma il payload di `quality_life_bes.build_bes_territory`.
  I link alle schede escono da `bes_data.bes_level_path(id, "provincia")`: una
  scheda a due livelli si apre sulle regioni, e da una provincia il lettore
  deve atterrare su `?livello=provincia`, dove c'e' la sua provincia, e
  direttamente sulla sua riga: il link finisce in `#p-<key>`, l'`id` della
  riga nella classifica della scheda.
- `/province` — l'indice geografico delle province, regione per regione, dal
  23 settembre 2026. Prima l'indice era la classifica: la classifica risponde a
  "chi e' prima", l'indice a "dov'e' la mia provincia". La briciola di una
  provincia passa dalla sua regione (Italia, regione, provincia), ogni pagina
  regione elenca le sue province, e `/provincia` e `/provincia/` fanno 301 qui.
  I raggruppamenti li fa `province_profile.by_region`, che solleva un errore se
  una provincia cade in una regione senza pagina.
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
- `/qualita-della-vita`, `/qualita-della-vita/classifica/<regioni|province>` —
  l'indice e le due classifiche della qualità della vita (`?profilo=` sceglie i
  pesi). `/qualita-della-vita/province` è un 301 verso la classifica
  provinciale, `/qualita-della-vita/metodologia` un 301 verso
  `/metodologia#qualita-della-vita`: i link interni puntano direttamente lì.
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
- `/confronto` — **solo regionale**: la voce del menu dice "Confronta le
  regioni", e le schede al livello provinciale non lo propongono. La casa
  canonica del confronto: pagina server-rendered che
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
