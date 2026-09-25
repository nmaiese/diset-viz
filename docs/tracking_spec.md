# Specifica tracciamento e consenso

Stato verificato il 2026-07-17.

Versione GTM live pubblicata: `7`, nome `Disable automatic page_view 2026-06-23`.

Questa specifica applica a Divario Italia la stessa gerarchia operativa usata su
Vecchio Conio: consenso inizializzato in pagina, Google Tag Manager come router,
GA4 gestito da tag nativi in GTM, eventi applicativi solo nel `dataLayer`.

## Principio

Il consenso va inizializzato prima di qualunque tag Google.

Ordine richiesto:

1. default Consent Mode in pagina
2. Google Tag Manager
3. AdSense diretto nel `<head>`
4. CMP Iubenda in GTM su `Consent Initialization - All Pages`
5. Google Tag e tag evento GA4
6. eventi applicativi nel `dataLayer`

Il default in pagina serve perché AdSense non è dentro GTM. Se aspetti solo la
CMP caricata da GTM, AdSense può partire prima del default di consenso.

## ID del progetto

| Oggetto | Valore |
|---|---|
| GTM public ID | `GTM-PZ45BG7D` |
| GA4 measurement ID | `G-THTPZZ02QH` |
| GA4 property | `542300588`, nome `Divario Italia` |
| AdSense client | `ca-pub-6806451730012282` |
| AdSense publisher | `pub-6806451730012282` |
| Iubenda widget | `https://embeds.iubenda.com/widgets/7af38c1d-4e6c-404c-98cc-3609428ac280.js` |
| Sito | `https://divarioitalia.it` |

## Consent Mode

Il template `app/templates/_third_party_head.html` imposta il default prima di
GTM e prima di AdSense:

```html
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag() {
    dataLayer.push(arguments);
  }
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied',
    'personalization_storage': 'denied',
    'functionality_storage': 'granted',
    'security_storage': 'granted',
    'wait_for_update': 2000
  });
  gtag('set', 'ads_data_redaction', true);
</script>
```

Regole:

- `ad_storage`, `ad_user_data`, `ad_personalization` e `analytics_storage` partono sempre da `denied`
- `personalization_storage` parte da `denied`
- `functionality_storage` e `security_storage` partono da `granted`
- `wait_for_update` resta a `2000`
- `ads_data_redaction` resta a `true`
- il default inline non sostituisce la CMP, evita solo una race condition prima che GTM finisca di inizializzare

## GTM

Configurazione pubblicata nel container `GTM-PZ45BG7D`.

Tag principali:

| Nome tag | Tipo | Trigger | Note |
|---|---|---|---|
| `iubenda Privacy Controls and Cookie Solution` | template Iubenda | `Consent Initialization - All Pages` | da collegare manualmente a Iubenda |
| `Consent update - Google ads from Iubenda TCF` | Custom HTML | `Consent Initialization - All Pages` | stesso schema di Vecchio Conio, concede consenso ads solo se Iubenda/TCF lo permette |
| `Google Tag` | Google tag | `Initialization - All Pages` | usa `G-THTPZZ02QH`, con `send_page_view=false` |
| `GA4 event - page_view` | GA4 event | `CE - page_view` | pageview unica da `dataLayer`, emessa dalle pagine server |
| `GA4 event - select_indicator` | GA4 event | `CE - select_indicator` | apertura indicatore |
| `GA4 event - back_to_atlas` | GA4 event | `CE - back_to_atlas` | ritorno all'atlante |
| `GA4 event - change_year` | GA4 event | `CE - change_year` | cambio anno |
| `GA4 event - change_region` | GA4 event | `CE - change_region` | cambio regione |
| `GA4 event - select_sibling_indicator` | GA4 event | `CE - select_sibling_indicator` | navigazione tra indicatori correlati |
| `GA4 event - change_visualization` | GA4 event | `CE - change_visualization` | cambio tab vista |
| `GA4 event - filter_theme` | GA4 event | `CE - filter_theme` | filtro tema |
| `GA4 event - sort_indicators` | GA4 event | `CE - sort_indicators` | ordinamento catalogo |
| `GA4 event - toggle_partial_data` | GA4 event | `CE - toggle_partial_data` | inclusione dati parziali |

Configurazione Iubenda rilevante:

- template `iubenda Privacy Controls and Cookie Solution`
- `embedCS` impostato a `jeeg`
- `emitGtmEvents` impostato a `true`
- `enableDefaultConsentFromStorage` impostato a `true`
- `storageType` impostato a `cookie`
- widget `https://embeds.iubenda.com/widgets/7af38c1d-4e6c-404c-98cc-3609428ac280.js`

Regole operative GTM:

- gli eventi GA4 restano tag nativi `gaawe`
- ogni tag evento GA4 usa `measurementIdOverride` a `G-THTPZZ02QH`
- ogni tag evento GA4 imposta anche `send_to` a `G-THTPZZ02QH`
- non creare un fallback Custom HTML per inviare eventi GA4
- non caricare `gtag/js` dal codice applicativo
- non inviare eventi GA4 direttamente dal codice applicativo
- il codice applicativo deve solo fare push nel `dataLayer`
- non rieseguire il Google Tag su `iubenda_gtm_consent_event`, l'aggiornamento consenso passa dal tag dedicato
- `send_page_view` sul Google Tag deve restare `false`, per evitare doppie pageview tra hit automatica e aggiornamenti consenso

## CSP

La CSP server-side è gestita in `app/__init__.py` e deve restare compatibile con:

- Google Tag Manager e Tag Assistant
- GA4 e gli endpoint di raccolta `google-analytics.com` / `analytics.google.com`
- AdSense e i suoi endpoint Google Ads
- Iubenda
- i font Google usati dal frontend

Host principali autorizzati oggi:

- `www.googletagmanager.com`
- `tagmanager.google.com`
- `ep2.adtrafficquality.google`
- `ssl.gstatic.com`
- `www.gstatic.com`
- `www.google.it`
- `cdn.iubenda.com`
- `www.google-analytics.com`
- `*.google-analytics.com`
- `*.analytics.google.com`
- `www.google.com`
- `*.google.com`
- `pagead2.googlesyndication.com`
- `googleads.g.doubleclick.net`
- `ad.doubleclick.net`
- `ep1.adtrafficquality.google`
- `ep2.adtrafficquality.google`
- `fonts.googleapis.com`
- `fonts.gstatic.com`
- `embeds.iubenda.com`
- `cdn.iubenda.com`
- `cs.iubenda.com`
- `idb.iubenda.com`
- `www.iubenda.com`
- `*.iubenda.com` in `frame-src` for the Iubenda consent widget iframe

## AdSense

AdSense è caricato direttamente nel `<head>` da
`app/templates/_third_party_head.html`, non da GTM.

Motivo:

- il loader AdSense deve stare nel `<head>` su tutte le pagine
- non va duplicato in GTM
- il default Consent Mode inline lo precede sempre

Il file `/ads.txt` deve rispondere:

```text
google.com, pub-6806451730012282, DIRECT, f08c47fec0942fa0
```

## Eventi dataLayer

Tutte le pagine sono server-rendered ed emettono `page_view` da
`app/templates/_third_party_head.html`, una per pagina. La SPA React, che
emetteva gli eventi dell'atlante e del confronto, se n'e' andata il 25
settembre 2026: gli eventi dell'interazione li emettono le isole delle due
pagine, con i nomi di prima, salvo `compare_select_indicator` del confronto.

Dal 25 settembre 2026 l'atlante (`/atlante`) e' una pagina server-rendered: la
sua `page_view` parte dal server con `page_type: "atlas"` (il template dichiara
`PAGE_TYPE`, che `_third_party_head.html` legge al posto di `server`), cosi' la
serie in GA4 non cambia tipo. Gli eventi del catalogo li emette l'isola
`app/static/js/atlante.js` con gli stessi nomi e parametri della SPA
(`filter_macro_area`, `filter_theme`, `filter_data_source`,
`filter_year_range`, `sort_indicators`, `toggle_partial_data`,
`select_indicator`). Il filtro nuovo e' "solo le serie complete" (`?complete=1`):
all'apertura l'atlante mostra tutte le serie, e `toggle_partial_data` porta
`enabled: true` quando le parziali sono visibili, cioe' col filtro spento.

Il confronto (`/confronto`) e' anche lui una pagina server-rendered dal 25
settembre 2026, e anche la sua `page_view` porta `page_type: "atlas"`, come
quando era la SPA. L'isola `app/static/js/confronto.js` emette
`compare_select_indicator` quando cambia l'indicatore, `change_region` quando
cambiano le regioni (dai campi o con un clic sulla mappa), `change_year` quando
cambia l'anno, `open_region` quando si apre il profilo di una regione dalla
tabella. **Non emette `select_indicator`**: quello resta la conversione
"apertura di un indicatore dall'atlante", e il selettore del confronto la
gonfierebbe a ogni cambio.

`TRACK_SERVER_PAGE_VIEW=false` in un template spegne la pageview del server
(`_third_party_head.html`): oggi nessun template lo imposta.

| Evento | Quando parte | Uso |
|---|---|---|
| `page_view` | apertura di ogni pagina, dal server | navigazione |
| `select_indicator` | apertura di un indicatore dall'atlante | interesse indicatore |
| `back_to_atlas` | ritorno dalla scheda all'atlante | navigazione |
| `change_year` | cambio anno nella scheda indicatore o nel confronto | esplorazione temporale |
| `change_region` | cambio regione nella scheda indicatore, o delle regioni del confronto | esplorazione territoriale |
| `compare_select_indicator` | cambio indicatore nel confronto | interesse indicatore, fuori dalla conversione |
| `open_region` | apertura del profilo di una regione dalla tabella del confronto | navigazione |
| `select_sibling_indicator` | click su indicatore correlato | navigazione tematica |
| `change_visualization` | cambio vista tra mappa, classifica e serie | uso visualizzazioni |
| `filter_theme` | filtro tema nel catalogo | segmentazione |
| `sort_indicators` | cambio ordinamento catalogo | comportamento catalogo |
| `toggle_partial_data` | mostra o nasconde indicatori parziali | comportamento catalogo |

Ogni evento include:

- `page_type`
- `page_path`
- `page_title`

Parametri applicativi:

| Parametro | Valori o significato |
|---|---|
| `page_location` | URL completo, solo su `page_view` |
| `indicator_id` | ID indicatore Istat interno |
| `indicator_name` | nome indicatore |
| `indicator_theme` | tema indicatore |
| `year` | anno selezionato |
| `region` | regione selezionata (nel confronto le chiavi delle regioni scelte, separate da virgola) |
| `region_key` | chiave della regione aperta, su `open_region` |
| `view_type` | vista selezionata |
| `theme` | tema selezionato nel catalogo |
| `sort` | ordinamento catalogo |
| `enabled` | valore booleano per dati parziali |

## Giochi

La nuova area giochi usa un tracciamento leggermente diverso finché il
container GTM non espone tag nativi dedicati ai giochi:

- il codice continua a fare `push` nel `dataLayer`
- il helper `trackGameEvent` chiama anche `gtag('event', ...)` con
  `send_to: G-THTPZZ02QH`
- l'endpoint interno `/api/events` resta solo log operativo, non inoltra a GA4

Eventi gioco oggi previsti:

| Evento | Quando parte | Uso |
|---|---|---|
| `game_start` | avvio di una partita | inizio sessione gioco |
| `game_guess` | risposta in "Indovina la Regione" | engagement round quotidiano |
| `game_finish` | fine partita del gioco quotidiano | completamento round |
| `game_share` | condivisione del risultato | retention / viralità |
| `game_stats_open` | apertura statistiche | engagement |
| `game_archive_open` | apertura archivio round | engagement |
| `compare_start` | inizio di "Chi è maggiore?" | avvio sfida |
| `compare_answer` | risposta a un round di confronto | risposta corretta / errata |
| `order_start` | inizio di "Ordina le regioni" | avvio sfida |
| `order_answer` | invio dell'ordine | completamento sfida |
| `leaderboard_submit` | invio punteggio in classifica | conversione gioco |
| `leaderboard_view` | apertura classifica | engagement |
| `hub_mode_click` | click su una modalità dal hub | navigazione |
| `quiz_source_click` | click sulla fonte del round | fiducia e approfondimento |

Parametri gioco da registrare in GA4:

| Parametro | Valori o significato |
|---|---|
| `mode` | daily, practice, archive, compare, order |
| `score` | punteggio ottenuto |
| `total` | totale massimo del round |
| `result` | correct, wrong, timeout |
| `streak` | serie attuale |
| `difficulty` | livello difficoltà |
| `count` | numero regioni nel round order |
| `source` | etichetta della fonte mostrata |
| `period` | week, all |
| `attempt` | numero del tentativo |
| `attempts` | numero tentativi della partita |
| `correct` | true, false |
| `won` | true, false |

## GA4

Configurazione richiesta:

- usa il Google Tag con `G-THTPZZ02QH`
- imposta `send_page_view=false` sul Google Tag
- mantieni Enhanced Measurement attivo per scroll, outbound click, site search, video, download e form
- mantieni disattivato `pageChangesEnabled`, perché le isole dell'atlante e del confronto aggiornano l'URL (`replaceState`) anche per filtri, indicatore, anno e regione
- mantieni create le custom dimension evento per ogni parametro utile all'analisi
- marca come key event solo eventi che rappresentano un obiettivo reale, non `page_view`
- non salvare dati personali o testo libero non controllato

Dimensioni evento create nella property `542300588` il 2026-07-17:

- `page_type`
- `indicator_id`
- `indicator_name`
- `indicator_theme`
- `year`
- `region`
- `view_type`
- `theme`
- `sort`
- `enabled`
- `correct`
- `won`

Key event creato:

- `select_indicator`, counting method `ONCE_PER_EVENT`

Key event aggiunto per i giochi:

- `leaderboard_submit`, counting method `ONCE_PER_EVENT`

Key event rimossi perché non rappresentano una conversione:

- `change_year`
- `change_region`

Key event ancora presente ma non cancellabile via Admin API:

- `purchase`

## Checklist operativa

1. inserisci il default Consent Mode prima di GTM e prima di qualunque script Google
2. carica la CMP Iubenda con `Consent Initialization - All Pages`
3. usa un template CMP che chiama le API GTM `setDefaultConsentState` e `updateConsentState`
4. tieni i tag Google su trigger successivi a Consent Initialization
5. non spostare AdSense in GTM
6. manda eventi applicativi nel `dataLayer`, non chiamare GA4 direttamente dal codice app
7. verifica con Tag Assistant che il default arrivi prima di ogni tag
8. verifica in rete che le hit Google partano con consenso coerente
9. aggiorna questa specifica se cambiano ID, CMP, eventi o parametri

## Stato automazione GTM

Il 2026-06-23 la configurazione e la pubblicazione GTM sono state completate via
API dopo re-auth OAuth con scope `analytics.edit`,
`tagmanager.edit.containers`, `tagmanager.edit.containerversions` e
`tagmanager.publish`.

Verifica live eseguita con Chrome headless e API Google:

- il container pubblico `GTM-PZ45BG7D` contiene `G-THTPZZ02QH`
- il JavaScript GTM contiene `send_page_view=false` sul Google Tag
- il JavaScript GTM non contiene piu `iubenda_gtm_consent_event` come trigger del Google Tag
- la stream GA4 mantiene Enhanced Measurement attivo ma con `pageChangesEnabled` disattivato
- il codice applicativo emette una sola `page_view` manuale per pagina server-rendered
