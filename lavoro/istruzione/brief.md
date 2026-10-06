# Brief per lo scrittore: istruzione per regione (materiale, non scaletta)

## Domanda (query vere, Search Console 28 giorni al 3/10)
"livello di istruzione in italia per regione" (18 impressioni, posizione 2,3), "livello di istruzione più elevato" (27), "livello di istruzione in italia" (9). Chi cerca vuole sapere dove ci sono piu o meno persone istruite. La nostra scheda `ter-104` misura il contrario: la quota di adulti 25-64 anni con AL PIU la licenza media (meno e meglio). L'articolo deve dirlo con parole comuni nel primo paragrafo, senza far credere che sia la quota di laureati.

## Tesi (una frase, verificabile)
In sei anni la quota di adulti fermi alla licenza media e scesa in tutte le venti regioni, ma il Mezzogiorno ha ancora 1,27 volte la quota del Nord, esattamente come nel 2018: il divario in punti si e ridotto da 9,3 a 8,0, quello in proporzione no.

## Dati verificati (ricalcolati dal CSV `Assoluti_Regione.csv`, idIndicatore 104, e confermati da una seconda persona; fonte Istat, Banca dati territoriale, ultimo anno 2024)
- Media SEMPLICE delle 20 regioni (non e la media nazionale, dirlo): 38,1% nel 2018, 33,0% nel 2024.
- Estremi 2024: Sicilia 44,1%, Sardegna 43,7%, Puglia 43,2%; in basso Umbria 24,3%, Lazio 25,2%, Friuli-Venezia Giulia 25,4%. Distanza 19,8 punti, rapporto 1,8 volte.
- Ripartizioni (media semplice delle regioni): Nord 34,7% nel 2018 e 30,2% nel 2024; Centro 33,2% e 28,0%; Mezzogiorno (Sud e Isole, 8 regioni, Abruzzo compreso) 44,0% e 38,2%. Distanza Mezzogiorno meno Nord: 9,3 punti nel 2018, 8,0 nel 2024. Rapporto Mezzogiorno/Nord: 1,268 e 1,266.
- Nessuna regione e peggiorata. Piu migliorate (punti): Umbria -7,5, Calabria -7,2, Molise -6,9. Meno: Valle d'Aosta -2,1, Toscana -2,5, Emilia-Romagna -3,6.
- Correlazione di rango sulle venti regioni, 2024: con il PIL pro capite -0,60, con il reddito disponibile -0,56, con il tasso di occupazione -0,55. Dirla in parole semplici ("sulle venti regioni, lineare" no: e di rango; "i due ordinamenti vanno in senso opposto, ma con molte eccezioni").
- Il Trentino-Alto Adige e per noi una regione sola (27,1%, 17o posto); l'Istat dà le due province separate: Bolzano 31,3% e Trento 22,9% nel 2024 (file Istat, `fonti.md` riga 1). Se si citano Bolzano o Trento, con quella fonte e quell'anno.
- La Valle d'Aosta e sesta (37,0%), unica regione del Nord fra le meridionali; popolazione piccola, stima piu incerta; nessuna fonte spiega il valore: non attribuirlo a una causa.
- Contesto esterno (da `fonti.md`, citare solo cosi): Eurostat 2025, Italia 33,0% contro UE 18,8% (rapporto circa 1,8, ed e nazionale: non dire "il doppio" del Sud sul Nord); Istat Noi Italia: Mezzogiorno 41,3% e Centro-Nord 29,6% (rapporto circa 1,4); Istat report 2024 sui livelli di istruzione.

## Fonti ammesse e cosa dicono per la CAUSA
`fonti.md` (22 URL aperti, 6 "non trovato"). Nessuna fonte propone una causa unica del divario regionale: sono associazioni e contesto (famiglia di origine, abbandono scolastico, migrazione dei laureati dal Sud, occupazione). Si scrivono come associazioni con la fonte e l'anno, mai come causa. Frase sua: "i dati mostrano dove, non perche".

## Cose da NON scrivere
- Che la quota "al piu licenza media" sia l'opposto della quota di laureati (indicatori diversi).
- "Il Sud ha il doppio degli adulti poco istruiti" (il rapporto Mezzogiorno/Nord e 1,27 con i nostri dati, circa 1,4 per Istat; il doppio e il confronto Italia-UE).
- Una media semplice chiamata media nazionale; "miglioramento" o "trend" senza dire che la serie nazionale ha un salto di circa 2,5 punti fra 2022 e 2023 senza spiegazione trovata (rottura di serie Eurostat nel 2018 e 2021).
- Il dato 2025 per le regioni (non esiste; il 2025 e solo nazionale Eurostat).
- Cause senza fonte. Giudizi ("bene", "male", "preoccupante"). Un confronto regione-UE (non c'e il dato regionale Eurostat equivalente).
- Aperture da manuale: "Chi cerca...", definizioni lunghe, termini tecnici (ISCED, secondario inferiore, tasso) nei primi due paragrafi.

## Lezioni dei pezzi precedenti (skill `redazione-divario` sezione 3 e 4)
Apertura = un messaggio in parole comuni, un numero per frase. H2 narrative e diverse, nessuno schema fisso. Esempi con due regioni a confronto (Sicilia contro Umbria; Calabria contro Veneto sulle migliorate...). Un titolo con la tesi. Il 2018-2024 come arco, i valori veri.

## Forma
Tetto proposto 1100 parole di corpo (dati breve), obiettivo 900-1000. File `content/posts/2026-10-07-livello-istruzione-regioni-licenza-media.md` con frontmatter come i pilota (vedi `content/posts/2026-10-05-reddito-pro-capite-regioni-non-e-il-pil.md`: `dataset` con `download`, `external_figures`, `cover_*`), un CSV scaricabile in `app/static/data/articles/` creato DA UNO SCRIPT dal CSV sorgente (regione, ripartizione, 2018, 2024, variazione). Marcatori di figura per due grafici (il lavoro del grafico e di un altro ruolo): (1) classifica delle 20 regioni 2024 colorata per ripartizione; (2) 2018 e 2024 per ripartizione (Nord, Centro, Mezzogiorno) che mostri che il rapporto non cambia. Copertina: foto reale (vedi `fonti.md`, voce 23); il lavoro della foto e di un altro ruolo, lascia il campo `cover_*` come nei pilota con segnaposto dichiarato.
