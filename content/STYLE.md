# Guida di stile per gli articoli di Divario Italia

Questa guida vale per ogni articolo in `content/posts/`. Serve a tenere i testi
coerenti e a farli sembrare scritti da una persona, non da un bot. Vale sia per
chi scrive a mano sia per gli agenti AI (Claude, Codex) che pubblicano in
automatico.

## Regole tipografiche (vincolanti)

1. **Mai il trattino lungo `—` (em-dash) né il trattino medio `–` (en-dash)** nel
   testo. Per gli incisi usa le virgole o due frasi separate. Per gli intervalli
   scrivi "dal 1981 al 2024", oppure usa il trattino normale `-` solo dentro le
   tabelle (`1981-2024`).
2. **Mai il punto e virgola `;`**. Spezza in due frasi oppure usa la virgola.
3. **Mai i puntini di sospensione come carattere unico `…`**. Se proprio servono,
   scrivi tre punti normali `...`.
4. Non scrivere `--`, `---` o sequenze pensando che diventino trattini o ellissi:
   l'engine non li converte (l'estensione `smarty` è disattivata di proposito) e
   comunque non li vogliamo.
5. Usa virgolette dritte normali (`"` e `'`).

## La skill scrittura-italiana, e chi vince sul conflitto

Per il mestiere della lingua (togliere i tic dell'italiano generato, dare voce,
regolare ritmo e retorica) il progetto adotta la skill esterna
**`scrittura-italiana`** (`motore:scrittura-italiana`, nel plugin `motore` di platform, CC BY-SA 4.0).
Questa guida la **cita**, non la ricopia: le quattro virtù retoriche, le cinque
varianti del bipolare, l'antilingua e il lessico di plastica vivono nei suoi
`references/`, e ripeterli qui li manderebbe fuori sincrono.

**La precedenza è esplicita, e non è negoziabile: su ogni conflitto vincono
gli assoluti di progetto.** La skill lavora nel registro *testo controllato* e
lì consiglia i caporali `« »`, le lineette spaziate e il punto e virgola. Le
regole tipografiche qui sopra li **vietano**: niente `—`, `–`, `;`, `…`,
virgolette dritte. Quando la skill suggerisce una di quelle forme, si tiene la
regola di progetto e si scioglie l'inciso con virgole o due frasi. Il conflitto
è sistematico, non un caso di bordo: sta nel registro esatto in cui vivono le
nostre pagine. Il cancello deterministico che lo fa rispettare è `lab/lint.py`
(i caratteri vietati dallo stile) e, nel contatore della skill, il campo
`vietati` sempre vuoto.

**La precedenza non riguarda solo i caratteri.** La skill consiglia anche di
variare il ritmo, e qui la varietà è lecita ma non è il metro: il metro è che
la frase si prenda al primo passaggio (criterio 8 della rubrica, e la sezione
"Tecniche da giornalista" qui sotto). Quando un suggerimento della skill allunga
una frase o le aggiunge un inciso, vince la leggibilità. Vale anche per due
metriche del suo contatore: `mente` e `gerundite` possono salire su un testo più
leggibile, e lì non sono un verdetto. Il campo `vietati` resta l'unico cancello.

Cambiare il prompt di chi scrive per agganciare la skill in rilettura è un
cambio da misurare su una run prima di tenerlo (obbligo di `CLAUDE.md`): la skill installata è
**disponibile** nel plugin, ma finché la definizione di `motore:lab-scrittore`
(`plugin/agents/lab-scrittore.md` di platform) non la richiama il comportamento
non cambia.

## Tono: scrivi come una persona

- Frasi di lunghezza varia. Ogni tanto una corta. Va bene iniziare con "Ma" o "E".
- Una sola idea per paragrafo. Niente riempitivi.
- Voce attiva, soggetti concreti, verbi semplici.
- Numeri precisi e verificati al posto degli aggettivi vaghi.

## Tecniche da giornalista (fai così)

I numeri, da soli, non sono un articolo. Un buon desk di data journalism parte
dalle stesse cifre e scrive un pezzo che il lettore ricorda.

**I modelli non sono descritti qui, sono in [`content/esempi/`](esempi/):** testi
veri di Openpolis, Pagella Politica, lavoce.info, Info Data, YouTrend, il Post e
Istat, scelti su un criterio solo, che si leggano al primo passaggio. Se ne
sceglie **uno** prima di scrivere, quello con la forma di storia più vicina alla
propria, e lo si tiene aperto. Non si mediano: otto registri mescolati fanno
l'assenza di registro. Le sei mosse qui sotto dicono che cosa cercare in quel
testo, non lo sostituiscono.

- **Rispondi a "e allora?".** Ogni pezzo fa un punto, non un inventario. Il
  lettore deve finire sapendo perché quei numeri contano, non solo che forma ha la
  classifica. Un rapporto tra fasce d'età è un peso previdenziale e di cura, la
  spesa in ricerca è la scommessa di un territorio sul proprio futuro. Di' la
  posta in gioco una volta, in parole semplici, senza inventare una causa che il
  dato non mostra.
- **Decidi il filo prima di scrivere, poi tienilo.** Una frase sola: qual è
  l'unica cosa vera che questo dato dice quest'anno? Il titolo la annuncia, i
  paragrafi la reggono. Non paragrafi separati messi in fila, un'idea che avanza.
- **Apri sul significato, non sulla meccanica.** Un incipit tipo "la distanza si è
  ridotta di 0,22 punti" fa lavorare il lettore. Parti da cosa vuol dire quella
  distanza, la cifra arriva dopo.
- **Trasforma un numero in una scala umana.** "Quasi sette volte più veloce", "una
  donna su tre al lavoro", "tre volte la media". Un'immagine che resta, non un
  decimale nudo.
- **Dai al pezzo un ancoraggio concreto.** Un solo contrasto vivido che il lettore
  porta via, due territori che quasi non si sfiorano, un valore che era il fondo e
  ora è la vetta. Uno che se lo merita, non una lista.
- **Un'idea per frase, e le clausole nell'ordine in cui si pensano.** È la mossa
  che conta più di tutte, perché è quella che il lettore sente per prima. Una
  seconda idea, anche quando è una cautela vera che va detta, prende la frase
  successiva: non si aggancia con un'altra virgola a quella in corso. Il difetto
  da cui questa regola nasce, preso da un articolo pubblicato che nessuna guardia
  aveva fermato:

  > "In alto due regioni si staccano, la Basilicata e il Piemonte, e fra il
  > Piemonte e la terza, la Valle d'Aosta, corrono già due punti e mezzo, il salto
  > più largo dell'intera graduatoria."

  Tre idee, cinque virgole, e il lettore torna indietro. Scritto in tre frasi
  dice le stesse tre cose e si prende al primo passaggio:

  > "In alto due regioni si staccano, la Basilicata e il Piemonte. Fra il Piemonte
  > e la terza, la Valle d'Aosta, corrono già due punti e mezzo. È il salto più
  > largo dell'intera graduatoria."

  Puoi variare la lunghezza delle frasi quanto vuoi, e va bene farlo: la varietà
  è lecita, non è il metro. Il metro è che la frase non vada riletta. Rileggi il
  paragrafo ad alta voce: se ti manca il fiato o perdi il soggetto per strada,
  spezza.

## Imperfezione controllata

La levigatura uniforme è un tell da bot quanto la sciatteria, e un pezzo dove
nessuna frase esce dallo schema non è stato scritto da nessuno. Ma la libertà
che questa sezione concede si ferma dove comincia la fatica del lettore: **prima
la frase si legge al primo passaggio, poi ha una voce.** Nell'ordine, non in
alternativa. Un inciso in più è un lusso da spendere una volta per pezzo, non
il modo normale di dire la seconda cosa.

La regola d'oro, perché questa sezione non venga letta come un permesso:
**l'imperfezione è concessa e richiesta nella forma, è vietata nel contenuto.**
Puoi aprire una frase con "Ma", concederti un inciso, lasciare una sezione più
corta dell'altra. Non puoi toccare l'aritmetica, aggiungere una causa che il dato
non mostra, citare una fonte che non hai verificato. Quando chiedi a te stesso di
essere più umano, l'errore facile è diventare più libero anche sui numeri, ed
è l'unico errore che non si può correggere dopo.

- **Nut graf.** Un paragrafo, non un accenno, che dice perché questi numeri
  contano: quante persone tocca, quale sistema regge, quale scommessa è. Di'
  l'importanza, non una causa.
- **Il peso lo decide il dato, non lo stile.** Se la storia sta nella
  distribuzione, il quadro viene lungo e la dinamica corta, e va bene così.
  Sezioni di lunghezza diversa sono una conseguenza, mai un obiettivo: non
  allungare una sezione per rompere la simmetria.
- **Digressione.** Una per pezzo, che allarga il campo temporale o comparativo
  restando dentro la serie o citando una fonte reale. Mai un "probabilmente
  perché".
- **Il caveat prende la sua frase.** Un limite va detto dove il numero può
  essere frainteso, e lì va detto in una frase sua: agganciarlo con la virgola
  alla frase in corso è il modo più rapido di renderla illeggibile. Non
  ripetere il disclaimer sulla media non ponderata, quello sta già nell'apparato.
- **Non scrivere il numero due volte.** O l'immagine ("una su due") o la cifra
  ("48%"), mai "quasi la metà (48%)". Il lettore riceve lo stesso fatto due
  volte e la frase si ferma.

## Schemi da evitare (suonano da bot)

- Strutture parallele ripetute: "non solo X, ma anche Y", "non è X, è Y" usato di
  continuo, le triadi di aggettivi.
- Il "due punti drammatico" a fine di ogni paragrafo.
- Chiuse retoriche tipo "In conclusione", "In sintesi", "Insomma", "In definitiva".
- La domanda retorica in chiusura di paragrafo ("il mercato assume di più o le
  giovani restano fuori?"). Non risponde a niente e suona da bot. Fai il punto o
  taglia la frase.
- Avverbi gonfi: "davvero", "assolutamente", "incredibilmente", "chiaramente".
- Frasi-slogan tipo "Leggere X significa leggere Y".
- Prosa a singhiozzo: frasi tutte corte e slegate, accostate senza un nesso, che
  si leggono come un elenco puntato travestito da paragrafo.
- Gergo e paroloni quando basta una parola comune.
- Falsi intervalli: "dal Nord al Sud", "dalle Alpi alla Sicilia", "dai piccoli
  comuni alle grandi città", quando i due estremi non stanno su un continuo
  vero. In un atlante il punto interessante è quasi sempre in mezzo.
- La regola del tre: tre aggettivi in fila, tre esempi, tre cause. Se le cose da
  dire sono due, sono due.
- Riassunti compulsivi in un pezzo da 600 parole: "Nel complesso", "In generale",
  "Tirando le somme". Il lettore ha appena letto, non serve ricapitolare.
- Lessico spia: cruciale, panorama, tessuto, plasmare, sottolineare, evidenziare,
  giocare un ruolo, non da ultimo, a tal proposito, degno di nota. Nessuna di
  queste parole è vietata, ma quando ne trovi una nella tua bozza quasi sempre
  ce n'è una più comune che dice la stessa cosa meglio.

## Struttura: utile, non seriale

- `In breve` e `Dati usati` sono ammessi e spesso utili. Servono a far capire
  subito fonte, periodo, territorio, unita e limite.
- Non usare lo stesso telaio completo in ogni articolo. Se molti post hanno tutti
  `In breve`, `Dati usati`, `Le regioni agli estremi`, `Perche conta`, il lettore
  percepisce una produzione a stampo.
- Mantieni i blocchi di fiducia quando servono, ma varia gli H2 narrativi:
  "Dove il problema pesa di piu", "Cosa segnala sul mercato del lavoro",
  "Dove si produce piu valore", "Cosa cambia per servizi e territorio".
- Le chiusure devono portare a un prossimo passo concreto: atlante, indicatore,
  tema, metodologia o articolo correlato. Niente chiuse da riassunto scolastico.

## Dati: sempre veri

- Usa solo numeri reali presi dagli indicatori. Puoi ricavarli dall'API
  (`/api/indicator/<id>` e `/api/indicator/<id>/year/<year>`) o dallo script dati.
  Non inventare cifre e non arrotondare in modo fuorviante.
- Cita la fonte (Istat) e spiega in una riga come hai calcolato eventuali medie.
- Collega l'articolo al catalogo: imposta `indicator` nel frontmatter e inserisci
  link interni con il **percorso canonico** dell'indicatore, per esempio
  `[testo](/indicatore/tasso-di-turisticita/ter-105)`. È il `path` che il
  catalogo espone per ogni voce. Non usare `/?indicator=...` né
  `/atlante?indicator=...`: la prima forma oggi apre la home, la seconda resta
  sull'Atlante e arriva alla scheda solo via JavaScript.
- Prima di pubblicare, prepara una claim table anche se non entra nel testo:
  claim, fonte, periodo, territorio, unita, trasformazione e confidenza.
- Se usi una seconda fonte di contesto, deve essere autorevole e verificata. Se
  non esiste una seconda fonte pertinente, dichiaralo invece di inventarla.

## SEO (mantienila, ma naturale)

- Titolo con la keyword principale all'inizio, possibilmente entro 60 caratteri.
- `description` di 150-160 caratteri, naturale, con la keyword.
- `seo_title` opzionale per tenere il tag `<title>` piu corto dell'H1.
- `updated` opzionale nel frontmatter (stessa sintassi di `date`, es. `2026-07-20`):
  impostalo solo quando aggiorni davvero i dati o il testo di un articolo gia
  pubblicato. Guida `dateModified` nello schema Article e mostra "Aggiornato il..."
  in pagina; senza `updated`, `dateModified` resta uguale a `date`.
- Sottotitoli `##` e `###` sensati, con varianti della keyword senza forzature.
- Tag pertinenti (2-4).
- Schema candidate solo se il contenuto e visibile in pagina. Niente FAQ o
  Dataset schema di riempimento.

## Controlli prima di pubblicare

```bash
rg -n "[—–;]" content/posts
python3 scripts/prose_lint.py --show <id>   # solo pagine indicatore
```

Il primo comando deve tornare vuoto. Il secondo elenca i tell di questa guida che
una regex sa trovare, sull'articolo di un indicatore. Non copre tutto e non
pretende di farlo: quello che vuole un lettore sta in
[`docs/WRITING_RUBRIC.md`](../docs/WRITING_RUBRIC.md), i dieci criteri con cui
si misura un articolo prima di pubblicarlo, su quattro assi con un pavimento
ciascuno. Per template, frontend e SVG testuali controlla
anche il testo visibile, ma ignora i punti e virgola di CSS, JS, JSON-LD e CSV.

Controlla anche che non ci siano sequenze identiche di H2 tra piu articoli. I
blocchi `In breve` e `Dati usati` possono ripetersi, gli H2 interpretativi no.

Controlla infine: link a metodologia o fonte, link a indicatore o tema, caveat,
next step concreto, title/description/H1 coerenti e non identici.

## Frontmatter

Vedi il blocco di esempio nel README e l'articolo
`content/posts/2026-06-19-divario-turistico-nord-sud-2024.md`.
