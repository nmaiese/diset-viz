---
paths:
  - "app/**"
---

# Le rotte, e le regole che non si vedono rompendole

- `/` — la home, **server-rendered** (`app/templates/v1/home.html` con un
  partial per fascia in `app/templates/v1/home/`, e `home.html` come ripiego):
  la testata con la ricerca e la mappa per andare a una regione, nei colori
  della qualita' della vita (`home.hero_map`, profilo predefinito, con la sua
  legenda; senza classifica torna la mappa grigia);
  le porte del sito; un indicatore in evidenza **diverso a ogni visita**
  (`app/home_pick.py`, per regione o per provincia), con tutti e due i livelli
  nello stesso pannello quando tutti e due stanno nel pool; regioni e province
  con un territorio estratto a caso e l'anteprima della sua scheda; la fascia
  "Gli indicatori, tema per tema" (`#temi`), che e' la porta dell'atlante; la
  qualita' della vita come porta, senza classifica; il quiz; le storie; fonti
  e metodo. Per questo **non sta nella cache di pagina**: rimetterci
  `@cache.cached` mostrerebbe lo stesso indicatore e gli stessi territori a
  tutti per cinque minuti. Le anteprime dei territori
  (`home.territory_previews`) escono dalle stesse funzioni delle pagine
  regione e provincia e si calcolano una volta per processo: costano circa
  un secondo alla prima home di ogni istanza. `?indicatore=<codice>&livello=`
  fissa la scelta (e `?indicator=<id>` del selettore di prima) se quella coppia
  sta nel pool, se no si torna al caso. Il canonico resta `/`. Non e'
  l'atlante. La fascia `#temi` (dal 25 settembre 2026) ha un solo bottone
  primario, "Esplora i N indicatori nell'atlante", con N dalle righe regionali
  dell'atlante (`atlante.rows("regione")["total"]`), che porta sempre alle
  regioni; il selettore Regioni/Province di `_feature.html` con id propri
  (`temi-*`, perche' `tab-regione` e `lv-regione` sono dell'indicatore in
  evidenza); i conteggi d'area verso `/atlante?area=<nome intero dell'area>`
  (con `livello=provincia` sulle province), il valore che `atlante.js`
  confronta con `data-atlas-area`; e per ogni area l'indicatore cambiato di
  piu' (`home.atlas_band`, `synchronized_cache`): variazione della media
  semplice sul pannello fisso divisa per lo scarto interquartile dei territori
  nell'ultimo anno, fra le righe indicizzabili con la linea, regola scritta
  nella riga fonte. Il pannello Province ha solo quello, senza testa e coda.
  La fascia si calcola fuori da `design.render` (`_home_atlas_band`, come
  `_home_feature_pick`): se cede, restano le schede delle regioni di prima
  invece del ripiego della pagina intera. Non costa niente a freddo, perche'
  la proiezione la scalda gia' `home_pick`. Il gemello Markdown ha la stessa
  sezione.
- `/atlante` — dal 25 settembre 2026 una **pagina della 1.0 resa dal server**
  (`design.render("atlante", "v1/atlante.html", None)`, composta da
  `app/design/pages/atlante.py`), non piu' la SPA. In alto "Sulla mappa", il
  modulo dato della scheda (`indicatore.explore_module`, la macro `ui.explore`)
  su un indicatore fisso, `atlante.MAP_INDICATOR` (ter-105, fisso e non estratto
  perche' la pagina sta in cache). Sotto "Tutti gli indicatori": una tabella
  per tema con **tutte le serie** del catalogo regionale all'apertura (597 il
  25 settembre 2026: il numero si legge da `atlante.rows`, mai scritto), link
  canonico alla scheda, sparkline della media semplice sul pannello fisso
  (`indicator_view.fixed_panel`), variazione in chiaro, etichetta di stato
  sulle parziali. Filtri, ricerca e ordine li fa l'isola `static/js/atlante.js`
  sui `data-*` delle righe, con i parametri di prima (`theme`, `area`,
  `source`, `yfrom`, `yto`, `q`, `sort`, `fav`, `partial`) piu' `complete`.
  Le regole che non si vedono:
  - **i 301 stanno fuori dalla cache**, nella view: `?indicator=<id>` e
    `?view=detail` alla scheda (alla `/province` quando il link chiede le
    province), `?view=regioni&rk=<key>` a `/regione/<key>`, `?view=regioni` a
    `/regioni`, `?view=confronto` a `/confronto`, `?view=atlas&indicator=` a
    `?mappa=`. Con la chiave del solo percorso `/atlante` serviva la risposta
    data a `/atlante?indicator=910`. Il ramo Markdown resta primo;
  - **la cache e' per (livello, indicatore)** (`_atlante_page`, `cache.memoize`)
    e **solo sulla mappa di partenza di ogni livello**. I parametri che il
    server legge sono due: `livello` e `?mappa=<codice>`, il bottone "Sulla
    mappa" di una riga, che si risolve contro le righe del livello
    (`atlante.map_choice(code, level)`, un valore che non regge fa 301
    all'atlante di quel livello) e quelle pagine non vanno in cache, perche' seicento varianti da
    600 KB riempirebbero la SimpleCache di tutto il sito;
  - **il bottone "Sulla mappa" non ricarica la pagina** (dal 25 settembre
    2026): `atlante.js` chiede il modulo a
    `/api/atlante/modulo?indicatore=<codice>&livello=<regione|provincia>` e lo
    sostituisce con `DiV1.init`, e l'URL prende `?mappa=` tenendo i filtri. Il
    GET del form con `?mappa=` resta il ripiego, senza JavaScript o se l'API
    non risponde. Il modulo lo compone solo `atlante.map_payload` e lo rende
    solo `v1/_atlante_mappa.html`, per la pagina e per l'API: una prova li
    confronta. L'endpoint risolve il codice con `map_choice` (404 su codice o
    livello sbagliato), sta sotto `/api/` con `noindex`, fuori dall'OpenAPI,
    in cache 300 s con la query string;
  - le righe si compongono una volta per processo (`atlante.rows`,
    `synchronized_cache`) dalla proiezione: **circa 3 s alla prima richiesta
    di ogni istanza**, e `indicator_universe.cache_clear()` le svuota;
  - la pagina pesa sotto 90 KiB compressi (c'e' una prova: 87,3 con le
    province);
  - **le province** stanno a `/atlante?livello=provincia` (dal 25 settembre
    2026): una riga per scheda BES con il livello provinciale, costruita da
    `bes_data.all_bes_indicators` e dalla proiezione, **non** dal catalogo
    dell'atlante, che resta regionale come `/api/catalog`. Link da
    `bes_level_path(id, "provincia")`, area ricavata dal tema (un tema senza
    area solleva un errore), mappa di partenza `MAP_INDICATOR_PROVINCE`
    (bes-01SAL001, la prova guarda il livello provinciale e non `meta`). Il
    selettore `.seg` e' l'unico controllo del livello, e i suoi conteggi
    vengono dalle fonti di ciascun livello: un guasto delle province non
    manda nel ripiego la pagina delle regioni. Le righe regionali con una
    vista provinciale dicono "anche per provincia" (ter-910 porta a
    bes-01SAL001/province). **Il robots lo decide solo il livello**:
    `?livello=provincia` e' `noindex, follow` con canonical `/atlante`, header
    e meta insieme, fuori dalla sitemap. `?anno=`, `?regione=` e un livello
    sconosciuto restano la pagina delle regioni, indicizzabile;
  - **non c'e' un ripiego**: se la regia cede, `design.render` scrive l'errore
    nel log ("pagina 1.0 atlante: nessun ripiego, 500") e la risposta e' un
    500. Il ripiego era `app.html`, la SPA, che se n'e' andata il 25 settembre
    2026: una pagina senza le righe sarebbe un 200 che dice che l'atlante c'e'
    mentre e' rotto.
  - la page view porta `page_type: "atlas"` (`PAGE_TYPE` nel template), non
    `server`, e l'isola emette gli stessi eventi GTM che emetteva la SPA
    (`docs/tracking_spec.md`). Il token dei preferiti lo prende da
    `window.diAuth.token()` (`frontend/src/site/auth.js`).
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
- `/confronto`: dal 25 settembre 2026 una **pagina della 1.0 resa dal
  server** (`design.render("confronto", "v1/confronto.html", None)`, composta
  da `app/design/pages/confronto.py`), non piu' la SPA. Un indicatore, fino a
  tre regioni: la frase in testa, un `form` GET che senza JavaScript e' il modo
  di cambiare confronto, la mappa dell'anno con le regioni scelte contornate,
  la tabella con valore, posizione e la media semplice delle regioni, la serie
  nel tempo. L'isola `static/js/confronto.js` tiene lo stesso form, legge
  `/api/indicator/<id>` e ridisegna senza ricaricare. Le regole che non si
  vedono:
  - **lo stato sta nell'URL** e lo normalizza `confronto.resolve_state`:
    `indicator` (l'id del catalogo, `105` o `bes:10AMB014`, oppure il codice,
    `ter-105`), `region` ripetuto fino a tre volte (la chiave o il nome),
    `year`, con gli alias `indicatore`, `regione` e `anno`. Un valore che non
    regge cade e vale quello di partenza (l'indicatore in evidenza del
    catalogo, Lombardia, Lazio e Campania, l'ultimo anno): un link vecchio
    apre sempre un confronto. L'isola riscrive l'URL con gli stessi nomi.
  - **due livelli, mai mescolati** (dal 25 settembre 2026):
    `?livello=provincia` confronta fino a tre province, nel parametro
    `provincia` ripetuto (la chiave o il nome), e ignora `region`, come il
    livello regionale ignora `provincia`. Offre solo le schede la cui
    `/province` passa la regola (`indicator_universe.level_pages(listed=True)`,
    cioe' `level_passes_rule`, non l'interruttore): il numero si legge da
    `confronto.province_ids()`, mai scritto. La partenza del livello e'
    bes-01SAL001 su Milano, Roma e Napoli. Il selettore delle province e' per
    regione (optgroup da `province_profile.by_region`), il riferimento e' la
    media semplice delle province con la regola di pannello del livello, la
    mappa e' quella provinciale della 1.0. In testa il selettore `.seg`
    Regioni/Province (`confronto.switch_href`) tiene l'indicatore se l'altro
    livello lo offre. Un livello sconosciuto vale le regioni. La voce del menu
    dice ancora "Confronta le regioni".
  - la `/province` di una scheda offerta propone "Metti a confronto le
    province" (`confronto.compare_path`), come la vista regionale propone
    `/confronto`. Due guardie (`test_testa_per_livello`, `test_url_migration`)
    tolgono solo quell'href esatto prima di cercare `livello=`: ogni altro
    link al confronto con un livello le fa fallire.
  - il canonical e' `/confronto` per ogni stato. **Il robots lo decide solo il
    livello**, come sull'atlante: le regioni sono indicizzabili,
    `?livello=provincia` e' `noindex, follow`, header e meta insieme (lo
    strumento sta sopra serie che hanno gia' la loro `/province`
    indicizzabile, e le terne di province sarebbero migliaia di pagine
    sottili). `/atlante?view=confronto` e' un 301 qui: uno strumento, una URL
    pubblica.
  - **in cache c'e' solo la pagina nuda di ogni livello** (`_confronto_page`,
    `cache.memoize` sul livello): gli altri stati si rendono ogni volta,
    perche' sono migliaia e il payload dell'indicatore e' gia' in cache per
    processo.
  - l'isola legge `/api/indicator/<id>`, e al livello provinciale
    `/api/indicator/<id>?livello=provincia` (`indicator_universe.province_payload`,
    la stessa serie della `/province` della scheda, in `explain` solo il
    verso). Senza parametro, o con `livello=regione`, la risposta e' quella di
    sempre, e un livello sconosciuto, o che l'indicatore non ha, e' un 404. Il
    parametro sta nell'OpenAPI.
  - **non c'e' un ripiego**: se la regia cede, la risposta e' un 500 loggato,
    come l'atlante. Una prova lo guarda.
  - la pagina nuda pesa sotto 45 KiB compressi, su tutti e due i livelli
    (c'e' una prova: circa 37 le regioni, 40 le province).
  - i confronti salvati compaiono solo dopo l'accesso: l'isola prende il token
    da `window.diAuth.token()` (`frontend/src/site/auth.js`) e parla con
    `/api/comparisons` (`docs/ACCOUNT.md`).
  - la page view porta `page_type: "atlas"` (`PAGE_TYPE` nel template), come
    quando il confronto era la SPA, e l'isola emette `compare_select_indicator`,
    non `select_indicator`, che e' la conversione dell'atlante, con il
    parametro `level` su ogni evento e `open_province` al livello provinciale
    (`docs/tracking_spec.md`).
  - testata, briciole e piede li rende Flask da `blog_base.html`, come su ogni
    pagina: non c'e' piu' una testata dentro una SPA.
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

**Il titolo della pagina regione** lo compone `views._region_title`, per la 1.0
e per il ripiego: porta la posizione media sugli indicatori, lo stesso numero
dell'H1, e dice "in media". La figura d'apertura mostra un'altra misura, la
qualita' della vita, che la descrizione (`_region_description`) nomina per
esteso: "7ª su 20 regioni" senza la sua misura si leggeva come quella
(`tests/integration/test_titoli_regioni.py`, su tutte le 20).

**Il `page_type` del page_view** lo decide `app/page_types.py` dal percorso, per
ogni pagina e per ogni ripiego. Un template lo sovrascrive solo dichiarando
`PAGE_TYPE` (atlante e confronto `atlas`, la 404 `error`). La tabella dei valori
sta in `docs/tracking_spec.md`.

**I punti delle strisce** (`design.charts._strip`, `mini_strip`) portano nome e
cifra in `data-tip`, mai in un `<title>`: la striscia e' in tre tagli, e i
`<title>` finivano tre volte nel testo che un estrattore legge. `v1.js` crea il
`<title>` al primo passaggio del mouse.
