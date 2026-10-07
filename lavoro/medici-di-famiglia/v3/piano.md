# Medici v3: passi successivi, senza pubblicazione

Data: 2026-10-07. Autore: Codex GPT-6 Astra. La consegna corrente termina con scelta, brief, questo piano e commit locale dei tre file. Il nuovo Gate A, l'articolo e la bozza HTML non sono stati prodotti. Nessun lancio di altri agenti in questo incarico.

## 1. Data della scheda AGENAS: prova primaria recuperata

Integrazione C-DIV 2026-10-07: il [feed Atom ufficiale AGENAS](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=atom) riporta published 2026-04-15T12:58:07+02:00 per la scheda che collega il Terzo rapporto; il [feed RSS](https://www.agenas.gov.it/i-quaderni-di-monitor-%E2%80%93-supplementi-alla-rivista?format=feed&type=rss) conferma pubDate e link/GUID. La pagina ufficiale riporta ultima modifica 2026-04-16; il PDF non indica un giorno proprio. Non confondere questi campi. Aggiornati scelta, fonti e brief; serve secondo Gate A indipendente sul nuovo SHA/hash prima dello scrittore.

Per il rapporto SDO 2024 il titolare ha segnalato la [pagina ministeriale dei rapporti annuali](https://www.salute.gov.it/new/it/tema/assistenza-ospedaliera/rapporti-annuali-sui-ricoveri-ospedalieri/) con aggiornamento 2026-06-24. Da questo worker l'URL restituisce la pagina Gcore, anche con HTTP 200, non il contenuto. La copia ISS del PDF è invece aperta e letta. Registrare l'aggiornamento come tale quando verificabile, senza promuoverlo automaticamente a data di pubblicazione. Questa verifica non data il rapporto AGENAS.

Se il giudice ritiene insufficiente la data pubblicata della scheda come data della fonte che collega il PDF, mantenere il brief FERMO. Una rifocalizzazione su sole fonti integralmente datate richiede un brief diverso, con tesi sostenuta senza la fonte esclusa e tre istituzioni pertinenti, non la semplice rimozione della riga scomoda. Niente richiesta allo scrittore di colmare lacune.

## 2. Nuovo Gate A indipendente

Il coordinatore assegna la verifica a un giudice che non abbia scritto questo brief, nel rispetto della separazione di famiglie rispetto allo scrittore previsto Claude. Si usa il contratto `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v3.md` e il formato esatto di `lavoro/medici-di-famiglia/gate-a.md`, non il vecchio gate v2. La versione v3 invalida il precedente giudizio anche a parità di hash.

Il report deve fissare SHA del commit e SHA256 del brief corrente, autore e giudice, tipo blog, domanda, almeno due angoli verificati, tesi, codici/livello/periodo, ultimo dato, data e URL della fonte, ruolo base degli indicatori, tabella delle tre istituzioni e grafico esterno. I cinque criteri ricevono prove specifiche e limiti, senza aggiungere soglie inventate. Un solo «no», compresa una data mancante, impedisce PASSA. Il presente caporedattore non si attribuisce quel giudizio.

Controlli centrali: rileggere le sei celle GIMBE del grafico, distinguere valore economico e ricoveri, mobilità attiva e passiva, totale ed effettiva. Non presentare il 54,5% GIMBE come quota del totale largo di 5,15 miliardi. Non interpretare il 2023 GIMBE e il 2024 AGENAS come variazione annuale. Verificare che il confronto per settore aggiunga una tesi al pezzo Divario già esistente. Conservare Toscana come controllo contrario. Qualunque modifica sostanziale al brief richiede aggiornamento di SHA/hash e nuova valutazione, secondo i limiti di ritorno previsti dal PIANO.

## 3. Solo dopo PASSA: autore e figure

Lo scrittore riceve brief verificato, fonti ammesse, dossier pertinente, `content/STYLE.md` e un solo modello di voce. Produce una bozza nuova, `draft: true`, senza riutilizzare la v2.1 come prova o forma obbligata. L'attacco spiega al lettore chi eroga le cure pagate dal SSN. Non ripete una graduatoria di emigrazione. Il brief resta l'unico input numerico ammesso.

Il grafico nasce dalle sei celle della tabella in `brief.md`, con dati esterni, unità e anno visibili, generatore del progetto o script dedicato conforme. Verificare trascrizione, scala comune e denominatore in didascalia. Se si recupera una tabella equivalente 2024, prima ricontrollare interamente perimetro e controesempio, poi aggiornare brief e gate. Non limitarsi a cambiare l'anno del grafico. La copertina segue la skill: foto reale con licenza compatibile, fonte e credito verificati.

Rileggere il catalogo per il percorso canonico di `bes:12SER025` e le chiavi dei territori. Nessuna modifica ai dataset necessaria per questo angolo. Non estendere al provinciale una prova soltanto regionale. Tenere separato il vecchio post: questo piano non ne autorizza correzioni.

## 4. Bozza HTML v3 e review

Con articolo e figure pronti, usare il generatore standard `bin/py -m scripts.editoriale.bozza_html` secondo `docs/WORKFLOW_ARTICOLI_TREND.md`, con i parametri reali del successivo incarico. L'HTML v3 deve apparire nell'indice delle bozze ed essere aperto e letto. Verificare figure, didascalie, link, mobile e desktop, temi chiaro e scuro, assenza di overflow. Una risposta HTTP 200 non basta a provare la resa.

Revisore di famiglia diversa dallo scrittore. Claim table con frase, fonte, periodo, territorio, unità, trasformazione e limite. Controlli Gate B invariati: T tesi sostenuta, R confronto territoriale utile, L significato concreto nei primi due paragrafi, N risultato non ovvio e controllo contrario. Niente persone inventate, cause o flussi individuali dedotti da medie. PASSA solo con almeno 4, zero bloccanti e HTML letto sullo SHA corrente. Massimo due giri, poi FERMO alla direzione se restano bloccanti.

Eseguire le verifiche editoriali e tecniche pertinenti alla futura bozza, registrandone comando ed esito. Guardie verdi non certificano date, causalità o senso delle percentuali. Nessuna pubblicazione prevista da questo piano: eventuali passaggi successivi appartengono alla direzione.

## Verifica della consegna corrente

Controllo documentale eseguito: 11 URL aperti con contenuto, due URL ministeriali bloccati da Gcore e dichiarati tali. Fonti centrali AGENAS/GIMBE/Istat lette, date qualificate, sei valori del grafico uguali in PDF, brief e scout, differenze ricalcolate, tre celle Divario e ultimo anno regionale 2024 verificati. Fonte SDO riconosciuta come copia ISS. `git diff --check` e `git diff --cached --check` senza errori, staging limitato ai tre file nuovi. Il CSV altrui `data/derived/casa_titolo_godimento.csv` conserva SHA256 `1b77162bc1205e5c2f9c4fbd7ab2061223fbcbd05f74465783ad9e08a67ffdeb`. Nessun test applicativo eseguito per questa consegna documentale. Questi controlli non equivalgono a Gate A PASSA.
