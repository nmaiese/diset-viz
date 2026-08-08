# La pipeline lite

Una seconda catena editoriale, indipendente da `officina/` e `packs/`, tenuta al
minimo apposta: serve a misurare quanto della macchina attuale sia necessario.
Non sostituisce niente e non tocca `content/`.

```
  ter-6, oppure niente e la sceglie la coda
    |
 [1] lab-dossierista   Bash, haiku    bin/py -m lab.dossier      -> data/lab/dossier/<codice>.json
    |
 [2] tre scout in parallelo, lenti distinte, ciechi l'uno all'altro
    |  lab-scout        Web, sonnet   che cosa è successo: eventi datati
    |  lab-scout-europa Web, sonnet   dove sta l'Italia, con le trappole di comparabilità
    |  lab-scout        Web, sonnet   perché conta: conseguenze documentate
    |
 [3] lab-scrittore     Read, sonnet   una bozza sola. Tesi, temi, numero di sezioni,
    |                                 ordine, titoli e link: decide tutto lui
 [4] lab-verificatore  Bash+Web, opus bin/py -m lab.controlla --salva  -> data/lab/bozze/<codice>.json
    |                                 cifre, fonti rifetchate, link risolti
    |                                 smentite? [3] corregge una volta sola
    |                                 ancora smentite? non si scrive niente
 [5] lab-pubblicatore  Bash, haiku    bin/py -m lab.pubblica --bozza   -> data/lab/articoli/<key>.json
```

Nove agenti per articolo nel caso peggiore, quindi **un codice per run**.

Le differenze che contano rispetto a `.claude/workflows/produci-indicatori.js`:

| | catena attuale | lite |
| --- | --- | --- |
| bozze per articolo | due, più giudizio cieco e selezione | una |
| contesto esterno | corpus preesistente in `data/corpus/` | tre scout web per run, lenti distinte, claim non persistiti |
| chi sceglie l'angolo | `packs/angles.py`, punteggio calibrato sui quantili | chi scrive, quando ha tutto davanti |
| forma dell'articolo | quattro sezioni, un ruolo ciascuna | variabile: ruoli ripetibili, ordine e titoli scelti |
| cancello | `scripts/pipeline_gate.py` + lint bloccante | nessuno |
| unico controllo | 14 regole di lint, di cui 8 bloccanti | cifre, fonti e link inventati, giudicati dal verificatore |
| codice | `officina/` 1473 + `packs/` 1789 righe | `lab/` 1342 righe |
| dove scrive | `content/indicators/` | `data/lab/articoli/` |

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
pagina è indicizzabile) e ci aggiunge i due filtri che la lite vuole, il dato
dell'anno chiesto e la pagina non già completa.

Numeri di oggi: la coda dice **0 articoli con vintage arretrato**, quindi il
`+100` non scatta mai. Incrociandola con la freschezza restano **96 pagine con
dati 2025, indicizzabili e incomplete**: 62 `bes`, 23 `ims`, 11 `ter`, di cui 83
a 2/4 e 13 a 0/4.

Su una pagina a 2/4 la lite scrive un **articolo intero concorrente** in
`data/lab/`, non una toppa alle due sezioni mancanti: è un'operazione diversa
da quella della catena vera, e il confronto va letto sapendolo.

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

- **Le cifre**, contro i valori del dossier, con la tolleranza di officina
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

Nella catena attuale i link sono validati solo dalla suite, che gira su
`content/indicators/` e non vede i file della lite.

## Il testo passa in un prompt una volta sola

Fra lo scrittore e il verificatore. Da lì in poi viaggia come file:
`lab.controlla --salva` congela la bozza giudicata e ne stampa l'`impronta`
(caratteri, parole, cifre, sezioni, fonti, calcolata su lead, sezioni **e**
testo e url delle fonti); il workflow ricalcola la stessa impronta sulla bozza
che ha in mano e, se non coincide, ferma l'articolo invece di scriverne uno
diverso da quello verificato.

Le due implementazioni devono restare identiche. L'unico punto in cui hanno già
divergito: `isdigit()` in Python è vero anche per l'esponente di `km²`, che
`\d` in JavaScript non conta, quindi si usa `isdecimal()`. Se si tocca una delle
due, si verifica così:

    bin/py -m lab.controlla ter-6 --bozza bozza.json | grep impronta

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
  gli H2 come li vedrebbe un lettore. È l'unico modo di controllare la forma di
  un articolo che nessuna pagina rende, perché `data/lab/articoli/` non è
  letto da niente.

## Il lint è un metro, non un cancello

`lab.pubblica` scrive **prima** e misura **dopo**, chiamando
`officina.lint.lint_entry` dentro un try/except. I rilievi finiscono nell'uscita
del comando, compresi quelli che nella catena attuale bloccano. Due regole non
si applicano alla lite e vanno lette sapendolo: `angolo-non-rilevato` (la lite
non produce gli angoli calibrati di `packs/angles.py`, quindi l'angolo scelto è
registrato come `angolo_scelto`) e `gemello`, che confronta con gli articoli
pubblicati.

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
1,62 $ il solo scout web (uno stadio che la catena attuale non ha). La fetta
confrontabile con la catena attuale, dossier più scrittura più verifica più
pubblicazione, è **2,37 $**. La catena attuale misura 1,97 $ per articolo, ma
senza nessuna ricerca di contesto.

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
  `data/lab/articoli/13.json`, 782 parole, due giri di correzione, un solo
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

## Come si confrontano le due pipeline

1. **Un codice `ter-*` per run**, senza articolo committato: la definizione
   ufficiale esiste solo per la famiglia territoriale, quindi le due pipeline
   ricevono lo stesso input. Nel repository ce ne sono 195. Un codice e non due,
   perché la lite adesso spende nove agenti per articolo nel caso peggiore e il
   consiglio di sessione è `medium`, sotto i quindici.
2. Le due run **in serie**: agenti in parallelo sullo stesso HEAD collidono.
3. Costo e turni: `bin/py scripts/baseline_tokens.py --workflow wf_… --articles N`,
   separando la fetta contesto dal resto come si è fatto alla prima run.
4. Qualità: l'agente `giudice-cieco`, che esiste già, legge i due testi senza
   sapere da dove vengono.

Poi **una seconda run della sola lite su un `bes`/`ims` a 0/4**, dove la
definizione ufficiale non esiste: è lì che si vede se l'assorbimento della
definizione nel blocco "Come leggere il dato" funziona davvero, e sono 85 delle
96 pagine della coda 2025.

Attenzione a due cose nel confronto dei costi. I modelli della lite sono scelti
per ruolo (haiku, sonnet, opus) mentre gli agenti della catena attuale girano
tutti su `inherit`: il delta mescola architettura e tier, e per isolare
l'architettura serve un giro della lite con `model: inherit` ovunque. E la lite
adesso fa tre ricerche web dove la catena attuale non ne fa nessuna: la fetta
contesto va tolta prima di confrontare, o si confrontano due cose diverse.

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
che niente lo dica. Due delle tre skill della lite erano così. Si controllano
tutti insieme:

    bin/py -c "import glob,yaml
    for p in glob.glob('.claude/agents/*.md') + glob.glob('.claude/skills/*/SKILL.md'):
        try: yaml.safe_load(open(p).read().split('---')[1])
        except Exception as e: print(p, e)"

La cura è lo scalare a blocco `>-`, che è come sono scritti adesso tutti i
`description` della lite.

Fuori dalla lite ne resta uno rotto, `.claude/agents/scrittore-indicatore.md`
della catena attuale: non è stato toccato qui perché cambiare un prompt di
quella catena vuole il giro di canary di `docs/CANARY.md`, e farlo alla vigilia
del confronto fra le due pipeline confonderebbe la misura.
