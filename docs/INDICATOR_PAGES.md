# Regole per le pagine indicatore

Le pagine indicatore devono aiutare una persona a capire il dato, confrontare i
territori, verificare la fonte e riusare la serie. Non sono contenitori SEO
riempiti con frasi intercambiabili.

## La pagina, in tre zone

Un solo template (`app/templates/indicator_page.html`) serve tutte e quattro le
famiglie: indicatori territoriali, Eurostat, BES e Multiscopo. Prima ce n'erano
due, con due modelli dati diversi, e le pagine sono andate alla deriva.

1. **Il cruscotto.** Tutti i numeri della pagina, una volta sola, in alto.
   Riga dei fatti, switch di livello territoriale dove esistono regioni e
   province, slider dell'anno, selettore del territorio a fuoco, una riga di KPI
   e le tre viste (mappa, classifica, serie storica). È l'unica parte interattiva.
2. **L'articolo.** Quattro sezioni in ordine fisso, un unico blocco di prosa,
   nessuna card o tessera in mezzo ai paragrafi.
3. **L'apparato.** Fonti, definizione originale, perimetro del calcolo, verso
   dell'indicatore, come nasce il testo, come citare, immagine da condividere,
   indicatori correlati, percorso.

**La testa della vista provinciale** segue il livello. Il titolo tiene sempre
la coda " per provincia" (`seo_titles._province_title`): se sfora si rinuncia
nell'ordine all'unita', al nome intero (per il nome breve di
`indicator_notes.SHORT_NAMES`), all'accorciamento con guardia, alle cifre
(", dati {anno}") e all'anno. L'H1, dove non ce n'e' uno scritto, e' "{nome}
nelle province italiane", composto da `views._page_h1` e mai scritto dentro
`article["h1"]`, che `page_title` leggerebbe. Frase-risposta e description
sono la stessa frase (`seo_titles.province_answer`): gli estremi coi
territori fra parentesi, e la distanza piu' ampia dentro una regione
(`in_region`, `from_place` per le preposizioni). Dataset e briciola sono per
livello, e sulla vista province di una scheda a due livelli la briciola finisce
in "Province". Nelle linguette la voce corrente non e' un link, e ogni altra
voce porta all'URL del suo livello (`lv["preferred_path"]`): la base per le
regioni, la `/province` per le province, mai un `?livello=`. I link verso
l'altro livello o la gemella dicono di che cosa parlano ("Speranza di vita
nelle 107 province").

**La vista provinciale e' una pagina a se'** (dal 25 settembre 2026):
`/indicatore/<slug>/<codice>/province`, per ognuna delle 34 schede a due
livelli, con canonical su se stessa, `Content-Location`, robots e dataset
presi dal livello (`level["canonical_path"]`). Ogni altro indirizzo, `?livello=`
compreso, fa un 301 in un salto solo li', tenendo `anno` e `regione`; una
scheda senza province risponde 404 sulla `/province`. Le schede solo
provinciali restano sul loro URL base.

- **La regola 17/17.** Una `/province` e' indicizzabile quando il suo livello
  provinciale passa la regola di `bes_data.all_bes_indicators` (copertura
  almeno 0,8 e anno almeno 2023, `indicator_view.level_passes_rule`): 17
  `index`, 17 `noindex, follow`. La prova sta in `tests/integration/`, e un
  numero che cambia va capito, non ritoccato.
- **L'interruttore** `seo_policy.LEVEL_PAGES_INDEXABLE`: spento, tutte le
  `/province` diventano `noindex, follow` ed escono dalla sitemap, mentre link
  e 301 restano. E' il modo di tornare indietro se Google le fonde con la base.
  Le `/province` si somigliano fra loro al 62%: si guarda Search Console prima
  di decidere.
- **Chi le elenca** legge `indicator_universe.level_pages()`, una voce per
  pagina di livello indicizzabile (la base di ogni scheda e le sue `/province`
  che passano): sitemap, llms-full, `/catalogo-dati` e
  `scripts/duplicazione.py`. `level_pages(listed=True)` tiene anche quelle che
  l'interruttore spento toglie dall'indice, e la usa la ricerca: l'interruttore
  toglie l'indice, non i link. `indexable_catalog()` resta una voce per
  scheda.
- **Il confronto fra province** offre le stesse schede, quelle con la
  `/province` in `level_pages(listed=True)`, e la `/province` di ognuna
  propone "Metti a confronto le province" (`confronto.compare_path`, nella
  corsia "Lo stesso dato, altre viste"), verso
  `/confronto?indicator=<id>&livello=provincia`. E' l'unico `livello=` che una
  `/province` puo' contenere, e le guardie tolgono solo quell'href prima di
  cercarlo.
- **La somiglianza** delle `/province` si misura a parte:
  `bin/py scripts/duplicazione.py --solo province` (e `--solo basi` per le
  sole basi). I tetti stanno in `tests/integration/test_duplicazione_schede.py`,
  66% per il racconto e 75% con il metodo, su tutte le `/province`
  indicizzabili.

**Il title delle BES omonime.** Le tre BES che hanno il nome di una
territoriale con cifre diverse (`taxonomy.SAME_NAME_BES_IDS`: 10AMB008,
12SER006, 12SER025) portano la famiglia fra parentesi nell'H1 e, dal 25
settembre 2026, anche nel `<title>` della vista regionale
(`seo_titles._same_name_qualifier` dentro `answer_title`, etichetta da
`sources.family_short_label`). Il qualificatore ha la precedenza su unita',
coda del livello e cifre, che a sessanta caratteri non ci stanno: e' l'ordine
di `_province_title` capovolto, perche' qui cio' che distingue due pagine e' la
fonte. Le territoriali gemelle non cambiano.

**Il corpo della vista provinciale** e' fatto per chi cerca la sua provincia.
Vale per le `/province` delle schede a due livelli e per le
schede solo provinciali, e le compone `app/design/pages/indicatore.py`.

- **"Dentro le regioni"**, dopo la mappa e la classifica: un titolo che afferma
  ("La distanza piu' ampia e' in Sicilia, 41,3 punti da Trapani a Palermo") e
  una riga per ogni regione con piu' di una provincia (la piu' alta, la piu'
  bassa, la distanza), coi link a `/regione/<key>` e `/provincia/<key>`. Il
  verso si dice a parole. Titolo, frase-risposta e blocco leggono la distanza
  da una funzione sola, `seo_titles.region_gaps`, che arrotonda ai decimali
  della colonna e a pari distanza ordina per nome. Con una parita' in testa il
  titolo nomina tutte le regioni pari.
- **Ogni riga della classifica** ha `id="p-<key>"`, e `:target` la evidenzia
  anche senza JavaScript (`scroll-margin-top` la tiene fuori dalla barra delle
  sezioni). `/provincia/<key>` linka la scheda direttamente su quella riga.
- **"Trova la tua provincia"** accende la riga e scrive in una live region
  "Pavia: 82,6 anni, 86ª su 107"; accanto, il link "Vai alla riga nella
  classifica" la porta a vista (le frecce sul campo non fanno scorrere la
  pagina).
- **La classifica a 107** mostra le prime 10 e le ultime 10, le altre nello
  stesso DOM dentro un `details`. Il cambio d'anno ridisegna le righe senza
  perdere id, `details` e riga accesa.

Le prove stanno in `tests/integration/test_province_body.py`.

**Le province.** Il cruscotto ha la mappa per tutti e due i livelli. Quella
delle province la compone `app/design/pages/indicatore.py`, con i contorni di
`design.maps` e la stessa rampa a sei gradini della home, mentre
`LEVELS["provincia"]["has_map"]` resta falso perché lo leggono il template di
ripiego e il vecchio esploratore, che hanno solo le regioni. Quando il livello
che manca a una scheda sta in un'altra pagina (la speranza di vita regionale,
ter-910, e quella con le province, bes-01SAL001), il view model porta `twin`
(`indicator_view.twin_level`, dalle coppie di `taxonomy.PROVINCE_TWINS`): il
selettore Regioni/Province ha la voce della gemella come le altre, la corsia
"Lo stesso dato, altre viste" dice "La stessa misura per province", e il
Markdown lo scrive. Chi linka una scheda da un contesto provinciale usa
`bes_data.bes_level_path(id, "provincia")`, che restituisce la `/province`
delle schede a due livelli (`sources.level_path`) e il canonico delle schede
solo provinciali.

**La coppia ter-910 e bes-01SAL001** e' un caso a se'. La vista regionale di
bes-01SAL001 e' identica a ter-910 in ogni cella, quindi ha il **canonical su
ter-910** (`indicator_view.canonical_elsewhere`, da
`taxonomy.REGIONAL_CANONICALS`) **senza noindex**: resta raggiungibile, ma
sitemap, llms-full e `/catalogo-dati` non la elencano e al suo posto elencano
la sua `/province`, e le linguette Regioni delle due schede portano a ter-910.
Il path di arrivo si prende dal catalogo, mai ricostruito: se ter-910 sparisce,
la pagina torna canonica di se stessa invece di puntare a un 404.

Fra l'articolo e l'apparato sta il blocco **«Come leggere il dato»**
(`id="come-leggere"`), reso **sempre** e sempre dopo la narrazione.

La regola che tiene insieme il tutto: **una cifra si mostra una volta**. Il
cruscotto la mostra, la prosa la interpreta. Un paragrafo che rilegge il massimo,
il minimo e la media è la duplicazione che questo layout ha eliminato.

E la regola gemella, arrivata il 22 settembre 2026: **il metodo non sta nel
racconto**. Come si legge il valore, su che perimetro vale il confronto, in che
verso va la graduatoria, chi scrive il testo: sono frasi che valgono uguali su
ogni scheda, e dentro l'articolo erano l'unica cosa che un lettore trovava
identica altrove. Il 42,5% delle parole dell'articolo medio viveva dentro una
sequenza di otto parole ripetuta su più di cinque pagine, e una sola frase
stava su 269 pagine su 372. Adesso il metodo vive in «Come leggere il dato» e
nell'apparato, e il racconto è sceso al 26,8%.

Il numero lo misura `bin/py scripts/duplicazione.py`, che ne stampa **due**:
solo l'articolo, e articolo più blocco del metodo. Il secondo c'è perché
altrimenti spostare una frase da una stanza all'altra farebbe scendere la
misura senza che niente sia cambiato per chi legge.

## Chi possiede che cosa

| | proprietario | dove |
|---|---|---|
| numeri, aggregati, ordinamenti | `app/indicator_view.py` | cruscotto |
| prosa scritta | `content/indicators/<chiave>.md` | articolo |
| prosa composta, quando manca la scritta | `app/templates/_indicator_article.html` | articolo |
| fonte, copertura, citazione, disclaimer sulla media | template | apparato |
| perimetro del confronto, verso dell'indicatore, come nasce il testo | template | apparato |
| come si legge il valore (`explain.example`, `scope`, `reading`) | `app/indicator_notes.py` | blocco «Come leggere il dato» |

`app/indicator_view.py` è il modello dati unico. Espone `meta` (tutto ciò che non
dipende da un territorio) e `levels` (una voce per livello territoriale, ciascuna
con i propri anni, osservazioni, aggregati e confronto annuale). Non duplicare
quei calcoli altrove.

## Dove vive la prosa: un file per articolo

`content/indicators/<chiave>.md`, con i due punti della chiave scritti `__`:
`bes:10AMB004` sta in `content/indicators/bes__10AMB004.md`. Un frontmatter con
i campi, poi il lead, poi le sezioni, ognuna aperta da `<!-- sezione: ruolo -->`
e con il suo `## titolo`. Lo store è `scripts/indicator_store.py`, che possiede
il formato e la codifica e li spiega per intero.

Era un JSON unico da 365 voci sotto `app/static/data/`, e il formato costava due
cose distinte. Scrittore e revisore (due agenti che allora esistevano)
condividevano il perimetro e giravano tutti e due ogni giorno, quindi ogni loro
modifica riscriveva l'intero file e due run vicine su articoli diversi finivano
in conflitto su qualcosa che nessun agente
può risolvere leggendolo. E il diff di una revisione non diceva di quale
indicatore parlasse, perché la chiave che possiede le righe cambiate poteva
stare cento righe più su.

Adesso `git log content/indicators/920.md` è la storia editoriale di
quella pagina, e due stadi che lavorano su articoli diversi non hanno niente da
fondere.

Il Markdown è arrivato dopo, il 6 settembre 2026, per la seconda metà della
stessa ragione. In JSON una sezione sta su una riga sola con gli a capo scritti
`\n`: la pull request in cui il pezzo va letto prima di pubblicarlo non lo
mostrava, non lo si poteva commentare riga per riga, e la correzione di una
parola produceva un hunk che nessuno poteva giudicare. Il merge di quella PR è
la pubblicazione, quindi è proprio lì che il testo deve essere leggibile.

Quello che **non** è cambiato: una voce vale per un livello territoriale solo, e
il livello resta un campo dentro la voce. Il modello è ancora una voce per
indicatore, non una per coppia (indicatore, livello).

```bash
python3 scripts/indicator_store.py --list
python3 scripts/indicator_store.py --show ter-920
```

## L'articolo: quattro ruoli

Ordine fisso, titolo `h2` scritto dall'autore. La struttura è uniforme su tutte
le pagine, la superficie no: `content/STYLE.md` vieta lo stesso telaio ripetuto,
e 621 pagine con gli stessi identici H2 si leggono come uno stampo.

- `definizione` — che cosa misura, il perimetro, che cosa vale un singolo valore
- `quadro` — come si distribuisce oggi e che forma ha quella distribuzione
- `dinamica` — come si è mosso, serie lunga e ultimo passaggio tenuti distinti
- `limiti` — che cosa il numero non cattura

Più `lead` (una o due frasi, che sono anche la meta description in SERP), `fonti`
e `vintage`.

**Un ruolo assente non è una sezione vuota.** Il template lo compone dai dati, e
la pagina mantiene lo stesso scheletro. È un fallback funzionante, non una pagina
finita: serve perché il layout sia uniforme su tutti i 621 indicatori mentre solo
una parte è passata da un editor. Lo stato di ciascuno lo calcola
`app/editorial_state.py`, ed è quello che legge la coda della redazione
(`motore coda divarioitalia`, nel repo `redazione-ai`).

Il testo composto **non** viene congelato nel file, di proposito: così non può
invecchiare in silenzio dietro un aggiornamento dei dati, e la guardia sul
`vintage` si applica solo alle frasi davvero scritte da qualcuno.

### `roles_covered`: la definizione può non aprire l'articolo

I quattro ruoli qui sopra sono il default, non l'unica forma possibile. Con la
`definizione` sempre in prima posizione ogni articolo apriva sulla contabilità
prima che sulla notizia, ed è il difetto che il criterio 8 della rubrica
(leggibilità) punisce.

Un'entrata può quindi dichiarare `roles_covered`: la lista dei ruoli che scrive
come `h2`. Se la `definizione` non è fra quelli, non apre più l'articolo.

Il blocco **«Come leggere il dato»** (`id="come-leggere"`) è composto
server-side dai metadati `explain` e reso **dopo** la narrazione, mai prima: il
blocco esiste per togliere la contabilità dall'apertura, non per rinominarla.
Dal 22 settembre 2026 si rende **su ogni scheda**, non solo quando la
definizione è assorbita, perché è l'unico posto dove `example`, `scope` e
`reading` vivono: una scheda senza non direbbe più in che verso si legge la sua
graduatoria. L'unica cosa che dipende ancora da com'è fatta la scheda è
`explain.plain`, che compare solo quando non lo sta già dando il lead composto
o una sezione `definizione` scritta.

Le regole, tutte meccaniche:

- **Solo la `definizione` è omettibile.** `quadro`, `dinamica` e `limiti`
  restano sempre, anche se una dichiarazione parziale non li nomina: il blocco
  copre quel ruolo lì e nessun altro.
- **Il campo è opt-in e additivo.** Senza `roles_covered` la pagina rende i
  quattro ruoli come ha sempre fatto, e i trecento articoli esistenti non
  cambiano di un byte.
- **Ed è usabile.** Fino ad agosto 2026 non lo era: un test asseriva che
  l'elenco degli articoli opt-in fosse *vuoto*, quindi il solo meccanismo
  costruito per non aprire sulla definizione era progettato, implementato,
  documentato qui, e vietato. Zero file su 375 lo usavano, mentre 52 articoli
  su 52 aprivano allo stesso modo: il freno di sicurezza di un rilascio
  graduale era diventato il motivo per cui il rilascio non partiva. Adesso la
  guardia controlla la coerenza di chi opta, non il fatto che qualcuno opti.
- **Un ruolo assorbito non è un ruolo mancante.** La coda della redazione e
  `scripts/pending_notes.py` contano contro i ruoli emessi, altrimenti chi
  scrive troverebbe per sempre la `definizione` «da scrivere» e la
  riscriverebbe a ogni giro.
- **Assorbire la definizione cambia l'impronta della prosa.** Cambia cosa la
  pagina mostra senza toccare una parola, quindi
  `app/editorial_state.impronta_prosa` mescola l'insieme dei ruoli emessi: due
  entry con le stesse parole e `roles_covered` diverso non sono la stessa
  pagina, e il cruscotto non deve leggerle "in linea" l'una per l'altra.
  Dichiarare tutti e quattro i ruoli invece non muove l'impronta, perché la
  sequenza emessa resta quella di sempre.
- **La navigazione segue.** La domanda di definizione punta a `#come-leggere`
  invece che a `#sezione-definizione`, che in quella forma non esiste.

**Un articolo vale per un livello territoriale solo.** Cita le cifre di quel
livello, quindi non può viaggiare sull'altro: i 31 BES a due livelli avevano un
lead che nominava l'Umbria e dava la media delle regioni sopra un cruscotto di
province. Un'entrata dichiara il livello che descrive con il campo `level`, che
vale `regione` quando manca, e viene usata solo lì. Su ogni altro livello la
pagina ricade sullo scheletro composto, che legge il livello che gli viene dato.
Lo garantisce `ProseStaysOnTheLevelItWasWrittenFor` in `tests/integration/test_indicator_texts.py`.

## La forma libera: un articolo che non fa le quattro fermate

I quattro ruoli sono la forma dei dati, non la forma di un racconto:
obbligano ogni pezzo a passare dagli stessi quattro titoli nello stesso ordine,
qualunque cosa i dati abbiano da dire. Una sezione di ruolo **`libera`** porta
il proprio titolo, sta dove l'autore l'ha messa, e non ha nessuno scheletro
dietro: la pagina non la compone se manca, perche' una sezione che nessuno ha
scritto non esiste.

    <!-- sezione: libera -->
    ## Il seggio non e' la poltrona

Basta una sezione `libera` perche' l'articolo sia **esattamente quello che
l'autore ha scritto**, nel suo ordine: nessun ruolo si aggiunge, nessuno
scheletro si compone, e una eventuale `roles_covered` non lo ribalta. La
definizione la copre il blocco "Come leggere il dato", che la pagina compone
comunque dai metadati.

Tre conseguenze che vale la pena sapere:

- **L'ancora nasce dal titolo** (`sezione-il-seggio-non-e-la-poltrona`), non
  dal ruolo: `libera-2` e `libera-3` non dicono niente a chi condivide un link
  e cambiano appena qualcuno riordina il pezzo.
- **Una sezione libera senza titolo non arriva in pagina.** La pagina non ha un
  titolo di scorta da darle e un H2 vuoto e' peggio di una sezione in meno.
  Lettore tollerante, scrittore severo: il renderer la scarta, `motore verifica`
  della redazione la rifiuta prima.
- **La lista di consegna lo sa.** `scripts/pending_notes` rispecchia la regola,
  quindi un articolo libero risulta completo e il produttore non lo rilancia a
  ogni giro chiedendo sezioni che quell'articolo ha deciso di non avere.

I trecento articoli a quattro ruoli non cambiano di un pixel: la forma libera
e' un'aggiunta, non un allentamento.

## Le figure dentro l'articolo

La regola delle tre zone dice che una cifra si mostra una volta, e per questo
l'articolo non ha grafici: mappa, classifica e serie storica stanno gia' nel
cruscotto, e ridisegnarle sotto sarebbe la duplicazione che il layout ha tolto.

Ci sono pero' due cose che il cruscotto non mostra e che nessun'altra pagina
del sito mostra. Non ripetono niente, quindi possono stare nel testo, e si
chiedono con un marcatore nel corpo della sezione.

**La dispersione**: come questo indicatore si dispone rispetto a un altro, una
regione per punto.

```
<!-- grafico: dispersione con=dem-BIRTHRATE evidenzia=Sardegna,Lazio
     didascalia="Le due regioni accese non seguono le altre." -->
```

**Il ritratto**: dove sta **una regione** fra il valore piu' basso e il piu'
alto d'Italia, su piu' indicatori insieme. E' il contesto di un posto, e la
pagina non lo da' da nessuna parte perche' ogni pagina parla di un indicatore
solo. Non porta nessun numero: le unita' di sei indicatori non si confrontano,
e il senso della figura e' la posizione.

```
<!-- grafico: ritratto regione=Sardegna con=ter-921,bes-12SER026,ter-401
     didascalia="Dove sta la Sardegna, e non solo sui figli." -->
```

`con` e' il codice dell'altro indicatore come sta nell'URL, una lista separata
da virgole nel ritratto. `evidenzia` accende i territori che rompono il
disegno, che sono il motivo per cui la dispersione esiste; `regione` dice chi
si ritrae; `didascalia` aggiunge una frase davanti a quella che il sito compone
da solo.

**Si disegna al render, mai salvata.** `app/charts.py` rilegge i valori dei due
indicatori a ogni richiesta, come le sezioni composte del template: un SVG
congelato nel Markdown mostrerebbe i numeri del giorno in cui e' stato scritto,
e un aggiornamento della fonte lo lascerebbe indietro in silenzio.

**Una figura che non si puo' disegnare sparisce e il testo resta intero.**
Indicatore inesistente, dati mancanti, meno di otto territori in comune: il
marcatore viene tolto e non arriva niente in pagina. Il pezzo va scritto perche'
regga anche senza. Il rovescio e' che una figura persa non lascia traccia, e per
questo `motore verifica` della redazione tratta un marcatore che punta a un
indicatore inesistente come un difetto **bloccante**, non come un rilievo.

L'SVG e' `aria-hidden`: una nuvola di punti non si legge ad alta voce. Il
contenuto sta nella `<figcaption>`, che nomina i due indicatori, i due anni,
quante regioni entrano nel confronto e quali sono accese.

## Scrivere un articolo

Si comincia sempre da qui, e **non da questo repo**: il dossier e il brief li
calcola la redazione, in `nmaiese/redazione-ai`.

```bash
motore brief divarioitalia ter-178   # il testo che si mette davanti a chi scrive
```

Il dossier (cifre, angoli, contesto) lo costruisce `motore/dossier.py` di quel
repo e lo scrive qui in `data/lab/dossier/`. Chi scrive un articolo non lancia
niente a mano da questo repo:

Che cosa contiene il brief, sezione per sezione, lo possiede `REDAZIONE.md` §3
del repo della redazione, e il codice che lo scrive e' `motore/brief.py` di
quel repo: qui non si ripete, perche' la descrizione che stava qui (un blocco
`INDICATORI CORRELATI` con `rho`, un pacchetto che stampava il valore di
`level`) era rimasta a una versione che non esiste piu'.

Le regole editoriali complete stanno in `content/STYLE.md`. Le classi di
errore che solo una lettura trova non le trova uno strumento: le trova chi
rilegge. Quello che ferma un pezzo sono le quattro guardie di `motore verifica`
nel repo della redazione, piu' i controlli di struttura (lead, sezioni, ruoli,
fonti con testo e url, marcatori di figura): una cifra fuori dal dossier, un
link interno inesistente, una fonte che non risponde, un link a una fonte nella
prosa che non sta anche nell'elenco. Un'affermazione su un insieme che la
classifica smentisce ("nessuna regione supera X") e la media semplice delle
regioni chiamata media nazionale **non** le ferma nessuna guardia: le trova
chi rilegge. Non c'è una rubrica a punti. Le fonti secondarie
ammesse stanno in [`SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md), insieme a
quello che resta da guardare a mano: un aggregato nazionale ponderato non è la
nostra media semplice delle venti regioni, e le due si possono ancora
accostare come se fossero confrontabili.

## Risposte obbligatorie

Ogni scheda deve rendere visibili, tra cruscotto e articolo:

1. Il nome dell'indicatore e una definizione comprensibile.
2. Il perimetro, compresi popolazione, fascia di età, genere, numeratore,
   denominatore e unità quando disponibili nella definizione della fonte.
3. Un esempio numerico che spieghi che cosa rappresenta il valore.
4. La direzione, oppure l'assenza di una direzione univoca.
5. Il limite principale e ciò che il dato non consente di concludere.
6. L'ultimo anno, la copertura territoriale, la fonte e i download disponibili.
7. Il confronto con l'anno precedente disponibile.
8. Il trend di lungo periodo, quando esistono almeno due anni confrontabili.
9. Un collegamento all'atlante, alla metodologia, al tema o a un indicatore
   strettamente collegato.

La denominazione amministrativa originale può restare nei metadati e nel blocco
della fonte. Il testo principale deve tradurla in italiano chiaro senza cambiare
il significato statistico.

## Confronto con l'ultimo anno

Il confronto usa l'ultimo anno pubblicato e l'anno precedente effettivamente
disponibile nella stessa serie. Se manca un anno intermedio, il testo deve indicare
entrambi gli anni e non deve chiamarlo confronto annuale.

Regole di calcolo e scrittura:

- Confrontare solo i territori con un valore in entrambi gli anni.
- Dichiarare quanti territori compongono la base comune.
- Chiamare il risultato `media semplice dei valori regionali`, non `media
  Italia` o `media nazionale`.
- Per tassi e quote percentuali, esprimere le variazioni in punti percentuali.
  Vale anche per la variazione di lungo periodo: accostare un "9,8% in più" a un
  livello del "54,87%" mette due percentuali di natura diversa nella stessa
  frase. Il modello espone `meta.percentage_like` proprio per questo.
- Indicare quante regioni aumentano, diminuiscono o restano stabili.
- Mostrare la maggiore diminuzione e il maggiore aumento solo se esistono.
- Usare `migliora`, `peggiora` o `favorevole` solo quando la direzione
  dell'indicatore è revisionata.
- Per indicatori contestuali descrivere soltanto aumento, diminuzione o
  stabilità.
- Non attribuire cause a una variazione osservata.

Se la serie ha un solo anno, la pagina deve dichiarare che il confronto temporale
non è disponibile. Non va costruita una frase sostitutiva.

## Trend di lungo periodo

Il confronto tra primo e ultimo anno resta separato dalla variazione più recente.
Deve indicare gli anni, l'unità e la base territoriale.

Il primo anno è il primo con dati veri, non quello dichiarato nei metadati:
quattro indicatori dichiarano un anno iniziale per cui nessuna regione ha un
valore, e il vecchio codice per questo ometteva del tutto il trend.

## Ordinamento e parità

Un solo ordinamento per tutte le famiglie: valore più alto per primo, e la
direzione decide se il primo è il migliore. Gli indicatori contestuali non hanno
un migliore, quindi `best` e `worst` restano vuoti e la classifica ordina soltanto.

Le parità si rompono per nome. Non è un dettaglio estetico: prima i territori a
pari valore restavano nell'ordine del CSV e una delle due vecchie strade
rovesciava la lista, quindi quale di due regioni identiche venisse chiamata
"migliore" dipendeva dall'ordine delle righe in un file di dati e poteva cambiare
a ogni ricarico. Quel nome finisce nella prosa.

## Accuratezza

- La definizione della fonte è il riferimento principale.
- Numeratore e denominatore non vanno dedotti quando la fonte non li esplicita.
- Una media regionale non sostituisce un indicatore nazionale ponderato.
- Una correlazione territoriale non dimostra una causa.
- Una graduatoria non dimostra l'efficacia di una politica.
- Totale, uomini e donne sono perimetri distinti e non vanno confusi.
- Un divario tra due tassi va espresso in punti percentuali e non descrive da
  solo il livello complessivo dei due tassi.

## Che cosa è verificato e che cosa no

`tests/integration/test_indicator_texts.py` copre la parte meccanica:

- struttura, ruoli noti e non duplicati, punteggiatura editoriale, `vintage` e
  risoluzione dell'indicatore,
- lunghezza della prima frase del `lead`, che deve reggere da sola in SERP,
- H2 scritti a mano non riutilizzati su più indicatori,
- **ogni cifra con decimale attribuita a una regione** ("il 24,3% del Molise")
  confrontata con il dato di quell'anno,
- **ogni soglia asserita su un elenco di regioni** ("supera il 78% in A, B e C")
  verificata regione per regione,
- **ogni link interno nella prosa**: forma canonica (mai `/?indicator=` né
  `/atlante?indicator=`, che arrivano alla scheda solo via JavaScript), un
  indicatore che esiste davvero, un percorso che il sito serve, e un'anchor che
  dice dove porta invece di "clicca qui".

Le ultime due nascono da errori reali: una nota diceva che l'affollamento
carcerario supera "ovunque" la capienza mentre tre regioni erano sotto, e
un'altra metteva la Sardegna sopra il 78% di differenziata quando stava al
76,6%. Un intero senza decimale non viene controllato, perché in questa prosa è
quasi sempre un'approssimazione ("circa 27%", "quasi 78%").

`tests/integration/test_indicator_view.py` copre i numeri: ogni aggregato di tutti i 621
indicatori è confrontato con una fixture estratta dal codice precedente, e ogni
pagina viene resa per verificare che non ci siano 500.

Restano **fuori dai test**, e vanno rivisti a mano. Non a memoria, però:
`motore coda divarioitalia` cerca esattamente questi pattern e
mette in fila gli articoli per quanto è probabile che siano sbagliati. Li
rilegge la redazione, dove chi scrive si rilegge il proprio testo e a valle il
verificatore indipendente prova a smentirlo.

Un articolo firmato porta **due** campi, `reviewed_at` e `reviewed_vintage`, e
solo con entrambi esce dalla coda. I due campi restano vivi anche adesso che
nessun agente firma: li scrivevano il revisore e poi il produttore della catena
ritirata, e oggi la redazione riscrive l'articolo intero con `motore pubblica`. Il
secondo è il `vintage` che chi ha riletto aveva davanti: quando l'articolo si
aggiorna su un anno nuovo tutte le
cifre cambiano, i due valori smettono di combaciare e l'articolo **rientra** in
coda col segnale `rilettura`, che pesa più di ogni segnale di rischio. Gli altri
marcano una frase che potrebbe essere sbagliata, quello marca un articolo in cui
non è stato controllato niente.

- le affermazioni universali su un andamento ("è cresciuto ovunque"): il brief
  ha un blocco apposta, `SI MUOVONO CONTROCORRENTE`,
- le attribuzioni causali ("grazie a", "spinto da"): o si documentano o si
  riformulano come contesto, non come causa accertata,
- i confronti con l'estero ("tra i più alti d'Europa"): richiedono una fonte in
  `fonti`, verificata, altrimenti vanno tolti,
- **una provincia scritta con un nome che il dataset non usa** ("Reggio Emilia"
  per "Reggio nell'Emilia"): la guardia non trova il nome e passa. Manca
  copertura, non inventa un errore. Fino ad agosto 2026 qui c'era un buco molto
  più largo, cioè l'intero livello provinciale: la regex elencava a mano le venti
  regioni, quindi 67 indicatori su 103 province non erano verificati da niente e
  le guardie restavano verdi senza incontrare un solo nome. Ora l'elenco dei
  territori si deriva dai dati, e `test_the_guard_actually_reaches_the_provinces`
  fallisce se la copertura si rispegne,
- **se l'incrocio con un altro indicatore è onesto**: il verbo calibrato sulla
  prova (una correlazione di rango è una co-occorrenza, non un meccanismo), il
  confondente nominato, almeno un'eccezione al pattern. Le guardie controllano
  che il link funzioni, non che la frase intorno regga.

A metà strada c'è `scripts/prose_lint.py`, che non fa fallire niente e conta: i
tell da bot che `content/STYLE.md` nomina, articolo per articolo, e il totale del
catalogo. Serve a scegliere il lotto da rileggere e a misurare se un giro di
riscritture ha spostato qualcosa, invece di stabilirlo a occhio.

```bash
python3 scripts/prose_lint.py --show 178
python3 scripts/prose_lint.py --summary
```

## La definizione, che è un'altra cosa dai numeri

Tutto quello che sta qui sopra confronta l'articolo con **la serie**. Nessuna di
quelle guardie confronta l'articolo con la **definizione della fonte**, e questa
è la distinzione che conta: un numero sbagliato muore al primo lettore che apre
il brief, una definizione sbagliata sopravvive a ogni rilettura che controlla
l'aritmetica, perché l'aritmetica è giusta.

Non è un'ipotesi. Rileggendo undici articoli contro i dati non è uscito **un
solo errore di calcolo**, e sono uscite quattro descrizioni sbagliate di che
cosa l'indicatore conta. `ter-402` chiamava "imprese a guida femminile" quello
che Istat definisce come titolari donne di imprese individuali, e lo ripeteva
nella sezione `limiti`, cioè nel punto che serve a dire che cosa l'indicatore
non misura. `ter-72` scriveva "almeno dieci addetti" dove la fonte dice "più di
dieci addetti", che è un'altra popolazione con le stesse parole.

Le definizioni di fonte sono in due archivi committati. Il primo viene dal
foglio `Metadati` di `Metainformazione.xls` della Banca dati territoriale. Il
secondo federa i metadati BES e BES dei Territori, le codelist SDMX delle
indagini Multiscopo e demografiche, i metadati Eurostat e le serie locali che
il vecchio foglio territoriale non contiene:

```bash
python3 scripts/fetch_definitions.py            # riscrive data/definitions/istat_territoriali.csv
.venv/bin/python scripts/fetch_federated_definitions.py  # riscrive data/definitions/federated.csv
python3 scripts/definition_check.py --show ter-402
python3 scripts/definition_check.py --summary
```

`scripts/xls_reader.py` legge il `.xls` con la sola libreria standard, perché
gli script della catena girano su un checkout pulito prima che esista un venv.
Il fetcher federato usa invece l'ambiente del progetto: legge i workbook `.xlsx`
e interroga le strutture SDMX con cache e rispetto del limite della fonte. Ogni
riga conserva URL e riferimento preciso al workbook, alla codelist o al dataset
da cui deriva.

Il confronto è **lessicale e lo dichiara**: cerca le parole su cui poggia la
definizione ufficiale e chiede se l'articolo le usa mai. Un sinonimo risulta
mancante, e un articolo può usare tutte le parole giuste e descrivere lo stesso
la cosa sbagliata. Quattro segnali, in ordine di quanto vale fidarsene:

| segnale | che cos'è |
| --- | --- |
| `contraddizione` | l'articolo dice una cosa **diversa**, non una in meno: la classe di età della fonte non compare e ne compare un'altra, oppure "almeno N" dove la fonte dice "più di N". È l'unico che afferma invece di suggerire |
| `base` | il denominatore che la fonte nomina non compare nella `definizione` scritta |
| `soglia` | una soglia o una classe di età della fonte non compare da nessuna parte nell'articolo |
| `termini` | l'articolo riprende meno di un terzo delle parole portanti della definizione. È la rete più larga e la più rumorosa, e per questo **non** entra nella coda |

I primi tre diventano il segnale `definizione` di `scripts/prose_lint.py`, che
pesa più di ogni altro, `rilettura` compreso. `scoperto` significa che il codice
non ha trovato una riga nell'archivio federato: non equivale mai a un controllo
superato e segnala che una fonte nuova o non aggiornata va recuperata.

## SEO e struttura

La pagina serve prima di tutto gli intenti di definizione, confronto, fonte e
riuso del dato. Titolo, descrizione, H1 e testo visibile devono essere coerenti.
Ogni pagina indicizzabile deve avere:

- titolo e descrizione unici
- una sola H1 descrittiva
- fonte, periodo, territorio e unità visibili
- HTML server-rendered con testo utile anche senza JavaScript, cruscotto compreso
- canonical autoreferenziale
- `Dataset` JSON-LD la cui `description` è il lead che il lettore vede davvero
- `BreadcrumbList` JSON-LD

Il titolo lo compone `seo_titles.page_title`, con la formula "{nome} per
{livello}, {da A a B}{unita'}" e la coda del livello anche nel ripiego
(`indicator_notes.seo_title(..., tail=)`). Quando il nome non ci sta,
l'accorciatore taglia a una giuntura, ma tiene almeno due parole, non butta
una negazione e, sulle province, nemmeno cifre, sigle e soglie. Dove nessun
taglio regge, il nome breve e' scritto a mano in `indicator_notes.SHORT_NAMES`,
una riga per (codice, livello) riletta contro la definizione del manifest.
`seo_titles.UNVERIFIED_EXTREMES` elenca le schede i cui estremi non vanno in
titolo, description e Dataset finche' non sono verificati (bes-06POL012P:
Fermo al 358% nel 2024, dal 116% dell'anno prima). Gli zeri di Macerata e
Savona dal 2016 non erano una misura, erano province senza posti regolamentari
da contare: `bes_data.NOT_MEASURED` li toglie in `get_bes_rows`, l'unico punto
da cui passano scheda, mappa, pagina provincia, qualita' della vita, llms e
API, e ognuno li vede n.d. La description nomina
i pari merito ("in 16 province") e conta i territori col dato, e il Dataset
non porta Markdown.
- link alla metodologia e al contesto tematico

Niente `FAQPage`: la FAQ generata rileggeva massimo, minimo e media, cioè quello
che il cruscotto mostra già, ed è stata rimossa insieme al suo schema.

Gli stati di esplorazione (`?anno=`, `?regione=`) sono stati della stessa
pagina, mai documenti nuovi: restano `noindex` e il canonical punta all'URL del
livello. `?livello=` sta ancora nell'elenco ma non rende piu' una pagina: fa un
301 alla `/province` o alla base. L'elenco sta in `app/seo_policy.py:EXPLORE_PARAMS`, e va tenuto
aggiornato quando se ne aggiunge uno.

Non aggiungere paragrafi di riempimento. Le varianti quasi duplicate, incomplete
o obsolete seguono le regole di indicizzazione definite in `app/profiles.py`.

### Perche' le serie sono piu' delle schede in sitemap

L'atlante dichiara tutte le serie regionali del catalogo (597 il 26 settembre
2026, il numero lo legge `atlante.rows`), la sitemap solo le schede
indicizzabili. Non ogni serie merita una pagina in indice, e la regola e' una:
`indicator_view.indexability`, che da' anche il motivo del no. Al 26 settembre
2026, sulle 597 serie regionali:

| | serie |
|---|---|
| in sitemap come scheda regionale | 345 (ter 173, bes 113, ims 46, dem 11, eur 2) |
| `copertura`: meno di 20 regioni o completezza sotto 0,98 (ter 110, bes 3, ims 2) | 115 |
| `variante`: la meta' maschile o femminile di una serie che ha il totale (ter 60, dem 2) | 62 |
| `vecchia`: ultimo anno prima del 2020 per le territoriali, fuori dalla finestra della famiglia per il BES (ter 48, bes 27) | 75 |

La sitemap porta poi 26 schede BES solo provinciali e 17 viste `/province`
di schede a due livelli: 345 + 26 + 17 = 388 URL sotto `/indicatore`. Le
regioni di bes-01SAL001 non ci sono perche' hanno il canonical su ter-910.
Una scheda fuori indice resta una pagina servita, linkata e `noindex, follow`:
il motivo si legge in `meta.indexable_reason`. Fino al 26 settembre 2026 le 48
territoriali vecchie risultavano `copertura`, perche' il payload dell'atlante
non porta copertura e numero di regioni: il motivo ora li prende dal catalogo,
come la regola.

### Redirect e URL definitive

Ogni indirizzo vecchio arriva al canonico con **un 301 solo**, tenendo `anno` e
`regione`: l'URL numerica di prima della migrazione (`/indicatore/901-pil-pro-capite`),
il codice prima dello slug, lo slug sbagliato, `?livello=`. Su `www.` il 301 va
all'apex, e per l'URL numerica risolve anche il percorso nello stesso salto
(`app/__init__.py`, `redirect_www_to_apex`). Una barra finale su una pagina che
esiste senza (`/regione/lazio/`) fa 301 alla forma senza barra (il gestore
della 404). Il passaggio da http a https non lo fa l'app: lo fa Cloudflare, e
l'app manda HSTS. `tests/integration/test_redirect_e_sitemap.py` guarda i salti
e che ogni scheda della sitemap risponda 200 con il canonical su se stessa.

### "Da non confondere con"

Alcune misure si scambiano con un'altra che il lettore cercava: il PIL pro
capite con il PIL totale o col reddito, l'occupazione con la disoccupazione.
`indicator_notes.DISTINCT_FROM` porta per quelle schede una frase di
definizione, senza cifre, e i codici delle schede che misurano l'altra cosa;
i link li risolve `indicator_view` sul catalogo, e una scheda che non c'e' si
toglie invece di diventare un link inventato. La riga sta nel blocco "Secondo
la fonte" e nel gemello Markdown.

## Verifica

Prima della pubblicazione:

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/prose_lint.py --summary
git diff --check
```

L'audit editoriale è il controllo che conta sui trattini, e va usato al posto di
un `grep` sui sorgenti. Viveva in uno script fuori dal repo, sotto un percorso
assoluto della macchina di chi lo aveva scritto, quindi per chiunque altro il
comando qui sopra non esisteva. La parte che serve a questa verifica la fa
`scripts/prose_lint.py`, che sta in repo e gira ovunque. Un `grep -rn "[—–;]" app/templates` restituisce sempre
righe, perché i template contengono CSS e JavaScript pieni di punti e virgola, e
soprattutto **non vede le entity**: `&ndash;` rende un trattino medio vietato da
`content/STYLE.md` senza che il carattere compaia nel sorgente. È così che
"Copertura 2015 – 2024" è rimasto in pagina.

Controllare almeno una pagina per ciascuna famiglia e per ciascuna forma:
percentuale, rapporto, valore assoluto, unità per abitante, punteggio, differenza
tra tassi, serie con un solo anno, indicatore contestuale e indicatore BES a due
livelli territoriali.
