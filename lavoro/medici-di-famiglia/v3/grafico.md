# Grafico v3: chi eroga le cure fuori regione

## Output

- Script riproducibile: `scripts/trend_articles/figure_cure_fuori_regione.py`
- Figura: `content/figures/chi-eroga-cure-fuori-regione/erogatori-cure-fuori-regione.svg`
- Marcatore servito: `<!-- figura: erogatori-cure-fuori-regione -->`
- Formato: SVG con classi `fig fig--narrow`, `viewBox="0 0 370 386"`, `<title>` e `<desc>`.

## Valori sorgente

Ho riletto indipendentemente la tabella del brief e le righe del CSV dichiarato nel frontmatter. Le sei celle coincidono:

| Regione di destinazione | Ricoveri ordinari e day hospital | Specialistica ambulatoriale |
|---|---:|---:|
| Lombardia | 73,2% | 61,9% |
| Emilia-Romagna | 59,1% | 25,5% |
| Toscana | 34,0% | 5,5% |

Sono quote del valore economico della mobilità attiva erogata dal privato convenzionato. Il denominatore è il valore pubblico più privato dello stesso settore e della stessa regione di destinazione. Non sono quote di pazienti, ricoveri o prestazioni.

Lo script seleziona soltanto la fonte GIMBE esatta, l'anno 2023, l'unità `percentuale del valore` e le sei combinazioni attese di territorio e misura. Una cella mancante, duplicata, fuori intervallo o inattesa produce `ValueError`. Le righe AGENAS 2024 e Istat 2024 del CSV non entrano nella figura.

## Calcolo e scala

Scala lineare comune da 0 a 100%. L'area utile va da x=166 a x=346, quindi ogni barra misura `valore / 100 * 180`. Le larghezze SVG risultano 131,8, 111,4, 106,4, 45,9, 61,2 e 9,9. I valori visibili mantengono un decimale e la virgola italiana.

I due settori sono distinti da colore e legenda, senza colori scritti direttamente nello SVG. I colori arrivano dai token già usati da `.fig__bar` e `.fig__bar.is-on`, quindi cambiano con il tema.

## Fonte

Fondazione GIMBE, *La mobilità sanitaria interregionale nel 2023*, Rapporto Osservatorio 1/2026, tabella 4.5, pagina PDF 26, pubblicato il 4 marzo 2026. La figura dichiara fonte, data, anno osservato, unità, denominatore e limite del confronto.

## Prove visive

Ho servito localmente la pagina reale con i CSS e i font del sito. Poiché l'articolo è `draft: true`, la route pubblica risponde 404: per la sola prova ho disattivato `draft` in memoria nel processo Flask, senza modificare il file dell'articolo. Screenshot temporanei, fuori dal repository:

- `/tmp/cure-375-light.png`
- `/tmp/cure-375-dark.png`
- `/tmp/cure-1440-light.png`
- `/tmp/cure-1440-dark.png`

A 375px lo SVG occupa 343px, il testo di note e fonte misura 11,59px effettivi e `scrollWidth` coincide con `clientWidth` a 375px. A 1440px lo SVG occupa 480px e il testo misura 16,22px. In tutti e quattro i casi il controllo dei bounding box ha trovato zero elementi oltre il `viewBox` e nessun overflow orizzontale.

Ispezione degli screenshot: titolo, anno, unità, legenda, sei valori, denominatore, limite, fonte e data sono leggibili. Nessuna etichetta si sovrappone o viene tagliata. Nel tema chiaro e in quello scuro testo, griglia e due serie restano distinguibili. La prima prova mostrava il bordo sinistro del sottotitolo a -1,08 unità SVG; ho spostato i blocchi testuali di 2 unità e ripetuto tutte e quattro le prove con zero elementi fuori tela.

## Controlli

- Test temporanei RED/GREEN sullo script: 6/6 passati. Coprivano selezione delle sei celle, cella mancante, duplicata e inattesa, scala comune, metadati e scrittura del file. Il test temporaneo non è stato mantenuto perché la spec limita il commit a script, SVG e report.
- Confronto indipendente brief/CSV: sei celle coincidenti.
- Rigenerazione dal solo script: SHA256 stabile `dfe3fed808364dc7ff178c76d6f3c42fbea0baaa283aa534ec070b6f5126addc`.
- Parse XML con `xml.etree.ElementTree`: valido.
- `guardia_articolo`: 0 errori, 0 avvisi, 0 non verificabili, 757 parole su tetto 1100.
- `git diff --check`: esito 0.
- Suite completa `bin/py -m unittest discover -s tests -v`: un solo fallimento, `integration.test_viewport_mobile.IlTelefono.test_le_pagine_chiave_reggono_sul_telefono`. Il rerun mirato conferma un limite dell'ambiente: Playwright cerca `~/.cache/ms-playwright/chromium_headless_shell-1243/...`, che non è installato, e chiede `npx playwright install`. Le prove visive di questa figura sono state eseguite con Playwright usando esplicitamente `/usr/bin/google-chrome`.

## Limiti e lavoro restante

Il grafico confronta tre destinazioni e due settori nel 2023. Non misura qualità delle cure, cause della mobilità o traiettorie individuali e non rende confrontabili GIMBE 2023 e AGENAS 2024. Non è stata eseguita una prova in produzione.

La copertina resta da preparare e verificare: `guardia_articolo` non la controlla. Articolo, CSV, figure precedenti e `data/derived/casa_titolo_godimento.csv` sono rimasti intatti.
