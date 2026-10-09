---
paths:
  - "app/design/pages/atlante.py"
  - "app/templates/v1/atlante.html"
  - "app/templates/v1/_atlante_mappa.html"
  - "app/static/js/atlante.js"
  - "app/views.py"
  - "tests/**/test_atlante*.py"
---

# L'atlante: le regole che non si vedono rompendole

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
    bes-01SAL001/province). **Meta robots e header**: noindex per livello
    provincia e per query con `area` o `theme` insieme a `partial=1`;
    gli altri parametri non cambiano indicizzazione.
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
