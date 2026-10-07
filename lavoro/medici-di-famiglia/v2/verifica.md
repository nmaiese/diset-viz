# Verifica indipendente, Gate B: medici di famiglia v2

Bozza esaminata: `content/posts/2026-10-07-medici-di-famiglia-regioni.md`, commit `4c01ebaeaef4ca3f2ab6db87273e62888efb1728`, SHA-256 `34105d7ec7e443bbcd75f88af1d8d6cb770d505b3cfe044339bfed57b66b4b79`. La spec nomina anche `lavoro/medici-di-famiglia/bozza.md` nella riga di esempio per l'hash, ma quel file non esiste: ho usato il percorso della bozza indicato esplicitamente nella stessa spec. Ho letto brief v3, gate A ter, numeri, fonti, autore, SVG e le due rese PNG. Non ho preso i calcoli dell'autore per buoni.

## Ricalcolo dai CSV regionali

Ho letto direttamente `app/static/data/Assoluti_BES_Regione.csv` e `app/static/data/Assoluti_Multiscopo_Regione.csv` con separatore `;`, `Area=Regione`, `Livello/Variazione=Livello`, `Anno=2023`. Virgole decimali convertite in punti. Per ogni serie: 20 regioni, Trentino-Alto Adige aggregato. Spearman calcolato dai ranghi medi in caso di parità, come covarianza dei ranghi divisa per il prodotto delle deviazioni standard. Nessun peso regionale. Questo ricalcolo non usa `calcola.py`, `calcola_incroci.py` né il CSV dell'articolo.

| Cella nel testo | Valore ricalcolato | Riga bozza | Esito |
| --- | ---: | ---: | --- |
| Medici oltre soglia, Lombardia | 74,0% | 112 | corretto |
| Medici oltre soglia, Molise | 21,6% | 112 | corretto |
| Dimissioni fuori regione, Molise | 32,6% | 116 | corretto, massimo regionale |
| Dimissioni fuori regione, Lombardia | 5,1% | 116 | corretto, minimo regionale |
| Utenti ASL in fila oltre 20 minuti, Lombardia e Molise | 47,1% e 67,6% | 118 | corretti |
| Medici oltre soglia, Sardegna | 60,6% | 134 | corretto |
| Dimissioni fuori regione, Sardegna | 7,1% | 134 | corretto |
| Rinunce a visite/esami, Sardegna | 13,7% | 136 | corretto, massimo regionale; circa una su sette |
| Uso pronto soccorso, Lombardia e Molise | 64,8 e 39,8 per mille | 142 | corretti |

| Coppia con medici oltre soglia | N=20, rho | N=18 senza Lombardia e Molise, rho | Testo |
| --- | ---: | ---: | --- |
| Dimissioni fuori regione | -0,503197 | -0,318018 | -0,50 e -0,32, corretto |
| Fila ASL oltre 20 minuti | -0,547368 | -0,514964 | -0,55 e -0,51, corretto |
| Uso pronto soccorso | +0,422556 | +0,360165 | +0,42 e +0,36, corretto |
| Rinunce a visite/esami, controllo ulteriore | -0,217375 | -0,161074 | «nessun ordinamento comune evidente», prudente |

Il 15,8% Italia 2004 e il 51,7% Italia 2023 coincidono con `data/derived/bes_areas_12SER027.csv`; il rapporto 51,7/15,8 = 3,27, quindi «più che triplicata» è corretto. Sono valori nazionali della serie derivata, non medie semplici delle 20 regioni. La matrice di 13 indicatori in `numeri.md` implica 13×12/2 = 78 coppie; non ho ricostruito tutte le 78 coppie dai CSV.

## Definizioni e limiti obbligatori del Gate A ter

Le definizioni in `data/definitions/federated.csv` confermano che 12SER027 è percentuale di medici oltre 1500 assistiti, 12SER025 è percentuale di dimissioni ordinarie per acuti dei residenti fuori regione e 12SER026 è percentuale di persone che dichiarano una rinuncia negli ultimi 12 mesi per motivi aggregati. Il CSV Multiscopo usa `%` per fila ASL e persone per mille per pronto soccorso. Popolazioni e denominatori differiscono.

1. **Quote, mai conteggi: non rispettato integralmente.** Riga 148: «La quota di medici oltre soglia conta quante liste sono lunghe» tratta una percentuale come numero di liste. L'SVG, invece, dice «quota di dimissioni» nel titolo. Correzione: «indica la percentuale di medici con più di 1500 assistiti».
2. **Denominatori e definizioni: rispettato.** Riga 116 distingue dimissioni da persone e ricoveri acuti; riga 118 distingue quota di utenti, durata e liste cliniche; riga 136 dice «circa una persona su sette». Quest'ultima frase ripete lo stesso numero come rapporto e percentuale: sceglierne uno.
3. **Esplorazione: rispettato.** Riga 124 dichiara 78 coppie, scelta dopo la matrice, cronologia non provata e anni non indipendenti. Nessuna pretesa di significatività o causa.
4. **Controlli contrari: rispettato.** Righe 130 e 142 riportano -0,32 senza estremi e pronto soccorso di segno opposto (+0,42). L'indicatore 12SER004 non è promosso a prova centrale.
5. **Limite del singolo dato: rispettato con una frase da stringere.** Righe 148 e 152 dicono che da solo non basta a giudicare come ci si cura. Riga 134 «Non è dunque una questione di Nord e Sud» deduce troppo da un controesempio: «non si riduce alla sola distinzione Nord-Sud» sarebbe più fedele.

Le frasi che chiedono o suggeriscono un perché sono alle righe 112, 116, 120, 136 e 144. Le righe 116, 120, 136 e 144 negano esplicitamente una causa osservata. La riga 112 mette la lettura intuitiva al condizionale e la ribalta subito, ma conviene indicare che è un'ipotesi del lettore, non una spiegazione. Nessuna persona nominata; la riga 110, però, presenta come fatto che **il medico del lettore** superi 1500 assistiti. La quota regionale non permette quell'affermazione individuale. Va trasformata in ipotesi esplicita («Se il tuo medico...»).

## T, R, L, N e racconto

- **T sì:** «Da solo no» (riga 110), seguito da confronto tra quota di medici, dimissioni e fila. Prove regionali sostengono il limite del singolo indicatore, senza misurare la qualità della cura.
- **R sì:** Molise 32,6% contro Lombardia 5,1% (riga 116) rovescia la lettura proposta dalla sola classifica alla riga 112. Il confronto muove il racconto.
- **L sì:** «Questo numero dice quanto è difficile curarsi nella tua regione? Da solo no» (riga 110) porta la conseguenza per il lettore nei primi due paragrafi. La premessa individuale della stessa riga resta da correggere.
- **N sì:** «È anche fragile» con -0,32 (riga 130), e «L'uso del pronto soccorso va nell'altro verso» (riga 142). Risultato non ovvio e controlli contrari sono riconoscibili.

Il pezzo ha un filo leggibile, non è solo un elenco di coefficienti: apre con una domanda pratica, passa per Lombardia/Molise, poi Sardegna e un controllo contrario. La sezione da riga 122 a 130 accumula comunque metodo e coefficienti; si può alleggerire dopo aver preservato l'avvertenza esplorativa. Riga 126 «Dove più medici superano..., la quota ... è più bassa» suona come regola per ogni regione, mentre rho -0,50 è un ordinamento moderato con eccezioni visibili. Scrivere «tende a essere più bassa» e spiegare la fragilità lì, vicino all'affermazione. Stessa correzione nel titolo del grafico. Riga 150 «dove i residenti vanno a farsi ricoverare» va resa come quota di dimissioni fuori regione, per non passare dai ricoveri alle persone.

## Grafico visto nelle rese fornite

- **375 px:** titolo e sottotitolo leggibili, assi con unità `%`, fonte e nota sui due estremi presenti. Le etichette di Campania, Trentino Alto Adige, Friuli-Venezia Giulia, Lazio, Piemonte, Emilia-Romagna, Sardegna, Veneto e Lombardia si incrociano o toccano i punti: gruppo basso destro non si legge in modo affidabile. Asse orizzontale molto piccolo. Questo è bloccante visivo.
- **1100 px:** figura resta larga circa 680 px. Assi, colori e distinzione cerchi/quadrati si vedono; Campania/Trentino Alto Adige e il gruppo Lazio/Friuli/Sardegna/Veneto restano troppo vicini. Nomi delle regioni principali si vedono meglio, ma il groviglio non è risolto.
- **Cautela:** sottotitolo riporta -0,50 su 20 regioni e -0,32 senza Lombardia/Molise. Il titolo afferma la direzione senza «tende», più forte del dato. Colore arancione indica le regioni evidenziate, non una misura; forme separano Centro-Nord e Mezzogiorno. Serve ridurre etichette o riposizionarle, lasciando le venti regioni nella tabella e mantenendo in evidenza almeno Lombardia, Molise e Sardegna.

## Link e limiti della verifica

Il 7 ottobre 2026 `curl -L` ha ottenuto HTTP 200 per [appendice Istat](https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip), [Data Browser Istat](https://esploradati.istat.it/databrowser/#/it), [pagina Wikimedia della foto](https://commons.wikimedia.org/wiki/File:Ambulatorio_medico_Albonese_01.jpg) e i sei link interni alle tre schede e a Lombardia, Molise e Sardegna. La pagina Wikimedia mostra Fabiocrotti67 e CC0 1.0. HTTP 200 verifica raggiungibilità, non contenuto di ogni pagina o riconciliazione delle celle con lo ZIP primario. Il Data Browser richiede JavaScript; lo ZIP non è stato aperto. Non ho verificato microdati/pesi dell'indagine, incertezza campionaria, motivi dei ricoveri, motivi individuali della rinuncia, cronologia dei controlli né HTML completo del post.

Il CSV scaricabile dell'articolo contiene venti regioni e Italia, ma non la serie del pronto soccorso usata come controllo contrario: la promessa «I dati dell'articolo si scaricano in CSV» (riga 154) è incompleta. La guardia articolo non è partita: il Python del repository, puntato alla venv principale via `DIVARIO_PYTHON`, manca di `PIL`; nessun file di ambiente è stato modificato. Il giudizio qui si fonda su ricalcolo, definizioni e ispezione visiva delle due immagini fornite.
