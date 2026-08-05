# I modelli di registro: testi veri da leggere prima di scrivere

Questa cartella esiste per una ragione sola, e vale la pena dirla per intero
perche' e' il difetto che ha prodotto la cartella.

Fino al 2026-08-04 tutto cio' che questo progetto diceva al produttore sulla
lingua era una **proibizione**: mai il trattino lungo, mai il punto e virgola,
mai il lessico spia, mai la domanda retorica in chiusura, niente falsi
intervalli, niente regola del tre, niente gerundite, niente perifrasi. Trenta
divieti e zero esempi. `content/STYLE.md` nominava Openpolis, Pagella Politica,
lavoce.info e Info Data, ma li **descriveva** soltanto: nessuno di quei testi e'
mai stato messo davanti a chi scriveva.

Il risultato era prevedibile a posteriori. Gli articoli rispettavano ogni
divieto e non somigliavano a niente. La prosa passava ogni guardia
(`prose_lint`, `tic_count`, la rubrica a 19 su 20, il verificatore) e un lettore
la trovava faticosa, perche' nessuna di quelle guardie misura la fatica. Il
difetto tipico era l'**impilamento**: tre idee dentro una frase sola, tenute
insieme dalle virgole, ogni singola frase difendibile e il paragrafo da
rileggere.

Un registro non si deduce da un elenco di cose da non fare. Si prende per
imitazione, da testi che qualcuno ha scritto davvero.

## Come si usano

**Uno per articolo, non tutti.** Prima di scrivere si apre l'estratto con la
forma di storia piu' vicina a quella che si ha in mano, e lo si tiene aperto
mentre si scrive. Mediarne otto produce l'assenza di registro, che e' esattamente
il punto di partenza.

**Si legge ad alta voce, prima il modello e poi il proprio testo.** La domanda e'
una sola: il mio paragrafo si prende al primo passaggio come il suo? Dove si
torna indietro, si e' impilato. La correzione non toglie niente, spezza.

**Non si copiano le parole, si copia il movimento.** Come entra un numero nella
frase, dove va la cautela metodologica, quanto dura una frase prima del punto,
in che ordine arrivano le clausole. Le cifre restano quelle del brief, sempre.

## Il criterio con cui sono stati scelti

Uno solo: **si leggono al primo passaggio.** Non la vicinanza a un modello di
stile particolare, non l'autorevolezza della testata, non la bellezza della
prosa. Un testo che va riletto e' fuori anche se e' scritto benissimo.

I registri sono **diversi di proposito**. Uno asciutto istituzionale, uno con
piu' voce, uno che apre su un caso concreto, uno che apre sul numero, uno che
smonta un'affermazione. Servono a coprire forme di storia diverse, non a
convergere su un tono unico.

## Che cosa NON sono

**Non sono contenuto pubblicato.** Nessuna rotta li serve, non stanno nella
sitemap, non sono nel blog. L'app legge `content/posts/`, `content/indicators/`,
`content/uploads/` e `content/agent-skills/`, mai questa cartella.

**Non sono una fonte di dati.** Le cifre che compaiono negli estratti valgono
per il testo in cui stanno e non si citano mai in un nostro articolo. I numeri
vengono dal brief deterministico, e da nient'altro.

**Non sono una nuova regola.** Nessuno deve obbedirvi. Sono un metro, e il
posto dove il criterio 8 della rubrica (`Leggibilita'`) trova il suo 2 in della
prosa esistente invece che nella parola "leggibile".

## Citazione e licenza

Ogni estratto e' una **citazione breve** (150-300 parole di un articolo intero)
riportata testualmente, con testata, autore, data e URL, per studio e discussione
del registro. E' uso legittimo di citazione, art. 70 della legge 633/1941. I
testi restano dei rispettivi titolari e non vengono ripubblicati: chi vuole
leggerli per intero segue il link.

Se il titolare di uno di questi testi chiede la rimozione, si toglie il file e
si aggiorna l'indice qui sotto. Non serve altro: nessun agente dipende da un
estratto in particolare.

## La tipografia degli estratti non e' la nostra

Gli estratti sono **verbatim**, e diversi contengono caratteri che
`content/STYLE.md` vieta in assoluto: lineette lunghe `—`, trattini medi `–`,
caporali `« »`, punti e virgola. Restano dove sono per due motivi. Falsificare il
testo di un giornalista firmato sarebbe peggio del rischio che si vuole evitare,
e la citazione fedele e' la condizione dell'art. 70. Nei file interessati c'e'
un'**avvertenza tipografica** che nomina i caratteri presenti.

**Si copia il movimento delle frasi, mai un carattere.** Il cancello resta il
campo `vietati` di `evals/scrittura-italiana/tic_count.py`, che sul nostro
output e' duro e non si negozia.

Dove l'originale ha un refuso (`Oltrettutto` in Openpolis, `e oggi ha oggi` nel
Post) e' rimasto: e' una citazione, non una bozza da correggere.

## L'indice

Dieci estratti, da otto testate. `<testata>-<argomento>.md`, con fonte, autore,
data e URL, il testo verbatim, e una lettura di che cosa lo rende leggibile.

| file | testata | forma di storia | serve per |
| --- | --- | --- | --- |
| [`infodata-mortalita-comuni.md`](infodata-mortalita-comuni.md) | Info Data | una classifica di rapporti, letta dal primo | un indicatore che e' un rapporto, il caso piu' frequente qui |
| [`lavoce-salari-sud.md`](lavoce-salari-sud.md) | lavoce.info | perche' due grandezze divergono | spiegare una composizione o un confondente |
| [`istat-conti-territoriali.md`](istat-conti-territoriali.md) | Istat | il comunicato istituzionale asciutto | l'ultimo anno non definitivo, le ripartizioni in fila |
| [`openpolis-aree-interne.md`](openpolis-aree-interne.md) | Openpolis | due dati incrociati, una tesi sola | il `quadro` che poggia su un indicatore correlato |
| [`openpolis-abruzzo-spopolamento.md`](openpolis-abruzzo-spopolamento.md) | Openpolis | un dato che copre meno di quel che sembra | la sezione `limiti` |
| [`pagellapolitica-record-occupati.md`](pagellapolitica-record-occupati.md) | Pagella Politica | un confronto che non regge | dire che la lettura ovvia del dato e' sbagliata |
| [`ilpost-disagio-urbano.md`](ilpost-disagio-urbano.md) | Il Post | un indice composito spiegato da zero | un indicatore costruito, non misurato |
| [`ilpost-borgo-albergo.md`](ilpost-borgo-albergo.md) | Il Post | il luogo prima della cifra | un territorio estremo che vale la pena nominare |
| [`youtrend-priorita-lavoro.md`](youtrend-priorita-lavoro.md) | YouTrend | una distribuzione letta cifra per cifra | un `quadro` fatto di percentuali in fila |
| [`lavoce-decentramento-storico.md`](lavoce-decentramento-storico.md) | lavoce.info | una domanda, poi il tempo che risponde | la `dinamica` su una serie lunga |

## Che cosa e' stato scartato, e perche'

Vale la pena registrarlo, perche' il criterio si capisce meglio dagli scarti.

**Istat, Report BesT regionali 2025.** Autorevole e pertinente, e illeggibile:
32,1 parole per frase, "si caratterizza per la maggioranza di indicatori con
livelli di benessere relativo superiori alla media-Italia, a cui si affianca
l'assenza di indicatori su livelli piu' bassi". E' esattamente il registro da cui
questo lavoro esiste per uscire, e la firma dell'istituzione non lo salva.

**Un pezzo di Info Data dell'11 febbraio 2026** dichiarava in coda di avere
estratto i dati "utilizzando Claude Opus 4.5" e verificato "con Gemini 3". Prosa
buona, ma una libreria di modelli di italiano scritto da persone non puo'
poggiare su un testo con una catena AI dichiarata.

**Openpolis 2024-2026.** Il registro di casa non e' cambiato, ma la prosa recente
e' spezzata in tratti di 140 parole tra una visualizzazione e l'altra: nessun
passaggio continuo abbastanza lungo da fare da modello. I due Openpolis in
libreria sono percio' del 2023 e del 2024.

**Report Istat in PDF.** L'estrazione porta dentro la sillabazione di riga
("soste-nibilita'"), e ricucirla sarebbe modificare il testo.

## Una cosa che il contatore non vede, e che questa cartella dimostra

I due estratti Openpolis pesano **21,4 e 18,9 tic per mille parole** al
contatore di `evals/scrittura-italiana/tic_count.py`. L'articolo `ter-167` da cui
e' nato tutto questo lavoro, quello giudicato illeggibile, ne pesa **2,2**.

Prosa professionale che lo strumento boccia, prosa faticosa che lo strumento
promuove. Non e' un difetto del contatore, che misura il lessico dell'italiano
generato e lo misura bene: e' la prova che **il lessico e la leggibilita' sono
due assi diversi**, e che sul secondo il metro e' la lettura. Il campo `vietati`
resta l'unica cosa dura che esce da li'.

