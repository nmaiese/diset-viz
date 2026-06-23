# Specifica tracciamento e consenso

Stato verificato il 2026-06-23.

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
| `GA4 event - page_view` | GA4 event | `CE - page_view` | pageview unica da `dataLayer`, SPA e pagine server |
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

Gli eventi SPA sono emessi da `frontend/src/main.jsx`. Le pagine server-rendered
emettono `page_view` da `app/templates/_third_party_head.html`. La homepage SPA
esclude la pageview server con `TRACK_SERVER_PAGE_VIEW=false`, quindi al primo
accesso resta una sola pageview, quella emessa da React.

| Evento | Quando parte | Uso |
|---|---|---|
| `page_view` | apertura SPA, cambio vista SPA, apertura pagine server | navigazione |
| `select_indicator` | apertura di un indicatore dall'atlante | interesse indicatore |
| `back_to_atlas` | ritorno dalla scheda all'atlante | navigazione |
| `change_year` | cambio anno nella scheda indicatore | esplorazione temporale |
| `change_region` | cambio regione nella scheda indicatore | esplorazione territoriale |
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
| `region` | regione selezionata |
| `view_type` | vista selezionata |
| `theme` | tema selezionato nel catalogo |
| `sort` | ordinamento catalogo |
| `enabled` | valore booleano per dati parziali |

## GA4

Configurazione richiesta:

- usa il Google Tag con `G-THTPZZ02QH`
- imposta `send_page_view=false` sul Google Tag
- mantieni Enhanced Measurement attivo per scroll, outbound click, site search, video, download e form
- mantieni disattivato `pageChangesEnabled`, perché questa SPA aggiorna l'URL anche per filtri, anno e regione
- mantieni create le custom dimension evento per ogni parametro utile all'analisi
- marca come key event solo eventi che rappresentano un obiettivo reale, non `page_view`
- non salvare dati personali o testo libero non controllato

Dimensioni evento create nella property `542300588` il 2026-06-23:

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

Key event creato:

- `select_indicator`, counting method `ONCE_PER_EVENT`

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
- il codice applicativo emette una sola `page_view` manuale per SPA o pagina server-rendered
