# Numeri e verifiche

Riproduzione: dalla radice, esportare DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python e lanciare bin/py lavoro/medici-di-famiglia/v2/calcola.py. Correlazioni di Spearman calcolate sulle viste complete indicator_view, ranghi medi in caso di parità. Nessuna ponderazione. I 20 territori sono le regioni e le province autonome come fornite dal sito, incluso Trentino-Alto Adige come aggregato. Per H1/H2 uso il 2022 come anno alternativo; per H3 chiudo la variazione al 2022. Questi controlli sono stati scelti prima del calcolo riproducibile, ma dopo una passata esplorativa dei dati: non sono preregistrati in senso stretto. Sono mantenuti risultati negativi.

## Test preregistrati

| ID | Formula e righe/chiavi | N, esclusioni | Esito 2023 | Controllo contrario scelto prima |
|---|---|---|---|---|
| H1a | rho Spearman tra percentuale MMG oltre 1.500 assistiti (bes-12SER027) e rinuncia (bes-12SER026), celle regionali 2023 per le 20 chiavi elencate sotto. | N=20, nessuna esclusione. | rho=-0,217, legame monotono debole. | 2022: N=20, rho=-0,364. Segno uguale, intensità ancora limitata. |
| H1b | rho tra bes-12SER027 e medici per 1.000 residenti (bes-SDG-3), stesso anno e chiavi. | N=20, nessuna esclusione. | rho=-0,204, legame debole. | 2022: N=20, rho=-0,185. |
| H1c | rho tra bes-12SER027 e infermieri/ostetriche per 1.000 residenti (bes-SDG-4). | N=20, nessuna esclusione. | rho=0,057, nessun ordinamento comune apprezzabile. | 2022: N=20, rho=0,217. |
| H2a | rho tra bes-12SER027 e quota residente 65+ (dem-POP65OVER). | N=20, nessuna esclusione. | rho=-0,193, non emerge un ordinamento comune. | 2022: N=20, rho=-0,167. |
| H2b | rho tra bes-12SER027 e anziani trattati in ADI (bes-12SER003). | N=20, nessuna esclusione. | rho=-0,476, associazione inversa di intensità moderata. Non dimostra che l’ADI spieghi o riduca il carico. | 2022: N=20, rho=-0,223. L’intensità cambia sensibilmente. |
| H3a | rho tra variazioni territoriali 2018-2023 di bes-12SER027 e uso PS (ims-MULTI_PRONTO_SOCCORSO), variazione=end meno inizio. | N=20, nessuna esclusione. | rho=0,143, andamento non accompagnato in modo netto. | Fine 2022: N=20, rho=-0,057. |
| H3b | rho tra variazioni 2018-2023 di bes-12SER027 e uso guardia medica (ims-MULTI_GUARDIA_MEDICA). | N=20, nessuna esclusione. | rho=0,105, andamento non accompagnato in modo netto. | Fine 2022: N=20, rho=0,119. |
| H3c | rho tra variazioni 2018-2023 di uso PS e guardia medica. | N=20, nessuna esclusione. | rho=0,287, legame debole. | Fine 2022: N=20, rho=0,412. |

Chiavi comuni H1/H2: abruzzo, basilicata, calabria, campania, emilia-romagna, friuli-venezia-giulia, lazio, liguria, lombardia, marche, molise, piemonte, puglia, sardegna, sicilia, toscana, trentino-alto-adige, umbria, valle-d-aosta, veneto. H3 usa la stessa intersezione fra le quattro serie negli anni iniziale e finale. Nessuna riga è stata esclusa per dato mancante. Per H1 e H2 i 20 valori sono regionali, non provinciali.

## Celle a supporto

Valori 2023, dalla matrice annuale del dossier. Unità restano quelle proprie di ogni indicatore.

| Regione | MMG oltre soglia % | Rinunce % | Medici per 1.000 | Quota 65+ % | ADI anziani % | Pronto soccorso % | Guardia medica % | Emigrazione ospedaliera % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Lombardia | 74,0 | 7,2 | 4,6 | 23,3 | 3,7 | 64,8 | 20,2 | 5,1 |
| Sardegna | 60,6 | 13,7 | 5,4 | 26,2 | 2,1 | 50,8 | 57,5 | 7,1 |
| Calabria | 37,2 | 7,3 | 4,5 | 23,6 | 1,6 | 29,1 | 20,7 | 21,8 |
| Molise | 21,6 | 9,0 | 5,0 | 26,5 | 7,2 | 39,8 | 40,4 | 32,6 |
| Liguria | 50,7 | 7,8 | 5,6 | 28,9 | 4,0 | 63,5 | 18,4 | 15,3 |

Questi esempi non sono casi individuali e non identificano meccanismi. Misure di uso, dotazione e rinuncia hanno denominatori diversi.

## Matrice rho, misure regionali con anno comune 2023

N=20 per ogni coppia. Sono riportati tutti gli indicatori inclusi con serie regionali e osservazioni 2023. Il costo ADI (ultimo anno 2012), l’assistenza sociosanitaria e le spese comunali (ultimi anni 2021-2022) non condividono questo anno e restano fuori. Perciò non esiste un singolo anno comune a tutte le misure incluse: la matrice riguarda la coorte contemporanea con anno effettivamente condiviso. Nessuna correlazione è una causa. Il legame negativo tra uso del PS e fila ASL oltre 20 minuti è forte (rho=-0,862), ma i denominatori differiscono. La correlazione tra difficoltà di accesso e fila ASL (rho=0,776) è in parte attesa perché la prima definizione include accesso al pronto soccorso tra i servizi.

| | MMG oltre soglia | Rinunce | Medici | Infermieri | ADI | Quota 65+ | PS | Guardia | Emigrazione | Fila ASL | Letti alta assistenza | Multicronicità 75+ | Difficoltà servizi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MMG oltre soglia | 1,000 | -0,217 | -0,204 | 0,057 | -0,476 | -0,193 | 0,423 | -0,095 | -0,503 | -0,547 | -0,190 | -0,524 | -0,552 |
| Rinunce | -0,217 | 1,000 | 0,355 | -0,060 | -0,011 | 0,242 | -0,416 | 0,021 | 0,150 | 0,395 | 0,025 | 0,268 | 0,237 |
| Medici | -0,204 | 0,355 | 1,000 | 0,379 | 0,166 | 0,412 | 0,037 | -0,189 | -0,051 | 0,037 | 0,133 | 0,063 | 0,110 |
| Infermieri | 0,057 | -0,060 | 0,379 | 1,000 | 0,378 | 0,345 | 0,578 | 0,106 | -0,017 | -0,586 | 0,081 | -0,552 | -0,467 |
| ADI | -0,476 | -0,011 | 0,166 | 0,378 | 1,000 | 0,417 | 0,297 | 0,260 | 0,111 | -0,056 | 0,243 | -0,171 | -0,181 |
| Quota 65+ | -0,193 | 0,242 | 0,412 | 0,345 | 0,417 | 1,000 | 0,328 | 0,228 | 0,216 | -0,233 | 0,086 | -0,172 | -0,257 |
| PS | 0,423 | -0,416 | 0,037 | 0,578 | 0,297 | 0,328 | 1,000 | 0,089 | -0,486 | -0,862 | -0,049 | -0,741 | -0,809 |
| Guardia | -0,095 | 0,021 | -0,189 | 0,106 | 0,260 | 0,228 | 0,089 | 1,000 | 0,287 | -0,081 | -0,406 | -0,029 | -0,113 |
| Emigrazione | -0,503 | 0,150 | -0,051 | -0,017 | 0,111 | 0,216 | -0,486 | 0,287 | 1,000 | 0,269 | -0,112 | 0,410 | 0,376 |
| Fila ASL | -0,547 | 0,395 | 0,037 | -0,586 | -0,056 | -0,233 | -0,862 | -0,081 | 0,269 | 1,000 | 0,152 | 0,706 | 0,776 |
| Letti alta assistenza | -0,190 | 0,025 | 0,133 | 0,081 | 0,243 | 0,086 | -0,049 | -0,406 | -0,112 | 0,152 | 1,000 | 0,053 | 0,042 |
| Multicronicità 75+ | -0,524 | 0,268 | 0,063 | -0,552 | -0,171 | -0,172 | -0,741 | -0,029 | 0,410 | 0,706 | 0,053 | 1,000 | 0,694 |
| Difficoltà servizi | -0,552 | 0,237 | 0,110 | -0,467 | -0,181 | -0,257 | -0,809 | -0,113 | 0,376 | 0,776 | 0,042 | 0,694 | 1,000 |

Non si calcola un rho fra indicatori provinciali (bes-12SER002P, bes-12SER003P-N25) e regionali: livello territoriale e popolazione d’osservazione differiscono. Le liste d’attesa cliniche e la spesa sanitaria totale non compaiono come serie nel catalogo. Il costo ADI ter-145 termina nel 2012.
