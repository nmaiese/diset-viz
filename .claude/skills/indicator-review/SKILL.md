---
name: indicator-review
description: >-
  Le classi di errore che le guardie automatiche di Divario Italia non vedono:
  definizioni sbagliate, universali, causali, aggregati ponderati contro media
  semplice, cifre provinciali, eco del cruscotto, tell da bot. Da caricare
  quando si scrive, si rilegge o si verifica un articolo indicatore.
---

# Le classi di errore che solo una lettura trova

La suite copre struttura, cifre attribuite a una regione, soglie, link e
vintage. `scripts/prose_lint.py` conta i tell meccanici. Tutto il resto è
questa lista: classi di affermazione che un regex trova ma solo una persona
giudica. Un flag della coda è un posto dove guardare, mai un verdetto. La
scala su cui si giudica il pezzo intero resta `docs/WRITING_RUBRIC.md`.

## `definizione` — l'articolo descrive un'altra quantità

L'errore più costoso e il più invisibile: rileggere undici articoli contro i
dati ha trovato **zero errori aritmetici** e quattro descrizioni sbagliate di
che cosa l'indicatore conta. `ter-402` chiamava "imprese a guida femminile"
quello che Istat definisce titolari donne di imprese individuali. `ter-72`
scriveva "almeno dieci addetti" dove la fonte dice "più di dieci": un'altra
popolazione con le stesse parole. Tutti sopravvissuti a una suite verde,
perché i numeri erano giusti.

```bash
python3 scripts/definition_check.py --show <codice>
```

Si legge la definizione ufficiale, poi la sezione `definizione`, poi `limiti`,
dove un perimetro sbagliato viene ripetuto come caveat. La prosa si corregge
verso la fonte, mai il contrario. Numeratore, denominatore e soglie si copiano
dalla fonte in parole piane, mai dedotti dal titolo. Il check usa gli archivi
committati in `data/definitions/` e copre territoriali, BES, Multiscopo,
Eurostat e demografici. `scoperto` significa che una serie nuova non è ancora
entrata nell'archivio: nessuno ha guardato, e lì si torna alla fonte.

## `universale` — "ovunque", "sempre", "da anni", "in tutte le regioni"

Un controesempio rende la frase falsa, e il brief lo trova in uno sguardo: il
blocco `SI MUOVONO CONTROCORRENTE` elenca i territori che contraddicono
l'affermazione. Se la frase regge, si tiene. Se un territorio la rompe, lo si
nomina: il controesempio è ciò che rende la frase onesta. "Primo nell'ultimo
anno" non è primo "da anni": ogni anno va controllato prima di scriverlo.

## `causale` — "grazie a", "dipende da", "spinto da"

Un indicatore territoriale mostra un livello, mai un meccanismo. Le uscite
oneste sono tre: documentare con una fonte vera in `fonti`, riformulare come
contesto ("nelle regioni con più imprese grandi il valore è più alto" dice
l'associazione, non la causa), o tagliare. Su un rimando a un altro indicatore
il verbo si calibra sulla prova: una correlazione di ranghi è una
co-occorrenza ("va di pari passo con", "si accompagna a"), un'ipotesi va
marcata come tale ("una possibile spiegazione è"), un nesso causale chiede
uno studio citabile progettato per stabilirlo. Confondente nominato (in questo
atlante è quasi sempre il reddito dell'area) e almeno un'eccezione.

E le decomposizioni che i dati non calcolano: due tassi con denominatori
diversi non dicono chi pesa di più, un tasso basso non si spacca in "quanti
hanno trovato lavoro e quanti hanno smesso di cercarlo".

## `esterno` — una cifra da fuori, senza fonte

Ogni claim su Europa, dato nazionale o primato si verifica con
WebSearch/WebFetch presso l'istituzione che lo pubblica e finisce in `fonti`
come `{testo, url}`. Non verificabile = si taglia. Mai inventare una fonte.

**La trappola che passa ogni guardia: un aggregato ponderato e la nostra media
semplice non sono la stessa quantità.** Istat, Eurostat, SVIMEZ, Banca
d'Italia e OCSE pubblicano aggregati ponderati; le nostre pagine fanno la
media di venti valori regionali. "In Italia lo fa un occupato su dieci" da una
media semplice è sbagliato anche ad aritmetica giusta. O si tengono separati
ed etichettati ("dato nazionale Istat" contro "la media semplice delle
regioni") o si taglia il confronto.

## `provincia` — cifre su un articolo provinciale

Le guardie numeriche conoscono i venti nomi regionali, quindi una cifra
attribuita a una provincia non la controlla niente. Si verifica a mano, una
per una, contro il brief:

```bash
bin/py -m officina.brief <codice> --level provincia
```

## `eco` — una cifra che il cruscotto già stampa

Il cruscotto mostra valore e posizione del territorio, il massimo e il minimo
con i nomi, la media, il divario e la variazione sull'anno prima. Una cifra
nella prosa deve fare un lavoro che quelle non fanno: ancorare un confronto,
dimensionare un cambiamento, marcare una soglia, nominare un gruppo. L'eco
silenziosa: il cruscotto stampa il conteggio sopra/sotto media, quindi una
frase geografica costruita su quegli stessi due numeri ("le prime dodici del
Centro-Nord, le ultime otto del Sud") ripete la macchina anche se cambia le
parole.

## `mestiere` — i tell che `content/STYLE.md` nomina

Il lessico da spia (*cruciale, panorama, tessuto, sottolineare, evidenziare,
giocare un ruolo*), i falsi intervalli ("dal Nord al Sud" quando i due capi
non sono un continuo), i riassunti compulsivi, il numero scritto due volte
("quasi la metà (48%)"), le strutture parallele, la domanda retorica di
chiusura che non risponde a niente. Nessuno rende una frase falsa, tutti si
correggono sul posto: c'è quasi sempre una parola più piana.

## Regole puntuali che non hanno un flag

- **Un indicatore `contextual` non ha un meglio.** Mai "migliora", mai
  "peggiora", mai una classifica di merito.
- **"Più che dimezzato" solo sotto la metà.** Da 13,76 a 6,89 è "quasi
  dimezzato".
- **Il livello dichiarato vincola le cifre.** Un articolo con `level:
  provincia` cita cifre provinciali, e viceversa.
- **La soglia legata a una regione.** La guardia lega `supera/sotto <numero>
  in <Regione>` al valore DI QUELLA regione: un divario o la cifra di un altro
  indicatore in quella forma fallisce. Regione prima ("in Campania supera i 36
  punti") o quantità nominata ("un divario di 36 punti in Campania").
