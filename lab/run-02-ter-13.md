# Run 02, ter-13: come ragionano, e dove si sono rotti

Prima run della lite con l'architettura estesa (tre scout, gruppi, parenti,
forma variabile). Codice `ter-13`, tasso di occupazione, livello regione,
dati 2025.

`wf_d8e1d9f9-43d`, 8 agenti, 30 turni, 38 chiamate a strumenti, 15 minuti e 38
secondi, **3,89 $**, **zero articoli scritti**.

Non è un fallimento della catena: è la catena che fa quello per cui è stata
scritta. La bozza è stata smentita due volte e si è fermata **prima** del
disco, non dopo. Quello che va corretto sta nel giro di correzione, non nel
cancello.

Scelta del codice: `ter-61` era il primo `ter` della coda fresca, ma il suo nome
non ha una parentesi finale, quindi `_radice` non trova nessuna variante e gli
otto parenti sono tutti "stesso tema", **nessuno con valori**. Le due funzioni
nuove da mettere alla prova (citare la cifra di un fratello, linkarlo) sarebbero
rimaste spente. `ter-13` le accende tutte.

## I passaggi, per agente

| agente | modello | turni | strumenti | $ |
| --- | --- | --- | --- | --- |
| dossier | haiku | 2 | 1 Bash | 0,11 |
| eventi | sonnet | 6 | 1 Read, 2 ricerche, 3 fetch | 0,45 |
| perche-conta | sonnet | 6 | 1 Read, 2 ricerche, 3 fetch | 0,41 |
| europa | sonnet | 6 | 1 Read, 2 ricerche, 2 fetch | 0,33 |
| scrivi | sonnet | 2 | 1 Read | 0,90 |
| verifica | opus | 3 | 1 Bash, 1 Read, 3 fetch | 0,65 |
| correggi | sonnet | 2 | 1 Read | 0,21 |
| verifica (2) | opus | 3 | 1 Bash, 1 Read, 3 fetch | 0,81 |

Il giro precedente (`wf_3398ebc3-b19`, ter-6, uno scout solo): 42 turni,
4,99 $, e un verificatore che ne bruciava 16 senza restituire niente.

## Il freno tiene, e costa meno

Il budget dichiarato nel prompt è due ricerche e tre fetch. **Nessuno dei tre
scout ha sforato.** Al giro precedente lo scout unico faceva 3 ricerche e 5
fetch, e il verificatore 16 turni a decomprimere un PDF a mano.

Questo era il punto aperto più grosso: `maxTurns` dentro un workflow non viene
rispettato (16 dichiarati, 31 fatti alla run 1), quindi il budget scritto nel
prompt era l'unico freno e non era mai stato provato. Ora lo è.

Risposta alla domanda "quanto costa di più il ventaglio": **costa di meno.**

| | run 1 (uno scout) | run 2 (tre scout) |
| --- | --- | --- |
| contesto | 1,62 $, 9 turni | 1,19 $, 18 turni |
| lettura di cache, tutta la run | 1.762.475 | 643.835 |
| totale | 4,99 $ | 3,89 $ |

La cache riletta a ogni turno è il costo vero, e cresce col quadrato dei turni.
Tre agenti corti costano meno di uno lungo: 18 turni distribuiti su tre contesti
separati rileggono meno di 9 turni su un contesto solo.

**Cautela sulla misura**: il trascritto dell'agente `correggi` registra
`output_tokens: 2` sulla richiesta che ha restituito la bozza corretta intera.
È il trascritto a essere incompleto, non `baseline_tokens.py`, che lo legge
fedelmente. Alla run 1 lo stesso stadio registrava 5.061. Quindi 3,89 $ è un
pavimento, non una cifra esatta, e nel confronto con la catena complessa va
detto.

## Come ragionano

### Lo scout Europa ha detto di no, ed è la risposta giusta

Ha letto il dossier, ha visto che `ter-13` misura la fascia **15-64**, ha
cercato Eurostat e ha trovato che l'indicatore headline europeo è **20-64**
(il target Europa 2030). Ha fetchato la pagina per controllare e ha verificato
che non contiene nessuna cifra per paese sulla 15-64. I valori 15-64 trovati
via ricerca venivano da aggregatori secondari e si contraddicevano fra loro
(Italia data come 62,20% oppure 67,1% secondo la fonte). Ha restituito lista
vuota con il motivo.

E ha aggiunto da solo la seconda trappola della skill, senza che gliela
chiedesse nessuno:

> Va notato anche che il "valore nazionale" del dossier (63.04) è la media
> semplice delle 20 regioni, non un dato nazionale ponderato

È esattamente il difetto che il verificatore aveva preso al giro precedente,
ma preso qui **prima che il testo esistesse**. La skill `confronto-europeo` ha
fatto il suo lavoro proprio nel caso in cui il confronto non si fa.

### La lente eventi ha trovato la cosa che conta

Dal 1 gennaio 2021 la Rilevazione sulle forze di lavoro ha cambiato
metodologia, con ricostruzione obbligatoria delle serie storiche. Il dossier
elenca rotture nel 2022 su Valle d'Aosta, Toscana, Trentino Alto Adige, Puglia
e Marche, e nel 2021 sulla Basilicata: **rotture simultanee su più regioni**,
che nessuna spiegazione regionale può reggere.

Ha anche scartato una citazione debole (`un divario territoriale molto
consistente`) invece di forzarla dentro un claim.

### La lente "perché conta" ha pagato il pedaggio

Il report Istat sulla povertà assoluta è un PDF che il fetch non legge in
chiaro, e una seconda pagina Istat risponde 404: due fetch su tre buttati. Ha
applicato la regola "non si insegue" invece di combattere col PDF, che è
precisamente il comportamento mancato alla run 1. Col fetch rimasto ha preso un
claim laterale (studio Banca d'Italia su asili nido e fertilità, ripreso da
ANSA) e ha lasciato scritto a chi scrive dove andare a prendere il resto.

Onesto, ma il materiale più solido (occupazione e povertà) è rimasto fuori.
Il budget è un freno che taglia anche il buono, e questa è la sua prima
fattura leggibile.

### Chi scrive ha usato i gruppi, non la geografia

Angolo scelto: **"Un'Italia spaccata in tre, non in due"**. Quattro sezioni,
`quadro / dinamica / quadro / limiti`, nessuna `definizione`, due link interni.
Ha costruito il pezzo sul blocco `gruppi`, notando che i tre gruppi che i valori
formano da soli non ricalcano le tre macroaree, e che Toscana, Umbria e Marche
stanno col Nord mentre il Lazio sta col Sud.

Il verificatore ha registrato la tensione senza smentirla: il dossier dice
`coincide_con_macroaree: true` con sovrapposizione 0,8, quindi l'angolo vive nel
residuo del 20%, e lo definisce "difendibile ma tirata". Giusto così: è una
lettura, non una cifra, e il posto per giudicarla è un lettore, non un
controllo.

I due link (`ter-177`, `ter-178`) sono entrambi risultati "nel dossier",
copiati da `percorso_canonico`, nessuno composto a mano. E il meccanismo che
doveva impedire l'autosabotaggio ha girato davvero: nell'uscita di
`lab.controlla` i quattro valori dei fratelli sono ammessi con la loro
etichetta, non a mano dal verificatore.

```
58,06 -> valore di Tasso di occupazione (maschi) (ter-177) per Calabria nel 2025
34,86 -> valore di Tasso di occupazione (femmine) (ter-178) per Calabria nel 2025
77,8  -> valore di Tasso di occupazione (maschi) (ter-177) per Trentino Alto Adige nel 2025
67,88 -> valore di Tasso di occupazione (femmine) (ter-178) per Trentino Alto Adige nel 2025
```

**La richiesta 6 funziona da capo a fondo**, `_voci_dei_parenti` compreso.
Senza, queste quattro cifre sarebbero state smentite e al secondo giro chi
scrive avrebbe tolto due link buoni.

## I quattro difetti da correggere

### 1. La correzione tocca il corpo e lascia il titolo

Al primo giro il verificatore smentisce la frase che attribuisce parte della
crescita del 2022 al cambio di metodologia. Chi scrive corregge il corpo,
correttamente, e ci scrive dentro **"è una coincidenza temporale, non una
prova"**.

Ma lascia il titolo della sezione: **"Il balzo del 2022 è anche un cambio di
righello"**. E lascia l'`angolo`, che continua a dire "una parte del balzo
coincide con un cambio nel modo in cui l'Istat conta".

Al secondo giro il verificatore lo prende con gravità **alta**: il titolo
afferma il contrario del proprio testo. E ha ragione anche nel merito, con un
argomento che al primo giro non era stato fatto: il cambio decorre dal 1 gennaio
2021, quindi cinque dei sei salti, tutti datati 2022, sono misurati fra due anni
**entrambi già sotto la nuova definizione**.

Causa: il prompt di correzione dice `Cambia SOLO ciò che ognuna nomina`. Serve
a impedire che la correzione riscriva l'articolo, e quel vincolo va tenuto. Ma
un titolo di sezione e un `angolo` sono **lo stesso claim in un altro posto**, e
oggi nessuno lo dice a chi corregge.

Cura: aggiungere al prompt di correzione che una smentita su una frase vale
ovunque quel claim compaia, titolo, lead e `angolo` compresi, e che la sezione
va riletta intera dopo la correzione per vedere se il titolo regge ancora.

### 2. La classe di difetto non propaga

Il primo verdetto smentisce il `63,04%` presentato come tasso nazionale: è la
media semplice delle venti regioni. Chi corregge ri-etichetta le **tre**
occorrenze del 63,04 con cura, elencandole una per una.

E lascia `16,85 punti` nel lead, che è la differenza fra due medie semplici di
otto regioni ciascuna, cioè **lo stesso identico difetto**. Il verificatore lo
prende al secondo giro, e nota che la stessa cifra è etichettata correttamente
nella dinamica ("misurato sulle medie di macroarea"): il lead è l'unico punto
dove sopravvive.

È la stessa lezione già scritta per Codex: **passare in rassegna la classe di
difetto, non il punto segnalato**. Vale per il correttore quanto per il
revisore, e oggi non è scritto da nessuna parte in `lab-scrittore.md`.

### 3. Il verificatore non è esaustivo per giro

Al secondo giro compare una smentita di tipo `cifra` che al primo non c'era, su
un passaggio che il primo giro non aveva toccato: il gruppo intermedio descritto
come "a crescita più rapida" mentre nel dossier `delta_5a` mostra che le
regioni del gruppo più basso crescono quanto o più.

Verificato col diff delle due bozze: nella sezione `quadro` l'unica cosa
cambiata è `media nazionale` diventato `media delle venti regioni`. **La frase
smentita al secondo giro è identica parola per parola nella prima bozza.**
Quindi non è stata introdotta correggendo: c'era, e il primo passaggio non
l'ha vista. Due giri trovano più cose di uno **anche a testo fermo**.

Conseguenza operativa: con un solo giro di correzione, una catena che smentisce
a strati non converge. O si accetta che il secondo verdetto sia l'ultimo e si
pubblica con i rilievi bassi aperti, o serve un terzo giro, che raddoppia il
costo dello stadio più caro (opus, 0,65 e 0,81 $ i due giri). Da decidere dopo
il confronto, non adesso.

### 4. Il territorio vicino cancella il candidato giusto

Il verificatore ha verificato 66 cifre e ne ha dovute ricontrollare otto a mano.
Guardando l'uscita vera del comando, la causa non è la tolleranza: è
`_territori_vicini`, che pesca il territorio dalla finestra sbagliata e poi
**quel territorio sbagliato filtra via il candidato vero**.

| cifra nel testo | territorio dedotto | esito | è davvero |
| --- | --- | --- | --- |
| 51,01 | Trentino Alto Adige | nessuna corrispondenza, propone la media del Mezzogiorno | Puglia 2025 |
| 64,17 | Marche | nessuna corrispondenza, propone la media dell'ultimo anno | Lazio 2025 |
| 80 | Trentino Alto Adige | nessuna corrispondenza | `sovrapposizione_con_macroaree` 0,8 |

Il contesto stampato dal comando lo mostra: `tra 46,41 e 51,01%, è compatto e
tutto meridionale: Calabria,` e il territorio dedotto è il Trentino, rimasto
dalla frase precedente. Gli estremi di un gruppo appartengono a regioni nominate
prima o dopo, mai accanto al numero.

Poi c'è il difetto speculare, ed è il più grave perché produce un **falso
positivo dichiarato corretto**:

```
64 (quadro) -> valore di Lazio nel 2025 (territorio non nominato nella frase)
              [scritto 64, dato 64.17]     stato: TROVATA
   contesto: è una persona su cento, tra i 15 e i 64 anni, che ha un lavoro
```

Il 64 è l'estremo della fascia d'età. Nella frase non c'è nessun territorio,
quindi il ramo che entra quando `vicini` è vuoto mette a candidato **tutti** i
territori dell'anno, e il Lazio a 64,17 rientra nella tolleranza dell'1,1%. Il
comando ha detto "trovata" su una cifra che non è un valore. Il gemello `15`
della stessa frase è finito invece fra le non trovate, proposto contro il
coefficiente di variazione 14,0.

Nessuna di queste ha prodotto una smentita sbagliata, perché opus le ha
smontate una per una a mano. Ma è rumore pagato a prezzo di opus, e un falso
positivo è peggio di un falso allarme: il falso allarme lo si vede, questo no.

Cura, in due mosse che non si toccano:

1. un territorio dedotto non deve mai **togliere** candidati. I valori degli
   altri territori dell'anno vanno aggiunti sempre, con l'etichetta che dichiara
   che l'attribuzione è dedotta, invece di comparire solo quando `vicini` è
   vuoto;
2. a parità di distanza, preferire la corrispondenza **esatta** a quella per
   tolleranza, ed escludere dai candidati i numeri che fanno parte di un
   intervallo di età (`tra i 15 e i 64 anni`), che sono etichette come gli
   anni e non grandezze misurate.

## Che cosa resta non provato

La run si è fermata prima della pubblicazione, quindi:

- `impaginazione` (gli H2 che la pagina renderebbe) non è mai stata stampata,
  e il rifiuto sulle sezioni perse non è mai scattato;
- `lab.pubblica` non ha girato, e con lui il lint;
- `usage: external_comparison` non è mai stato emesso, perché lo scout Europa
  ha giustamente restituito una lista vuota. Per esercitarlo serve un indicatore
  la cui definizione coincida con quella europea.

## Che cosa cambiare, in ordine

1. `lab-scrittore.md`, modo correggi: una smentita vale ovunque quel claim
   compaia (titolo, lead, `angolo`), e la classe di difetto va passata in
   rassegna, non solo il punto segnalato. Sono i difetti 1 e 2, sono la stessa
   cura, e sono la ragione per cui questa run non ha prodotto niente.
2. `lab/controlla.py`: un territorio dedotto non toglie candidati, e un numero
   dentro un intervallo di età non è una grandezza. Difetto 4, e la metà
   grave è il falso positivo, non i falsi allarmi.
3. Il numero di giri di correzione: da decidere dopo il confronto. Difetto 3.

## Le correzioni applicate, 2026-08-08

Tutte e tre, nello stesso giro, e poi la run ripresa dalla cache con
`resumeFromRunId`: dossier, tre scout e prima bozza non si rifanno, ripartono
la correzione e la seconda verifica. Il ripescaggio costa circa 1 $ contro i
3,89 $ di una run intera, e soprattutto rimette in gioco **la stessa bozza**,
quindi ciò che cambia è il giro di correzione e nient'altro.

**`lab/controlla.py`**, tre mosse:

1. `ETA`, che riconosce una fascia (`15-64 anni`, `tra i 15 e i 64 anni`) e
   tratta i suoi due numeri come etichette, come già si fa con gli anni. Solo
   l'intervallo, mai il numero singolo: "negli ultimi 5 anni" è una durata, e
   chiamarla età sarebbe un'etichetta sbagliata al posto di nessuna.
2. Un secondo giro di accoppiamento sui candidati larghi (tutti i territori
   degli anni citati, etichettati come dedotti) quando quelli stretti non danno
   niente. Un territorio dedotto adesso può solo aggiungere, mai togliere.
3. I gruppi entrano fra le voci derivate: le tre bontà in frazione **e** in
   percentuale, gli estremi di ogni gruppo, la cardinalità. La prosa scrive
   "l'80%", il dossier tiene 0,8, e senza le due forme una cifra centrale
   dell'articolo finiva fra le non trovate.

Misurato sulla stessa bozza congelata: **da otto cifre da ricontrollare a
mano a una**, e quella è il 2026 di pubblicazione di ANSA, cioè esattamente
il caso che il docstring lascia al verificatore. Il falso positivo del `64` non
c'è più. `ter-6` resta a 40 su 40.

**`lab-scrittore.md`** e il prompt di correzione del workflow: una smentita
nomina una frase ma vale sul claim, quindi si cambia anche ogni altro posto
dove quel claim compare (titolo, `lead`, `angolo`) e ogni altro punto con lo
stesso difetto, e in `correzioni` si dichiara dove si è propagato.

**`lab-verificatore.md`**, ottavo passo: trovato un difetto, cercarne la classe;
e `angolo`, `lead` e ogni `h` sono testo da giudicare come il corpo. Un titolo
che afferma ciò che il suo corpo nega è una smentita con la stessa dignità
di una cifra sbagliata.

Il file dell'agente non basta a far ripartire uno stadio: la cache del workflow
è battuta su prompt e opzioni, non sul contratto dell'agente. Per questo la
correzione è cambiata anche nel workflow, ed è quella modifica a rimettere in
moto lo stadio giusto lasciando gli scout dove sono.

### L'esito del ripescaggio

**Da quattro smentite a una**, e la gravità alta è sparita. Costo del solo
ripescaggio 1,38 $ (36 turni cumulati contro 30, cioè sei turni nuovi).

La propagazione funziona, e si legge nelle `correzioni` dichiarate:

> titolo della sezione limiti (da 'Il balzo del 2022 è anche un cambio di
> righellò a 'Il balzo del 2022 e il cambio di righello: una coincidenza, non
> una provà), angolo (da 'coincide con un cambio... non solo con più lavoro
> verò a 'coincidono con un cambio... introdotto proprio in quel periodò)

Il difetto 1 è chiuso: chi corregge tocca ora titolo e `angolo` insieme al
corpo, e dichiara dove ha propagato.

**Il difetto 2 no, non del tutto.** Il `16,85` del lead è ancora lì senza
etichetta, e questa volta il verificatore non l'ha ripreso: la frase adesso
apre con "La media del tasso di occupazione nelle venti regioni italiane", e
dentro quella cornice la seconda metà passa. Difendibile, ma la classe di
difetto non è stata passata in rassegna, e chi l'ha lasciata correre è un
opus che la volta prima l'aveva vista. **Due opus sullo stesso difetto danno
due risposte**, ed è una cosa da sapere prima di appoggiarsi a un giudice
solo.

**Quel che resta è esattamente il difetto 3.** L'unica smentita è la stessa
frase di prima ("un gruppo di regioni del Sud a crescita più rapida"), presente
dalla prima bozza, che il primo passaggio non ha mai visto. Il verificatore
adesso la smonta con i numeri in mano (il Molise, che sta nel gruppo, è la
regione meridionale cresciuta **meno** di tutte) e scrive lui stesso la cura:
togliere quattro parole.

Ma il giro di correzione è uno solo, quindi l'articolo si ferma di nuovo. Non
per un difetto grave: per un difetto scoperto tardi. Il nodo da sciogliere è
questo, e non è più rimandabile al dopo-confronto:

- **un secondo giro di correzione** costa un opus in più (circa 0,8 $) e
  chiude questo caso;
- **oppure** si pubblica quando restano solo rilievi `bassa` e `media`, e le
  smentite gravi restano le uniche a fermare. Il verificatore già assegna la
  `gravita`, quindi il dato per decidere c'è e non è usato da nessuno.

La seconda strada è più onesta con quello che la lite è: un solo controllo,
nessun cancello, e un giudizio che si consegna invece di iterare finché tace.

Restano non provati, per la terza volta, `impaginazione`, `lab.pubblica`, il
lint e `usage: external_comparison`.

### Il terzo passaggio: iterare non converge

Aggiunto un terzo passaggio del verificatore (`VERIFICHE = 3`, due giri di
correzione). Ha trovato **due smentite nuove**, tutte e due su frasi presenti
dalla prima bozza e mai toccate da nessuna correzione: il Lazio che
nell'`angolo` "si allinea al Sud" (sta a 64,17, sopra la media delle venti
regioni e sopra ogni regione del Mezzogiorno: sta in quel gruppo perché il
gruppo è una fascia di livello, non perché somigli al Sud), e il titolo
"Perché un punto di occupazione pesa di più sulle donne", che promette un
"perché" che il corpo non spiega e usa un "peso" che il dossier non misura.

Il conto per passaggio, sempre sullo stesso testo e sempre roba nuova:

| passaggio | rilievi | gravità massima |
| --- | --- | --- |
| primo | 3 | media |
| secondo | 1 | media |
| terzo | 2 | media |

**Non è il testo che non converge, è la lettura.** Un critico forte richiamato
un'altra volta trova un'altra cosa, e a questo ritmo un articolo non esce mai:
il quarto passaggio ne troverebbe altre, tutte vere e nessuna grave. La strada
dei giri è chiusa, e la misura che la chiude è questa tabella.

Quindi il freno non è più il silenzio del critico ma la **gravità che il
critico stesso assegna**. All'ultimo passaggio l'articolo esce se non restano
rilievi `alta`, e i rilievi che restano viaggiano col pezzo in
`rilievi_aperti` invece di sparire. Un rilievo senza gravità dichiarata conta
come grave: una severità che nessuno ha scritto non è un permesso a
pubblicare.

È anche più fedele a cosa è la lite: un solo controllo, nessun cancello, un
giudizio che si consegna. Il verificatore assegnava già la `gravita` a ogni
rilievo, e fino a qui non la leggeva nessuno.

### Scritto

`data/lab/articoli/13.json`, 782 parole, due giri di correzione, 64 cifre
verificate, due rilievi aperti non gravi che viaggiano con l'articolo.

**La forma variabile arriva fino in fondo.** L'impaginazione che il
pubblicatore ha stampato, cioè gli H2 che la pagina renderebbe, è questa, e
`indicator_texts.emitted_roles` sull'articolo scritto restituisce esattamente
`['quadro', 'dinamica', 'quadro', 'limiti']`:

| ruolo | H2 | parole |
| --- | --- | --- |
| quadro | Un'Italia spaccata in tre, non in due | 208 |
| dinamica | Il Sud rincorre, ma il divario non si chiude | 174 |
| quadro | Perché un punto di occupazione pesa di più sulle donne | 180 |
| limiti | Il balzo del 2022 e il cambio di righello: una coincidenza, non una prova | 190 |

Nessuna sezione persa, nessuna `definizione` (assorbita), due `quadro` distinti
che sopravvivono al renderer. È la prima volta che la richiesta 3 si vede
finita invece che dimostrata su un caso di prova.

Provato anche sul renderer vero e non solo sulla simulazione di
`lab.pubblica`: sostituendo `indicator_texts.get_text`, `build_article` sul
file scritto restituisce quattro sezioni tutte `authored`, con gli stessi
titoli e le stesse lunghezze, e `come_leggere: True`, cioè il blocco "Come
leggere il dato" al posto dell'H2 di definizione. La forma del file di
`data/lab/articoli/` è la stessa di `content/indicators/` (`lead`, `sections`,
`fonti`, `key`, `vintage`), quindi la simulazione e il render leggono la stessa
cosa.

Lint: **un solo rilievo**, `dinamica-senza-fonte` di severità `segnala` (il
corpus non ha contesto citabile per questo indicatore). Lo stesso rilievo, e
solo quello, che aveva preso `ter-6`.

Costo cumulato dell'intera vicenda, quattro lanci compresi i tre ripescaggi:
**6,62 $ e 43 turni**. Le tre riprese sono costate meno di 3 $ in tutto perché
scout e prima bozza non si sono mai rifatti.

**Quanto costi una run pulita di questa architettura non lo sappiamo ancora.**
Il 6,62 $ contiene tre replay pagati zero, quindi ricavarne per sottrazione un
"circa 4,7 $" sarebbe una stima, non una misura, e finirebbe citata contro
l'1,97 $ misurato della catena attuale. Il numero vero si prende con un lancio
solo, dall'inizio alla fine, e quello è il primo pezzo del confronto.

### Che cosa resta aperto

- `usage: external_comparison` non è ancora mai stato emesso. Serve un
  indicatore la cui definizione coincida con quella europea.
- Il `16,85` del lead resta senza etichetta e nessuno dei tre passaggi l'ha
  ripreso dopo il primo. Non è grave, ma è il promemoria che **due letture
  dello stesso opus danno due risposte**, e che il freno sulla gravità è
  necessario proprio perché il giudizio non è stabile.
- La seconda run sulla stessa architettura, su un `bes`/`ims` a 0/4, per
  esercitare l'assorbimento della `definizione` dove non esiste una definizione
  ufficiale.
- Poi il confronto con la catena attuale sullo stesso codice.

## Run 03, bes-04BEC003 (Rischio di povertà): scrittore su opus

`wf_2bb7c8b6-41f`. **Articolo scritto**: 1055 parole, sei sezioni, 113 cifre
verificate, due giri di correzione, un rilievo aperto di gravità bassa.

Prima prova con lo scrittore su opus e con le tre letture del verificatore.

**Opus scrive un altro articolo, non solo più caro.** Sei sezioni contro
quattro, con due `dinamica` e tre `quadro`: la forma variabile usata come
strumento e non come dimostrazione. I titoli sono asserzioni ("Si muove il
centro, gli estremi stanno fermi"), non etichette.

**Le tre letture alzano la copertura di metà**: 113 cifre contro le 64 di
`ter-13`. E cambiano il grado dei rilievi. Il più istruttivo: il verificatore
ha rifetchato la pagina ANSA, ha trovato la citazione **identica**, e l'ha
smentita lo stesso, perché quel 20% -> 18,8% non è una variazione osservata fra
due anni ma l'uscita di una microsimulazione. Una verifica per stringa la
promuoveva. Altri due della stessa classe: "5,73 volte" è un rapporto fra
percentuali e il testo lo raccontava come rapporto fra persone; "la serie più
aggiornata del suo tema" è un pari merito, non un primato.

**Costo: 8,73 $ per 66 turni**, di cui 1,70 $ spesi nella run interrotta per il
difetto degli accenti. Una run pulita di questa configurazione sta intorno ai
**7 $**, contro i 3,89 $ di `ter-13` con sonnet e due verifiche. Il prezzo sta
quasi tutto in opus che scrive e in tre passaggi opus che verificano.

**Due falsi positivi del lint della catena attuale**, entrambi `blocca`:
"Lombardia detto 1,24, dato 9.2" e "Molise detto 4,75, dato 17.5". Sono le
**volatilità**, dette correttamente dal testo ("la volatilità del Molise è
4,75"), e `lab.controlla` le etichetta giuste. È la stessa classe di difetto
che la lite ha già corretto dentro di sé: un numero accostato al valore della
regione nominata accanto. Qui il metro ha avuto torto, e non ha fermato niente
perché nella lite non è un cancello.

### Il prossimo difetto di `lab.controlla`: il segno

Sull'articolo pubblicato restano 9 cifre `non_trovata`, e la maggioranza ha una
causa sola: una variazione negativa raccontata in parole come una perdita si
scrive positiva. Il dossier ha `salto di Molise nel 2023: -9.9`, il testo dice
"il Molise perde 9,9 punti", e il confronto fallisce di 19,8.

Cura: offrire anche il valore assoluto dei candidati con segno (delta, salto,
variazione, scarto), con l'etichetta che dice che è in valore assoluto. Il
verificatore li ha sciolti a mano tutti e nove, ma è lavoro pagato a prezzo di
opus per un difetto aritmetico.

### Il segno, corretto e misurato

Due aggiunte a `lab/controlla.py`, tutte e due come **ripiego**, cioè solo
quando i candidati normali non danno niente:

1. il valore assoluto dei candidati di segno opposto, etichettato "in valore
   assoluto". Copre "il Molise perde 9,9 punti" contro `salto di Molise nel
   2023: -9.9`;
2. le voci calcolate che appartengono a un territorio (delta, salti,
   volatilità, scarti) rimesse in gioco quando la frase nomina il territorio
   sbagliato. Prima il ripiego rioffriva solo i **valori** delle regioni.

La prima versione le ammetteva con la tolleranza dell'1,1%, e i falsi allarmi
sparivano portandosi via il controllo. Misurato alterando una per una le 76
cifre dell'articolo `bes`:

| | falsi allarmi sull'articolo vero | alterate di +0,5 | +2,0 | +7,0 |
| --- | --- | --- | --- | --- |
| prima delle aggiunte | 9 | 40/76 | 45/76 | 42/76 |
| aggiunte con tolleranza | 0 | 15/76 | 29/76 | 38/76 |
| aggiunte **esatte** | 0 | 40/76 | 43/76 | 56/76 |

Il ripiego esatto tiene tutte e due le cose, e la ragione è che chi scrive le
cifre del dossier le **copia**: la tolleranza serve per la prosa che arrotonda,
non per un accoppiamento che è già una supposizione. La riga di mezzo è il
motivo per cui questa misura andava fatta invece di guardare i falsi allarmi e
dichiarare vittoria.

Resta il limite noto e dichiarato: `18,37` alterato in `19,10` non viene
smentito, perché combacia con `media nazionale nel 2023` (19,01) dentro la
tolleranza. Il comando non è un cancello, stampa un elenco **etichettato**, e
una corrispondenza assurda la vede chi legge la riga. È il secondo passo delle
tre letture del verificatore, non un lavoro dello script.

### Interrogare invece di arbitrare

Due aggiunte, dopo la domanda "non conviene dare gli strumenti al verificatore
invece di fare controlli dopo?".

La risposta è che le due cose fanno lavori diversi e servono tutte e due. Lo
spazzolamento garantisce la **copertura**: un modello a cui si chiede di
guardare 109 cifre ne salta, uno script no. L'interrogazione serve alla
**risoluzione**: lo script non sa se "media nazionale nel 2023" è il referente
giusto per una frase che parla del 2025.

1. **`--cerca NUMERO`**, dentro `lab.controlla` e non in un comando nuovo,
   perché il contratto del verificatore gli concede un solo eseguibile.
   Restituisce ogni voce del dossier compatibile con quel numero. Su `19,10`
   ne trova sette, e la prima riga dice tutto: `19.1 (valore di Liguria nel
   2022)`.
2. **Due marcatori nel riepilogo**, tarati sul rumore invece che sull'idea:
   - `[oppure: ...]` solo dove la corrispondenza è arrivata da un ripiego.
     Provato su tutte le cifre riempiva 75 righe su 109 di **sinonimi dello
     stesso valore** e faceva crescere l'uscita del comando di due volte e
     mezzo. Ristretto ai valori davvero diversi e ai soli ripieghi: 9 righe.
   - `[ATTENZIONE: l'etichetta parla del 2023, la frase del 2025]`, che è il
     caso che ha motivato tutto. Cinque righe su `bes`, quattro su `ter-13`,
     tre su `ter-6`.

Costo delle due: circa 400 token in più nel risultato che il verificatore già
riceve, e zero chiamate in più. Quello che **non** si fa è sostituire lo
spazzolamento con 109 interrogazioni: i turni sono il costo di questa
architettura e crescono col quadrato, e il verificatore passerebbe da tre turni
a cento per un lavoro che una funzione fa gratis.
