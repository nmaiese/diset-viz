# Il modello a pratica editoriale (RFC, Fase A)

Questo documento e' la **Fase A** della revisione chiesta dal mandato: definire il
dominio prima di toccare l'implementazione. Non contiene codice, non cambia il
comportamento della catena, non apre una sola pull request in piu' di oggi. E' il
linguaggio comune che va **ratificato** prima di scriverne la macchina, perche' la
regola del mandato e' esplicita: *la PR unica puo' essere parte del miglioramento,
ma non deve guidare l'architettura*. Se si formalizza il contenitore prima del
ciclo di vita, il contenitore eredita i problemi di adesso, piu' grande.

Criterio di uscita di questa fase, preso dal mandato: **non si passa alla Fase B
finche' due sviluppatori non descrivono lo stesso percorso di un indicatore
usando gli stessi stati e arrivando allo stesso esito.** Questo documento e' la
proposta su cui misurare quell'accordo. Dove propone una risposta, la propone per
essere discussa, non per essere data per approvata.

Per come funziona la catena oggi: [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).
Per lo stato corrente: [`DISCOVERY_STATUS.md`](DISCOVERY_STATUS.md).
Per il contratto di ogni agente: [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md).

---

## 0. La tesi in una pagina

Il difetto non e' il numero delle pull request. E' che **l'unita' osservata e'
sbagliata**: la catena osserva run, stadi, code, commit e PR, mentre l'oggetto
editoriale che interessa, l'indicatore lungo un suo ciclo, non e' un oggetto del
sistema. Nessun file dice, per l'indicatore X, dove sta, da quando, che decisioni
ha attraversato, su quali dati, se e' davvero pubblicato e se quella versione e'
ancora valida. Lo si ricostruisce a mano unendo `triage_status` in un CSV, una
riga di `curation.csv`, i campi dentro un articolo JSON, una scheda in
`verifiche/` e la prosa di `summary`/`detail` in un diario di run. E' una
ricostruzione, ogni volta.

La buona notizia, e la ragione per cui questa revisione e' fattibile senza
riscrivere la catena, e' che **le primitive esistono gia', ma per stadio e
dedotte invece che per pratica e dichiarate**:

| il mandato chiede | il repo ha gia' | cosa manca |
| --- | --- | --- |
| identita' della sessione e del tentativo | `run_id` (`<stadio>-<timestamp>-<hex>`), `session_id` | l'identita' della **pratica** e della **pubblicazione** |
| validita' che scade quando cambia l'input | `data_year` (curatela), `vintage` vs `reviewed_vintage`, impronta `prosa` | che le dipendenze siano **dichiarate**, non riscoperte a ogni run |
| stato dichiarato e verificabile | stato **dedotto** da presenza file + campi | un record di stato per pratica, **riconciliabile** con gli artefatti |
| perimetri limitati per stadio | `pipeline_gate.STAGE_PATHS`, guardia, un file per record | classificare le **risorse** per decidere la concorrenza |
| "run conclusa" e "pubblicato" coincidono | il merge chiude la run e pubblica | il progetto ha ratificato merge = pubblicazione (§8), non un controllo del sito mancante |

Quindi il modello proposto non e' un impianto nuovo calato sopra. E' la
**unificazione** di cose che ci sono: dare all'indicatore-in-un-ciclo un nome e un
record, dichiarare le dipendenze che oggi sono impronte sparse, e riconoscere il
merge come pubblicazione (§8). Tutto il resto della catena, un lanciatore che elenca
il lavoro per-indicatore lanciabile in parallelo, un file per record, il cancello
come perimetro, il rientro guidato dai dati, resta in piedi e regge il modello.
Anzi, l'unita' di osservazione che questo documento chiedeva, l'indicatore invece
dello stadio, e' diventata nel frattempo l'unita' di **lavoro** della catena
stessa: i sette stadi sono ora tre ruoli (ammissione, produttore, verificatore),
e produttore e verificatore girano per-indicatore, esattamente la grana su cui il
modello ragiona (vedi [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md)).

---

## 1. Identita' (mandato 3.1, decisioni 1-2)

Sette identita', tutte distinte, **nessuna sostituita dal numero della PR** (che
oggi non e' gia' piu' l'identita' di niente: la run e' il suo `run_id`). Le prime
cinque esistono nel repo, le ultime due vanno introdotte.

| identita' | che cos'e' | chiave, con esempio reale | dove vive oggi |
| --- | --- | --- | --- |
| **fonte** | un'istituzione con una licenza citabile | famiglia in `app/sources.py` (`dem`, `eur`, `bes`, `multiscopo`, territoriale) | `SOURCES`, `config/istat_series.yaml`, `config/external_sources.yaml` |
| **candidato-fonte** | un dataflow non ancora ammesso | `<source_kind>:<dataflow_id>`, es. `istat_sdmx:DF_DCSS_HUDW_3_PROV` | `data/discovery/source_candidates.csv` |
| **candidato-indicatore** | una serie dentro una fonte ammessa | `<source>:<source_indicator_id>`, es. `eurostat_regional:rd_e_gerdreg` | `data/discovery/candidates.csv` |
| **indicatore** | l'identita' **permanente** di una voce d'atlante | `<famiglia>:<id>`, es. `dem:NMIGRATEIN`, o numerico `901`, o `bes:09PAE009-N25` | manifest, dataset esterno, `content/indicators/` |
| **sessione autonoma** | un firing di Routine, checkout fresco | `session_id` (`.session_meta.json`), `run_id` per stadio | `data/pipeline/runs/`, `.session_meta.json` |
| **pratica editoriale** *(nuovo)* | un **ciclo** dell'indicatore con un inizio, un esito, un tipo | `<indicator_id>#<tipo>-<seq>`, es. `dem:NMIGRATEIN#nuovo-1`, `901#aggiornamento-3` | da introdurre: `data/pipeline/practices/` |
| **pubblicazione** *(nuovo)* | la versione fusa su master, che il progetto tratta come pubblicata | impronta della versione (commit + `prosa` + `vintage`) fusa su master | campo `published` nella pratica, raggiunto al merge |

La distinzione che il mandato chiede a 2.2 e' fra le ultime due righe e la riga
"indicatore": **l'indicatore e' permanente, la pratica e' un ciclo, la
pubblicazione e' una versione.** Un indicatore vive molti cicli (prima
pubblicazione, un aggiornamento di vintage, una correzione dopo una smentita), ogni
ciclo e' una pratica con la sua fine, ogni pratica che arriva online produce una
pubblicazione datata. Nessuna PR eterna, nessuna pratica eterna.

La chiave della pratica lega insieme i tre livelli senza confonderli:
`<indicator_id>` la ancora all'identita' permanente, `<tipo>` dice che genere di
ciclo e', `<seq>` la ordina nella storia dell'indicatore. La curatela ha gia' una
chiave composta di questa forma (`target_indicator_id` + `source` +
`source_indicator_id`), perche' due fonti possono arricchire lo stesso indicatore:
la pratica va indicizzata sullo stesso livello, `(indicator_id, level)`, dato che
le code di scrittore e revisore lavorano gia' per coppia `(indicatore, livello)`.

**Decisione 1 (unita' fondamentale): l'indicatore e' l'identita', la pratica e'
l'unita' di avanzamento e responsabilita'.** Non e' un aut-aut. Si osserva
l'indicatore (la sua storia e' la sequenza delle sue pratiche), si fa avanzare, si
blocca e si chiude la pratica. Il mandato lo dice a 1.1: "l'indicatore, o una sua
specifica pratica editoriale, come unita' principale".

---

## 2. Tipi di pratica (mandato 1.12, 3.6, decisioni 5-6)

Un nuovo indicatore e un aggiornamento di vintage non hanno lo stesso percorso.
Una sola sequenza rigida farebbe passaggi inutili o salti non controllati. Otto
tipi, piu' due oggetti **pre-pratica** che non sono ancora un indicatore.

**Pre-pratica (non aprono una pratica).** Vivono nei due CSV di discovery e non
hanno un ciclo editoriale finche' non diventano un indicatore:
- **candidato-fonte**: un dataflow in triage nello scout. Esito nel suo
  `triage_status`.
- **candidato-indicatore**: una serie in triage nel cacciatore. Esito nel suo
  `triage_status`.

**Tipi di pratica (aprono un record di pratica).** Il punto d'ingresso e i
passaggi obbligatori cambiano per tipo:

| tipo | nasce quando | ingresso | stadi obbligatori | stadi saltabili |
| --- | --- | --- | --- | --- |
| **nuovo** | un candidato `approved` viene promosso | promoter | curator, writer, reviewer, verificatore | nessuno |
| **aggiornamento-dati / vintage** | la fonte pubblica un anno nuovo (`year_max` supera il `vintage` dell'articolo, o il `data_year` della curatela) | writer (o curator se cambia il verso) | writer, reviewer | curator se il verso regge, verificatore se la prosa non cambia le cifre |
| **revisione-editoriale** | una guardia di `review_queue` alza una bandiera (universale, causale, eco, ...) | reviewer | reviewer | writer se il testo non va riscritto da zero |
| **correzione-smentita** | il verificatore registra `esito=smentito` | reviewer (bandiera `smentita`, peso 60) | reviewer, verificatore | writer, curator |
| **integrazione-fonte** | una seconda fonte arricchisce un indicatore esistente (`duplicate_of` / `target_indicator_id`) | curator | curator, writer, reviewer, verificatore | nessuno |
| **ritiro** | una fonte smette di pubblicare, o si decide di togliere l'indicatore | curator o manutenzione | curator (toglie `score_eligible`), writer (nota di ritiro) | verificatore |
| **rollback** | una pubblicazione si rivela sbagliata e va tornata alla versione prima | reviewer/manutenzione | reviewer | tutti gli altri |
| **modifica-metadati** | cambia categoria, tema, direzione senza toccare le cifre | curator | curator | writer, reviewer, verificatore se la prosa non cita il metadato |

La regola generale: **il tipo dichiara gli stadi obbligatori, gli stadi saltabili
si saltano solo se una condizione verificabile lo consente** (es. verificatore
saltabile "se la prosa non cambia" e' controllabile con l'impronta `prosa`, che
gia' esiste). Nessun salto implicito (mandato 3.3).

**Decisioni 5-6** (stadi obbligatori per nuovo / per aggiornamento) sono le due
righe in grassetto della tabella. Un nuovo indicatore attraversa tutti e quattro
gli stadi editoriali, un aggiornamento di sole cifre puo' fermarsi a
writer + reviewer, e rientra al verificatore solo se l'impronta della prosa
cambia, che e' esattamente il meccanismo di rientro che c'e' gia'.

---

## 3. Il vocabolario finito degli stati (mandato 3.2, decisione 12)

Il mandato chiede uno **stato dichiarato**, non dedotto, con un vocabolario finito
e transizioni ammesse. Oggi lo stato e' una funzione degli artefatti: un articolo
e' "revisionato" se ha `reviewed_at` e `reviewed_vintage == vintage`, "verificato"
se esiste una scheda in `verifiche/` la cui `prosa` combacia con l'impronta
corrente. Utile come controllo, insufficiente come stato: non distingue "non
iniziato" da "fallito", "completato ma invalidato" da "completato".

Otto stati, uno solo attivo per pratica. Lo stato di sosta e' uno solo,
`in-attesa`, e un `motivo` lo qualifica (armonizza i due di prima,
`in-attesa-di-monte` e `bloccata`, che avevano lo stesso significato "ferma,
aspetta qualcosa" con una linea sola di differenza).

| stato | significato | condizione verificabile (contro gli artefatti) |
| --- | --- | --- |
| `proposta` | esiste un candidato `approved` non ancora promosso | candidato con `triage_status=approved`, nessuna riga manifest |
| `in-lavorazione` | uno stadio obbligatorio non e' ancora completo | esiste l'artefatto di ingresso, manca almeno un artefatto obbligatorio a valle |
| `in-attesa` | ferma in attesa di una condizione; il `motivo` dice quale | vedi la tabella dei motivi qui sotto |
| `pronta-al-merge` | tutti gli stadi del ciclo completi, il cancello e' verde | gli artefatti obbligatori esistono e passano `pipeline_gate` |
| `pubblicata` | **fusa su master** (il progetto ha ratificato merge = pubblicazione, §8) | il ciclo obbligatorio e' completo e l'articolo e' committato su master |
| `invalidata` | un input e' cambiato: uno o piu' passaggi non valgono piu' | uno stamp di dipendenza non combacia (§6) |
| `in-quarantena` | `in-attesa` terminale, tolta dalla coda per non fermare le altre | `tentativi >= soglia` con errore non transitorio, o decisione umana |
| `chiusa` | esito terminale raggiunto (§7) | c'e' un `esito` da vocabolario di chiusura |

I motivi di `in-attesa` (`scripts/practice_model.IN_ATTESA_MOTIVI`), ognuno con la
sua classe d'errore (§9) e il suo peso sull'urgenza (solo il primo non conta come
fermo, e' contropressione normale):

| motivo | significato | classe d'errore | e' un fermo? |
| --- | --- | --- | --- |
| `monte-mancante` | l'artefatto dello stadio a monte non esiste ancora (es. curatela assente) | nessuna | no |
| `dipendenza-esterna` | aspetta un chiarimento o un cambio alla fonte / config | `ripetibile-dopo-cambio-esterno` | si' |
| `tecnico` | una correzione tecnica (cancello rosso, conflitto) | `tecnico` | si' |

**Il record di pratica non sostituisce gli artefatti: li proietta.** Ogni stato ha
una condizione verificabile contro i file, e un **riconciliatore** (Fase C)
ricalcola lo stato atteso e segnala la divergenza. Cosi' lo stato e' insieme
**dichiarato** (una sessione a freddo lo legge senza ridedurlo) e **ricostruibile**
(non puo' derivare in silenzio dagli artefatti). Questo scioglie la tensione del
mandato a 2.1: *la PR rappresenta lo stato, non lo possiede*, e *lo stato
autorevole e' persistente e verificabile indipendentemente dalla PR*. Autorevole
e' il record di pratica, verificabile perche' riconciliato con gli artefatti, che
restano la verita' di fondo.

Il record porta, oltre allo stato: `stato_precedente`, `passaggi_completati`,
`passaggi_invalidati`, `passaggio_richiesto`, `motivo_blocco`, `tentativi`,
`esito`. Le descrizioni libere (come `detail` nei run) **spiegano** lo stato, non
lo **sostituiscono** (mandato 3.2).

**Decisione 12 (quarantena):** una pratica va in quarantena quando i tentativi
superano la soglia del suo tipo di errore (§9) **e** l'errore non e' transitorio,
oppure quando un blocco editoriale non ha una via d'uscita automatica (un dubbio
che nessun dato scioglie). La quarantena la toglie dalla coda del lanciatore senza
cancellarne la storia, cosi' una pratica malata non ferma le sane (mandato 1.10).

---

## 4. Transizioni (mandato 3.3)

Ogni transizione dichiara: **precondizioni, input, responsabile, artefatti
prodotti, controlli, condizione di completamento, condizione di invalidazione,
possibile ritorno.** Nessun salto implicito. Le transizioni ricalcano gli stadi
reali, la novita' e' che ognuna scrive anche la riga di stato della pratica, oltre
all'artefatto che gia' scrive.

Esempio, la transizione **curator -> writer** per una pratica `nuovo`:
- **precondizione**: pratica in `in-lavorazione`, manifest `status=integrated` per
  il target (la curatela ha fuso).
- **input**: riga di `curation.csv` (`reviewed_direction`, `reviewed_category`,
  `score_eligible`, `data_year`), dataset esterno.
- **responsabile**: `indicator-writer`, perimetro `content/indicators/` +
  `data/pipeline/runs/`.
- **artefatti prodotti**: `content/indicators/<key>.json` con `lead`, quattro
  sezioni, `fonti`, `vintage`. In forma opt-in (`roles_covered`, vedi
  [`docs/INDICATOR_PAGES.md`](INDICATOR_PAGES.md)) le sezioni sono i soli ruoli
  dichiarati, e la `definizione` puo' mancare perche' la copre il blocco "Come
  leggere il dato".
- **controlli**: `check_writer_vintage` (il `vintage` non supera `year_max`),
  suite, `check_blast_radius`, `check_run_is_recorded`.
- **completamento**: le sezioni **dichiarate** hanno `body` e il `lead` e'
  presente. Senza `roles_covered` la dichiarazione sono i quattro ruoli, che e'
  la regola di sempre; con `roles_covered` restano comunque richiesti `quadro`,
  `dinamica` e `limiti`, perche' solo la `definizione` e' assorbibile.
- **invalidazione**: se `data_year` della curatela si muove **mentre** la pratica e'
  aperta, l'output del writer nasce gia' contro un input vecchio: la pratica torna
  `invalidata`, il passaggio writer entra in `passaggi_invalidati`.
- **ritorno**: al curator, se il verso va rigiudicato sull'anno nuovo.

La matrice completa delle transizioni ammesse per tipo e' l'allegato che la Fase A
deve produrre come tabella unica (una riga per `(tipo, da_stato, a_stato)`), ma la
forma e' questa, e ogni riga e' gia' derivabile dagli stadi che esistono. Le
transizioni **non ammesse** sono altrettanto importanti: writer -> pubblicata
saltando reviewer non esiste, pronta-al-merge -> pubblicata senza il verdetto
verde del cancello non esiste (§8).

---

## 5. Batch e individualita' (mandato 1.5, decisione 14)

Il mandato non chiede di abolire il batch: chiede di distinguere cio' che puo'
restare collettivo da cio' che deve diventare individuale.

- **Resta batch (collettivo, senza pratica):** la **ricognizione delle fonti** e la
  **scoperta dei candidati**. Scout e cacciatore scandiscono un intero catalogo e
  triano molte righe in una run, ognuna con il suo `triage_notes`. Sono decisioni
  su oggetti pre-pratica, e il mandato lo concede a 1.5. Il costo e' che una riga
  di config sbagliata non deve uccidere l'intera scansione: gia' oggi "una serie
  illeggibile costa solo se stessa".
- **Diventa individuale (una pratica):** dalla **promozione in poi**. Nel momento
  in cui un candidato `approved` diventa un indicatore identificato, nasce una
  pratica, e da li' il produttore (che fonde curator, writer e reviewer) e il
  verificatore lavorano **un indicatore alla volta**. E' dove si producono
  decisioni editoriali e artefatti pubblicabili, ed e' dove il mandato vuole
  responsabilita' singola: un errore su un indicatore non deve bloccare gli altri,
  e costo e durata vanno misurati per indicatore.

**Decisione 14:** batch fino alla promozione, individuale dalla promozione. E'
esattamente la linea su cui la ri-architettura ha tagliato i ruoli:
l'**ammissione** (scout+hunter+promoter) e' batch, una sessione triaga l'intera
coda e promuove; il **produttore** (curator+writer+reviewer) e il **verificatore**
sono per-indicatore. Il lanciatore (`scripts/pipeline_launch.py`) elenca una voce
di produttore o verificatore per ogni indicatore pronto e una sola voce di
ammissione batch, cosi' due indicatori diversi si lanciano in parallelo senza
contendere. Il batch non si tiene solo perche' riduce il numero di run: si tiene
dove l'oggetto e' pre-pratica (un catalogo da scandire), non dove e' un articolo
da firmare.

---

## 6. Provenienza e validita' (mandato 3.4, 3.5, 2.3, decisioni 9-10)

Il cuore del mandato a 2.3: un passaggio dichiarato completo puo' non essere piu'
valido al momento della pubblicazione, perche' i dati, il vintage, le definizioni,
la copertura, la prosa o le regole editoriali sono cambiati nel frattempo.

Oggi l'invalidazione **esiste gia'**, ma come impronte sparse che una coda
riscopre a ogni run:
- la curatela porta `data_year`, l'anno su cui il verso e' stato giudicato: la
  fonte pubblica un anno nuovo e la curatela rientra in `recheck`.
- l'articolo porta `reviewed_vintage`: il writer rinfresca il `vintage` e la firma
  del revisore non combacia piu', l'articolo rientra in `rilettura`.
- la scheda di verifica porta l'impronta `prosa`: il revisore riscrive una frase,
  l'impronta cambia, la verifica scade e l'articolo torna al verificatore.

Il modello **le nomina come dipendenze dichiarate**. Ogni risultato intermedio
dichiara da quali input dipende e con quale stamp li ha visti:

| passaggio | dipende da | stamp che porta | invalidato quando |
| --- | --- | --- | --- |
| curatela | anno della fonte | `data_year` | `data_year < latest_year(target)` |
| articolo (writer) | cifre del livello | `vintage` | `vintage < year_max` |
| firma (reviewer) | vintage dell'articolo | `reviewed_vintage` | `reviewed_vintage != vintage` |
| verifica | testo dell'articolo | impronta `prosa` | l'impronta non combacia |
| sezione `definizione` | definizione della fonte | (mancante oggi) | la fonte ridefinisce la serie |

L'ultima riga e' la lacuna vera che il modello va a coprire: una **definizione
ridefinita** non cambia nessun numero e non rompe nessun test, ma invalida la
sezione `definizione` di ogni articolo che descriveva la vecchia (lo nota gia'
`fetch_definitions.py`, ma nessuno stamp lo intercetta). Il modello aggiunge uno
stamp di definizione allo stesso modo degli altri.

**Decisioni 9-10** (cosa invalida una revisione, cosa invalida una verifica):
- una **revisione** e' invalidata quando `reviewed_vintage != vintage` (cifre
  rinfrescate) **o** quando c'e' una smentita aperta sull'articolo.
- una **verifica** e' invalidata quando l'impronta `prosa` non combacia (testo
  riscritto). Mai per scadenza di calendario: *una verifica scade quando cambia il
  testo, non quando passa il tempo*.

Provenienza (3.4): ogni decisione importante e' gia' collegabile a dati, fonte,
periodo, copertura, unita', trasformazioni, versione della prosa, regole, sessione
e controllo che l'ha accettata. Il modello la rende **leggibile in un posto**: il
record di pratica indicizza i `run_id` che l'hanno toccata, i `data_year` /
`vintage` / impronte contro cui ogni passaggio e' stato prodotto, e il verdetto di
cancello che l'ha accettato. Oggi questo legame esiste solo come prosa in
`summary`/`detail` e come inferenza dai file che il commit ha toccato.

---

## 7. Chiusura (mandato 3.6, decisione 4)

Ogni pratica termina con un **esito esplicito**. "PR chiusa" non e' un esito
editoriale. Vocabolario finito di chiusura:

| esito | significato |
| --- | --- |
| `pubblicata` | fuso su master (§8), il solo esito "riuscito" |
| `rifiutata` | il candidato non e' ammissibile (resta la riga `rejected` con il motivo) |
| `duplicata` | coincide con un indicatore esistente (`duplicate_of` puntato) |
| `sostituita` | un ciclo successivo l'ha soppiantata |
| `ritirata` | l'indicatore e' stato tolto dall'atlante |
| `bloccata-terminale` | un blocco che nessun tentativo automatico scioglie (in quarantena) |
| `annullata` | non piu' necessaria (es. la fonte e' stata rimossa a monte) |

**Decisione 4 (quando una PR chiude senza pubblicazione):** una PR (cioe' un passo
di ciclo, §10) chiude senza pubblicazione quando la pratica raggiunge uno degli
esiti diversi da `pubblicata`, oppure quando il passo e' un passaggio
intermedio di un ciclo che continua. Gli **artefatti invalidati restano nella
storia** (mandato, vincolo non negoziabile): una pratica `sostituita` non
cancella cio' che aveva prodotto, lo marca superato.

---

## 8. Che cosa significa "pubblicato" (mandato 1.7, decisioni 7-8)

Il progetto ha **ratificato una scelta**: **merge = pubblicazione**. Un articolo
fuso su master **e'** pubblicato, e lo stato `pubblicata` si raggiunge al merge.
Non e' un'ovvieta' da nascondere ma una decisione presa con gli occhi aperti,
perche' i due eventi si possono tenere distinti e per un periodo lo sono stati.
Sette eventi che, sotto questa scelta, collassano in uno:

1. **esito della run**, la sessione autonoma finisce (`outcome` nel diario).
2. **esito dello stadio**, l'artefatto dello stadio e' completo.
3. **approvazione tecnica**, `pipeline_gate` e' verde.
4. **merge**, `pipeline_merge.py` fonde su master (squash via REST).
5. **deploy**, il sito si ricostruisce (non osservato dalla catena).
6. **pubblicazione sul sito**, la pagina pubblica mostra quella versione.
7. **verifica del contenuto**, le affermazioni reggono contro i dati (verificatore).

La ratifica dice che lo stato `pubblicata` scatta all'evento 4, il merge, e non
aspetta gli eventi 5 e 6. Il deploy e la pubblicazione sul sito **seguono** il
merge per costruzione (un push su master ridispiega il sito), ma la catena non
li osserva piu': non c'e' un controllo che confronti la pagina pubblica con la
versione attesa.

**Il costo, dichiarato.** "Repo avanti / sito indietro" non e' piu' osservabile
dalla catena: se un deploy fallisce in silenzio, il cruscotto continua a dire
`pubblicata` mentre il sito serve la versione vecchia. E' il falso positivo che
una verifica del sito avrebbe intercettato. Il progetto lo accetta come
compromesso registrato, non come lacuna nascosta: in cambio si toglie una
macchina intera (la verifica del sito, il suo registro di prove, il passo del
lanciatore che la chiudeva) e lo stato `pubblicata` diventa deterministico,
raggiunto dal solo fatto verificabile che l'articolo e' su master.

**La verifica del contenuto resta, ed e' un'altra cosa.** Il verificatore
controlla le **affermazioni della prosa contro i dati** (evento 7), su file
committati, non che la pagina sia viva. E' editoriale, indipendente dalla verifica
del sito che e' stata rimossa, e resta **prima** del merge: e' una condizione del
ciclo, non un controllo post-deploy.

**Decisione 7 (verifica prima o dopo la pubblicazione):** la **verifica del
contenuto** (il verificatore, evento 7) e' **prima** del merge, su articoli
firmati, ed e' una condizione editoriale del ciclo che resta com'e'. Non c'e'
piu' una verifica del sito dopo il merge: la scelta merge = pubblicazione l'ha
resa non necessaria.

**Decisione 8 (quando il sistema puo' dichiarare "pubblicato"):** al **merge**.
La pratica si considera conclusa con successo (`pubblicata`) quando il ciclo
obbligatorio e' completo e l'articolo e' committato su master. Non c'e' un evento
di sito ulteriore da attendere.

---

## 9. Tassonomia degli errori e ripresa (mandato 1.8, 1.9, decisione 11)

Un blocco generico non dice se e quando ritentare. Sei classi, ognuna con un
comportamento:

| classe | esempi | comportamento |
| --- | --- | --- |
| **transitorio** | fonte irraggiungibile, rete, piattaforma giu', SIGSEGV della suite senza referto | ritenta con backoff, fino a una soglia bassa, non conta come tentativo editoriale |
| **ripetibile-dopo-cambio-esterno** | candidato-fonte `approved` senza riga di config (orfano), adapter mancante, categoria da creare | **non** ritentare da solo: aspetta un cambiamento esterno (codice, config, decisione umana), resta segnalato |
| **editoriale** | dubbio sul verso, dati insufficienti, smentita | torna allo stadio giusto (curator o reviewer) come rientro, non come errore |
| **tecnico** | cancello rosso su perimetro, whitespace, trailer, conflitto di merge | correggibile nella stessa pratica, ritenta dopo la correzione |
| **terminale** | il candidato non e' ammissibile, l'indicatore va ritirato | chiude la pratica con l'esito relativo, non ritenta |
| **cambiamento-in-corsa** | un input e' cambiato mentre la pratica lavorava | invalida i passaggi dipendenti (§6), non e' un errore da ritentare ma un rientro |

**Decisione 11 (quante volte si ritenta):** un tetto per classe, mai infinito
(vincolo non negoziabile). Proposta: transitorio fino a 3 con backoff, tecnico
fino a 2 dopo correzione, editoriale e cambiamento-in-corsa non contano contro il
tetto perche' sono rientri, non fallimenti, ripetibile-dopo-cambio-esterno e
terminale non si ritentano affatto. Superato il tetto, la pratica va
`in-quarantena`. Il tetto vive nel record di pratica (`tentativi`), non nel prompt
di un agente.

**Ripresa (1.9, idempotenza):** una sessione puo' interrompersi dopo aver scritto
artefatti, committato, pushato, aperto una PR, aggiornato lo stato o chiuso un
controllo. Il tentativo successivo non deve duplicare ne' contraddire. La chiave
di idempotenza c'e' gia': il **`run_id`** e' coniato prima che la PR esista e non
dipende da niente che accada dopo. Il modello la estende alla pratica: ogni
transizione dichiara **come riconoscere un effetto gia' applicato** (l'artefatto
esiste con lo stamp atteso), cosi' riprendere una pratica interrotta e' rileggere
il suo record, guardare quali `passaggi_completati` hanno gia' l'artefatto con lo
stamp giusto, e ripartire dal primo che manca. Gli stati con condizione
verificabile (§3) servono esattamente a questo: distinguono "fatto" da "iniziato e
non finito" senza indovinare.

---

## 10. La PR: vista, non memoria (mandato 2.1, 2.2, 2.5, 1.3, decisione 3)

Questa e' la parte in cui il mandato e' piu' netto, e va presa alla lettera: **la
PR unica non deve diventare la fonte autorevole dello stato, e non deve guidare
l'architettura.** Il rischio, se lo stato vive nella PR, e' che il lanciatore
dipenda dalla disponibilita' della piattaforma, che una modifica manuale alteri la
rappresentazione, che una sessione a freddo non ricostruisca il contesto.

La posizione proposta, ed e' una scelta di architettura da ratificare:

1. **Lo stato autorevole e' il record di pratica** in `data/pipeline/practices/`,
   un file per pratica (rispetta l'invariante "un file per record"), riconciliabile
   con gli artefatti. **Non** e' la PR.
2. **La PR resta cio' che e' oggi: un passo di ciclo**, con la sua cadenza di
   merge (oggi ogni ruolo fonde `auto` sul cancello locale, che gira la suite
   intera prima del merge: la CI remota non parte sulle PR aperte via il GitHub
   MCP, quindi aspettarla comprava un deadlock, non un verdetto). Questa cadenza
   e' portante: il rientro guidato dai dati, il lanciatore che elenca il lavoro
   per-indicatore, il merge sul cancello locale, nessun umano nel giro, dipendono
   dal fatto che ogni passo fonde per conto suo. **Una PR unica e lunga che
   attraversa tutti gli stadi contraddice tutto questo** (un umano che la
   sorveglia in una catena non presidiata, o un branch di giorni che invalida i
   suoi stessi passaggi mentre i dati si muovono).
3. La "PR unica per indicatore" **si declassa da architettura a strato di
   leggibilita' opzionale**: la sede unica in cui leggere l'intero percorso e' il
   **record di pratica** (e la sua vista, §11), non una PR gigante. Il mandato
   arriva alla stessa conclusione: *la PR deve essere una vista leggibile, non la
   sola memoria del processo*.
4. **Si pilota** (Fase D) la PR unica **solo** sul ciclo di **prima pubblicazione
   di un nuovo indicatore**, su perimetro limitato (fonte gia' ammessa, dati
   disponibili, nessun conflitto), e **anche li' lo stato autorevole resta il
   record di pratica, non la PR.** I cicli di manutenzione (§2) tengono la cadenza
   a passo.

**Decisione 3 (quando si apre la PR):** una PR si apre quando un passo di ciclo
produce per la prima volta una modifica destinata a master (oggi: alla chiusura di
ogni stadio che scrive). Nel pilota della PR unica, si apre alla promozione e si
chiude al merge del ciclo di prima pubblicazione. **Nasce e finisce con un
ciclo**, mai eterna (mandato 2.2).

**Livelli di lettura (2.5):** la PR e la vista di pratica hanno cinque livelli, e
la sintesi e' **derivata** dai dati reali, non li sostituisce: (1) stato sintetico,
(2) decisioni editoriali, (3) prove e controlli, (4) dettagli operativi,
(5) cronologia completa. Oggi il diario ha gia' `summary` (1) e `detail` (2), il
cancello ha (3), i `run_id` con provenienza hanno (4-5). Manca solo comporli per
indicatore.

**Frammentazione (1.3):** oggi ci sono piu' PR per lo stesso indicatore (una per
stadio) e piu' indicatori nella stessa PR (il batch). Il modello risolve la
seconda con l'individualita' dalla promozione (§5), e la prima con il record di
pratica che lega insieme le PR di un ciclo, senza doverle fondere in una sola.

---

## 11. Concorrenza e priorita' (mandato 1.10, 1.11, 2.4, decisioni 13, 15)

**Tre concorrenze diverse, che il vecchio dispatcher trattava come una (mandato
1.10, 2.4).**

Il dispatcher serializzava tutto: un tick, uno stadio, nessun lock perche' non
c'era mai un secondo scrittore, e in piu' rifiutava di partire finche' una PR
della catena era aperta. Era semplice e sicuro, ma trasformava una singola
anomalia in un blocco globale, ed e' esattamente cio' che il mandato vuole
evitare. La ri-architettura ha risolto proprio questo distinguendo le tre
concorrenze invece di escluderle tutte:

- **stessa pratica**: due sessioni sullo stesso ciclo. Va esclusa sempre (e la
  quarantena toglie la pratica malata dalla coda, cosi' non blocca le altre). Il
  lanciatore, che e' per-indicatore, non emette mai due voci sullo stesso
  indicatore.
- **risorsa condivisa**: due pratiche indipendenti che toccano lo stesso file.
  Qui serve classificare le risorse (sotto), non escludere tutto.
- **pipeline intera**: il blocco globale di ieri. E' stato **rimosso**: il
  lanciatore non ha piu' il lock una-PR-aperta, quindi una pratica in quarantena
  o incagliata non ferma una pratica pronta e indipendente. Indicatori diversi
  toccano file diversi (un articolo per record) e si lanciano in parallelo.

**Classificazione delle risorse (2.4, decisione 15):**

| classe | esempi | concorrenza |
| --- | --- | --- |
| **specifica dell'indicatore** | `content/indicators/<key>.json`, la sua scheda in `verifiche/` | escludi solo sulla stessa pratica |
| **specifica della fonte** | riga in `config/istat_series.yaml`, adapter | escludi fra pratiche della stessa fonte |
| **condivisa** | manifest, `normalized_external_indicators.csv`, `curation.csv`, `config/theme_categories.csv` | escludi sulla scrittura, ammetti la lettura |
| **derivata** | punteggio qualita' vita, totali per macro-area, profili | non si scrive: si ricalcola a runtime |

Gli store a un file per record rendono la classe "specifica dell'indicatore"
gia' priva di conflitti (due articoli diversi non collidono mai), ed e' la
proprieta' che permette al lanciatore di lanciare piu' produttori in parallelo.
Il rischio vero resta sulla classe "condivisa": due promozioni che scrivono il
manifest, due curatele che scrivono `curation.csv`. Qui aiuta che l'ammissione
sia **batch** (una sessione sola scrive il manifest e la config, non due che si
contendono), mentre la scrittura condivisa del produttore (`curation.csv`,
`theme_categories.csv`) resta il punto da sorvegliare. Il modello lega la regola
di concorrenza **alla risorsa realmente modificata**, non al fatto che esistano
due PR aperte. La migrazione naturale, quando i CSV condivisi diventeranno un
collo di bottiglia, e' spezzarli a un file per record come gia' fatto per i tre
store, ma non e' necessaria adesso: e' una conseguenza, non una premessa.

**Priorita' oltre l'ordine di catena (1.11, decisione non numerata ma implicita).**

L'ordine di catena da solo (a monte prima, scout prima di verificatore) fa
propagare il lavoro ma e' insufficiente: **una correzione urgente di un dato
pubblicato aspetterebbe dietro una coda di candidature nuove.** Il lanciatore
ordina invece le voci per un punteggio di priorita' della **pratica** (non dello
stadio), leggibile e verificabile, e l'ordine di ruolo rompe solo i pari merito.
E' `stage_priorities`/il campo `priority` del dossier per-indicatore, consultato
a ogni piano:

- **errore pubblico** (una smentita su una pagina online): massimo.
- **prossimita' alla pubblicazione**: una pratica quasi conclusa vale piu' di una
  appena nata (riduce il lavoro a meta').
- **dati scaduti** su un indicatore nel punteggio.
- **anzianita'** della pratica (evita la fame di una classe).
- **tentativi gia' falliti** (una pratica che ha fallito molte volte scende, per
  non monopolizzare).

Il punteggio e' derivato da campi verificabili del record di pratica, non da un
giudizio. Nessuna classe deve restare permanentemente in attesa.

**Decisione 13 (nuovo evento sullo stesso indicatore mentre una pratica e'
aperta):** dipende dall'asse.
- Se l'evento tocca lo **stesso output pubblicabile** del ciclo aperto e il ciclo
  non e' ancora fuso, si **assorbe** nel ciclo (es. una smentita mentre il
  produttore sta ancora scrivendo: la si corregge nello stesso giro).
- Se tocca un **asse di dipendenza diverso** o il ciclo e' gia' fuso, si apre una
  **nuova pratica collegata** (`<indicator_id>#<tipo>-<seq+1>`), figlia della
  storia dell'indicatore, non un riavvio della stessa unita' di lavoro. E' il modo
  in cui l'indicatore ha "cicli distinti ma collegati" (Fase E) senza una pratica
  eterna.

---

## 12. Cambiamenti fuori dalla pipeline e ritiro (decisioni 16, 17)

**Decisione 16 (modifica fuori dalla pipeline):** un dato corretto a mano, una
riga di config cambiata da uno sviluppatore, un articolo modificato fuori dal
flusso. Il modello lo rappresenta con il **riconciliatore** (Fase C): confronta lo
stato dichiarato di ogni pratica con gli artefatti, e quando trova una divergenza
non spiegata da una transizione apre una **pratica di riconciliazione** che la
registra e la porta a uno stato coerente. Cosi' *un errore non osservabile non
viene interpretato come assenza di lavoro* (vincolo non negoziabile): la
divergenza e' un evento, non un silenzio.

**Decisione 17 (ritiro di un indicatore pubblicato):** e' il tipo di pratica
`ritiro` (§2). Il curator toglie `score_eligible` e, se serve, la voce dal
punteggio, il writer scrive la nota di ritiro, l'indicatore esce dai totali ma la
sua storia (le pratiche precedenti, gli artefatti invalidati) **resta**. Un ritiro
e' una chiusura con esito `ritirata`, non una cancellazione.

---

## 13. Le diciotto decisioni, in una tabella (mandato 7)

Risposte proposte, per essere ratificate. "Team" segna le poche che restano un
giudizio umano piu' che una deduzione dal sistema.

| # | decisione | risposta proposta |
| --- | --- | --- |
| 1 | unita' fondamentale | indicatore = identita', pratica = unita' di avanzamento (§1) |
| 2 | quando nasce una pratica | alla **promozione** di un candidato `approved` (§1, §5) |
| 3 | quando si apre la PR | alla prima modifica destinata a master del passo di ciclo (§10) |
| 4 | quando una PR chiude senza pubblicazione | quando la pratica raggiunge un esito diverso da `pubblicata`, o e' un passo intermedio (§7) |
| 5 | stadi obbligatori per un nuovo | curator, writer, reviewer, verificatore (§2) |
| 6 | stadi obbligatori per un aggiornamento | writer, reviewer, gli altri se una condizione lo impone (§2) |
| 7 | verifica prima o dopo la pubblicazione | contenuto **prima** del merge, nessuna verifica del sito (rimossa, §8) |
| 8 | quando dichiarare "pubblicato" | al **merge**: merge = pubblicazione (§8) |
| 9 | cosa invalida una revisione | `reviewed_vintage != vintage`, o una smentita aperta (§6) |
| 10 | cosa invalida una verifica | l'impronta `prosa` non combacia (§6) |
| 11 | quante volte si ritenta | tetto per classe di errore, mai infinito (§9) |
| 12 | quando in quarantena | tentativi oltre soglia con errore non transitorio, o blocco editoriale senza uscita automatica (§3) |
| 13 | nuovo evento a pratica aperta | assorbi se stesso output e non fuso, altrimenti nuova pratica collegata (§11) |
| 14 | cosa resta batch | scout e hunter (pre-pratica), individuale dalla promozione (§5) |
| 15 | risorse con esclusione reciproca | condivise (manifest, `curation.csv`, `theme_categories.csv`) in scrittura, le derivate non si scrivono (§11) |
| 16 | modifica fuori dalla pipeline | pratica di riconciliazione aperta dal riconciliatore (§12) |
| 17 | ritiro di un pubblicato | tipo di pratica `ritiro`, esito `ritirata`, storia conservata (§12) |
| 18 | come si misura il miglioramento | le metriche di §15, confronto prima/dopo documentato (Fase F), **Team** sceglie le soglie |

---

## 14. Il piano di lavoro (mandato 4), mappato sugli script reali

L'ordine e' quello del mandato, e non e' negoziabile: dominio, poi osservabilita',
poi macchina a stati in controllo, poi recupero e invalidazione provati, poi il
pilota, poi la manutenzione, poi la sostituzione.

- **Fase A, dominio (questo documento).** Uscita: due sviluppatori descrivono lo
  stesso percorso con gli stessi stati. Nessun codice.
- **Fase B, osservabilita', senza cambiare la pubblicazione. [implementata]** La
  **timeline per indicatore** si ricostruisce dai file che ci sono gia', unendo
  `triage_status`, `curation.csv`, i campi dell'articolo, le schede `verifiche/` e
  i `run_id`, in `scripts/practice_timeline.py` (read-only). Per un indicatore
  qualsiasi dice senza analisi manuale quando e' entrato, cosa e' successo, quali
  passaggi ha completato, quali run lo hanno toccato, se la verifica regge. Il
  limite dichiarato: una pratica per indicatore, gli eventi di manutenzione sono
  nella timeline ma non ancora spezzati in cicli distinti.
- **Fase C, macchina a stati in controllo. [implementata]** Il **riconciliatore**
  (`practice_timeline.py --check`) calcola lo stato atteso di ogni pratica dagli
  artefatti e lo confronta con i record dichiarati (`--write` li materializza in
  `data/pipeline/practices/`), segnalando le divergenze. Il vocabolario, le
  transizioni, la tassonomia degli errori e la priorita' sono codice puro in
  `scripts/practice_model.py`, provati da `tests/unit/test_practice_model.py`.
  Affianca il flusso senza pubblicare.
- **Fase D, pilota della PR unica**, solo su nuovi indicatori a perimetro
  limitato, con lo stato nel record di pratica e non nella PR. Il pezzo che un
  tempo era davvero nuovo, la **verifica del sito**, e' stato **rimosso** quando
  il progetto ha ratificato **merge = pubblicazione** (§8):
  `scripts/verify_publication.py`, il registro delle prove in
  `data/pipeline/pubblicazioni/`, lo stadio `publisher` del cancello e la
  transizione `fusa -> pubblicata` non esistono piu'. Lo stato `pubblicata` si
  raggiunge ora al merge, per costruzione, senza un controllo del sito a valle.
  Cio' che **resta** e' il ricalcolo dello stato dai file committati (un articolo
  su master e' pubblicato) e il pilota della PR unica sul solo ciclo di prima
  pubblicazione, con lo stato autorevole nel record di pratica. Il flag `--publish`
  del lanciatore sopravvive ma ora segna solo il battito del lanciatore nel
  diario, non piu' una verifica del sito. Il compromesso accettato, "repo avanti /
  sito indietro" non piu' osservabile dalla catena, e' registrato in §8.
- **Fase E, manutenzione. [implementata]** `practice_timeline.split_cycles`
  spezza la storia di un indicatore in cicli distinti ma collegati: il primo e'
  `nuovo`, poi ogni innesco su una pagina gia' a valle apre un ciclo nuovo (una
  smentita, un anno nuovo della fonte), l'ultimo e' quello attivo e porta lo
  stato corrente, i precedenti restano chiusi con esito `sostituita`. `--write`
  scrive un record per ciclo. Sui dati veri, `eur:rd_e_gerdreg` risulta due
  cicli, `nuovo-1` (sostituita) e `smentita-2` (attivo, invalidata), senza una PR
  eterna. Ricostruibili sono `smentita` e `aggiornamento`, `ritiro`, `rollback`,
  `integrazione` e `metadati` esistono nel modello ma vogliono un segnale
  esplicito. Provata in `tests/unit/test_practice_timeline.py`.
- **Fase F, sostituzione. [macchina pronta, priorita' della pratica in produzione]**
  Le tre condizioni di codice sono fatte e provate: la **priorita' della pratica**,
  ora nativa nel lanciatore (`pipeline_launch.py` ordina le voci per il campo
  `priority` del dossier, `stage_priorities`, cosi' una smentita su una pagina
  online, peso 100, apre il piano davanti a una candidatura nuova, senza affamare
  la scoperta), le **metriche** del confronto prima/dopo (`practice_metrics.py`),
  il **recupero** provato (la ricostruzione e' pura, rieseguirla dopo
  un'interruzione da' lo stesso stato). Lo storico e' gia' classificato (`--write`
  materializza un record per ciclo). Nel vecchio dispatcher la priorita' era un
  flag opt-in (`--priority`) sopra un ordinamento a uno-stadio-per-tick; nel
  lanciatore per-indicatore l'ordinamento per priorita' e' il comportamento di
  base, perche' il piano e' gia' una lista di pratiche, non uno stadio scelto. Cio'
  che **resta**, ed e' operativo non codice: girare il confronto delle metriche su
  run reali prima e dopo perche' il modello diventi autorevole anche sulla
  scrittura dei record di pratica, come chiede il mandato.

Nessuna fase indebolisce i vincoli non negoziabili del mandato (sezione 6),
tutti gia' presenti nella catena e da preservare: lo stato sopravvive alle
sessioni (`run_id`, store committati), le decisioni sono motivate (`triage_notes`,
`detail`), gli input sono verificabili (stamp di §6), i perimetri sono limitati
(`STAGE_PATHS`), uno stadio non allarga le proprie autorizzazioni (il cancello non
e' consultivo), i controlli sono indipendenti dal giudizio dell'agente
(`pipeline_gate` rigira nel merge), un errore non osservabile non e' assenza di
lavoro (il riconciliatore), gli artefatti invalidati restano nella storia, i
retry non sono infiniti (tetto per classe), un indicatore malato non ferma la
catena (quarantena), la PR e' una vista non la memoria (record di pratica).

**Un vincolo e' stato cambiato di proposito, e va registrato come decisione, non
fatto sparire.** Il modello proponeva "una pratica non e' pubblicata perche' la PR
e' fusa" (stato `pubblicata` != `fusa`), con una verifica del sito a separare il
merge dalla pubblicazione. Il progetto ha **ratificato l'opposto**: **merge =
pubblicazione**, quindi lo stato `pubblicata` si raggiunge al merge per
costruzione e lo stato `fusa` non esiste piu' (§8). Il compromesso accettato,
scritto per intero e non nascosto, e' la perdita dell'osservabilita' "repo avanti
/ sito indietro": se un deploy fallisce in silenzio, la catena continua a dire
`pubblicata`. In cambio si toglie una macchina intera e lo stato diventa
deterministico. Resta intatta la **verifica del contenuto** (il verificatore, che
smentisce le affermazioni **prima** del merge): e' editoriale, e non e' cio' che
e' stato rimosso.

### Stato dell'implementazione

Le Fasi B, C, E e la **macchina** della F sono codice provato, la Fase D si e'
ridotta quando la verifica del sito e' stata rimossa (§8, ne resta il ricalcolo
dello stato dai file committati), e la ri-architettura per-indicatore le ha
portate dal fianco del flusso al flusso
stesso: il dossier per-indicatore che la Fase B ricostruiva e' ora la sorgente
del **lanciatore** (`pipeline_launch.py`) e del **monitoraggio**
(`pipeline_monitor.py`, la rotta `/_pipeline`), e la priorita' della pratica non
e' piu' un flag opt-in ma l'ordinamento nativo del piano di lancio. Cio' che
resta da rendere autorevole non e' un interruttore ma un confronto di metriche
(vedi Fase F).

| file | cosa | fase | prova |
| --- | --- | --- | --- |
| `scripts/practice_model.py` | stati, transizioni, tipi, errori, priorita' | A | `tests/unit/test_practice_model.py` |
| `scripts/practice_store.py` | lo store un-file-per-record delle pratiche | A | `tests/unit/test_practice_store.py` |
| `scripts/practice_timeline.py` | ricostruzione, riconciliatore, cicli, priorita' per stadio | B, C, E | `tests/unit/test_practice_timeline.py` |
| `scripts/practice_metrics.py` | le metriche del confronto prima/dopo (mandato §5) | F | `tests/unit/test_practice_metrics.py` |
| `scripts/pipeline_launch.py` | il piano di lancio per-indicatore, priorita' nativa | F | `tests/unit/test_pipeline_launch.py` |
| `scripts/pipeline_monitor.py` | la vista di lettura "dov'e' fermo e perche'", `/_pipeline` | B | `tests/unit/test_pipeline_monitor.py` |

```bash
python3 scripts/practice_timeline.py                       # una riga per indicatore
python3 scripts/practice_timeline.py --indicator eur:rd_e_gerdreg   # la storia intera
python3 scripts/practice_timeline.py --check               # dichiarato vs artefatti
python3 scripts/practice_metrics.py                        # le metriche, prima/dopo
python3 scripts/pipeline_launch.py                         # il piano di lancio, per priorita'
python3 scripts/pipeline_monitor.py                        # dov'e' fermo, e perche'
```

**Il passo del sito e' stato rimosso.** Con la ratifica di merge = pubblicazione
(§8) lo stato `pubblicata` si raggiunge al merge, quindi non c'e' piu' una
verifica del sito da agganciare: `scripts/verify_publication.py`, il registro
`data/pipeline/pubblicazioni/` e lo stadio `publisher` del cancello non esistono
piu'. Il flag `pipeline_launch.py --publish` sopravvive ma ora segna solo il
battito del lanciatore nel diario, non una verifica contro il sito.

**Resta fuori il cutover che rende il modello autorevole**, ed e' operativo non
codice: girare `practice_metrics.py` su run reali prima e dopo e documentare il
confronto. Legare allo stesso modo la scrittura dei record di pratica e' l'ultimo
pezzo. Il modello non diventa autorevole al posto dello stato dedotto finche' quel
confronto non e' documentato, come chiede il mandato. La sostituzione dello stato
dedotto con il record di pratica non e' ancora documentata su run reali.

---

## 15. Metriche (mandato 5)

Il progetto non e' riuscito perche' usa una PR unica. E' riuscito se, per ogni
indicatore, si sa senza ricostruzione manuale da dove e' partito, che decisioni ha
attraversato, su quali dati, perche' si e' fermato o e' avanzato, quale versione e'
pubblicata e se quella versione e' visibile e ancora valida. Le metriche misurano
proprio questo, e le soglie le fissa il team (decisione 18).

- **Osservabilita'**: quota di pratiche con storia completa, quota di eventi
  (run) associati a un indicatore (oggi solo prosa + inferenza dai file), pratiche
  con stato incoerente (le trova il riconciliatore).
- **Affidabilita'**: tentativi duplicati, transizioni applicate due volte,
  pratiche perse dopo una sessione interrotta, risultati invalidati pubblicati per
  errore, errori pubblici rilevati dopo la pubblicazione.
- **Velocita'**: tempo dall'ammissione alla pubblicazione (un tempo fino a tre
  settimane, che prima il tick e poi il lanciatore per-indicatore in parallelo
  hanno accorciato), tempo in ogni stato, tempo
  medio di blocco, tempo per una correzione urgente, pratiche ferme oltre soglia.
- **Qualita'**: correzioni dopo revisione, smentite dopo pubblicazione,
  aggiornamenti con vintage errato, controlli saltati, ritorni a uno stadio
  precedente.
- **Costo**: sessioni per pratica, tentativi per stadio, controlli ripetuti,
  pratiche annullate dopo molto lavoro, rapporto costo nuove / aggiornamenti.

---

## 16. Cosa questo documento **non** decide

Per onesta', le scelte che restano aperte e che la Fase A deve chiudere con il team
prima di scrivere codice:

1. Le **soglie** dei tetti di retry e della quarantena (§9), e le soglie delle
   metriche (§15). Sono un giudizio operativo, non una deduzione.
2. Il **formato esatto** del record di pratica e della matrice delle transizioni
   (§3, §4): la forma e' proposta, i campi vanno congelati insieme.
3. Se e quando spezzare i **CSV condivisi** (manifest, `curation.csv`) a un file
   per record (§11): serve solo quando la concorrenza sulle risorse condivise
   diventa reale, non prima.

Il resto e' unificazione di primitive che la catena ha gia'. Ed e' il motivo per
cui questa revisione si puo' fare senza rompere niente: il modello a pratica non e'
un secondo sistema accanto al primo, e' il primo, letto per indicatore invece che
per stadio.
