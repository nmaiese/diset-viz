---
paths:
  - "app/design/pages/confronto.py"
  - "app/templates/v1/confronto.html"
  - "app/static/js/confronto.js"
---

# Il confronto: le regole che non si vedono rompendole

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
