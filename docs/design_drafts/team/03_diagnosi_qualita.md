# Diagnosi di qualità della prosa, e rubrica per scrittore e revisore

Bozza del 28 settembre 2026, per il nuovo team editoriale. Parte da un giudizio
di Nello su `docs/design_drafts/pilot_carceri/scratch_store/bes__06POL012P.md`,
la scheda sull'affollamento delle carceri uscita dal pilota della pipeline:
"molto grezzo, davvero tanto". Il pilota l'aveva promossa. Ha passato il Gate 2
deterministico (17 frasi, zero problemi), il linter di prosa del repository
(zero tell meccanici) e una lettura avversaria che ha trovato un solo difetto,
il 105 contro 107. Nessuna di quelle prove misura quello che Nello chiede:
un italiano impeccabile nella forma e nella sostanza, un testo discorsivo che
dica al lettore che cosa rappresenta il numero, che cosa è cambiato fra i
territori e negli anni, che cosa pesa sul tema e perché i numeri sono questi.

Il documento ha quattro parti. La prima dice perché la bozza è grezza, frase
per frase. La seconda dice che cosa lo scrittore deve ricevere, e che cosa no.
La terza è la rubrica del revisore. La quarta è una dimostrazione, marcata come
tale, di lead e sezione riscritti con le sole cifre del dossier.

Non tocca `content/` né codice. È una proposta: nessuno dei criteri qui sotto
vale finché il team non lo adotta.

## 1. Perché la bozza è grezza, frase per frase

### Prima della forma, un difetto di sostanza

Il pezzo è costruito su un numero che il sito stesso considera non verificato.
In `app/seo_titles.py` l'insieme `UNVERIFIED_EXTREMES` contiene proprio
`bes-06POL012P`, con questo commento: Fermo "al 358% nel 2024 dal 116% dell'anno
prima: può essere vero, la causa non è verificata, e un titolo non è il posto per
scoprirlo". Per questo il titolo e la description della scheda non mostrano gli
estremi. La bozza fa il contrario: mette il 358,1% di Fermo nell'`angolo_scelto`,
nella prima frase del lead e nel titolo della sezione sulla dinamica, e lo
ripete tre volte. Nessuna parola avverte il lettore che il dato va preso con
cautela.

Lo scrittore non poteva saperlo, perché il dossier non glielo dice. È il primo
esempio di una regola che torna in tutta la diagnosi: **quasi ogni difetto della
bozza nasce nel brief**, come aveva già scritto la ripartenza del 4 settembre
(`git show 9730a3fc:docs/RIPARTENZA.md`, sezione 1.3, "Gli articoli sono tecnici
perché il brief è tecnico"). Il dossier del pilota è più ricco di quello di
allora, 39 fatti invece di una manciata, ma sono ancora 39 fatti statistici e
nessuna frase che dica che cosa significa il numero per una persona.

### Il lead

> "Nel 2024 l'istituto di pena più sovraffollato tra le 107 province è quello di
> Fermo, al 358,1% dei posti regolamentari."

Tre problemi in una frase. Il primo è il dato non verificato, detto sopra. Il
secondo è di sostanza: l'indicatore è provinciale, e mettere insieme
"l'istituto" e "le province" fa credere che ogni provincia abbia un carcere solo
e che la graduatoria sia di istituti. Il terzo è il 107: nel 2024 il dato c'è per
105 province, perché Macerata e Savona non hanno posti regolamentari da contare
(`app/bes_data.py`, `NOT_MEASURED`). Il lettore che prende sul serio il 107 si
aspetta 107 valori e ne trova 105.

C'è anche un difetto di mestiere. Il lead apre sull'estremo invece che sul
significato. Chi arriva sulla pagina non sa ancora che cosa voglia dire "358,1%
dei posti regolamentari", e la prima cosa che gli si chiede è di tenere a mente
una cifra che non sa leggere. `content/STYLE.md` lo dice in una riga: "Apri sul
significato, non sulla meccanica".

> "Il meno affollato è quello di Arezzo, al 35,2%, una distanza di 322,9 punti
> percentuali tra i due estremi."

La distanza fra il massimo e il minimo è un'aritmetica che al lettore non serve.
Nessuno si porta via "322,9 punti percentuali", e un'unità in punti percentuali
su un rapporto che supera il 300% è già difficile da immaginare. Arezzo al 35,2%
avrebbe invece una storia: un carcere dove i detenuti sono circa un terzo dei
posti è un fatto strano quanto il suo opposto. La frase lo presenta come un
record positivo, "il meno affollato", e passa oltre.

Il frontmatter contiene una formulazione migliore del testo: "A Fermo il carcere
ospita più di tre volte e mezzo i detenuti previsti". Una scala umana, proprio la
mossa che `content/STYLE.md` chiede ("Trasforma un numero in una scala umana").
Sta nell'`angolo_scelto`, cioè in un campo che il lettore non vede, e nella
prosa non entra mai.

### La sezione sulla definizione

> "L'indicatore rapporta il numero di persone detenute ai posti regolamentari
> disponibili negli istituti di pena."

È corretta, ed è l'unica frase del pezzo che dice che cosa si misura. Manca il
passo successivo, quello che rende leggibili tutte le cifre dopo: che 100 vuol
dire un detenuto per ogni posto, e che 129 vuol dire 129 persone dove lo spazio
è pensato per 100. Il modello di Info Data in `content/esempi/` costruisce il
rapporto davanti al lettore, numeratore, denominatore, risultato. Qui il
rapporto è nominato e lasciato lì.

> "Il confronto applica la stessa definizione in tutte le province e per ciascun
> anno, dal 2015 al 2024."

Metadiscorso. Parla del metodo del sito, non del fenomeno, e non cambia come il
lettore legge nessuna cifra. Viene dal campo `definition.scope` del dossier,
copiato quasi alla lettera.

> "Per questo indicatore il valore più basso occupa la posizione migliore, la
> graduatoria va quindi dal dato minore al maggiore."

La polarità del sito tradotta in prosa. Detta così, dà ad Arezzo al 35,2% il
titolo di "migliore", ed è un giudizio che il dato non regge: un carcere pieno a
un terzo non è per forza una buona notizia, può essere un istituto in parte
chiuso o sottoutilizzato. La soglia che conta per un lettore non è il verso
della graduatoria, è 100. Anche questa frase viene quasi intera dal dossier
(`definition.reading`).

C'è poi quello che il dossier conteneva e lo scrittore, per fortuna, non ha
usato: `definition.example`, "Un valore di 20 indica che la condizione descritta
riguarda 20 unità ogni 100 nel gruppo di riferimento". Su un rapporto che va da
35 a 358 l'esempio è sbagliato, perché non esiste una "condizione descritta" e
il valore non è una quota di un gruppo. `docs/AUDIT_VOCE.md` conta la stessa
frase su 197 schede. Un brief che la contiene prepara l'errore.

### La sezione sul quadro

> Titolo: "Poche punte spingono la media"

Il titolo promette una tesi che la sezione non dimostra. Media e mediana
distano 3,7 punti, 129,0 contro 125,3: è una distribuzione un po' spostata a
destra, non una media tirata su da poche province. Il testo non nomina nessuna
delle "punte". Un titolo che fa un'affermazione deve essere la frase che la
sezione dimostra.

> "Nel 2024 la media semplice delle province è 129,0%, già oltre i posti
> disponibili."

È la frase più importante del pezzo, ed è sepolta nel secondo blocco. Il paese,
in media, ha più detenuti che posti: è la fotografia che doveva aprire. "Media
semplice delle province" è corretto, e la regola di progetto vieta di chiamarla
media nazionale, ma per un lettore è gergo. Va detto una volta, in parole
comuni, che cosa è e perché non è il conto nazionale. "Già" non aggiunge niente.

> "Il valore mediano è più basso della media, 125,3% contro 129,0%."

Statistica descrittiva senza un perché. Il lettore non sa che cosa sia una
mediana né perché dovrebbe importargli che stia sotto la media. Eppure la
mediana, qui, dice una cosa forte, e la bozza non la vede: se la provincia che
sta a metà classifica ha 125,3 detenuti ogni 100 posti, vuol dire che **in più di
metà delle 105 province con un dato** i detenuti superano i posti. È la differenza fra leggere
una cifra e farla parlare. E la stessa cifra, 129,0%, compare quattro volte in
due sezioni.

> "Sopra la media si contano 45 province, sotto sono 60, su 107 osservate in
> tutto."

La somma non torna, 45 più 60 fa 105, ed è l'unico difetto che la lettura
avversaria del pilota aveva trovato. Il difetto più grave è un altro. Il conteggio
che interessa non è sopra o sotto la media, è sopra o sotto 100, cioè quante
province hanno più detenuti che posti. Il dossier non lo contiene, e quindi lo
scrittore non poteva scriverlo.

### La sezione sulla dinamica

> Titolo: "Un salto che sposta la media, e uno che non ha eguali"

Due affermazioni che il testo non regge. Non c'è una misura di quanto il salto
di Fermo sposti la media, e "non ha eguali" è un'enfasi da slogan su un dato non
verificato. È anche la struttura a bipolare che `content/STYLE.md` elenca fra
gli schemi da evitare.

> "Rispetto al 2023, la media semplice delle province è salita da 121,4% a
> 129,0%, un aumento di 7,6 punti percentuali."

Tre cifre per un fatto solo. "Da 121 a 129" basta, e la differenza il lettore la
vede da sé. Scrivere anche la differenza è scrivere lo stesso fatto due volte,
che `content/STYLE.md` chiede di evitare.

> "Nell'ultimo anno sono aumentate 69 province e diminuite 35, con un caso
> stabile."

Errore di italiano. Il soggetto grammaticale sono le province, e le province non
aumentano: aumenta il loro valore. Letta alla lettera, la frase dice che 69
province sono cresciute. È il tipo di errore che nessun gate vede e che un
lettore attento nota subito.

> "Il salto più netto è quello di Fermo, che passa dal 116,3% del 2023 al 358,1%
> del 2024, un aumento di 241,8 punti percentuali."

Fermo per la seconda volta, lo stesso 358,1% per la seconda volta, di nuovo
senza cautela. Manca l'unica cosa che un lettore deve sapere per leggere un
salto del genere: un rapporto sale perché crescono i detenuti o perché calano i
posti, e il dato non dice quale delle due cose sia successa. Questa non è una
causa inventata, è la meccanica del rapporto, e sta nella definizione.

> "Il calo più ampio è quello di Brindisi, con una variazione di -41,2 punti
> percentuali."

Un segno meno in prosa, e nessun livello di partenza o di arrivo: il lettore non
sa se Brindisi sia passata da 150 a 109 o da 80 a 39. Il segno meno ha una causa
precisa, che la sezione 3 tratta: il Gate 2 del pilota confronta le cifre con il
loro segno, e boccia "41 in meno" dove accetta "-41,2". La dimostrazione in
sezione 4 lo ha verificato.

> "Sull'intera serie, dal 2015 al 2024, la media semplice delle province passa da
> 108,2% a 129,0%, un aumento di 20,8 punti percentuali."

È la notizia vera del pezzo, le carceri si riempiono da anni, e arriva quinta
nella sezione, dopo Fermo e Brindisi. Ancora tre cifre per un fatto. Il fatto
che già nel 2015 la media stesse sopra 100 non viene detto.

> "Nello stesso periodo l'aumento più marcato resta quello di Fermo, 219,1 punti
> percentuali, mentre il calo più ampio è quello di La Spezia, -39,1 punti
> percentuali."

Due idee agganciate da "mentre", Fermo per la terza volta, un altro segno meno.
E un'incongruenza che il testo non spiega: se nell'ultimo anno Fermo sale di
241,8 punti e sull'intera serie di 219,1, il lettore attento si chiede come mai
il salto di un anno superi quello di dieci. La risposta è che Fermo nel 2015
stava a 139,0, più in alto che nel 2023 (`app/static/data/Assoluti_Provincia.csv`,
verificato per questo documento). Non è nel dossier e non è nel testo. "Quello
di La Spezia" è anche un italiano stentato: si dice "della Spezia".

Il CSV mostra anche due cose che il dossier nasconde. Brindisi, il "calo più
ampio", passa da 174,8 a 133,6: resta ben sopra 100, e la frase fa pensare a
un miglioramento che non c'è. E la media delle province non sale in linea retta
dal 2015. Tocca 126,4 nel 2019, scende a 110,6 nel 2020 e da lì risale. Il
dossier dà solo il primo anno, il penultimo e l'ultimo, e un testo che li mette
in fila suggerisce una salita continua che i dati smentiscono.

### La sezione sui limiti

> "La percentuale non mostra da sola quante persone siano coinvolte in valore
> assoluto."

Vero, e generico. È la frase di `definition.caveat`, identica su centinaia di
schede. Il limite specifico di questo indicatore, cioè che il rapporto si muove
anche quando cambiano i posti, non c'è.

> "Il confronto tra province descrive una differenza osservata, non ne dimostra
> le cause."

La stessa avvertenza di metodo che `docs/AUDIT_VOCE.md` trova su tutte le schede.
Non è sbagliata, ma qui prende il posto di una spiegazione che il pezzo non dà.
Il lettore esce senza sapere niente di che cosa pesa sul sovraffollamento.

> "La serie copre 107 province, non tutte hanno un dato per ogni anno."

Un limite senza numero, che il modello Openpolis in `content/esempi/` chiama "una
scusa". Il limite vero si può dire con precisione: dal 2016 Macerata e Savona non
hanno un valore, perché non hanno posti regolamentari da contare, e nel 2017 il
dato c'è per 46 province soltanto (conteggio sul CSV). E manca il limite più
grande di tutti, che il valore più alto della serie non è verificato.

### Le cause, sotto le frasi

Le frasi sono grezze per quattro ragioni che stanno a monte dello scrittore.

1. **Il brief contiene solo statistica.** 39 fatti (massimo, minimo, media,
   mediana, conteggi, delta) e nessuna riga su che cosa significhi il numero per
   una persona, su quale sia la soglia che conta, su che cosa c'è intorno al
   tema. Uno scrittore che riceve solo cifre scrive un inventario di cifre.
2. **Lo schema premia la frase che porta un fatto.** Ogni frase della bozza deve
   dichiarare i fatti che la reggono (`support`), e il Gate 2 controlla solo le
   cifre. Una frase di spiegazione, senza cifre, non guadagna niente al gate e
   rischia di sembrare un riempitivo. Il risultato è una prosa dove ogni frase è
   una riga di tabella.
3. **Il dossier passa frasi fatte che lo scrittore copia.** `definition.scope`,
   `definition.reading` e `definition.caveat` finiscono nel testo quasi alla
   lettera. Sono il telaio che `docs/AUDIT_VOCE.md` ha già misurato come
   ripetuto.
4. **Nessun modello di registro.** La proposta di pipeline prevede "un esempio
   editoriale in-repo scelto per forma narrativa simile", e il rapporto del
   pilota nomina come riferimento `content/indicators/13.md`, cioè un'altra
   scheda del sito. Negli artefatti del pilota non c'è traccia di un estratto di
   `content/esempi/`. Il README di quella cartella spiega che cosa succede senza:
   "Trenta divieti e zero esempi", e articoli che "rispettavano ogni divieto e
   non somigliavano a niente". Una scheda nostra, per quanto buona, insegna il
   nostro registro, non quello che vogliamo raggiungere.

## 2. Il brief minimo dello scrittore

Il brief è quello che lo scrittore legge prima di scrivere. Il dossier resta la
fonte delle cifre e il Gate 2 resta il controllo, ma lo scrittore non deve
partire dal dossier, deve partire da un testo corto che dica di che cosa parla
la storia. Il brief ha cinque parti, in quest'ordine.

### 2.1 Che cosa misura, per una persona normale, in una riga

Una frase, scritta da un umano o da un passaggio dedicato e rivista una volta per
indicatore, non generata a ogni run. Deve contenere la soglia che il lettore usa
per leggere il numero.

Per le carceri: "Quante persone sono detenute per ogni 100 posti che le carceri
della provincia hanno per regolamento. Sopra 100 ci sono più detenuti che posti."

La prova che la riga funziona: un lettore che la legge sa dire da solo se 129 è
tanto o poco. Con la definizione della bozza non lo sa.

### 2.2 La fotografia del paese

Tre o quattro frasi, calcolate in modo deterministico e scritte in chiaro,
senza gergo, con la cifra che serve e basta. Rispondono a tre domande. Com'è il
paese oggi, rispetto alla soglia? Da dove viene, cioè com'era all'inizio della
serie? Chi esce dal quadro, e con quale cautela?

Per le carceri, con i fatti del dossier più tre che il dossier oggi non ha:

- Nel 2024 la media delle province è 129 detenuti ogni 100 posti, e la provincia
  che sta a metà classifica ne ha 125. In più di metà delle 105 province con un
  dato i detenuti superano i posti.
- Nel 2015 la media era già 108, sopra la soglia. Nel 2023 era 121.
- Da aggiungere al dossier: **quante province stanno sopra 100**, anno per anno.
  È il conteggio che un lettore capisce, al posto di sopra e sotto la media. Sul
  CSV del sito, contato per questo documento, sono 87 su 105 nel 2024 e 68 su
  106 nel 2015.
- Da aggiungere al dossier: **la forma della serie**, non solo i suoi estremi. La
  media delle province tocca 126,4 nel 2019, scende a 110,6 nel 2020 e poi
  risale. Con il primo anno, il penultimo e l'ultimo soltanto, lo scrittore
  racconta una salita continua che non c'è stata. Il brief dice il massimo e il
  minimo della media nella serie, con l'anno, e che cosa succede fra i due.
- Da aggiungere al dossier: **il dato nazionale ponderato**, se Istat lo pubblica,
  con la sua fonte, tenuto separato dalla media delle province come chiede
  `docs/SECONDARY_SOURCES.md`.
- Da aggiungere al dossier: **l'avviso sui valori non verificati.** Fermo, 358,1
  nel 2024 da 116,3 nel 2023, è in `UNVERIFIED_EXTREMES`. Il brief lo dice in
  chiaro, e dice che cosa lo scrittore può farne: nominarlo con la sua cautela in
  una frase propria, mai aprirci il pezzo.

### 2.3 Il modello di registro, uno, con il motivo

Un estratto solo di `content/esempi/`, scelto per la forma della storia, con una
riga che dice quale movimento copiare. Mediarne più di uno, dice il README, fa
l'assenza di registro.

Per le carceri: **`ilpost-redditi-comuni.md`**. Il motivo è la forma della
storia. Quel testo ha davanti una classifica intera la cui cima è un caso da
maneggiare, Maccastorna prima per effetto di pochi contribuenti, e invece di
leggerla spiega che cosa la produce. Mette il limite che cambia la lettura nella
prima riga, e da lì il lettore sa leggere da solo ogni riga della tabella. La
scheda carceri ha lo stesso problema: una cima (Fermo) che non si può prendere
alla lettera e un fondo (Arezzo) che non è "il migliore", e il movimento da
copiare è spiegare che cosa fa muovere il rapporto prima di nominare chi sta in
cima.

L'alternativa scartata è `infodata-mortalita-comuni.md`, che costruisce il
rapporto davanti al lettore partendo dal record. È il modello giusto quando
l'estremo è la notizia. Qui l'estremo non è verificato, e aprire sul record
ripeterebbe l'errore della bozza.

### 2.4 Le dimensioni disponibili, e dove emergono differenze

Un elenco chiuso, calcolato dal catalogo, con una riga per dimensione e un sì o
un no su "emerge una differenza che vale una frase". Lo scrittore deve coprire
ogni dimensione segnata sì, o dire perché non lo fa. Una dimensione segnata no si
nomina al massimo in una frase.

Per le carceri:

- **Provincia, 2015-2024.** È il livello della scheda. Sì.
- **Regione.** Esiste un gemello regionale, `bes-06POL012` (`app/taxonomy.py`,
  `PROVINCE_ONLY_TITLE_COLLISIONS`). Il brief dice se la differenza fra regioni
  racconta qualcosa che le province non dicono, e dà il link canonico.
- **Ripartizione (Nord, Centro, Mezzogiorno).** Oggi non è nel dossier. Si
  ricava dalle province, e va calcolata dal dossier, non dallo scrittore.
- **Genere, età.** Non esistono per questo indicatore. Il brief lo scrive, così
  lo scrittore non le cerca e non le inventa.
- **Tempo.** Serie dal 2015, con il confronto sull'ultimo anno. Sì.

### 2.5 Il contesto raccolto dallo scout

Da una a tre frasi di contesto, ognuna con istituzione, data, URL aperto e
verificato, e la frase esatta della fonte che la regge. È il posto del "perché":
che cosa pesa sul tema, che cosa ha detto l'istituzione quando ha pubblicato il
dato. Senza questa parte il pezzo può solo descrivere, e la bozza lo mostra.

Per le carceri, lo scout deve sapere dove cercare, non che cosa trovare. I posti
più probabili sono i dati statistici periodici del ministero della Giustizia sui
detenuti e sulla capienza degli istituti, la relazione annuale del Garante
nazionale dei diritti delle persone private della libertà personale, e il
capitolo "Politica e istituzioni" del rapporto Bes di Istat, già nel registro
come `istat-bes`. Il ministero e il Garante oggi non sono in
`data/corpus/sources.json`: lo scout che li usa propone di aggiungerli, non li
cita da fuori registro. La domanda precisa che lo scout deve portare a casa è una
sola: che cosa è successo a Fermo fra il 2023 e il 2024, detenuti in più o posti
in meno. Se non trova una fonte primaria, la risposta è "non trovato", e il pezzo
lo dice.

Nessun URL in questa sezione è stato aperto per questo documento, a parte quello
di Istat che il dossier già porta. Sono indicazioni di ricerca, non fonti.

### 2.6 Che cosa lo scrittore NON deve ricevere

- **L'esempio generico di lettura**, "Un valore di 20 indica che la condizione
  descritta riguarda 20 unità ogni 100". Su questo indicatore è sbagliato, e su
  197 schede è identico.
- **Le frasi fatte del dossier** (`definition.scope`, `definition.reading`,
  `definition.caveat`) come testo da usare. Se servono, restano nell'apparato
  della pagina, dove già stanno.
- **La polarità come giudizio.** "Il valore più basso occupa la posizione
  migliore" diventa prosa. Il brief dà la soglia (100) e lascia il giudizio a chi
  scrive.
- **Cifre di servizio**: la distanza fra massimo e minimo (`latest.gap_abs`,
  322,90000000000003 nel dossier), la variazione percentuale di una percentuale
  (`long.avg_change_pct`, 19,2%), la copertura come frazione (0,9813), i
  conteggi sopra e sotto la media. Sono numeri corretti che non servono a nessun
  lettore, e ogni numero nel brief è un invito a scriverlo.
- **Numeri non arrotondati.** Il brief dà le cifre già nella forma in cui si
  scrivono (129,0, non 129.02). Arrotondare è una trasformazione, e le
  trasformazioni le fa il dossier.
- **Il gergo interno**: "dossier", "fatto", "support", "media semplice" senza la
  sua traduzione, i nomi dei campi. Lo scrittore li ripete, e il lettore non li
  capisce.
- **Un'`angolo_scelto` già scritto dal dossier.** L'angolo è il lavoro dello
  scrittore. Se lo decide il dossier, l'angolo è l'estremo, sempre.

## 3. La rubrica del revisore

La rubrica misura la leggibilità al primo passaggio, come chiede il README di
`content/esempi/`, e non solo i divieti. Il progetto ha già avuto una rubrica a
punti, e una prosa faticosa ci prendeva 19 su 20. Questa non dà punti. Ogni
criterio ha un esito, passa o non passa, e ogni "non passa" porta la frase
citata come prova. Un secondo modello deve poter rifare il controllo, trovare
la stessa frase e arrivare allo stesso esito.

Il revisore lavora in due passaggi. Nel primo legge **solo il testo**, senza
dossier né brief, come lo leggerebbe un lettore. Nel secondo legge il testo con
il brief e il dossier, per la fedeltà.

### 3.1 I cancelli, che restano fuori dalla rubrica

Questi non si discutono e non entrano nel giudizio di leggibilità. Se uno fallisce,
il pezzo torna indietro prima di arrivare al revisore.

- Zero caratteri vietati da `content/STYLE.md`: trattino lungo, trattino medio,
  punto e virgola, puntini di sospensione come carattere unico.
- Ogni cifra del testo corrisponde a un fatto del dossier (Gate 2).
- La media delle province non è mai chiamata media nazionale, media italiana o
  dato nazionale.
- Nessuna fonte senza URL verificato.

**Una correzione al Gate 2, trovata scrivendo la sezione 4.** Il gate confronta
le cifre con il loro segno. "Ci sono 41 detenuti in meno" non passa, "una
variazione di -41,2" sì. Il gate spinge lo scrittore a mettere il segno meno
nella prosa, che è peggior italiano. Deve confrontare i valori assoluti quando la
frase dice la direzione a parole ("in meno", "scende", "cala").

### 3.2 Primo passaggio: il testo da solo

**L1. Il test delle domande fisse.** Il revisore risponde a cinque domande usando
solo il testo, con una citazione per ogni risposta.

1. Che cosa misura l'indicatore, detto in parole comuni?
2. Com'è il paese oggi rispetto alla soglia che conta?
3. Che cosa è cambiato negli anni?
4. Quale territorio spicca, e il testo dice se il dato è affidabile?
5. Che cosa il numero non dice?

Passa se ogni risposta è giusta rispetto al brief e sta nel lead o nella prima
sezione. Le prime due devono stare nel lead. Sulla bozza carceri la risposta 2
sta nel secondo blocco, la 4 dice Fermo senza cautela, la 5 è generica: non
passa.

**L2. La parafrasi di ogni paragrafo.** Il revisore riassume ogni paragrafo in una
frase sola, senza "e" fra due affermazioni diverse. Se non ci riesce, il
paragrafo porta due idee e va spezzato. Il controllo è ripetibile: un secondo
modello riceve le parafrasi e i paragrafi, e verifica che ogni parafrasi copra
il suo paragrafo intero.

**L3. Un'idea per frase.** Per ogni frase il revisore elenca le affermazioni che
contiene. Una frase con due affermazioni non parallele non passa. Le clausole
parallele, come le quattro ripartizioni in fila del comunicato Istat in
`content/esempi/`, contano come una. Esempio dalla bozza: "Nello stesso periodo
l'aumento più marcato resta quello di Fermo, 219,1 punti percentuali, mentre il
calo più ampio è quello di La Spezia, -39,1 punti percentuali" porta due
affermazioni e non passa.

**L4. Ogni cifra ha accanto il suo perché.** Per ogni cifra il revisore scrive
in una riga perché il lettore ne ha bisogno. Se la riga non si scrive, o si
scrive solo come "completa il quadro", la cifra non passa. È la mossa che il
README degli esempi trova nel pezzo del Post sulla povertà. Soglia: al massimo
una cifra senza perché in tutto il pezzo. Sulla bozza, 322,9, 125,3, 45 e 60 non
hanno un perché.

**L5. Nessuna classifica letta ad alta voce.** Si contano le frasi che fanno solo
il nome di un territorio con il suo valore o la sua posizione, senza dire che
cosa quel posto significa. Più di due nel pezzo non passa. Sulla bozza sono
cinque frasi. Fermo è in tre, Arezzo e Brindisi in una ciascuna, e La Spezia
sta accanto a Fermo nell'ultima.

**L6. Nessun salto indietro.** Il revisore segnala ogni punto in cui per capire
una frase serve una cosa detta dopo, o in cui un pronome o un "quello" rimanda a
qualcosa di lontano. Ogni segnalazione è un "non passa" con la frase citata.

**L7. Nessuna cifra ripetuta, nessun territorio ripetuto come notizia.** La stessa
cifra compare al massimo due volte nel pezzo, lo stesso territorio al massimo
due volte come protagonista di una frase. Sulla bozza 129,0 compare quattro
volte e Fermo tre: non passa.

**L8. Il gergo è tradotto o assente.** Una lista chiusa di termini deve essere
spiegata alla prima occorrenza o non comparire: mediana, media semplice, punti
percentuali, posti regolamentari, graduatoria, valore, indicatore, e i termini
interni (dossier, fatto, serie). Il revisore cita la prima occorrenza di ciascuno
e dice se la spiegazione c'è.

**L9. L'italiano regge.** Il revisore elenca gli errori di grammatica e di senso:
concordanze, soggetti che fanno una cosa che non possono fare, preposizioni
sbagliate davanti ai nomi di luogo, segni meno in prosa. Uno solo non passa.
Esempi dalla bozza: "sono aumentate 69 province", "quello di La Spezia", "una
variazione di -41,2".

**L10. I titoli dicono quello che la sezione dimostra.** Per ogni titolo il
revisore scrive l'affermazione che contiene e cita la frase della sezione che la
dimostra. Se la frase non c'è, non passa. "Poche punte spingono la media" non
passa.

**L11. Una scala umana almeno, e mai due volte lo stesso fatto.** Almeno una delle
cifre principali è detta in una forma che si immagina ("in più di metà delle
province con un dato", "129 persone dove ce ne dovrebbero stare 100"). E nessun fatto è
detto due volte nella stessa frase, in cifra e in parole.

### 3.3 Secondo passaggio: il testo con brief e dossier

**S1. La fotografia del paese c'è.** Le frasi della fotografia del brief (2.2)
sono tutte nel testo, in forma riconoscibile. Il revisore cita dove.

**S2. Le dimensioni sono coperte.** Ogni dimensione segnata sì nel brief (2.4) è
trattata o c'è una frase che dice perché no. Nessuna dimensione segnata no è
diventata una sezione.

**S3. Il perché ha una fonte, o è la meccanica del rapporto.** Ogni frase causale
(con "perché", "per effetto di", "a causa di", "dovuto a", "spinto da") ha dietro
una frase dello scout con URL, oppure spiega come si muove il rapporto
(numeratore e denominatore). Tutto il resto non passa. La bozza carceri non ha
frasi causali, e questo passa il criterio ma fallisce L1 e S4.

**S4. Il lettore esce sapendo perché conta.** Una frase, nel lead o subito dopo,
dice la posta in gioco in parole semplici, senza inventare una causa. Il
revisore la cita. Se non c'è, non passa.

**S5. I limiti sono specifici e contati.** Ogni limite nomina un numero o un caso
(le due province senza posti, il valore non verificato). Un limite che vale per
qualunque indicatore del catalogo non conta come limite di questo.

**S6. Le cautele del brief ci sono.** Se il brief segnala un valore non
verificato, il testo lo dice in una frase propria vicino alla prima menzione, e
non ci apre il pezzo. Sulla bozza non passa.

### 3.4 Come si verifica il revisore

Il revisore restituisce un oggetto per criterio: codice, esito, frase citata,
una riga di motivo. Un secondo modello, di un'altra famiglia, riceve il testo e
il verdetto e fa tre cose. Controlla che ogni frase citata esista nel testo,
parola per parola. Rifà da zero L1 e L2, che sono i due criteri dove il giudizio
pesa di più. Segnala dove il suo esito è diverso. Il disaccordo non si risolve
a maggioranza, va all'editor umano con le due citazioni affiancate.

Il pezzo è pronto per la lettura umana quando i cancelli passano e non resta
nessun "non passa" su L1, L2, L3, L9, S4 e S6. Gli altri criteri segnalano, e
l'editor decide. La firma resta umana, come dice la proposta di pipeline.

## 4. Dimostrazione: lead e dinamica al registro giusto

> **Dimostrazione, non un testo da pubblicare.** Riscrive il lead e la sezione
> sulla dinamica della bozza carceri usando solo le cifre di
> `docs/design_drafts/pilot_carceri/dossier_v2.json`. Il modello di registro è
> `content/esempi/ilpost-redditi-comuni.md`. Lo slot marcato in fondo è dove
> andrebbe il contesto dello scout, che per questa scheda non esiste ancora.

### Il testo

Nel 2024, in più di metà delle 105 province con un dato, le carceri ospitano più
detenuti dei posti previsti dal regolamento. Vuol dire che gli spazi di un
carcere, pensati per un certo numero di persone, sono divisi fra più persone di
quelle previste. Se si fa la media dei valori provinciali, ogni 100 posti
ospitano 129 detenuti. Nel 2015 la stessa media era 108.

**Già sopra 100 nel 2015, più in alto oggi**

Nel 2015 la media delle province era già sopra 100, a 108 detenuti ogni 100
posti. Nel 2023 era a 121. Nel 2024 è salita a 129.

Un rapporto come questo si muove per due strade: cambiano i detenuti, oppure
cambiano i posti. I dati Istat danno solo il rapporto, non quale delle due cose
si sia mossa.

Nell'ultimo anno il rapporto è salito in 69 province ed è sceso in 35. In una è
rimasto fermo. La discesa più forte è quella di Brindisi, dove in un anno il
rapporto perde 41 punti.

Il caso che salta all'occhio è Fermo. Nel 2023 aveva 116 detenuti ogni 100
posti, poco sotto la media delle province. Nel 2024 ne risultano più di 358. È
il valore più alto d'Italia, raggiunto con l'aumento più forte dell'anno. Il
dato Istat non dice
se a Fermo siano arrivati più detenuti o se i posti siano diminuiti. Un salto di
questa misura in un anno solo va verificato alla fonte prima di leggerlo come
un'emergenza.

*Slot scout.* Qui va una frase con fonte primaria che dice che cosa è successo a
Fermo, se lo scout la trova. Senza fonte, il paragrafo sopra resta com'è.

*Slot brief.* Con la forma della serie nel brief (sezione 2.2), qui entrerebbero
anche il 2019 e il 2020, perché la salita non è stata continua. Il dossier del
pilota non ha quei due anni, e la dimostrazione non li usa.

### Da dove viene ogni cifra

| nel testo | fatto del dossier | valore nel dossier |
| --- | --- | --- |
| 2024 | `meta.year_max` | 2024 |
| in più di metà delle 105 province con un dato | `latest.median`, `recent.common_count` | 125,3 e 105 |
| 129 | `latest.year_avg`, `recent.current_avg` | 129,02 |
| 2015, 108 | `meta.year_min`, `long.year_min_avg` | 2015, 108,23 |
| 2023, 121 | `recent.previous_year`, `recent.previous_avg` | 2023, 121,44 |
| 69 | `recent.increase_count` | 69 |
| 35 | `recent.decrease_count` | 35 |
| in una | `recent.stable_count` | 1 |
| Brindisi, perde 41 punti | `recent.largest_decrease.*` | -41,2 |
| Fermo 116 | `recent.largest_increase.previous_value` | 116,3 |
| poco sotto la media | confronto fra 116,3 e 121,44 | |
| Fermo più di 358 | `recent.largest_increase.current_value`, `latest.max.value` | 358,1 |
| il più alto, l'aumento più forte | `latest.max.territory`, `recent.largest_increase.territory` | Fermo |

Tutte le cifre sono arrotondate all'unità, perché qui contano persone. Il 100
è la soglia della definizione, non un dato. "In più di metà delle 105 province
con un dato" è l'unica deduzione: la mediana di 105 valori è il cinquantatreesimo,
e se vale 125,3 almeno 53 province stanno sopra 100. Il 105 è il numero di
province con un dato sia nel 2023 sia nel 2024, lo stesso del 2024 da solo perché
le due province mancanti non hanno un valore in nessuno dei due anni. Il dossier
dovrebbe esporre il conteggio del 2024 direttamente.

La dimostrazione, in forma di bozza strutturata con i `support` per frase, è
stata passata al Gate 2 del pilota. **Esito del gate originale: FAIL, 1 problema
su 18 frasi.** È il 41 di Brindisi, rifiutato perché nel dossier il fatto vale
-41,2 e il testo dice la direzione a parole ("perde"). Con una copia del gate che
accetta anche il valore assoluto l'esito è PASS su 18 frasi, quindi il rifiuto
dipende solo dal segno: è il difetto descritto in 3.1, non un errore della
dimostrazione. La bozza e lo script (`run_gate.py <gate> <bozza> [--abs]`, che
carica `gate2_verify.py` e ne sostituisce solo il percorso della bozza e, con
`--abs`, il confronto) stanno nello scratchpad della sessione, fuori dal
repository.

### Che cosa è cambiato rispetto alla bozza, in breve

Il lead apre sul paese e sulla soglia, non su Fermo, e dice in una frase che
cosa vuol dire stare sopra 100 per chi sta in carcere. La mediana, che nella
bozza era una cifra senza perché, diventa "in più di metà delle 105 province con
un dato". La serie lunga, che era la quinta frase della dinamica, diventa il filo
della sezione, in ordine di tempo come nel modello di lavoce.info sulla serie
storica. La meccanica del rapporto arriva prima delle variazioni, così Brindisi e
Fermo si leggono già sapendo che un rapporto si muove anche per i posti. Fermo
compare una volta sola, con la sua cautela in frasi proprie. Le cifre sono meno
e ognuna ha accanto la ragione per cui c'è.

Quello che la dimostrazione non può fare, perché il dossier non lo contiene, è
dire quante province stanno sopra 100, confrontare le regioni e le ripartizioni,
e spiegare perché le carceri si riempiono. Sono le tre aggiunte al brief della
sezione 2, ed è lì che si decide se il prossimo pezzo sarà meno grezzo di questo.
