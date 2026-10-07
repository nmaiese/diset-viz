# Riscrittura dopo Gate B, giro 1: cure fuori regione v3

Articolo: `content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md` (resta `draft: true`). Partenza: HEAD `3ea6829407aa290776109dea8d47747c5c86a320`. Nessun cambio a valori, CSV, SVG, script figura, foto, crediti, link o fonti.

## R1 (bloccante): quote GIMBE come quote del valore

- `description`. Prima: «il privato fa il 73,2% dei ricoveri di chi arriva da fuori e il 61,9% della specialistica». Dopo: «il privato convenzionato eroga il 73,2% del valore dei ricoveri di chi arriva da fuori e il 61,9% di quello della specialistica. In Emilia-Romagna il 59,1% e il 25,5%.»
- Seconda frase della description (segnalata dal coordinatore): «In Emilia-Romagna il 59,1% e il 25,5%» ora ripete «del valore dei ricoveri» e «di quello della specialistica».
- Lead. Prima: «In Emilia-Romagna il 59,1% dei ricoveri, ma solo il 25,5% della specialistica» e «distano 14,1 punti percentuali». Dopo: «del valore» esplicito per entrambe le regioni e settori, e «la quota del valore dista 14,1 punti percentuali nei ricoveri e 36,4 nella specialistica». Il lead non cresce di numeri.
- Dopo il grafico. Lombardia: «pesa più della metà del valore». Emilia-Romagna: «59,1% del valore», «25,5% del valore, cioè un quarto».
- Toscana: «34,0% del valore»; «il valore della mobilità in arrivo va soprattutto al pubblico»; controesempio ER «nel valore».
- Frase «chi si cura fuori regione va nel privato» (unità persona) riscritta in «il valore della mobilità in arrivo va soprattutto al privato».
- Limite: il frontmatter `dataset`/`external_figures` diceva già «valore»: non toccato. Il titolo SEO non contiene numeri.

## R2 (bloccante): unità ricovero, non persona

- Prima: «Chi si sposta per un ricovero finisce più spesso in una struttura privata che in una pubblica.»
- Dopo: «Tra i ricoveri di mobilità effettiva, quindi, la quota maggiore è del privato accreditato, e la sua quota di spesa supera quella dei ricoveri.» Coorte, anno e confronto 62,62% / 69,23% restano. Il secondo membro è un confronto aritmetico dei due valori già citati, nessun fatto nuovo.

## R3 (medio): Modelli M al primo addebito

- Alla prima citazione GIMBE (sezione «Due poli») aggiunto: «Usa i valori dei Modelli M al primo addebito, cioè prima di contestazioni e compensazione fra regioni, e possono quindi cambiare: non sono il saldo definitivo.»
- Nota di metodo: «valore contabilizzato al primo addebito, non un costo reale né un margine». Precisazione già presente su costi e margini conservata.
- Limite: la formula «compensazione fra regioni» sintetizza «contestazioni, controdeduzioni e accordi di compensazione» del Gate B.

## Controlli

- `guardia_articolo`: 0 errori, 0 avvisi, 0 non verificabili, 817 parole su 1100.
- `git diff --check`: pulito (solo avviso CRLF sul file preesistente `casa_titolo_godimento.csv`, non toccato né aggiunto).
- Suite completa (`bin/py -m unittest discover -s tests`, con `PLAYWRIGHT_CHROMIUM=/usr/bin/google-chrome`): 2314 test, OK, nessun fallimento. Solo ResourceWarning sqlite, rumore preesistente.
- Nessun em-dash, en-dash, punto e virgola o puntini aggiunti.
