# Gate A: test-pipeline-fecondita-20261009
Contratto: v4.1
Tipo pezzo: blog
Esito: FERMO
SHA brief: fe928155a49893edc5b9ce19e4efbf4605407bc6
Hash brief: 0bcbb6c6101ed6284a61370a2be1ddf8e0b0caa8716f2647c94ab0e34a1cfcfb
Autore/modello: C-DIV, Codex gpt-6-sol
Giudice/modello: Antigravity Gemini 3.1 Pro (High)
Domanda: se una regione risale nella classifica della fecondità, significa che lì nascono più figli per donna?
Risposta in una frase: no: tra 2014 e 2024 la Calabria passa dal 16° al 5° posto fra 21 unità italiane NUTS 2 della serie Eurostat, ma il suo tasso scende da 1,29909 a 1,24701 figli per donna.
Dopo questa pagina, il lettore deve aver capito che…: una regione può avanzare in graduatoria perché il suo valore cala meno di altri, e il tasso di fecondità non è il numero di nascite.
Scheda editoriale:
Domanda: salire nella classifica dei figli per donna significa migliorare?
Definizione: tasso di fecondità totale, somma dei tassi specifici per età calcolati sui nati vivi e sulle donne residenti delle età riproduttive; unità figli per donna in un anno ipotetico.
Risultato centrale: Calabria 16°→5° nel 2014-2024, mentre 1,29909→1,24701 figli per donna; tutte le 21 unità Eurostat comparabili calano.
Confronto: stessi anni, 21 unità italiane NUTS 2, stessa misura Eurostat `tgs00100`, senza mescolare il dato nazionale Istat.
Rilevanza: il rango da solo può dare al lettore una falsa impressione di crescita.
Spiegazione: l'avanzamento aritmetico nella graduatoria deriva da cali maggiori altrove; le cause demografiche regionali restano non determinate da questo confronto.
Limite decisivo: il tasso annuale non conta i bambini nati e non predice i figli effettivi di una coorte di donne.
Passo successivo: per spiegare cause e numero di nascite servono popolazione femminile per età, nascite per età e analisi causali dedicate.
Variante: B cambiamento nel tempo
Schema del racconto: Risposta e definizione breve > Tutta la distribuzione > Perché il rango si muove > Aggiornamento separato > Limite e uscita
Angoli verificati: avanzamento relativo della Calabria mentre il suo valore cala; perdita di posizione della Valle d'Aosta mentre il suo valore cala
Definizione specifica: tasso di fecondità totale annuale, somma dei tassi specifici per età che dividono i nati vivi di madri residenti di una data età per le donne residenti della stessa età.
Unità: figli per donna
Denominatore: donne residenti della stessa età per ciascun tasso specifico
Popolazione: donne nelle età riproduttive, con intervallo esatto non dichiarato nell'output `tgs00100`
Territorio: 21 unità italiane NUTS 2, 19 regioni e due province autonome
Periodo: 2014 e 2024
Fonte e release: Eurostat `tgs00100` / `demo_r_frate2`, aggiornamento 2026-09-30T23:00:00+0200
Riferimento usato: nessuno nel confronto Eurostat; stima ufficiale Istat 2025 separata
Codici e confronto: `tgs00100`, NUTS 2 Italia, 2014 e 2024; `ter-922` solo link contestuale dopo verifica URL
Ultimo dato: 2024 per le unità regionali Eurostat; Istat nazionale provvisorio 2025 separato
Data fonte del dato: 2026-09-30
URL fonte del dato: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024
Ruolo indicatori interni: base e tassello, senza confronti numerici fra la serie interna e quella Eurostat
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Eurostat | 2026-09-30 | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024 | 42 valori NUTS 2 italiani, aggiornamento della serie e definizione del tasso | sì |
| Istat | 2026-03-31 | https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/ | stima nazionale 2025 1,14 e 2024 1,18 figli per donna; 2025 provvisorio | sì |
| WHO | 2021-08-01 | https://cdn.who.int/media/docs/default-source/gho-documents/health-equity/health-equity-assessment-toolkit/heat-plus/heat-plus-data-repository/indicator-compendium.pdf?sfvrsn=65bb6f_5 | pagina 31: tasso di periodo come media di coorte ipotetica, somma dei tassi per età, esempio 15-49 anni | sì |
Grafico con dati esterni: tasso di fecondità totale; 2014 e 2024; https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tgs00100?lang=en&time=2014&time=2024
Figure previste: andamento 2014→2024 dei 21 valori per verificare il calo; rango e valore della Calabria e dei confronti rappresentativi
Limiti: tasso di periodo, non numero di nati né fecondità compiuta; cause regionali non identificabili; serie Eurostat 2024 distinta dalla stima nazionale Istat 2025
Registro affermazioni:
| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |
|---|---|---|---|---|
| La Calabria passa dal 16° al 5° posto fra le 21 unità osservate. | calcolo | ordinamento decrescente delle 21 celle Eurostat in 2014 e 2024 | NUTS 2 Italia, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| Nella stessa serie la Calabria passa da 1,29909 a 1,24701 figli per donna. | dato | due celle `geo=ITF6` | Calabria NUTS 2, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| Il valore scende in tutte le 21 unità confrontate. | calcolo | 21 differenze 2024 meno 2014 inferiori a zero, 42/42 celle disponibili | NUTS 2 Italia, 2014 e 2024 | Eurostat `tgs00100`, API nella tabella fonti |
| L'avanzamento di rango della Calabria non significa aumento del tasso. | interpretazione | rango 16→5, differenza del valore -0,05208 figli per donna | Calabria e 21 NUTS 2, 2014-2024 | elaborazione Divario Italia da Eurostat |
| L'Istat stima 1,14 figli per donna per l'Italia nel 2025, dato provvisorio. | dato | comunicato, paragrafo «Il numero medio di figli per donna scende a 1,14» | Italia nazionale, 2025 | Istat, 2026-03-31, URL nella tabella fonti |
| Un tasso di periodo non equivale ai figli effettivamente avuti da una coorte. | limite | definizione del tasso ipotetico con tassi per età dell'anno | misura, non territorio specifico | Eurostat `tgs00100`; WHO 2021, URL nella tabella fonti |
| Le cause della diversa dinamica regionale non sono stabilite da questa serie. | limite | confronto descrittivo di due anni, nessun disegno causale | NUTS 2 Italia, 2014-2024 | limite metodologico del confronto |
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Misura definita | sì | il tasso è definito correttamente nel brief | età 15-49 non dichiarata da Eurostat |
| Confronti compatibili | no | la serie 2024 non è l'ultimo dato utile per il livello subnazionale | il perimetro Istat al 2025 esiste già nell'articolo |
| Livello delle affermazioni | sì | non inferite cause dalla statistica | cause demografiche non stabilite |
| Prove e figure | sì | i grafici verificano le dichiarazioni su rango e andamento | limite metodologico |
| Fonti e freschezza | no | la fonte NUTS 2 al 2024 è meno fresca del perimetro Istat al 2025 | non sfrutta i dati completi Istat |
Motivo: La proposta utilizza dati Eurostat NUTS 2 aggiornati solo al 2024, rinunciando alla freschezza del perimetro Istat regionale al 2025 già pubblicato e validato nell'articolo esistente. Pur chiarendo metodologicamente che non si confrontano i 21 Eurostat 2024 con l'Italia Istat 2025, la perdita di risoluzione temporale non migliora la pagina e non giustifica la revisione.
Correzione: Mantenere l'articolo esistente con la serie Istat 2010-2025.
Destinatario: leader
Data: 2026-10-09
