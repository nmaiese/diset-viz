# I modelli di registro: testi veri da leggere prima di scrivere

Questa cartella esiste per una ragione sola, e vale la pena dirla per intero
perché è il difetto che ha prodotto la cartella.

Fino al 2026-08-04 tutto ciò che questo progetto diceva al produttore sulla
lingua era una **proibizione**: mai il trattino lungo, mai il punto e virgola,
mai il lessico spia, mai la domanda retorica in chiusura, niente falsi
intervalli, niente regola del tre, niente gerundite, niente perifrasi. Trenta
divieti e zero esempi. `content/STYLE.md` nominava Openpolis, Pagella Politica,
lavoce.info e Info Data, ma li **descriveva** soltanto: nessuno di quei testi è
mai stato messo davanti a chi scriveva.

Il risultato era prevedibile a posteriori. Gli articoli rispettavano ogni
divieto e non somigliavano a niente. La prosa passava ogni guardia
(`prose_lint`, `tic_count`, la rubrica a 19 su 20, il verificatore) e un lettore
la trovava faticosa, perché nessuna di quelle guardie misura la fatica. Il
difetto tipico era l'**impilamento**: tre idee dentro una frase sola, tenute
insieme dalle virgole, ogni singola frase difendibile e il paragrafo da
rileggere.

Un registro non si deduce da un elenco di cose da non fare. Si prende per
imitazione, da testi che qualcuno ha scritto davvero.

## Come si usano

**Uno per articolo, non tutti.** Prima di scrivere si apre l'estratto con la
forma di storia più vicina a quella che si ha in mano, e lo si tiene aperto
mentre si scrive. Mediarne otto produce l'assenza di registro, che è esattamente
il punto di partenza.

**Si legge ad alta voce, prima il modello e poi il proprio testo.** La domanda è
una sola: il mio paragrafo si prende al primo passaggio come il suo? Dove si
torna indietro, si è impilato. La correzione non toglie niente, spezza.

**Non si copiano le parole, si copia il movimento.** Come entra un numero nella
frase, dove va la cautela metodologica, quanto dura una frase prima del punto,
in che ordine arrivano le clausole. Le cifre restano quelle del brief, sempre.

## Il criterio con cui sono stati scelti

Uno solo: **si leggono al primo passaggio.** Non la vicinanza a un modello di
stile particolare, non l'autorevolezza della testata, non la bellezza della
prosa. Un testo che va riletto è fuori anche se è scritto benissimo.

I registri sono **diversi di proposito**. Uno asciutto istituzionale, uno con
più voce, uno che apre su un caso concreto, uno che apre sul numero, uno che
smonta un'affermazione. Servono a coprire forme di storia diverse, non a
convergere su un tono unico.

## Che cosa NON sono

**Non sono contenuto pubblicato.** Nessuna rotta li serve, non stanno nella
sitemap, non sono nel blog. L'app legge `content/indicators/` e `content/posts/`,
mai questa cartella.

**Non sono una fonte di dati.** Le cifre che compaiono negli estratti valgono
per il testo in cui stanno e non si citano mai in un nostro articolo. I numeri
vengono dal brief deterministico, e da nient'altro.

**Non sono una nuova regola.** Nessuno deve obbedirvi. Sono un metro, e il
posto dove il criterio 8 della rubrica (`Leggibilita'`) trova il suo 2 in della
prosa esistente invece che nella parola "leggibile".

## Citazione e licenza

Ogni estratto è una **citazione breve** (150-300 parole di un articolo intero)
riportata testualmente, con testata, autore, data e URL, per studio e discussione
del registro. È uso legittimo di citazione, art. 70 della legge 633/1941. I
testi restano dei rispettivi titolari e non vengono ripubblicati: chi vuole
leggerli per intero segue il link.

Se il titolare di uno di questi testi chiede la rimozione, si toglie il file e
si aggiorna l'indice qui sotto. Non serve altro: nessun agente dipende da un
estratto in particolare.

## La tipografia degli estratti non è la nostra

Gli estratti sono **verbatim**, e diversi contengono caratteri che
`content/STYLE.md` vieta in assoluto: lineette lunghe `—`, trattini medi `–`,
caporali `« »`, punti e virgola. Restano dove sono per due motivi. Falsificare il
testo di un giornalista firmato sarebbe peggio del rischio che si vuole evitare,
e la citazione fedele è la condizione dell'art. 70. Nei file interessati c'è
un'**avvertenza tipografica** che nomina i caratteri presenti.

**Si copia il movimento delle frasi, mai un carattere.** Il cancello resta il
campo `vietati` di `la skill `scrittura-italiana``, che sul nostro
output è duro e non si negozia.

Dove l'originale ha un refuso (`Oltrettutto` in Openpolis, `e oggi ha oggi` nel
Post) è rimasto: è una citazione, non una bozza da correggere.

## L'indice

Dieci estratti, da otto testate. `<testata>-<argomento>.md`, con fonte, autore,
data e URL, il testo verbatim, e una lettura di che cosa lo rende leggibile.

| file | testata | forma di storia | serve per |
| --- | --- | --- | --- |
| [`infodata-mortalita-comuni.md`](infodata-mortalita-comuni.md) | Info Data | una classifica di rapporti, letta dal primo | un indicatore che è un rapporto, il caso più frequente qui |
| [`lavoce-salari-sud.md`](lavoce-salari-sud.md) | lavoce.info | perché due grandezze divergono | spiegare una composizione o un confondente |
| [`istat-conti-territoriali.md`](istat-conti-territoriali.md) | Istat | il comunicato istituzionale asciutto | l'ultimo anno non definitivo, le ripartizioni in fila |
| [`openpolis-aree-interne.md`](openpolis-aree-interne.md) | Openpolis | due dati incrociati, una tesi sola | il `quadro` che poggia su un indicatore correlato |
| [`openpolis-abruzzo-spopolamento.md`](openpolis-abruzzo-spopolamento.md) | Openpolis | un dato che copre meno di quel che sembra | la sezione `limiti` |
| [`pagellapolitica-record-occupati.md`](pagellapolitica-record-occupati.md) | Pagella Politica | un confronto che non regge | dire che la lettura ovvia del dato è sbagliata |
| [`ilpost-disagio-urbano.md`](ilpost-disagio-urbano.md) | Il Post | un indice composito spiegato da zero | un indicatore costruito, non misurato |
| [`ilpost-borgo-albergo.md`](ilpost-borgo-albergo.md) | Il Post | il luogo prima della cifra | un territorio estremo che vale la pena nominare |
| [`youtrend-priorita-lavoro.md`](youtrend-priorita-lavoro.md) | YouTrend | una distribuzione letta cifra per cifra | un `quadro` fatto di percentuali in fila |
| [`lavoce-decentramento-storico.md`](lavoce-decentramento-storico.md) | lavoce.info | una domanda, poi il tempo che risponde | la `dinamica` su una serie lunga |
| [`ilpost-redditi-comuni.md`](ilpost-redditi-comuni.md) | Il Post | una classifica spiegata invece che letta | hai davanti la graduatoria intera, cioè quasi sempre |
| [`ilpost-poverta-assoluta.md`](ilpost-poverta-assoluta.md) | Il Post | denso di cifre e leggibile lo stesso | il pezzo è per forza pieno di numeri |

## I due aggiunti il 7 settembre 2026, e perché proprio quelli

Non a occhio: `motore corpus divarioitalia` aveva appena misurato i 56 articoli
veri del sito contro questi modelli, e i due buchi erano precisi.

**Il primo è la classifica.** La classifica letta ad alta voce sta nel 44-83%
dei nostri articoli e nello **zero per cento** di questa cartella: è il difetto
che ci separa dai modelli più di ogni altro. Mancava però un testo che facesse
vedere come si fa, perché nessuno dei dieci aveva davanti una graduatoria
territoriale intera. `ilpost-redditi-comuni.md` ce l'ha, e invece di leggerla
spiega che cosa la produce.

**Il secondo smentisce una cosa che credevamo.** Per mesi abbiamo pensato che la
cura per i nostri pezzi fosse togliere numeri. `ilpost-poverta-assoluta.md` pesa
6,5 cifre ogni cento parole e ha un paragrafo denso su due, cioè più dei nostri
articoli, e si legge meglio di tutti. La densità è un sintomo, non la malattia:
quello che cambia è se ogni cifra ha accanto il motivo per cui c'è.

**La concorrenza vera sulle nostre query non è un modello.** Su "pil pro capite
regioni italiane" e simili, davanti a noi ci sono travel365, gimme5, blog di
classifiche. Fanno esattamente il difetto che stiamo togliendo, e imitarli
sarebbe peggiorare. I due testi nuovi vengono da chi compete per l'attenzione
sugli stessi temi, non per la stessa SERP.

## I link, che avevamo tolto noi

I dieci estratti originali sono stati trascritti **senza i link inline**: zero
link esterni in dieci testi. Non è come sono i testi veri. L'Openpolis in
libreria ne ha uno nel primo blocco, il Post ne mette cinque in ottocento
parole, la lavoce quattro in settecento.

Non è un dettaglio di trascrizione. Questa cartella è il modello, e per mesi ha
insegnato a chi scrive che una fonte non si linka dentro la prosa: nei nostri
articoli i link a una fonte nel testo sono **zero** in tutte le generazioni
tranne una al 6 per cento, mentre l'elenco `fonti` finisce in fondo alla pagina
dove nessuno arriva. I due estratti nuovi tengono i loro link esattamente dove
stanno nell'originale, ed è la ragione principale per cui sono qui.

## Che cosa è stato scartato, e perché

Vale la pena registrarlo, perché il criterio si capisce meglio dagli scarti.

**lavoce.info, "Italia, il paese più frammentato d'Europa" (2019).** Vagliato il
7 settembre 2026 e scartato. Sui numeri era il migliore dei tre candidati: 1,8
cifre per cento parole, quattro link nella prosa, zero classifiche lette ad alta
voce. Ma il registro è quello accademico da cui questo lavoro esiste per uscire:
"comportando così una netta alterazione nella misura della disuguaglianza
intra-regionale", più l'indice di Williamson e il coefficiente di variazione nel
corpo del testo. Il criterio è la lettura al primo passaggio, e i numeri buoni
non la sostituiscono.

**Istat, Report BesT regionali 2025.** Autorevole e pertinente, e illeggibile:
32,1 parole per frase, "si caratterizza per la maggioranza di indicatori con
livelli di benessere relativo superiori alla media-Italia, a cui si affianca
l'assenza di indicatori su livelli più bassi". È esattamente il registro da cui
questo lavoro esiste per uscire, e la firma dell'istituzione non lo salva.

**Un pezzo di Info Data dell'11 febbraio 2026** dichiarava in coda di avere
estratto i dati "utilizzando Claude Opus 4.5" e verificato "con Gemini 3". Prosa
buona, ma una libreria di modelli di italiano scritto da persone non può
poggiare su un testo con una catena AI dichiarata.

**Openpolis 2024-2026.** Il registro di casa non è cambiato, ma la prosa recente
è spezzata in tratti di 140 parole tra una visualizzazione e l'altra: nessun
passaggio continuo abbastanza lungo da fare da modello. I due Openpolis in
libreria sono perciò del 2023 e del 2024.

**Report Istat in PDF.** L'estrazione porta dentro la sillabazione di riga
("soste-nibilità"), e ricucirla sarebbe modificare il testo.

## Una cosa che il contatore non vede, e che questa cartella dimostra

I due estratti Openpolis pesano **21,4 e 18,9 tic per mille parole** al
contatore di `la skill `scrittura-italiana``. L'articolo `ter-167` da cui
è nato tutto questo lavoro, quello giudicato illeggibile, ne pesa **2,2**.

Prosa professionale che lo strumento boccia, prosa faticosa che lo strumento
promuove. Non è un difetto del contatore, che misura il lessico dell'italiano
generato e lo misura bene: è la prova che **il lessico e la leggibilità sono
due assi diversi**, e che sul secondo il metro è la lettura. Il campo `vietati`
resta l'unica cosa dura che esce da lì.

