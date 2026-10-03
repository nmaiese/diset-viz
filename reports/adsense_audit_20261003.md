# Audit AdSense, parte A2 (CMP, CWV, link rotti), 2026-10-03

Sola lettura. Core Web Vitals stimate da peso e risorse: PageSpeed API senza chiave ha risposto quota esaurita (429), dichiarato e ripiegato sulla stima.

## Consenso cookie / CMP

- CMP: Iubenda (https://www.iubenda.com/privacy-policy/)
- Consent Mode default inline prima di GTM/AdSense: si
- default denied (ad/analytics/personalization): si
- GTM loader (GTM-PZ45BG7D): si
- AdSense loader condizionale (non ADS_OFF, non noindex): si
- pulsante preferenze/revoca: si
- Non verificabile dal repo:
  - CMP caricata via GTM (widget iniettato da gtm.js, assente dall'HTML del server): senza JavaScript non compare alcun banner
  - certificazione Google della CMP e segnale TCF v2.2 effettivo: serve la dashboard Iubenda e un controllo live
  - nessuna unita' pubblicitaria (`<ins class="adsbygoogle">`) nel codice: c'e' solo il loader; ADSENSE_SLOT_BANNER e' configurato ma mai usato

## Core Web Vitals (stima da peso/risorse)

| pagina | HTTP | HTML KB | script | css | img | stima totale KB |
|---|---|---|---|---|---|---|
| home | 200 | 274.0 | 5 | 5 | 6 | 953.0 |
| indicatore | 200 | 172.6 | 5 | 5 | 2 | 379.1 |
| regione | 200 | 399.1 | 5 | 5 | 2 | 603.5 |
| provincia | 200 | 274.0 | 5 | 5 | 2 | 481.4 |
| blog | 200 | 55.9 | 5 | 5 | 6 | 712.1 |

- PageSpeed API: non disponibile: request failed: HTTP Error 429: Too Many Requests

## Link rotti (rapporto W2, non rifatto)

- link rotti: 0
- link verso URL non in sitemap: 6513
- pagine orfane: 10
- URL duplicate: 0
- canonical incoerenti: 0

## URL Inspection (Search Console)

- disponibile da CLI: False
- motivo: nessuno script Search Console in ~/dev/ops (solo GA4 analytics.py, Cloudflare, doctor.sh)

## ads.txt

- HTTP 200, riga attesa presente: True
