---
name: scrittura-indicatori
description: >-
  Il mestiere di scrivere la prosa di una pagina indicatore di Divario Italia.
  Quali temi un articolo copre, come si sceglie la forma e quante sezioni
  servono, i vincoli tipografici del progetto, i link agli indicatori
  imparentati e le regole di onestà causale. Da caricare quando si scrive, si
  corregge o si giudica la prosa di una pagina indicatore.
user-invocable: false
---

# Scrivere la prosa di una pagina indicatore

## Dove finisce quello che scrivi

Divario Italia (divarioitalia.it) è un atlante degli indicatori territoriali
italiani. Ogni indicatore ha una pagina, e ogni pagina ha già un grafico, una
tabella per territorio, una mappa e un blocco "come leggere il dato": tutto
questo il lettore lo vede senza di te.

La tua prosa sta sopra quel cruscotto e ha una sola ragione di esistere: **dire
quello che il grafico non dice**. Un testo che elenca i valori più alti e i
più bassi ripete il grafico in parole, e il lettore lo sente subito.

Chi legge non è uno statistico. È arrivato da una ricerca, ha una domanda
concreta ("come sta messa la mia regione?", "è vero che il divario si allarga?")
e decide in due frasi se restare.

## La tesi la scegli tu

Nessuno a monte ti propone un angolo. Il dossier porta cifre, anomalie, gruppi
e parenti, gli scout portano contesto verificato: sono **materiale**, non una
scaletta. Quale storia questo indicatore racconta quest'anno è una decisione
editoriale, e la prendi tu quando hai tutto davanti.

Dichiarala in `angolo`, in una riga, dicendo anche perché quella e non
un'altra. Se la tesi che scegli non è fra le anomalie misurate, va benissimo:
le anomalie sono i punti in cui la serie non somiglia a se stessa, non una
classifica di che cosa vale la pena raccontare.

Una tesi buona si riconosce così: **la si potrebbe contraddire**. "Il divario
Nord-Sud è ampio" non è una tesi, è l'aria. "Il divario non è geografico:
due regioni a statuto speciale stanno da sole, e tutte le altre si somigliano"
lo è.

## I temi, non lo stampo

Un articolo copre alcuni di questi temi, **non per forza tutti e non sempre
nello stesso ordine**:

| tema | la domanda a cui risponde |
| --- | --- |
| Che cosa misura | numeratore e denominatore, chi è contato e chi no |
| Differenze territoriali | come si distribuisce oggi, e che cosa rende notevole questa distribuzione |
| Andamento nel tempo | come ci si è arrivati: il movimento, la rottura, il sorpasso, la convergenza |
| Confronto europeo | se l'Italia sta sopra o sotto, e di quanto |
| Perché conta | che cosa cambia nella vita di chi ci abita |
| Limiti | che cosa questo numero non dice, e le note della fonte |

Quali coprire lo decide la tesi. Un indicatore senza confronto europeo
verificato non ha quella sezione. Un indicatore la cui storia sta tutta nel
tempo può avere due sezioni di dinamica e una sola sul quadro.

Le fonti non sono un tema: la pagina le rende già in un blocco suo, tu le
metti in `fonti`.

## Come si costruisce la forma

Ogni sezione ha un `role` fra questi quattro, e **solo** questi quattro:
`definizione`, `quadro`, `dinamica`, `limiti`. Un ruolo diverso viene scartato
in silenzio dalla pagina.

Ma i quattro ruoli sono **contenitori**, non i quattro titoli dell'articolo. La
pagina rende una sezione per ogni voce che scrivi, **nell'ordine in cui la
scrivi**, e il titolo lo prende dal tuo campo `h`. Quindi:

- **Un ruolo si può ripetere.** Due `quadro` con due `h` diversi rendono due
  titoli diversi. È così che un confronto europeo o un "perché conta"
  trovano posto.
- **L'ordine è quello che scegli tu.** Non c'è nessuna sequenza obbligata.
- **La `definizione` si può omettere.** Quando non la scrivi, la pagina compone
  da sola il blocco "Come leggere il dato" dai metadati, e l'articolo non apre
  più spiegando la meccanica. Spesso è meglio: apri sulla tesi. Omettila
  sempre quando il dossier ha `definizione: null`, perché vuol dire che il
  progetto non ha la definizione ufficiale e non la devi inventare tu.

**La regola che non si può rompere**: `quadro`, `dinamica` e `limiti` devono
esserci tutti e tre, ognuno con un corpo scritto. Se ne manca uno, la forma che
hai scelto viene buttata via e le sezioni in più spariscono senza che nessuno
se ne accorga. Chi pubblica rifiuta l'articolo quando succede.

Il titolo di ogni sezione lo scrivi tu, in lingua comune, e dice di che cosa
parla quel pezzo. "Dove sta l'Italia in Europa" è un titolo. "Confronto
europeo" è un'etichetta.

`lead`: la prima frase sta sotto i 200 caratteri, perché diventa la meta
description della pagina. Deve contenere il fatto più notevole, non una
premessa.

## Gli indicatori imparentati

Il dossier porta un blocco `parenti`: altri indicatori del catalogo che
raccontano una storia vicina, ognuno col nome, il percorso e spesso i valori
regione per regione.

**Da uno a tre entrano nell'articolo**, con un ruolo chiaro nella frase. Sono la
cosa che distingue un articolo che sta dentro un atlante da una scheda isolata,
e oggi quasi nessun articolo li usa.

- Il percorso si **copia** da `parenti`, non si compone a mano. Forma
  `/indicatore/<slug>/<codice>`, mai `/?indicator=`.
- L'anchor dice dove porta: `[il tasso di occupazione femminile](...)`, mai
  "clicca qui", "leggi", "qui".
- La frase che vale il link è quella che legge **lo stesso territorio su due
  indicatori**: "in Calabria lavora il 58,06 degli uomini e il 34,86 delle
  donne". I valori dei parenti stanno nel dossier, campo `valori`: solo quelli,
  nessuno dedotto.
- Un parente citato senza numero e senza ruolo nella frase è un link
  decorativo, e non conta.

## Le regole assolute

Queste non si negoziano, valgono su tutto il progetto e alcune sono controllate:

1. Mai il trattino lungo `—` né quello medio `–`. Virgole, o due frasi. Per gli
   intervalli: "dal 1999 al 2020".
2. Mai il punto e virgola `;`.
3. Mai i puntini in un carattere solo `…`. Se servono, tre punti separati.
4. Virgolette dritte, `"` e `'`.
5. **Gli accenti sono accenti, mai un apostrofo.** Si scrive `è`, `perché`,
   `più`, `già`, `così`, `può`, `città`, `povertà`, `né`, `sé`, `lì`, `ciò`.
   Mai `e'`, `perche'`, `piu'`, `poverta'`. L'unica parola che tiene
   l'apostrofo è `po'`, e le elisioni restano quelle che sono (`l'anno`,
   `un'altra`, `c'è`). Questa regola vale **solo per la prosa che scrivi**: i
   documenti interni e le istruzioni che stai leggendo possono usare
   l'apostrofo per ragioni loro, e non sono un modello da imitare. La pagina
   la legge una persona.
6. Solo cifre vere, prese dal dossier o da un claim verificato. Nessun numero
   dedotto, nessuna fonte inventata, nessuna percentuale calcolata a mente.
7. Mai scrivere il numero due volte ("quasi la metà (48%)"): o la parola o la
   cifra.

Se una skill generale di italiano suggerisce il contrario (caporali `« »`,
trattini spaziati, punto e virgola), **vincono queste regole**.

## Le cifre

Puoi citare solo cifre che stanno nel dossier: valori, medie, mediane, spread,
delta, ranghi, gruppi, valori dei parenti. Il dossier porta già calcolato tutto
ciò che serve, comprese le differenze fra anni: se ti viene voglia di fare una
sottrazione, la trovi già fatta.

**Quando citi una cifra di un anno che non è l'ultimo, scrivi l'anno accanto.**
"Nel 2014 l'Emilia-Romagna arrivava a 52,13", non "l'Emilia-Romagna arrivava a
52,13". Senza l'anno la frase dice una cosa falsa sull'ultimo anno, e un
controllo automatico la boccia giustamente.

Le medie territoriali del dossier sono **medie semplici sulle regioni**, non
ponderate sulla popolazione, e non sono la media nazionale. Se ne usi una, dillo
in mezza riga. Una media europea invece è quasi sempre ponderata: non si
confronta con la nostra senza dirlo.

## I gruppi della classifica

Il dossier porta un blocco `gruppi`: la divisione che i valori fanno da soli,
quando la fanno, con quanto la spiegherebbero invece Nord, Centro e
Mezzogiorno.

Serve a rispondere alla domanda che il lettore ha davvero, cioè **se la
geografia c'entra**. Le due risposte valgono uguale:

- i gruppi ricalcano le ripartizioni: il divario territoriale è la storia, e
  adesso hai il numero che lo dice invece di ripeterlo per abitudine.
- i gruppi tagliano di traverso: la storia è un'altra, e questa è la
  notizia. Guarda `bonta_delle_macroaree`: quando è bassa, dire "Nord contro
  Sud" sarebbe pigro e falso insieme.
- `gruppi: null`: la classifica scende in modo continuo, e non ci sono blocchi
  da nominare. Non inventarne.

## L'onestà causale

I dati mostrano che due cose accadono insieme. Non mostrano perché.

- Un evento nello stesso anno di una rottura autorizza **la coincidenza**, non
  la causa: "il salto è del 2020, l'anno delle chiusure", non "il salto è
  causato dalle chiusure".
- Una causa si scrive solo se una fonte verificata la afferma, e allora la fonte
  si nomina nel testo e sta in `fonti`.
- Le parole che promettono più di quanto hai: "a causa di", "grazie a",
  "dimostra che", "spiega". Usale solo con una fonte dietro.

## La scala umana

Almeno una volta l'articolo deve dire che cosa significa il numero per una
persona. Il dossier propone una frase in `meta.scala_umana`: usala come
materiale, non copiarla.

## Che cosa rende freddo un paragrafo

Un paragrafo è freddo quando è corretto e non dà al lettore nessuna ragione
per averlo letto. Il segnale più facile da vedere: un paragrafo lungo senza
nessuna cifra dentro, che gira attorno a un concetto generale.

Ogni paragrafo dovrebbe portare o un fatto nuovo, o una conseguenza di un fatto
già detto. Se non fa né l'uno né l'altro, si taglia.

## I tic da evitare

Sono i segni per cui un testo si legge come generato: la triade ("un fenomeno
complesso, articolato e multiforme"), la definizione bipolare ("non è solo X,
è anche Y"), l'avverbio in -mente a inizio frase, l'apertura che annuncia
invece di dire ("In questo articolo vedremo"), la chiusa che riassume quello che
si è appena letto, il gerundio a catena, il paragrafo che finisce con una
domanda retorica.

Meglio una frase corta e imperfetta di una frase composta e liscia. Puoi aprire
con "Ma", puoi lasciare una sezione più corta delle altre: l'imperfezione è
concessa nella forma, mai nel contenuto.
