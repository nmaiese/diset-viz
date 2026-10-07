# Brief del leader: medici di famiglia v2 (redazione v2, prova del 7 ottobre 2026)

Autore del brief: leader (Claude Sonnet 5.5, coordinatore). Pezzo: blog, 700-1100 parole, issue #352, PR #353 (draft).
Materiale: `lavoro/medici-di-famiglia/v2/` (`numeri.md`, `fonti.md`, `insight.md` dello scout Codex GPT-6 Luna, `copertura.csv` con 81 candidati dal catalogo, 20 dossier), `calcola_incroci.py` (controlli del leader, sotto).

## Domanda del lettore
«Il mio medico di famiglia ha troppi pazienti. Vuol dire che nella mia regione è più difficile curarsi?»

## Tesi (una frase)
Nel 2023 le regioni dove più medici di famiglia superano i 1500 assistiti non sono quelle dove è più difficile curarsi, ma quelle dove i servizi si raggiungono meglio e meno persone vanno a farsi ricoverare altrove: il tetto misura come è organizzata la medicina di base, non quanta ne manca.

## L'insight non ovvio (e perché è un insight)
Lo scout ha provato tre ipotesi preregistrate (rinunce, dotazione, età, ADI, pronto soccorso): associazioni deboli o instabili, nessuna storia. Scorrendo la matrice completa dei 13 indicatori regionali è emersa invece una relazione forte, coerente in tutti gli anni 2019-2023 e che regge senza gli estremi: la quota di medici oltre soglia (bes:12SER027) è **più alta dove le famiglie dichiarano meno difficoltà a raggiungere i servizi essenziali** (bes:12SER004), **dove la fila allo sportello ASL oltre 20 minuti è meno diffusa** (ims MULTI_ASL_FILA_OLTRE_20_MIN), **dove meno anziani di 75 anni e più hanno più patologie croniche o gravi limitazioni** (bes:01SAL021) e **dove meno persone emigrano per ricovero in altra regione** (bes:12SER025). Il lettore parte da «troppi pazienti = servizio in crisi» e i dati dicono quasi il contrario.
Rho di Spearman, 20 regioni, oltre-soglia contro: difficoltà servizi 2019-2023 da -0,43 a -0,65 (2023: -0,552, senza Lombardia e Molise -0,523); fila ASL da -0,51 a -0,66 (2023 -0,547, senza estremi -0,515); multicronicità 75+ da -0,46 a -0,81 (2023 -0,524, senza estremi -0,525); emigrazione ospedaliera da -0,47 a -0,60 (2023 -0,503, senza estremi -0,318: la più fragile); uso del pronto soccorso positivo da +0,54 a +0,71 (2023 +0,423, senza estremi +0,360). Rinunce a prestazioni, medici per residente, età e ADI: legami deboli (|rho| sotto 0,25, ADI -0,48 e instabile): scartati come filo, citabili come «non è l'età, non è la dotazione di medici».
Controllo contrario scelto PRIMA di calcolare e già eseguito: tutti gli anni in comune 2019-2023 e senza i due estremi (Lombardia 74,0 e Molise 21,6). Esito: segno e ordine di grandezza stabili, tranne l'emigrazione ospedaliera che cala a -0,32 senza gli estremi (dirlo).
Meccanismo: **ignoto**. Non c'è in nessuna fonte consultata una spiegazione documentata. Si può dire solo come lettura possibile del dato (non come causa) che il tetto di 1500 è una soglia contrattuale e una quota alta può convivere con una medicina di base organizzata in studi grandi o associati: va scritta come ipotesi del lettore, mai come fatto, e solo se lo scout o il verificatore trovano una fonte (Ministero della Salute, Agenas, Istat) che descriva la differenza di organizzazione; altrimenti «i dati non lo spiegano».
Limiti da dire: 20 regioni, correlazione di rango fra misure con unità e popolazioni diverse (confronto ecologico: dice dove, non perché e non per chi), le due indagini (Istat Aspetti della vita quotidiana) sono autodichiarate, nessuna prova causale.

## Indicatori incrociati (almeno tre; qui sei)
bes:12SER027 oltre-soglia (livello regionale, 2004-2023); bes:12SER004 difficoltà a raggiungere servizi; ims:MULTI_ASL_FILA_OLTRE_20_MIN; bes:01SAL021 multicronicità 75+; bes:12SER025 emigrazione ospedaliera; ims:MULTI_PRONTO_SOCCORSO (uso). Contesto negativo (non è l'età, non è la dotazione): dem:POP65OVER, bes:SDG-3 medici per residente, bes:12SER026 rinunce, bes:12SER003 ADI.

## Come raccontarlo (racconto, non sintesi di numeri)
- Apertura: la domanda del lettore e il suo equivoco, con UN numero (74,0% in Lombardia) e subito il rovesciamento (in Lombardia le difficoltà di accesso ai servizi sono fra le più basse; nel Molise il tetto è superato solo dal 21,6% dei medici e le persone che emigrano per farsi ricoverare sono il 32,6%). Il caso di apertura sono i due territori (Lombardia e Molise, con le celle del 2023 in `numeri.md`), non persone inventate.
- Parte centrale: due regioni a confronto (Lombardia/Molise, e come terzo caso la Calabria o la Sardegna per mostrare che non è una regola del Nord e del Sud: Sardegna 60,6% oltre soglia e rinunce al 13,7%), causa e effetto SOLO dove documentati: altrimenti «i dati accompagnano, non spiegano».
- Che cosa cambia per chi legge: non usare il «tetto superato» come termometro del disagio; guardare insieme dove si arriva ai servizi, quanto si aspetta, dove si va a farsi ricoverare; che cosa il tetto non dice (quanto tempo ha il medico per ciascun paziente).
- Un risultato contrario in prosa: l'emigrazione ospedaliera è la relazione più fragile (cala senza gli estremi); il pronto soccorso segue il segno opposto.
- Budget dei numeri: non più di 3 cifre per paragrafo; le tabelle e le serie complete restano nel dataset scaricabile.
- Il fatto che la quota sia più che triplicata dal 2004 (15,8% → 51,7% in Italia, valori Istat) è contesto in una frase, non il filo.
## Da non scrivere
Cause senza fonte (carenza di camici bianchi, pensionamenti, scelte regionali): non documentate. La parola «media nazionale» per una media semplice. Persone, medici o pazienti inventati o «composti». Il Nord «scoppia»/«soffre». Frasi come «i numeri parlano». Il titolo del v1.
## Grafico (un solo, generatore standard)
Dispersione regionale 2023: asse x quota di medici oltre soglia (bes:12SER027), asse y difficoltà a raggiungere i servizi (bes:12SER004), una regione per punto, con le tre ripartizioni a colori (`figures.py scatter`: leggi `docs/WORKFLOW_ARTICOLI_TREND.md`); titolo che dice la notizia (esempio: «Dove più medici superano il tetto, meno famiglie faticano a raggiungere i servizi»). Foto di copertina: quella della v1 (CC0, ambulatorio) va bene o una nuova con licenza. Prova a 375 px e nella bozza HTML.
## Verifiche richieste al verificatore (gate B)
Ricalcolo di almeno 8 rho (anche dopo l'esclusione degli estremi) con `calcola.py` e `calcola_incroci.py`; ogni frase che attribuisce un perché; la definizione dei sei indicatori (`data/definitions/federated.csv`, `istat_territoriali.csv`); i valori Lombardia/Molise/Sardegna/Calabria 2023.
