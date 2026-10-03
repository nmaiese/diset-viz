# Ondata 1 AdSense: esito (ramo `nmaiese/adsense-ondata-1`)

## URL tolte dalla sitemap (618 -> 602)

- 10 varianti `?profilo=` della classifica qualita' della vita (5 profili non di
  default x 2 livelli), ora `noindex, follow` con canonical alla base.
- 6 pagine del gioco (`/quiz` + 5 giochi), ora `noindex, follow`.
- Restano in sitemap le 2 basi: `classifica/regioni` e `classifica/province`.

Verifica: `bin/py -c "from app import app; import re; c=app.test_client();
locs=re.findall(r'<loc>([^<]+)</loc>', c.get('/sitemap.xml').get_data(as_text=True));
print(len(locs))"` -> `602`.

## Dove carica lo script AdSense, prima e dopo

Lo script e' un solo loader in `app/templates/_third_party_head.html:50`, gated
da `ADSENSE_CLIENT and not ADS_OFF and not noindex`.

Prima (grep su master): compareva su ogni pagina HTML indicizzata, comprese le
pagine del gioco (non avevano `noindex`) e le varianti `?profilo=` (auto-canonical).

Dopo: la condizione `noindex` ora e' vera per le pagine del gioco
(`_NOINDEX_FOLLOW_PATHS` in `app/__init__.py`) e per le varianti `?profilo=`
(passata dalla view). Verifica:

```
bin/py -c "from app import app, config; config.ADSENSE_CLIENT='ca-pub-test';
c=app.test_client();
print('quiz', 'adsbygoogle.js' in c.get('/quiz').get_data(as_text=True));
print('variante', 'adsbygoogle.js' in c.get('/qualita-della-vita/classifica/regioni?profilo=giovani').get_data(as_text=True));
print('atlante', 'adsbygoogle.js' in c.get('/atlante').get_data(as_text=True))"
# quiz False / variante False / atlante True
```

## Test

- `bin/py -m unittest discover -s tests/unit -q`: 725 test, 4 failure + 1 errore
  gia' presenti su master (manca `PIL`, modulo `photo`/`verify`), non toccati.
- Integration toccati verdi: `test_quality_life`, `test_game`, `test_game_pages`,
  `test_redirect_e_sitemap`, `test_hub_pages`, `test_leaderboard`, `test_app`,
  `test_link_interni`, `test_doppioni`, `test_external_atlas`, `test_confronto_province`,
  `test_atlante`, `test_url_migration`, `test_external_platform`, `test_profilo_regione_esterni`,
  `test_temi_v1`, `test_province_seo`, `test_v1_pages`, `test_design_system`,
  `test_game_hub`, `test_game_sicurezza`, `test_game_mappa_pagina`, `test_page_type`.
- Nota: `test_page_type` fallisce su `/atlante` e `/confronto` solo nella suite
  intera (inquinamento `GOOGLE_TAG_MANAGER_ID` fra moduli), gia' presente su
  master (verificato con `git stash`), non di questa ondata.
