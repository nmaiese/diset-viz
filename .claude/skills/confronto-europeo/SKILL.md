---
name: confronto-europeo
description: >-
  Le trappole di comparabilità fra una serie territoriale italiana e un dato
  europeo, per Divario Italia. Quali istituzioni pubblicano confronti
  utilizzabili, perché le regioni NUTS2 non coincidono con le regioni Istat, e
  perché una media UE non si confronta con la media delle venti regioni. Da
  caricare quando si cerca o si giudica un confronto fra l'Italia e il resto
  d'Europa.
user-invocable: false
---

# Confrontare l'Italia con l'Europa senza dire una cosa falsa

Un confronto europeo è la cosa più utile che si possa aggiungere a una pagina
indicatore: dice al lettore se il numero che sta guardando è grande o piccolo,
e nessun calcolo sulla serie italiana glielo può dire.

È anche la più facile da sbagliare in un modo che nessuno vede, perché due
numeri con lo stesso nome si sommano volentieri in una frase anche quando
misurano cose diverse.

**Le trappole vengono prima del numero.** Si controllano tutte e quattro, e se
una non si risolve il confronto non si scrive: un articolo senza confronto
europeo è molto meglio di un articolo con un confronto sbagliato.

## 1. La media europea non è la nostra media

È la trappola che costa di più, perché il risultato sembra sempre
ragionevole.

Gli aggregati che pubblicano Eurostat e la Commissione (UE27, area euro) sono
**ponderati sulla popolazione**: la Germania pesa quanto vale, Malta pure. Il
valore nazionale del dossier di Divario Italia è la **media semplice delle
venti regioni**, dove la Valle d'Aosta pesa come la Lombardia. Sono due
grandezze diverse, e la differenza fra loro non è rumore.

Quindi:

- **Il dato italiano di un confronto europeo si prende dalla fonte europea**,
  che pubblica anche l'Italia, non dalla media del dossier.
- Se in un articolo compaiono tutte e due, ognuna va detta per quello che è,
  in mezza riga.

Un articolo di questo progetto ha già chiamato "media nazionale" la media
semplice delle regioni, ed è stata la prima cosa che la verifica ha smentito.

## 2. Le regioni europee non sono le nostre regioni

Le regioni statistiche europee sono le **NUTS2**, e per l'Italia non coincidono
con le regioni amministrative:

- Il Trentino-Alto Adige è **due** NUTS2, la provincia autonoma di Bolzano e
  quella di Trento. La serie Istat lo tratta come una regione sola.
- Alcuni dataset europei riportano il Piemonte, la Valle d'Aosta e la Liguria
  in un raggruppamento (NUTS1 Nord-Ovest) invece che una per una.

Un confronto regione per regione con una fonte europea quindi **non torna**, e
non è un errore dei dati. Il confronto che regge è fra **paesi**: l'Italia
contro la media europea, o contro i paesi vicini per valore. Se serve dire
qualcosa di una regione italiana in Europa, la fonte deve nominarla come NUTS2
e la frase deve dirlo.

## 3. Stesso nome, altra misura

Prima del numero si confrontano la **definizione**, il **denominatore** e la
**fascia** a cui si riferisce.

Il caso più comune: il tasso di occupazione, che l'Europa calcola sulla fascia
20-64 anni e alcune serie italiane sulla 15-64. Gli indici di rischio di
povertà cambiano soglia. I tassi di abbandono scolastico cambiano l'età di
riferimento.

Se la fonte europea non dichiara la definizione nella pagina che citi, il claim
vale al massimo come contesto e non come confronto numerico.

## 4. L'anno quasi mai coincide

Eurostat pubblica con più ritardo dell'Istat: è normale che l'ultimo anno
europeo sia uno o due indietro rispetto all'ultimo anno del dossier.

Non è un ostacolo, è una cosa da scrivere: il confronto si fa **sull'anno che
hanno in comune**, e l'anno si nomina nella frase. Confrontare il 2025 italiano
con il 2023 europeo senza dirlo è una smentita, anche quando tutti e due i
numeri sono veri.

## Dove si cerca

In quest'ordine, e ci si ferma appena si trova una pagina leggibile:

1. **Eurostat**, pagine Statistics Explained e schede dataset. Sono HTML, hanno
   la definizione accanto al numero e si verificano.
2. **Commissione europea**, relazioni di settore e quadri di valutazione.
3. **OCSE**, quando l'indicatore ha un equivalente nelle sue raccolte.
4. **Istat**, che spesso pubblica lei stessa il confronto europeo nei
   comunicati: è la fonte migliore, perché il raccordo fra le due definizioni
   l'ha già fatto qualcuno il cui mestiere è quello.

Una pagina HTML batte sempre un PDF a parità di autorevolezza: chi verifica
rifà il fetch esattamente come l'hai fatto tu, e un PDF che non restituisce
testo si scarta invece di inseguirlo.

## Che cosa autorizza un confronto in prosa

Un claim che regge un confronto europeo ha, oltre ai campi che
`verifica-fonti` già pretende, tutte queste cose:

- `usage: "external_comparison"`
- il **territorio** dichiarato (un paese, o "UE27", mai "Europa")
- l'**anno** del dato europeo, che quasi mai è quello del dossier
- l'**unità** e il denominatore, che devono combaciare con quelli
  dell'indicatore
- la **citazione testuale** che contiene il numero

Senza uno di questi il claim non è un confronto: è un'informazione di
contorno, e va usata come tale.
