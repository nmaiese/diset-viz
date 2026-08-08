# La catena che scrive gli articoli

L'unica catena editoriale del progetto. Nasce come esperimento accanto a una
macchina molto più grande, per misurare quanto di quella fosse necessario: la
risposta è stata poca, e la macchina grande è stata ritirata.

Il principio è uno: **più lavoro al modello, meno a script che non possono
intercettare tutto**. Python calcola le cifre, che sono l'unica cosa che un
calcolo fa meglio di un modello; tutto ciò che richiede un giudizio (che storia
raccontare, se una fonte regge, se una frase promette più di quanto la fonte
dica) lo fa un agente, e il controllo è un altro agente che prova a smentirlo.

```
  ter-6, oppure niente e la sceglie la coda
    |
 [1] lab-dossierista   Bash, haiku    bin/py -m lab.dossier      -> data/lab/dossier/<codice>.json
    |
 [2] tre scout in parallelo, lenti distinte, ciechi l'uno all'altro
    |  lab-scout        Web, sonnet   che cosa è successo: eventi datati
    |  lab-scout-europa Web, sonnet   dove sta l'Italia, con le trappole di comparabilità
    |  lab-scout        Web, sonnet   perché conta: conseguenze documentate
    |  prima l'ultimo anno del dato, che è quello che l'articolo descrive,
    |  poi una finestra sul 2026, datata in `periodo` e mai confusa col dato
    |
 [3] lab-scrittore     Read, sonnet   una bozza sola. Tesi, temi, numero di sezioni,
    |                                 ordine, titoli e link: decide tutto lui
 [4] lab-verificatore  Bash+Web, opus bin/py -m lab.controlla --salva  -> data/lab/bozze/<codice>.json
    |                                 cinque classi passate in rassegna, non una
    |                                 lettura: cifre, fonti rifetchate, causali,
    |                                 definizione, coerenza fra titoli e corpi
    |                                 smentite? [3] corregge, al massimo due giri
    |                                 gravi all'ultimo giro? non si scrive niente
 [5] lab-pubblicatore  Bash, haiku    bin/py -m lab.pubblica --bozza   -> content/indicators/<key>.json
```

Nove agenti per articolo nel caso peggiore, quindi **un codice per run**.

Le scelte che la distinguono da una catena editoriale ordinaria, ognuna pagata
da una run che è andata storta prima:

| | come si fa qui | perché |
| --- | --- | --- |
| bozze per articolo | una | due bozze più un giudice costano il doppio per scegliere fra due testi che lo stesso modello ha scritto a dieci secondi di distanza |
| contesto esterno | tre scout web per run, lenti distinte, claim non persistiti | un corpus preesistente invecchia e nessuno se ne accorge; tre contesti corti costano meno di uno lungo |
| chi sceglie l'angolo | chi scrive, quando ha tutto davanti | un punteggio calcolato a monte propone la stessa storia a metà del catalogo |
| forma dell'articolo | variabile: ruoli ripetibili, ordine e titoli scelti | il renderer lo sapeva già fare e nessuno l'aveva usato |
| cancello | nessuno | l'unica cosa che ferma un articolo è una cifra o una fonte che non esiste, e la ferma un agente che legge, non una regola |
| quando esce | all'ultimo passaggio, se non restano rilievi `alta` | tre letture dello stesso testo trovano ogni volta rilievi nuovi: non è il testo che non converge, è la lettura |
| dove scrive | `content/indicators/` | è la pagina pubblica, con la struttura di sempre: il ricambio è per indicatore |

## I tre comandi

```bash
bin/py -m lab.dossier ter-6                      # i numeri, già calcolati
bin/py -m lab.dossier ter-6 --stdout             # il dossier a schermo
bin/py -m lab.dossier --coda 1 --freschi 2025    # il codice lo sceglie la coda editoriale
bin/py -m lab.controlla ter-6 --salva < bozza.json   # ogni cifra e ogni link contro il dossier
bin/py -m lab.pubblica ter-6 --bozza data/lab/bozze/ter-6.json
```

`lab.dossier` calcola: classifica dell'ultimo anno con rango, percentile e
scarto dalla mediana; media, mediana, spread, rapporto max/min, coefficiente di
variazione; medie per macroarea e divario Nord-Mezzogiorno; delta a 1, 5 e 10
anni per territorio; media nazionale anno per anno; convergenza o divergenza del
divario; massimo e minimo storico; volatilità; rotture di serie; inversioni di
tendenza; buchi nella copertura. Più un elenco di `anomalie` in italiano, che
serve a puntare gli scout.

Non calcola nessun punteggio d'angolo: quale storia raccontare è una scelta
editoriale, e la fa chi scrive.

### La coda

`--coda N` non calcola nessuna priorità: la prende da `lab/coda.py`,
che ordina il catalogo intero (cifre arretrate, poi sezioni mancanti, poi se la
pagina è indicizzabile) e ci aggiunge i filtri che servono qui: il dato
dell'anno chiesto, la pagina non già completa, e il livello.

"Non già completa" è il predicato di `lab.coda`, riusato e non riscritto:
`missing or not lead or stale`. Scriverlo a mano come "sezioni scritte meno
delle sezioni emesse" escludeva proprio la testa della coda, l'articolo completo
ma con le cifre più vecchie del dato, che vale `+100` mentre una sezione
mancante ne vale `10`.

**Il livello dev'essere quello di default dell'indicatore**, e non è un
dettaglio di comodo: `content/indicators/` ha un file per indicatore, non per
coppia (indicatore, livello). Un articolo provinciale di un indicatore che di
default è regionale finirebbe nello stesso `<key>.json` di quello regionale, e
siccome la pagina sceglie che cosa rendere leggendo `level`, non si
aggiungerebbe al primo: lo sostituirebbe, e la prosa regionale smetterebbe di
comparire senza che niente diventi rosso. Il filtro è quindi `livello ==
default`, non "salta le province": 33 delle 67 righe provinciali sono di
indicatori che di default **sono** provinciali, e per quelle non c'è
collisione. Le 34 che restano fuori diventeranno raggiungibili quando lo store
saprà tenere due articoli per indicatore.

Il livello viaggia poi fino ai comandi: `lab.controlla` e `lab.pubblica`
ricostruiscono il dossier da soli e senza `--livello` lo ricostruiscono sul
default, quindi il workflow glielo passa esplicitamente. Con il filtro qui
sopra i due coinciderebbero comunque: dirlo rende la catena giusta per
costruzione invece che per coincidenza.

Numeri di oggi: la coda dice **0 articoli con vintage arretrato**, quindi il
`+100` non scatta mai. Incrociandola con la freschezza restano **96 pagine con
dati 2025, indicizzabili e incomplete**: 62 `bes`, 23 `ims`, 11 `ter`, di cui 83
a 2/4 e 13 a 0/4, tutte e 96 al livello regione.

Su una pagina a 2/4 si riscrive l'**articolo intero**, non una toppa alle due
sezioni mancanti: chi scrive decide la forma quando ha il dossier davanti, e
non può farlo dentro il perimetro di una pagina già impostata da qualcun altro.
L'uscita di `lab.pubblica` dice `sovrascritto`, così rifare una pagina non è
mai una cosa che succede in silenzio.

### I gruppi della classifica

Il blocco `gruppi` cerca la divisione che i valori fanno da soli. Non è una
griglia di terzili, che esisterebbe sempre: si prova ogni taglio possibile sui
valori ordinati e si tiene il numero **più piccolo** di gruppi che porta la
bontà di adattamento (Jenks) sopra 0,85, con almeno due territori per gruppo.
Se nessuna divisione ci arriva, la risposta è `null` col motivo.

Il blocco riporta sempre **quanto spiegherebbero invece Nord, Centro e
Mezzogiorno** sullo stesso metro, perché la domanda editoriale non è "quali
gruppi ci sono" ma se la geografia c'entra. Su `ter-13` i gruppi ricalcano le
ripartizioni (0,95 contro 0,80). Su `ter-921`, l'indice di vecchiaia, la
geografia spiega **0,01**: il Trentino sta con la Campania e la Sicilia, e
scrivere "Nord contro Sud" sarebbe pigro e falso insieme.

### I parenti

Il blocco `parenti` porta gli altri indicatori che raccontano una storia vicina:
le varianti per sesso o età (stesso nome a meno della parentesi finale, 41
gruppi e 112 indicatori nella sola famiglia territoriale), le collisioni fra
famiglie, e i vicini di tema che `app/indicator_view.py` calcola già. Per le
prime tre varianti porta anche i **valori regione per regione**.

Quei valori non sono un vezzo. `lab.controlla` costruisce i candidati dal
dossier dell'indicatore corrente, quindi senza di loro la prima frase che legge
lo stesso territorio su due indicatori verrebbe smentita, e al secondo giro chi
scrive toglierebbe un link buono. Colma un buco misurato dal progetto: la
rubrica chiede da uno a tre correlati, e **sei articoli su 364** ne linkano uno.

## Le tre lenti

Non esiste in Claude Code un subagente di deep research da chiamare: i tipi
built-in sono `general-purpose`, `Explore`, `Plan`, `claude`,
`claude-code-guide` e `statusline-setup`, e nessuno è un ricercatore.
L'equivalente è il ventaglio, cioè agenti stretti che cercano cose diverse e
sono ciechi l'uno all'altro.

| lente | agente | cerca |
| --- | --- | --- |
| che cosa è successo | `lab-scout` | eventi datati che si affiancano ai movimenti della serie |
| dove sta l'Italia | `lab-scout-europa` | valore italiano in fonte europea, media UE, paesi vicini per valore |
| perché conta | `lab-scout` | conseguenze documentate, chi ne è toccato |

Il budget sta nel **prompt**, non nel frontmatter: `maxTurns` dentro un workflow
non viene rispettato (sedici dichiarati, trentuno fatti al primo giro reale), e
con tre scout l'esposizione a una run scappata triplica. Due ricerche e tre
fetch a testa.

Lo scout europeo ha una skill sua, `confronto-europeo`, e non è una gerarchia
di fonti bis: sono le quattro trappole di comparabilità. La più cara è la
media, perché gli aggregati europei sono ponderati sulla popolazione mentre il
valore nazionale del dossier è la media semplice delle venti regioni. È lo
stesso difetto che la verifica prese al primo giro reale. Le altre tre: NUTS2
spacca il Trentino-Alto Adige in due, stesso nome non vuol dire stessa
definizione, e l'anno europeo è quasi sempre indietro.

Un claim che serve a un confronto porta `usage: "external_comparison"`. È
l'unico valore di quel campo, ripreso dalla feature request #185: gli altri tre
che la FR propone ridicono quello che `relation_type` già dice, e due
vocabolari per lo stesso fatto divergono.

## Che cosa guarda `lab.controlla`

Quattro cose, tutte deterministiche, tutte con un'etichetta accanto: dire
"trovata" non aiuta nessuno, dire che il 41,73 di una frase sulla Toscana è la
**media nazionale del 2007** fa decidere in un colpo solo.

- **Le cifre**, contro i valori del dossier, con la tolleranza dell'1,1%
  (l'1,1%, perché la prosa arrotonda) e lo scarto stampato quando la
  corrispondenza non è esatta.
- **Gli anni, in modo esatto e mai per tolleranza.** L'1,1% di 2025 vale
  ventidue anni, quindi "nel 2014" passava come "l'anno 2025" e con esso
  qualunque data dentro un quarto di secolo. Un anno **assente** dalla serie è
  comunque legittimo da nominare, e il dossier adesso lo dice in
  `anni_mancanti`: su `ter-6` manca il 2004, l'anno in cui l'Istat spostò la
  rilevazione, e l'articolo lo diceva giustamente mentre il controllo lo
  smentiva.
- **I valori dei parenti**, ma **solo dove il parente è linkato in quel pezzo di
  prosa**. Aprire il paniere a tutti i fratelli allargherebbe le corrispondenze
  possibili senza che nessuna frase le abbia chieste.
- **I link interni**, con tre esiti distinti, perché confonderli farebbe
  togliere link buoni: `nel dossier` (copiato dai parenti), `esiste, fuori dai
  parenti` (composto a mano, è una nota), `non esiste` (è una smentita).

Il link inventato è la stessa classe di difetto della cifra inventata, e a
fermarlo è chi verifica, non chi pubblica.

## Il testo passa in un prompt una volta sola

Fra lo scrittore e il verificatore. Da lì in poi viaggia come file:
`lab.controlla --salva` congela la bozza giudicata e ne stampa l'`impronta`,
calcolata su lead, sezioni **e** testo e url delle fonti; il workflow ricalcola
la stessa impronta sulla bozza che ha in mano e, se non coincide, ferma
l'articolo invece di scriverne uno diverso da quello verificato.

**Il campo che decide è `digest`**, otto caratteri esadecimali. Gli altri
cinque (caratteri, parole, cifre, sezioni, fonti) non identificano il testo:
`sale` che diventa `cale` li lascia tutti identici e ribalta il verso della
frase. Restano accanto al digest perché servono a chi legge un blocco:
`caratteri: 4210 != 4208` dice **che cosa** è cambiato, un esadecimale diverso
dice solo che qualcosa lo è.

Il digest è FNV-1a a 32 bit sui punti di codice, e non `hashlib`, perché
dall'altra parte c'è uno script di workflow: niente API di Node, quindi niente
`crypto`. Serve una funzione che si riscriva in dieci righe di JavaScript
dando esattamente lo stesso risultato.

**Un'impronta che non torna vale come diversa, non come uguale.** Il controllo
restituiva `null` quando il verificatore ometteva il campo, cioè lo stesso
esito di una che coincide: la bozza congelata finiva su disco senza che nessuno
avesse stabilito che era quella giusta. Ora l'assenza è uno scarto, e lo schema
del verdetto pretende l'impronta con tutti i suoi campi.

Le due implementazioni devono restare identiche, ed è la forma che diverge.
I punti in cui hanno già divergito o potrebbero: `isdigit()` in Python è vero
anche per l'esponente di `km²`, che `\d` in JavaScript non conta, quindi si usa
`isdecimal()`; il digest gira su `Math.imul` e `>>> 0`, senza i quali la
moltiplicazione esce dagli interi esatti di JavaScript; si itera per punti di
codice (`for...of`, `codePointAt`) e non per unità UTF-16, che spezzerebbero le
coppie surrogate; e i pezzi si uniscono con un a capo, senza il quale l'ultima
parola di uno si fonde con la prima del successivo.

Non si controlla a vista: `tests/unit/test_lab_impronta.py` estrae le due
funzioni dal workflow, le esegue con `node` sulla stessa bozza e confronta il
risultato con quello di Python.

**Attenzione a un'asimmetria voluta**: l'impronta conta il testo **grezzo**, url
compresi, mentre la ricerca delle cifre gira sul testo **senza i bersagli dei
link**. Sono due domande diverse. L'impronta chiede "è lo stesso identico
oggetto", e un url storpiato nella ribattitura deve farla fallire. Il controllo
delle cifre chiede "questo numero il lettore lo legge", e `ter-177` dentro un
percorso non è un numero: allineare le due cose farebbe smentire quattro cifre
inesistenti su ogni articolo che linka un fratello.

## La forma dell'articolo è variabile, e il renderer lo sapeva già

I ruoli di sezione sono quattro (`definizione`, `quadro`, `dinamica`, `limiti`)
e un ruolo diverso viene scartato in silenzio. Ma **quattro ruoli non vuol dire
quattro sezioni**: `app/indicator_texts.py:267-282` tiene una **lista per
ruolo** e deriva la sequenza degli H2 dalle sezioni scritte, conservando ordine
e ripetizioni. Provato:

```
doppi, senza definizione:  ['quadro', 'quadro', 'dinamica', 'limiti']
doppi, con definizione:    ['definizione', 'quadro', 'quadro', 'dinamica', 'limiti']
senza dinamica (collassa): ['definizione', 'quadro', 'dinamica', 'limiti']
roles_covered esplicito:   ['quadro', 'dinamica', 'limiti']   <- perde il secondo quadro
```

Così i sette temi che un articolo può coprire (che cosa misura, differenze
territoriali, andamento, confronto europeo, perché conta, limiti, fonti) stanno
dentro quattro ruoli, col titolo `h` a portare il tema. Nessuna riga di `app/`
è stata toccata.

Due conseguenze da non dimenticare:

- **Niente `roles_covered`.** Dichiarare la forma una seconda volta è il modo
  di farla divergere, e la quarta riga lo dimostra: la dichiarazione vince, e un
  ruolo elencato una volta sola butta via la sezione gemella.
- **I tre ruoli sostanziali devono esserci tutti.** Se ne manca uno la
  derivazione non scatta, la forma scelta collassa in quella fissa e le sezioni
  in eccesso spariscono senza errore. `lab.pubblica` rifiuta quando succede,
  nominando la sezione che si perderebbe, e stampa sempre `impaginazione`, cioè
  gli H2 come li vedrebbe un lettore. Una sezione persa non dà errore da
  nessuna parte: non la vede l'app, non la vede il lint, e chi l'ha scritta la
  crede pubblicata.

## Il lint è un metro, non un cancello

`lab.pubblica` scrive **prima** e misura **dopo**, chiamando `lab.lint` dentro
un try/except: un'eccezione della misura non deve portarsi via l'unico prodotto.
I rilievi finiscono nell'uscita del comando, compresi quelli marcati `blocca`.

`lab/lint.py` tiene solo le regole che questa catena usa e che `lab.controlla`
non copre già: i caratteri vietati dallo stile, il lead sopra i 200 caratteri,
il link non canonico, l'articolo troppo corto, una dinamica che spiega senza
fonti, e la quota di paragrafi senza cifre. Le cifre non le rimisura, e non è
una svista: il lint precedente lo faceva con un metro più grossolano e ha dato
tre `cifra-falsa` bloccanti su due articoli, tutte e tre **volatilità** dette
correttamente dal testo e accostate al valore della regione nominata accanto.

Ciò che ferma davvero un articolo sta in `lab.pubblica._valida`, ed è solo ciò
che rende la pagina rotta: un lead vuoto, una sezione senza corpo, un ruolo
inesistente, un accento scritto con l'apostrofo.

## Il primo giro reale (ter-6, 2026-08-08)

Girato con l'architettura precedente: **uno** scout invece di tre, quattro
sezioni in ordine fisso, nessun parente, nessun gruppo, nessun controllo sui
link. Le misure qui sotto vanno lette con questa avvertenza, e vanno rifatte.

Articolo scritto, 422 parole, un giro di correzione, 41 cifre verificate, un
solo rilievo di lint (`dinamica-senza-fonte`, `segnala`). La bozza congelata e
l'articolo scritto coincidono campo per campo.

Il verificatore ha trovato quattro difetti veri, tutti invisibili a una lettura
distratta e nessuno rilevabile da una regola:

1. `11,76%` chiamata "media nazionale": è la media **semplice** delle venti
   regioni, non un aggregato ponderato.
2. "la variazione quinquennale più ampia di tutta la serie": il dossier calcola
   una sola finestra (2020-2025), quindi la frase prometteva un confronto che
   nessuno aveva fatto.
3. Nell'angolo, "oscilla più di ogni altra **da allora**": l'indice di
   volatilità è calcolato su tutta la serie 1995-2025.
4. Un nesso causale ("una rottura, una siccità") che nessuna fonte documenta.

La fonte Istat era un PDF: il fetch non ne restituisce il testo, quindi è
finita in `note` come **non verificabile**, che non blocca.

Costo, con `scripts/baseline_tokens.py`: **3,99 $** il percorso riuscito, di cui
1,62 $ il solo scout web. Senza la fetta contesto, dossier più scrittura più
verifica più pubblicazione, **2,37 $**.

Due cose che il giro ha smentito, entrambe scritte nel piano come da verificare:

- **`maxTurns` nel frontmatter non viene rispettato dentro un workflow.** Ne
  erano dichiarati 16, il verificatore ne ha fatti 31 nel primo tentativo. Il
  freno sta nel prompt, non nella configurazione.
- I modelli per ruolo invece **vengono applicati** (haiku, sonnet, opus nei
  metadati degli agenti), passandoli in `opts` a ogni chiamata.

## Il secondo giro reale (ter-13, 2026-08-08)

Il primo con l'architettura di adesso. Gli appunti stanno in
[`run-02-ter-13.md`](run-02-ter-13.md): che cosa ha fatto ogni agente, come ha
ragionato, e i quattro difetti da correggere. In breve:

- **zero articoli**, fermato dal verificatore al secondo giro, prima del disco;
- il budget scritto nel prompt **tiene**: tre scout, sei turni a testa, nessuno
  sfora le due ricerche e i tre fetch dichiarati;
- il ventaglio di tre scout **costa meno** di un singolo scout lungo: 1,19 $
  contro 1,62 $, e la run intera 3,89 $ contro 4,99 $, perché la cache riletta
  a ogni turno è il costo vero;
- lo scout Europa ha restituito **lista vuota** con il motivo giusto (il dossier
  misura 15-64, l'indicatore headline di Eurostat è 20-64);
- `gruppi` e `parenti` funzionano: l'angolo dell'articolo nasce dai gruppi, i due
  link interni risultano entrambi "nel dossier";
- il guasto vero era il **giro di correzione**, che toccava il corpo e lasciava
  il titolo e l'`angolo` a dire il contrario. Corretto, e l'articolo è uscito:
  `content/indicators/13.json`, 782 parole, due giri di correzione, un solo
  rilievo di lint.

Da quel giro vengono le due regole che oggi governano la verifica, e nessuna
delle due era nel piano:

- **si esce sulla gravità, non sul silenzio.** Tre passaggi dello stesso
  verificatore sullo stesso testo hanno prodotto 3, poi 1, poi 2 rilievi, ogni
  volta nuovi e ogni volta su frasi presenti dalla prima bozza. Non è il testo
  che non converge, è la lettura. All'ultimo passaggio l'articolo esce se non
  restano rilievi `alta`, e quelli che restano viaggiano col pezzo in
  `rilievi_aperti`. Un rilievo senza gravità dichiarata conta come grave.
- **una smentita vale sul claim, non sulla frase.** Chi corregge cambia anche
  il titolo della sezione, il `lead` e l'`angolo`, e gli altri punti con lo
  stesso difetto.

E una terza, che viene dalla stessa misura letta dall'altro verso: se i rilievi
nuovi arrivano su un testo che non è cambiato, il difetto non è la gravità, è
**quando** si trovano. Il verificatore quindi non legge il pezzo dall'inizio
alla fine, **passa in rassegna cinque classi** (cifra, fonte, causale,
definizione, coerenza), attraversa tutto il testo una classe alla volta,
rilegge le classi rimaste vuote prima di restituire, e dichiara in
`classi_passate` quelle che ha davvero guardato. Una classe non dichiarata
finisce nei log della run: senza quel campo, "non c'è niente" e "non ho
guardato" escono identici, cioè zero smentite.

## Il confronto che non è mai stato fatto

Questa catena è nata per essere misurata contro quella grande, sullo stesso
indicatore, con `giudice-cieco` a leggere i due testi senza sapere da dove
vengono. Il confronto **non è mai stato eseguito**: la catena grande è stata
ritirata prima, e i numeri che restano sono di run diverse su indicatori
diversi, quindi non si sottraggono.

Quello che si sa, e vale come ordine di grandezza e non come confronto:

- una run di questa catena con sonnet a scrivere e due verifiche costa **3,89 $**;
- con opus a scrivere e tre verifiche, **circa 7 $** (l'ultima misurata, 4,54 $
  come pavimento su un articolo senza correzioni);
- la forma di adesso, sonnet a scrivere e tre verifiche, sta fra le due e non è
  ancora stata misurata: il ritorno a sonnet è per la scrittura, non per il
  costo, e gli scout hanno più budget di prima;
- la catena ritirata misurava 1,97 $ per articolo, ma non faceva **nessuna**
  ricerca web e la fetta contesto qui vale più di un dollaro.

Le due cose da non confondere se un confronto si rifarà: i modelli qui sono
scelti per ruolo (haiku, sonnet, opus) e un delta contro una catena tutta su
`inherit` mescola architettura e tier; e la ricerca web non è ripetibile, come
si è visto rilanciando lo stesso indicatore e ottenendo due scout vuoti dove
prima ne erano tornati due pieni.

## Guardarla mentre gira

Il cruscotto sta a `monitor.divarioitalia.it/_pipeline/console` e non chiede
niente alla catena: **nessun agente batte, nessun prompt cambia, i turni
restano quelli**. Il monitoraggio è un processo che gira di fianco e legge i
trascritti che il runtime dei workflow scrive comunque.

```bash
bin/py -m lab.cruscotto --segui --per 5400 &     # PRIMA del workflow
Workflow({scriptPath: ".claude/workflows/indicatore-lite.js"})
```

Non serve dirgli quando la run è finita: lo vede, perché
`<sessione>/workflows/<runId>.json` compare solo allora, e da lì legge il
consuntivo (label, fase, modello, turni e costo per agente, riusando
`scripts/baseline_tokens.py`) e lo posta da sé.

Quello che si vede, e quello che non si può vedere:

| orizzonte | da dove | che cosa porta |
| --- | --- | --- |
| mentre gira | `journal.jsonl`, `agent-<id>.meta.json` | quali agenti sono aperti, di che tipo, su che indicatore |
| a passo finito | `journal.jsonl`, riga `result` | il **valore di ritorno completo** dell'agente che chiude |
| a run finita | `<runId>.json` più i `agent-*.jsonl` | fasi, label, modello, turni, strumenti, token e costo |

**Dal vivo la fase non esiste**: `label` e `phaseTitle` stanno solo in
`<runId>.json`. Il cruscotto la stima dal tipo di agente
(`lab/cruscotto.FASE_PER_TIPO`) e la mostra dichiarandola stimata finché non
arriva quella vera. Un tipo `lab-*` nuovo va aggiunto a quella mappa, e la
suite lo pretende: `tests/unit/test_cruscotto.py` rilegge questo workflow e
fallisce se un `agentType` non ha una fase.

**Ogni costo è un pavimento.** In una run reale un agente ha registrato
`output_tokens: 2` sulla richiesta che restituiva una bozza intera: il
trascritto è incompleto, la misura no. Le righe portano `costo_pavimento` e la
console lo dice.

## Nota operativa

Il registro degli agenti che il runtime dei workflow interroga è una fotografia
presa all'avvio della sessione. Nella sessione in cui un file `lab-*` viene
creato il workflow fallisce subito con `agent type '...' not found`: serve **una
sessione nuova**. Da lì in poi:

    Workflow({scriptPath: ".claude/workflows/indicatore-lite.js", args: ["ter-6"]})
    Workflow({scriptPath: ".claude/workflows/indicatore-lite.js"})   // lo sceglie la coda

Un agente nuovo va anche **dichiarato nella suite**:
`tests/integration/test_docs_match_the_code.py` elenca per nome chi non ha un
perimetro nel cancello, ed è l'unico modo di accorgersi che ne è comparso uno
senza che nessuno abbia deciso dove sta. I sei `lab-*` sono nell'insieme `lite`.

Se un tipo `lab-*` continua a non comparire, il primo sospetto è il frontmatter:
un `description` su una riga sola che contiene `: ` non è YAML valido e il file
viene scartato in silenzio. **Vale identico per le skill**, e lì non si vede
proprio: una skill scartata non viene precaricata e l'agente lavora senza, senza
che niente lo dica. Due delle tre skill nuove erano così. Si controllano
tutti insieme:

    bin/py -c "import glob,yaml
    for p in glob.glob('.claude/agents/*.md') + glob.glob('.claude/skills/*/SKILL.md'):
        try: yaml.safe_load(open(p).read().split('---')[1])
        except Exception as e: print(p, e)"

La cura è lo scalare a blocco `>-`, che è come sono scritti adesso tutti i
`description` di questa catena.

Adesso il controllo è anche un test: `tests/integration/test_docs_match_the_code.py`
carica il frontmatter di ogni agente e di ogni skill, verifica che le skill
precaricate esistano e che ogni `bin/py -m` citato sia un modulo vero. Alla
prima esecuzione ha trovato due difetti che nessuno vedeva.
