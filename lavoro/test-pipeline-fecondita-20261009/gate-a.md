# Gate A: test-pipeline-fecondita-20261009
Contratto: v4.1
Tipo pezzo: blog
Esito: FERMO
SHA brief: 9f4bfe785842a6356e0f7a6df9bfc11c6bd2957d
Hash brief: f9023e94656349efd743026595e470c314fd1c9a0ca2a996a55c3ebe1a857e22
Autore/modello: C-DIV, Codex gpt-6-sol
Giudice/modello: Antigravity Gemini 3.1 Pro (High)
Domanda: se una regione risale nella classifica della fecondità, significa che lì nascono più figli per donna?
Risposta in una frase: no: tra 2014 e 2024 la Calabria è passata dal 16° al 5° posto fra 21 unità italiane NUTS 2 della serie Eurostat, ma il suo tasso di fecondità totale è sceso da 1,29909 a 1,24701 figli per donna, mentre il valore è diminuito in tutte le 21 unità confrontabili.
Dopo questa pagina, il lettore deve aver capito che…: una regione può avanzare in graduatoria perché il suo valore cala meno di altri, e che tasso di fecondità e numero di nascite sono grandezze diverse.
Scheda editoriale:
Domanda: salire nella classifica dei figli per donna significa migliorare?
Definizione: tasso di fecondità totale, somma dei tassi specifici per età calcolati sui nati vivi e sulle donne residenti delle età riproduttive; unità figli per donna in un anno ipotetico.
Risultato centrale: Calabria 16°→5° nel 2014-2024, mentre 1,29909→1,24701 figli per donna; tutte le 21 unità Eurostat comparabili calano.
Confronto: stessi anni, 21 unità italiane NUTS 2, stessa misura Eurostat tgs00100, senza mescolare il dato nazionale Istat.
Rilevanza: il rango da solo può dare al lettore una falsa impressione di crescita.
Spiegazione: l'avanzamento aritmetico nella graduatoria deriva da cali maggiori altrove; le cause demografiche regionali restano non determinate da questo confronto.
Limite decisivo: la fecondità di periodo non coincide con i figli effettivamente avuti da una donna, e la classifica non dimostra le cause.
Passo successivo: la scheda interna della fecondità ter-922 per chi cerca la scomposizione per età.
Variante: B
Schema del racconto: Risposta e definizione breve > Tutta la distribuzione > Perché il rango si muove > Aggiornamento separato > Limite e uscita
Angoli verificati: avanzamento relativo della Calabria mentre il suo valore cala; Valle d'Aosta passa dal 2° al 19° posto; fecondità in calo in tutte le regioni nel 2025
Definizione specifica: tasso di fecondità totale annuale, somma dei tassi di fecondità specifici per età
Unità: figli per donna
Denominatore: donne residenti della stessa età
Popolazione: donne nelle età riproduttive
Territorio: 21 unità italiane NUTS 2
Periodo: 2014 e 2024
Fonte e release: Eurostat tgs00100, dataset demo_r_frate2, release 2026-09-30
Riferimento usato: Italia ufficiale (1,14 figli per donna, Istat 2025)
Codici e confronto: tgs00100, NUTS 2, 2014-2024
Ultimo dato: 2024
Data fonte del dato: 2026-09-30
URL fonte del dato: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024
Ruolo indicatori interni: base e tassello
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Eurostat | 2026-09-30 | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024 | 42 valori NUTS 2 italiani, aggiornamento della serie e definizione del tasso | sì |
| Istat | 2026-03-31 | https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/ | stima nazionale 2025 1,14 e 2024 1,18 figli per donna; 2025 provvisorio | sì |
| OECD | 2024-06-20 | https://www.oecd.org/it/publications/2024/06/society-at-a-glance-2024-country-notes_d98f4d80/italy_6c299f2d.html | definizione e contesto del tasso, 15-49 anni, età media al parto e limiti dell'interpretazione | no (HTTP 403) |
Grafico con dati esterni: tasso di fecondità totale; 2014 e 2024; https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024
Figure previste: figura 1 (il valore è salito o sceso nei singoli territori?); figura 2 (che cosa cambia quando si guarda al rango anziché al valore?)
Limiti: misura sintetica di periodo, non numero di nati né fecondità compiuta; le possibili cause generali indicate da OECD non spiegano la singola traiettoria regionale
Registro affermazioni:
| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |
|---|---|---|---|---|
| La Calabria passa dal 16° al 5° posto fra le 21 unità osservate. | calcolo | ordinamento decrescente delle 21 celle Eurostat in 2014 e 2024 | NUTS 2 Italia, 2014 e 2024 | Eurostat tgs00100, API nella tabella fonti |
| Nella stessa serie la Calabria passa da 1,29909 a 1,24701 figli per donna. | dato | due celle geo=ITF6 | Calabria NUTS 2, 2014 e 2024 | Eurostat tgs00100, API nella tabella fonti |
| Il valore scende in tutte le 21 unità confrontate. | calcolo | 21 differenze 2024 meno 2014 inferiori a zero, 42/42 celle disponibili | NUTS 2 Italia, 2014 e 2024 | Eurostat tgs00100, API nella tabella fonti |
| L'avanzamento di rango della Calabria non significa aumento del tasso. | interpretazione | rango 16→5, differenza del valore -0,05208 figli per donna | Calabria e 21 NUTS 2, 2014-2024 | elaborazione Divario Italia da Eurostat |
| L'Istat stima 1,14 figli per donna per l'Italia nel 2025, dato provvisorio. | dato | comunicato, paragrafo «Il numero medio di figli per donna scende a 1,14» | Italia nazionale, 2025 | Istat, 2026-03-31, URL nella tabella fonti |
| Un tasso di periodo non equivale ai figli effettivamente avuti da una coorte. | limite | definizione del tasso ipotetico con tassi per età dell'anno | misura, non territorio specifico | Eurostat tgs00100; OECD 2024, URL nella tabella fonti |
| Le cause della diversa dinamica regionale non sono stabilite da questa serie. | limite | confronto descrittivo di due anni, nessun disegno causale | NUTS 2 Italia, 2014-2024 | limite metodologico del confronto |
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Misura definita | sì | definizione del tasso e denominatore precisati nel brief | l'età 15-49 è OECD, Eurostat age=TOTAL non lo esplicita |
| Confronti compatibili | sì | 21/21 NUTS 2 osservati in due anni comuni senza mescolare dato nazionale Istat | l'ultimo anno regionale Eurostat è 2024, Istat nazionale è al 2025 |
| Livello delle affermazioni | sì | spiegato l'avanzamento aritmetico, esclusa esplicitamente deduzione di cause | cause demografiche non stabilite |
| Prove e figure | sì | due figure previste che rispondono alle domande di rango e distribuzione | - |
| Fonti e freschezza | no | fonte OECD inaccessibile (HTTP 403) per il claim su età e limiti | limite non confermabile via OECD |
Motivo: La fonte OECD fornita (society-at-a-glance-2024) restituisce errore HTTP 403 al controllo di rete e non è accessibile per la verifica, mancando il criterio fonti e freschezza.
Correzione: Sostituire l'URL OECD con un collegamento accessibile.
Destinatario: leader
Data: 2026-10-09
