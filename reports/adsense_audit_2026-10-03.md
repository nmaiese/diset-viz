# Audit AdSense, parte A (parziale), 3 ottobre 2026

Sola lettura, sul codice di master 121b86fd (HTML reso dal server con il test client Flask, senza JavaScript) e su Search Console. Ipotesi 1 della spec (contenuti scalati) misurata per prima. Le parti non fatte sono in fondo.

## Come si misura
- Tutte le 618 URL della sitemap, non un campione. Testo = contenuto di `<main>`/`<article>`, senza script, nav, header, footer, form, svg.
- "Testo unico" stimato: gli shingle di 5 parole (numeri normalizzati a `#`) presenti in almeno il 25% delle pagine dello stesso tipo contano come modello, il resto come unico. Quasi duplicato = similarita di Jaccard fra shingle di due pagine dello stesso tipo.
- Limite: normalizzare i numeri fa passare per "modello" le tabelle di cifre. E' voluto (le cifre non sono testo editoriale), ma abbassa il "testo unico" delle pagine piene di tabelle. Anche i nomi di territorio sostituiti in una frase uguale non vengono visti come modello: la stima del duplicato e per difetto.

## Sitemap per tipo, testo, duplicati (mediane)
| tipo | URL | parole visibili | testo unico stimato | % con unico ≥300 | quasi dup ≥50% | ≥80% |
|---|---|---|---|---|---|---|
| indicatore | 410 | 1433 | 514 | 100 | 338 (82%) | 7 |
| provincia | 107 | 3371 | 506 | 100 | 107 (100%) | 25 |
| regione | 20 | 6002 | 1180 | 100 | 20 (100%) | 0 |
| indicatore/province | 22 | 1898 | 529 | 100 | 13 | 0 |
| qualita-della-vita | 12 | 1900 | **161** | **8** | 11 | 10 |
| tema | 12 | 2180 | 1422 | 100 | 0 | 0 |
| blog | 17 | 1310 | 924 | 100 | 0 | 0 |
| quiz | 6 | 174 | 174 | 17 | n/d | n/d |
Pagine singole: home 962 parole, chi-siamo 705, metodologia 5563, privacy 910, contatti 284, termini 324. Nessun 4xx/5xx in sitemap, nessuna pagina noindex in sitemap.

## Lettura
- La soglia "≥300 parole di testo unico" e superata quasi ovunque, ma il quadro e meno buono di cosi: province e regioni sono quasi duplicati fra loro al 100% (stessa struttura, stesse frasi, cambiano nomi e cifre), e 338 schede indicatore su 410 hanno piu della meta degli shingle in comune con un'altra scheda. E' il profilo di contenuto da modello su cui Google scrive "scarso valore".
- Le pagine piu esposte sono `qualita-della-vita` (12 pagine, unico mediano 161, 10 quasi cloni all'80%) e i quiz (174 parole, interfaccia).
- Il punto forte sono blog (17), temi e regioni.

## Search Console (28 giorni, 04/09 to 01/10, `sc-domain:divarioitalia.it`)
Pagine con impressioni per tipo (pagine, clic, impressioni): indicatore 287/410, 284 clic, 10115 imp; provincia 100/107, 3 clic, 842 imp; blog 13/17, 29 clic, 662 imp; qualita-della-vita 13/12 (include sottopagine), 15 clic; regione 13/20, 1 clic, 35 imp. Controllo URL Inspection su 4 URL (indicatore, provincia, regione, home): tutte "Submitted and indexed".
- Ipotesi 2 (poca copertura) smentita sui tipi grandi: Google ha indicizzato e mostra la maggior parte delle schede. Il problema non e essere sconosciuti ma valere poco: 100 province con 842 impressioni e 3 clic.
- Il conteggio indicizzate/escluse per tipo non e in API; serve URL Inspection su un campione piu largo (quota 2000/giorno): da fare nella parte seguente.

## Requisiti AdSense
- ads.txt online: `google.com, pub-6806451730012282, DIRECT, f08c47fec0942fa0`.
- Pagine legali e contatti presenti e in sitemap (privacy 910 parole, termini 324, contatti 284, chi-siamo 705, metodologia 5563).
- CMP: nel codice c'e il consenso Iubenda/Funding Choices (`app/publisher.py`, `_funding_choices_revoke.html`); NON verificata la certificazione Google ne il comportamento in pagina. Da fare.
- Core Web Vitals su 5 pagine, link rotti interni: non misurati.
- Articoli editoriali: 17 nel blog in sitemap (target 30).

## Non fatto in questa passata
Top/bottom 10 per qualita (solo per parole visibili: sotto), copertura indicizzata su campione largo, CWV, link rotti, CMP.
Piu deboli per parole visibili: /quiz 117, /quiz/indovina-la-regione 133, /quiz/ordina 133, /quiz/indovina-la-provincia 174, /quiz/chi-e-maggiore 278, /contatti 284, /termini 324, /province 456, /quiz/province-italiane 495, /temi 574. Piu ricche: /atlante, /catalogo-dati, le 20 regioni (~6000).
Script: nello scratchpad della sessione, riproducibile con `bin/py` e il test client; lo porto in `scripts/` se serve ripeterlo (criterio "audit ripetuto" della spec).
