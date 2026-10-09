# Brief v4.1 — Fecondità regionale, 2014-2024

Stato: test editoriale, nessuna pubblicazione autorizzata. Tipo pezzo: blog. Variante B, cambiamento nel tempo. Responsabile del brief: C-DIV, Codex gpt-6-sol. Data di verifica delle fonti: 2026-10-09.

## Domanda, risposta, lettore

**Domanda reale:** se una regione risale nella classifica della fecondità, significa che lì nascono più figli per donna?

**Risposta in una frase:** no: tra 2014 e 2024 la Calabria è passata dal 16° al 5° posto fra 21 unità italiane NUTS 2 della serie Eurostat, ma il suo tasso di fecondità totale è sceso da 1,29909 a 1,24701 figli per donna, mentre il valore è diminuito in tutte le 21 unità confrontabili.

**Lettore e utilità:** chi legge classifiche regionali e notizie sulla natalità; la pagina mostra perché un rango relativo non misura il miglioramento del fenomeno.

**Dopo questa pagina, il lettore deve aver capito che…** una regione può avanzare in graduatoria perché il suo valore cala meno di altri, e che tasso di fecondità e numero di nascite sono grandezze diverse.

### Scheda editoriale in otto righe

1. Domanda: salire nella classifica dei figli per donna significa migliorare?
2. Definizione: tasso di fecondità totale, somma dei tassi specifici per età calcolati sui nati vivi e sulle donne residenti delle età riproduttive; unità figli per donna in un anno ipotetico.
3. Risultato centrale: Calabria 16°→5° nel 2014-2024, mentre 1,29909→1,24701 figli per donna; tutte le 21 unità Eurostat comparabili calano.
4. Confronto: stessi anni, 21 unità italiane NUTS 2, stessa misura Eurostat `tgs00100`, senza mescolare il dato nazionale Istat.
5. Rilevanza: il rango da solo può dare al lettore una falsa impressione di crescita.
6. Spiegazione: l'avanzamento **aritmetico nella graduatoria** deriva da cali maggiori altrove; le cause demografiche regionali restano non determinate da questo confronto.
7. Limite decisivo: il tasso annuale non conta i bambini nati e non predice i figli effettivi di una coorte di donne.
8. Passo successivo: per spiegare cause e numero di nascite servono popolazione femminile per età, nascite per età e analisi causali dedicate.

## Angoli verificati e decisione

- **Scelto:** avanzamento relativo della Calabria mentre il suo valore cala. Confronto su tutti i territori, non solo sugli estremi. Serie Eurostat 2014 e 2024, scaricata il 2026-10-09 dall'API, 21/21 valori presenti e variazione negativa per tutti. Calabria: rango 16/21 nel 2014, 5/21 nel 2024. Il risultato supera la classifica perché confronta posizione e valore nel tempo.
- **Alternativo, non scelto:** Valle d'Aosta passa dal 2° al 19° posto, 1,54362→1,05435. È un controesempio utile, ma centrare la storia sul caso estremo rischia di ridurre il pezzo a una gara di ranghi; può comparire come controllo della distribuzione, non come causa.
- **Scartato:** «fecondità in calo in tutte le regioni nel 2025». Istat 2025 è provvisorio e nel comunicato offre la sintesi nazionale, per ripartizione e alcuni valori regionali; non costruire da lì una tabella completa di 21 unità Eurostat 2025.

## Schema del racconto e prove

1. Risposta e definizione breve: Calabria sale nel rango ma scende nel valore, con anni, unità e ambito subito espliciti. Prova: Eurostat `tgs00100`.
2. Tutta la distribuzione, non solo Calabria: variazione 2014-2024 delle 21 unità, tutte negative, con due o tre confronti rappresentativi. Prova: figura 1, pendenza 2014→2024 per tutte le unità e tabella alternativa.
3. Perché il rango si muove: ordinare gli stessi 21 valori nei due anni; rendere visibili posizione e valore di Calabria, Basilicata, Valle d'Aosta e Sardegna, senza dedurre cause. Prova: figura 2, tabella compatta di rango e valore con metodo di ordinamento e pari merito.
4. Aggiornamento separato: Istat stima 1,14 figli per donna in Italia nel 2025, contro 1,18 nel 2024, dati 2025 provvisori. Non accostare la stima nazionale 2025 ai ranghi Eurostat 2014-2024 come se fossero la stessa serie. Prova: comunicato Istat del 2026-03-31.
5. Limite e uscita: misura sintetica di periodo, non numero di nati né fecondità compiuta; le possibili cause generali indicate da OECD non spiegano la singola traiettoria regionale. Prova: definizione Eurostat e OECD. Link alla scheda interna `ter-922` solo dopo averne verificato URL canonico e perimetro territoriale.

## Definizione specifica, disponibilità e compatibilità

- **Misura:** tasso di fecondità totale annuale, somma dei tassi di fecondità specifici per età. Numeratore di ciascun tasso: nati vivi di madri residenti nell'età considerata nell'anno; denominatore: donne residenti della stessa età. Eurostat pubblica la sintesi come numero medio ipotetico di figli per donna se i tassi per età dell'anno restassero invariati lungo la vita riproduttiva. Non è il numero effettivo di figli avuti da una coorte.
- **Popolazione:** donne nelle età riproduttive a cui si riferiscono i tassi specifici; il dataset `tgs00100` estrae il tasso totale (`age=TOTAL`) ma non espone nel suo output un intervallo di età esplicito. La nota OECD per l'Italia usa 15-49 anni, ma questo non prova che ogni cella Eurostat abbia esattamente la stessa convenzione: l'articolo non attribuirà la fascia 15-49 a Eurostat senza una sua fonte metodologica. Nel grafico l'etichetta sarà «donne in età riproduttiva» e il limite sarà dichiarato.
- **Territorio e geografia:** 21 unità italiane NUTS 2 Eurostat: 19 regioni amministrative più le due province autonome di Bolzano e Trento in luogo del Trentino-Alto Adige aggregato. I codici NUTS 2 italiani con dato in entrambi gli anni sono 21 su 21. Non chiamarle «21 regioni amministrative».
- **Periodo e fonte:** 2014 e 2024, Eurostat `tgs00100` (dataset `demo_r_frate2`), API aggiornata 2026-09-30T23:00:00+0200, letta 2026-10-09. URL query: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024 . L'ultimo anno del dataset regionale è 2024. Il comunicato Istat sul 2025 è aggiornamento separato e provvisorio.
- **Disponibilità:** 21 NUTS 2 italiani previsti per questo confronto, 21 osservati, 21 usati. Due anni comuni; 42 celle non mancanti. Nessuna media semplice chiamata Italia; riferimento nazionale ufficiale Istat 2025 **sì**, 1,14 figli per donna, ma fuori dal pannello 2014-2024. Nel grafico Eurostat nessun valore nazionale usato come linea di riferimento.
- **Rotture e stato:** nel JSON scaricato il campo `status` non segnala flag di rottura, stima o provvisorietà per nessuna delle 42 celle italiane usate. Il dataset complessivo contiene altri flag, dunque il controllo resta limitato a queste celle e alla release indicata. Nessun verso normativo («meglio») attribuito al tasso.

## Registro delle affermazioni

| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |
|---|---|---|---|---|
| La Calabria passa dal 16° al 5° posto fra le 21 unità osservate. | calcolo | ordinamento decrescente delle 21 celle Eurostat in 2014 e 2024 | NUTS 2 Italia, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| Nella stessa serie la Calabria passa da 1,29909 a 1,24701 figli per donna. | dato | due celle `geo=ITF6` | Calabria NUTS 2, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| Il valore scende in tutte le 21 unità confrontate. | calcolo | 21 differenze 2024 meno 2014 inferiori a zero, 42/42 celle disponibili | NUTS 2 Italia, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| L'avanzamento di rango della Calabria non significa aumento del tasso. | interpretazione | rango 16→5, differenza del valore -0,05208 figli per donna | Calabria e 21 NUTS 2, 2014-2024 | elaborazione Divario Italia da Eurostat |
| L'Istat stima 1,14 figli per donna per l'Italia nel 2025, dato provvisorio. | dato | comunicato, paragrafo «Il numero medio di figli per donna scende a 1,14» | Italia nazionale, 2025 | Istat, 2026-03-31, URL nella tabella fonti |
| Un tasso di periodo non equivale ai figli effettivamente avuti da una coorte. | limite | definizione del tasso ipotetico con tassi per età dell'anno | misura, non territorio specifico | Eurostat `tgs00100`; OECD 2024, URL nella tabella fonti |
| Le cause della diversa dinamica regionale non sono stabilite da questa serie. | limite | confronto descrittivo di due anni, nessun disegno causale | NUTS 2 Italia, 2014-2024 | limite metodologico del confronto |

## Figure previste

1. **«La fecondità scende in tutte le 21 unità, ma non allo stesso ritmo»**: slope chart 2014→2024 con tutte le 21 unità, Calabria evidenziata e Valle d'Aosta come controllo. Domanda: il valore è salito o sceso nei singoli territori? Sottotitolo «Tasso di fecondità totale · donne in età riproduttiva · 21 NUTS 2 italiani · 2014 e 2024»; asse figli per donna; nessun riferimento nazionale; campione 21/21, mancanti 0; eventuali flag; fonte Eurostat `tgs00100` release 2026-09-30, elaborazione Divario Italia. Nota di lettura e tabella alternativa con 21 righe e valori non arrotondati per i calcoli.
2. **«La Calabria sale di posizione mentre il valore cala»**: tabella/diagramma di ranghi con le 21 unità e colonne 2014, 2024, posizione e variazione in figli per donna. Domanda: che cosa cambia quando si guarda al rango anziché al valore? Stesse specifiche di fonte e campione; etichette dei pari merito esplicite, nessun giudizio «meglio».

Le figure risponderanno alle specifiche di REDAZIONE v4 §5, con titolo, sottotitolo, unità/denominatore, riferimento esatto, campione, stato, fonte/release, nota e accesso alternativo. Resa 375 e 1100 px, chiaro e scuro, da verificare nella bozza HTML. Un solo grafico può assolvere entrambi i passaggi se mostra le due risposte senza sovraccarico, ma la domanda di ciascun passaggio deve restare verificabile.

## Fonti esterne verificate

| istituzione | data fonte | URL aperto | affermazione verificata | limite |
|---|---|---|---|---|
| Eurostat | 2026-09-30 | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024 | 42 valori NUTS 2 italiani, aggiornamento della serie e definizione del tasso | 2024 ultimo anno regionale; controllo flag prima della figura |
| Istat | 2026-03-31 | https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/ | stima nazionale 2025 1,14 e 2024 1,18 figli per donna; 2025 provvisorio | non è la stessa tabella territoriale Eurostat 2014-2024 |
| OECD | 2024-06-20 | https://www.oecd.org/it/publications/2024/06/society-at-a-glance-2024-country-notes_d98f4d80/italy_6c299f2d.html | definizione e contesto del tasso, 15-49 anni, età media al parto e limiti dell'interpretazione | dato OECD 2022, non usare per confronti regionali 2024 |

Grafico con dati esterni: Eurostat `tgs00100`, tasso di fecondità totale, 2014 e 2024, 21 unità italiane NUTS 2; URL API sopra, verificato 2026-10-09.

## Cose da non scrivere

- «La Calabria fa più figli» senza anno e unità, oppure «la fecondità migliora» per il solo rango.
- «Tutte le regioni nel 2025» sulla base del comunicato Istat o «21 regioni amministrative» sulla serie Eurostat.
- «Cause del calo in Calabria» dedotte da classifica, occupazione, reddito o servizi senza studi dedicati.
- Unire nello stesso grafico il nazionale Istat 2025 e le celle Eurostat 2014-2024 come una sola serie.
- Chiamare il tasso «numero di nati» o «figli che ogni donna avrà davvero».
