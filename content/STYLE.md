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
**`scrittura-italiana`** (`.claude/skills/scrittura-italiana/`, CC BY-SA 4.0).
Questa guida la **cita**, non la ricopia: le quattro virtu' retoriche, le cinque
varianti del bipolare, l'antilingua e il lessico di plastica vivono nei suoi
`references/`, e ripeterli qui li manderebbe fuori sincrono.

**La precedenza e' esplicita, e non e' negoziabile: su ogni conflitto vincono
gli assoluti di progetto.** La skill lavora nel registro *testo controllato* e
li' consiglia i caporali `« »`, le lineette spaziate e il punto e virgola. Le
regole tipografiche qui sopra li **vietano**: niente `—`, `–`, `;`, `…`,
virgolette dritte. Quando la skill suggerisce una di quelle forme, si tiene la
regola di progetto e si scioglie l'inciso con virgole o due frasi. Il conflitto
e' sistematico, non un caso di bordo: sta nel registro esatto in cui vivono le
nostre pagine. Il perche' e il cancello deterministico che lo fa rispettare
(`tic_count.py`, campo `vietati` sempre vuoto) sono in
[`evals/scrittura-italiana/PRECEDENZA.md`](../evals/scrittura-italiana/PRECEDENZA.md).

Cambiare il prompt del produttore per agganciare la skill in rilettura e' un
cambio gated da `canary` (obbligo di `CLAUDE.md`): la skill installata e'
**disponibile**, ma finche' `producer.md` non la richiama il comportamento degli
agenti non cambia.

## Tono: scrivi come una persona

- Frasi di lunghezza varia. Ogni tanto una corta. Va bene iniziare con "Ma" o "E".
- Una sola idea per paragrafo. Niente riempitivi.
- Voce attiva, soggetti concreti, verbi semplici.
- Numeri precisi e verificati al posto degli aggettivi vaghi.

## Tecniche da giornalista (fai così)

I numeri, da soli, non sono un articolo. Un buon desk di data journalism
(Openpolis, Pagella Politica, lavoce.info, Info Data del Sole 24 Ore) parte dalle
stesse cifre e scrive un pezzo che il lettore ricorda. Sei mosse:

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
- **Varia il ritmo, ma tieni le frasi collegate.** Quasi tutte le frasi hanno una
  subordinata e portano alla successiva. Ogni tanto una no, e una riga breve dopo
  una lunga fa cadere il punto. La frase corta però è uno strumento raro, per dare
  enfasi, non la regola: un paragrafo di frasette secche di tre parole suona a
  singhiozzo, ed è un tell da bot tanto quanto il periodare uniforme che sostituisce.
  Il metro non è la lunghezza, è il flusso. Rileggi il paragrafo ad alta voce, ogni
  frase deve nascere dalla precedente, non stare accanto come una voce di elenco.

## Imperfezione controllata

La levigatura uniforme e' un tell da bot quanto la sciatteria. Un pezzo in cui
tutte le sezioni pesano uguale, nessuna frase esce dallo schema e niente viene
mai messo tra parentesi non e' stato scritto da nessuno, e si sente.

La regola d'oro, perche' questa sezione non venga letta come un permesso:
**l'imperfezione e' concessa e richiesta nella forma, e' vietata nel contenuto.**
Puoi variare il ritmo, spostare il peso tra le sezioni, concederti un inciso,
aprire una frase con "Ma". Non puoi toccare l'aritmetica, aggiungere una causa
che il dato non mostra, citare una fonte che non hai verificato. Quando chiedi a
te stesso di essere piu' umano, l'errore facile e' diventare piu' libero anche
sui numeri, ed e' l'unico errore che non si puo' correggere dopo.

- **Nut graf.** Un paragrafo, non un accenno, che dice perche' questi numeri
  contano: quante persone tocca, quale sistema regge, quale scommessa e'. Di'
  l'importanza, non una causa.
- **Asimmetria.** Le sezioni pesano dove pesa il dato. Se la storia sta nella
  distribuzione, il quadro e' lungo e la dinamica corta, e va bene cosi'.
- **Digressione.** Una per pezzo, che allarga il campo temporale o comparativo
  restando dentro la serie o citando una fonte reale. Mai un "probabilmente
  perche'".
- **Caveat inline.** Sposta un limite dentro il testo, come inciso, dove il
  numero puo' essere frainteso. Non ripetere il disclaimer sulla media non
  ponderata, quello sta gia' nell'apparato.
- **Non scrivere il numero due volte.** O l'immagine ("una su due") o la cifra
  ("48%"), mai "quasi la meta' (48%)". Il lettore riceve lo stesso fatto due
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
  comuni alle grandi citta'", quando i due estremi non stanno su un continuo
  vero. In un atlante il punto interessante e' quasi sempre in mezzo.
- La regola del tre: tre aggettivi in fila, tre esempi, tre cause. Se le cose da
  dire sono due, sono due.
- Riassunti compulsivi in un pezzo da 600 parole: "Nel complesso", "In generale",
  "Tirando le somme". Il lettore ha appena letto, non serve ricapitolare.
- Lessico spia: cruciale, panorama, tessuto, plasmare, sottolineare, evidenziare,
  giocare un ruolo, non da ultimo, a tal proposito, degno di nota. Nessuna di
  queste parole e' vietata, ma quando ne trovi una nella tua bozza quasi sempre
  ce n'e' una piu' comune che dice la stessa cosa meglio.

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
si misura un articolo prima di pubblicarlo. Per template, frontend e SVG testuali controlla
anche il testo visibile, ma ignora i punti e virgola di CSS, JS, JSON-LD e CSV.

Controlla anche che non ci siano sequenze identiche di H2 tra piu articoli. I
blocchi `In breve` e `Dati usati` possono ripetersi, gli H2 interpretativi no.

Controlla infine: link a metodologia o fonte, link a indicatore o tema, caveat,
next step concreto, title/description/H1 coerenti e non identici.

## Frontmatter

Vedi il blocco di esempio nel README e l'articolo
`content/posts/2026-06-19-divario-turistico-nord-sud-2024.md`.
