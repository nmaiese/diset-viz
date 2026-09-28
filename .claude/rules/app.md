---
paths:
  - "app/**"
---

# Le rotte, e le regole che non si vedono rompendole

- `/` — la home, server-rendered e mai in cache di pagina: regole in `.claude/rules/app-home.md`.
- `/atlante` — pagina della 1.0 senza ripiego, con 301 fuori dalla cache e robots deciso dal livello: regole in `.claude/rules/app-atlante.md`.
- `/temi`, `/tema/<slug>` — l'indice dei temi e la pagina di un tema, dal 26
  settembre 2026 **pagine della 1.0** (`design.render("temi"|"tema", ...)`,
  `app/design/pages/temi.py` e `tema.py`, ripiego `themes_index.html` e
  `theme_page.html`). Gli esempi di ogni tema, nell'indice come nella pagina,
  vengono da `_theme_featured`, mai dai primi in ordine alfabetico. La
  pagina tema legge il catalogo dell'atlante, che e' regionale, e in fondo ha
  la sezione "Per provincia" con le schede del tema che hanno i valori delle
  province, aperte sulle province (`indicator_view.province_indicators_by_theme`,
  col tema della scheda, lo stesso della sua briciola): senza, le schede
  solo provinciali non stavano in nessun tema. Quella sezione **filtra sul
  livello, non sulla scheda**: una scheda indicizzabile per le sue regioni puo'
  avere la `/province` fuori dall'indice, e si guarda la regola del livello
  (`level_passes_rule`), non l'interruttore `seo_policy.LEVEL_PAGES_INDEXABLE`.
- `/regioni`, `/regione/<key>` — l'indice delle regioni e il profilo di una.
  L'indice e' una pagina della 1.0 dal 26 settembre 2026 (`design/pages/regioni.py`,
  ripiego `regions_index.html`): le regioni per ripartizione, i fatti di ogni
  scheda dalle stesse funzioni della pagina regione, la mappa per scegliere
  solo da 960 pixel.
  La tabella "Tutti gli indicatori" ha la colonna Andamento, la serie della
  regione da `_region_series()`: una voce per processo (`synchronized_cache`,
  circa 55 ms alla prima pagina e 1,3 MB), mai una lettura per riga.
  **Regione e provincia hanno la loro immagine da condividere**: l'`og:image` e'
  `static/img/og/territori/<livello>-<key>.png` (`design.og.og_image`), 127 PNG
  committati, generati da `scripts/og_territori.py` e non al render. Un
  territorio senza file torna all'immagine del sito, e
  `tests/unit/test_og_territori.py` vuole un file per ognuno: dopo una nuova
  classifica della qualita' della vita si rigenerano. "E' la mia" e il segno
  nella testata vivono solo nel browser (`localStorage`, `di:mio`): la pagina
  che il server rende e' la stessa per tutti, e cosi' deve restare.
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
  deve atterrare sulla vista provinciale, `.../<codice>/province`, dove c'e'
  la sua provincia, e direttamente sulla sua riga: il link finisce in
  `.../province#p-<key>`, l'`id` della riga nella classifica della scheda.
- `/province` — l'indice geografico delle province, regione per regione, dal
  23 settembre 2026. Prima l'indice era la classifica: la classifica risponde a
  "chi e' prima", l'indice a "dov'e' la mia provincia". La briciola di una
  provincia passa dalla sua regione (Italia, regione, provincia), ogni pagina
  regione elenca le sue province, e `/provincia` e `/provincia/` fanno 301 qui.
  I raggruppamenti li fa `province_profile.by_region`, che solleva un errore se
  una provincia cade in una regione senza pagina. Pagina della 1.0 dal 26
  settembre 2026 (`design/pages/province.py`, ripiego `provinces_index.html`).
- `/catalogo-dati` — ogni indicatore indicizzabile, raggruppato per tema con un
  filtro (pagina della 1.0 dal 26 settembre 2026, `design/pages/catalogo_dati.py`,
  ripiego `data_catalog.html`). Il JSON-LD `DataCatalog` non cambia con la regia.
- `/chi-siamo`, `/contatti`, `/termini`, `/privacy` — le quattro pagine di
  fiducia. Stanno nel contratto di `PUBLIC_DISCOVERABILITY_EXPECTATIONS`, dove
  fino al 22 settembre 2026 non c'erano: l'audit contro produzione non si
  sarebbe accorto se una fosse tornata 404. L'indirizzo a cui si risponde e il
  nome della piattaforma dei consensi stanno in `app/publisher.py`, accanto
  all'identita' che dichiarano, e il `mailto:` va in chiaro: un indirizzo che
  solo JavaScript sa comporre non e' un contatto.
- `/blog`, `/blog/<slug>` — blog server-rendered (Jinja) dai Markdown in
  `content/posts/`. L'indice e' una pagina della 1.0 dal 26 settembre 2026
  (`design/pages/blog.py`, ripiego `blog_list.html`).
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
  canonico, le URL legacy fanno 301 qui. **La vista provinciale di una scheda a
  due livelli e' una pagina a se'**, `/indicatore/<slug>/<codice>/province`
  (dal 25 settembre 2026): li' il codice e' il penultimo segmento, e il terzo
  accetta solo `province`, altrimenti 404. Ogni altro indirizzo (slug
  sbagliato, codice prima dello slug, `/indicatore/<codice>/province`,
  `?livello=`) fa **un 301 in un salto solo** all'URL del livello, tenendo
  `anno` e `regione`. Una scheda senza livello provinciale risponde 404 sulla
  `/province` (ter-910, per esempio). Canonical, robots e sitemap delle
  `/province` stanno in `docs/INDICATOR_PAGES.md`. **Le regioni di
  bes-01SAL001** (speranza di vita BES) hanno il canonical su ter-910, la
  stessa serie, **senza noindex**: stanno fuori da sitemap, llms-full e
  `/catalogo-dati`, dove le sostituisce la loro `/province`. **Un template per tutte le famiglie**
  (`app/templates/indicator_page.html`) su un view model
  (`app/indicator_view.py`): leggere `docs/INDICATOR_PAGES.md` prima di toccare
  l'uno o l'altro.
- `/divari-regionali` — l'hub editoriale sul divario, da `app/divari.py`. Non
  è una seconda tassonomia: argomenta una tesi e la misura, quindi **ogni
  numero e ogni quota nella sua prosa è ricalcolata dal catalogo al render**.
  Mai una cifra hardcoded in quel template. Dal 26 settembre 2026 e' una
  pagina della 1.0 (`design/pages/divari_regionali.py`, ripiego
  `divari_regionali.html`): la mappa e' `ui.map` con la sua legenda, sui dati
  di `_map_hero`, e l'indicatore si sceglie con un form GET. Le medie delle
  partizioni sono medie semplici dei valori regionali, limite che la pagina
  dichiara.
- `/confronto` — pagina della 1.0 senza ripiego, stato nell'URL, due livelli mai mescolati: regole in `.claude/rules/app-confronto.md`.
- `/ricerca?q=` — ricerca interna, server-rendered, pagina della 1.0 dal 26
  settembre 2026 (`design/pages/ricerca.py`): risultati per tipo con
  `?tipo=`, 20 per pagina, pertinenza in `_search_rank` (territorio, tema,
  titolo, poi descrizione, piu' una tabella breve di sinonimi). **`noindex, follow` di
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
visibile lo sostiene. Ogni URL vecchia arriva al canonico in un 301 solo, anche
da `www.` (`redirect_www_to_apex` risolve l'URL numerica di una scheda), e la
barra finale su una pagina che esiste fa 301 alla forma senza (il gestore della
404). `tests/integration/test_redirect_e_sitemap.py` lo guarda.

**I titoli di regione e provincia non portano posizioni** (dal 26 settembre
2026). Li compongono `views._region_title` ("Lombardia in numeri: 312
indicatori su lavoro e redditi", la cifra e' il conteggio) e `views._titolo_provincia` ("Lecce, dati della
provincia e qualita' della vita"), per la 1.0 e per il ripiego: il nome e le
parole con cui la pagina si cerca. Una posizione nel titolo si leggeva come
un'altra classifica (la media sugli indicatori accanto alla qualita' della vita)
e rispondeva solo a chi cerca la classifica, che ha la sua pagina. Le posizioni
stanno nell'H1, nella figura e nella descrizione, sempre con il nome della loro
misura (`tests/integration/test_titoli_regioni.py`, `test_province_seo.py`).

**Il `page_type` del page_view** lo decide `app/page_types.py` dal percorso, per
ogni pagina e per ogni ripiego. Un template lo sovrascrive solo dichiarando
`PAGE_TYPE` (atlante e confronto `atlas`, la 404 `error`). La tabella dei valori
sta in `docs/tracking_spec.md`.

**I punti delle strisce** (`design.charts._strip`, `mini_strip`) portano nome e
cifra in `data-tip`, mai in un `<title>`: la striscia e' in tre tagli, e i
`<title>` finivano tre volte nel testo che un estrattore legge. `v1.js` crea il
`<title>` al primo passaggio del mouse.
