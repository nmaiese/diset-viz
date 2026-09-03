# La rubrica: come si misura un articolo indicatore

Dieci criteri, da 0 a 2, massimo 20. Serve a tre cose e a nessun'altra:

- **`motore:lab-scrittore`** ci passa sopra la bozza prima di consegnarla al
  verificatore, dentro il workflow (`.claude/workflows/indicatore-lite.js`),
- **`motore:giudice-cieco`** la usa come metro per dire quale delle due bozze si legge
  fino in fondo, e `lab/lint.py` impone deterministicamente ciò che si
  può contare,
- un **lotto** di articoli si legge prima e dopo un cambio di prompt, e il
  punteggio medio dice se il cambio ha funzionato invece di lasciarlo all'occhio.

I nomi contano: lo **scrittore** e il **revisore** erano due agenti separati e
non esistono più. Scrivere un articolo è passato alla catena di `lab/`, dove sei
tipi stretti (`motore:lab-*`, definiti nel plugin `motore` di platform, non in
questo repo) lo fanno dentro un workflow, e chi cerca il file di un ruolo che
questa pagina nomina deve trovarlo lì.

**Sotto 14/20 l'articolo non è pronto.** Non è una soglia morbida: sotto quel
punteggio la pagina descrive una classifica invece di raccontare un dato, che è
esattamente lo stato da cui questa rubrica esiste per uscire.

Ma il totale non basta, e questa è la seconda regola: **i dieci criteri stanno
su quattro assi, e un asse sotto il suo pavimento boccia l'articolo a prescindere
dal totale.** La media unica nascondeva un asse debole dietro gli altri: un
articolo tutto vero e ben strutturato ma illeggibile faceva 18/20 con il criterio
8 a zero e passava, ed è esattamente la pagina corretta-ma-illeggibile che questa
rubrica esiste per non lasciar passare. I quattro assi e i loro pavimenti sono in
fondo, dopo la tabella dei criteri.

La voce editoriale sta in [`content/STYLE.md`](../content/STYLE.md), che resta
l'unica fonte di verità. Qui non si ripetono le regole, si misura se sono state
seguite.

## I dieci criteri

| # | Criterio | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | **Apertura sul significato** | il lead descrive il grafico o la meccanica ("la distanza si è ridotta di 0,22 punti") | apre su una cifra ma ne dice il senso | apre su una tesi, la cifra arriva dopo, e la prima frase regge da sola come meta description |
| 2 | **Nut graf** | la posta in gioco non c'è o è un accenno di mezza riga | c'è una frase che dice perché conta | un paragrafo suo, che dice chi tocca e quanto, senza importare una causa che l'indicatore non misura |
| 3 | **Filo unico** | quattro sezioni riempite a turno | due sezioni si parlano | una tesi attraversa lead, quadro, dinamica e limiti, e i limiti dicono dove smette di valere |
| 4 | **Ragionamento ad ampio raggio** | l'articolo vive dentro la sua sola serie | un aggancio generico | almeno un aggancio a una grandezza vicina, a un livello storico o a un'altra voce del catalogo, dentro il dato o con fonte |
| 5 | **Incroci e link** | nessun link interno | un link, o un link a un indicatore che è lo stesso fenomeno misurato due volte | da 1 a 3 correlati con un ruolo chiaro, link canonici, anchor che dice dove porta, più l'hub del tema |
| 6 | **Scala umana** | decimali nudi, gli stessi che stampa il cruscotto | qualche rapporto tradotto | i rapporti diventano immagini che restano, e nessuna cifra ripete il cruscotto |
| 7 | **Onestà causale** | una causa che l'indicatore non mostra | verbo prudente ma nessun confondente nominato | verbo calibrato sulla prova, confondente nominato, almeno un'eccezione al pattern |
| 8 | **Leggibilità** | clausole impilate, tre idee in una frase tenute insieme dalle virgole, il paragrafo si rilegge per capirlo, oppure il difetto opposto, frasi brevi slegate accostate come un elenco | si legge al primo passaggio, ma gli incisi tornano frase dopo frase | ogni frase si prende al primo passaggio e nasce dalla precedente, ogni cautela ha la sua frase invece di essere agganciata alla precedente, le clausole stanno nell'ordine in cui si pensano |
| 9 | **Fonti** | un claim comparativo senza fonte, o una fonte inventata | fonte presente e verificata | fonte verificata, usata per contesto e non per il numero che il cruscotto già mostra, senza confondere un aggregato ponderato con la nostra media semplice |
| 10 | **Igiene anti-tell** | più di un tell | un tell | nessun falso intervallo, regola del tre, riassunto compulsivo, lessico spia, domanda retorica in chiusura, numero scritto due volte |

## I quattro assi, e il loro pavimento

I dieci criteri non pesano uguale, e non falliscono nello stesso modo. Stanno su
quattro assi, ognuno con un pavimento: **sotto il pavimento di un asse l'articolo
non è pronto, anche se il totale supera 14.** Un asse misura una cosa diversa
dagli altri, e nessuna media le compensa fra loro.

| asse | criteri | pavimento | come si misura |
|---|---|---|---|
| **1. Correttezza e onestà** | 7 (onestà causale), 9 (fonti) | **2 su ognuno** | il più duro: una causa che il dato non mostra o una fonte inventata boccia da sola. Le eval `writer`/`reviewer` (cifre fuori dal brief, classi d'errore) e il verificatore a valle |
| **2. Leggibilità** | 6 (scala umana), 8 (leggibilità) | **2 sul criterio 8** | la leggibilità è priorità primaria: un lettore comune capisce al primo passaggio, o l'articolo torna indietro. `motore:skeptical-editor` nelle run presidiate, e il confronto cieco di `motore:giudice-cieco` |
| **3. Tesi e struttura** | 1 (apertura), 2 (nut graf), 3 (filo unico), 4 (ragionamento) | **media >= 1,5** | c'è una tesi, un nut graf, un filo che attraversa le sezioni, un respiro oltre la propria serie. Lettura umana |
| **4. Mestiere** | 5 (incroci e link), 10 (igiene anti-tell) | **1 su ognuno** | incroci con un ruolo chiaro, nessun tell da bot. `prose_lint` per la parte contabile, lettura per il resto |

Perché quattro assi e non una somma. Prima esisteva solo il totale, e un articolo
poteva arrivare a 14 con la leggibilità a zero, purché fosse forte altrove: è
la pagina corretta-ma-tecnica, quella che un utente ha giudicato "macchinosa, si
vede che è tradotta in inglese", ed è precisamente il difetto che il totale non
vedeva. Il pavimento per asse lo prende: la leggibilità non si compra con
l'accuratezza, ne la struttura con le fonti.

L'asse 2 aveva un giudice indipendente suo, il **reader-editor**, ritirato con
la catena grande. Dentro il workflow nessuno lo misura: `motore:lab-verificatore`
passa in rassegna cifre, fonti, causali, definizione e coerenza, non la
leggibilità. La leggibilità la giudica `motore:skeptical-editor` nelle run
presidiate dell'Agent Team, e `motore:giudice-cieco` quando si confrontano due
bozze. Gli altri tre assi restano giudizio interno alla catena (il giro di
correzione; l'asse 1 anche del verificatore, a valle).

Un rilievo di leggibilità non punteggia il criterio 8 direttamente, quindi la
corrispondenza va detta invece che dedotta: **un `revise` per leggibilità è il
criterio 8 sotto il pavimento**, e l'articolo torna a chi lo ha scritto per una
riscrittura qualunque sia il totale. Un `pass` non regala il 2: dice che l'asse 2 non blocca.

I pavimenti valgono per un articolo che si dichiara **finito**. Un articolo a
metà è semplicemente da scrivere, non bocciato: la coda che lo dice è
`lab/coda.py`, non questa scala.

## Perché il criterio 8 non premia più il ritmo

Fino al 2026-08-04 il criterio 8 si chiamava **Ritmo e imperfezione** e dava 2 a
"ritmo vero, sezioni di peso diverso, una digressione". Premiava cioè la
varietà del periodare, e chi scriveva la produceva: gli articoli firmati
suonavano scritti, e si leggevano due volte.

Il difetto vero non era il ritmo, era l'**impilamento**. Da `ter-167`, un
articolo che questa rubrica avrebbe dato per buono:

> "In alto due regioni si staccano, la Basilicata e il Piemonte, e fra il
> Piemonte e la terza, la Valle d'Aosta, corrono già due punti e mezzo, il
> salto più largo dell'intera graduatoria."

Tre idee, una frase, cinque virgole. Nessuna regola violata, e il lettore torna
indietro. La varietà di ritmo **resta lecita** e nessuna riga di
`content/STYLE.md` la vieta: ha smesso di essere il punteggio. Si può variare
il ritmo scrivendo frasi che si prendono al primo passaggio, ed è quello che il
criterio ora misura.

Il pavimento del criterio vecchio però resta, ed è scritto nella colonna dello
zero: **spezzare non vuol dire sminuzzare.** Un paragrafo di frasette secche
accostate come voci di elenco è illeggibile quanto una frase con cinque virgole,
ed è il modo tipico in cui si sbaglia questo criterio inseguendo il 2. Le frasi
restano corte quando serve e collegate sempre.

Il metro sta nei testi veri di [`content/esempi/`](../content/esempi/), non in
questa descrizione: chi assegna il punteggio ne legge uno prima, così il 2 è
ancorato a della prosa esistente invece che alla parola "leggibile".

Attenzione a due strumenti che su questo criterio **non aiutano**. La
`burstiness` di `la skill `scrittura-italiana`` misura la varianza della
lunghezza delle frasi, che sotto il criterio nuovo non è né un bene né un
male. E le categorie `mente` e `gerundite` dello stesso contatore possono salire
su un testo più leggibile. Restano indicative, il cancello che vale lì dentro
è il solo campo `vietati`.

## Cosa si misura da solo, e cosa no

Quattro criteri, o metà di essi, li conta uno script. Gli altri vogliono un
lettore, e dirlo è parte della rubrica: un punteggio che finge di essere
automatico dove non lo è è peggio di nessun punteggio.

```bash
python3 scripts/prose_lint.py --show 178     # i tell del criterio 10, su un articolo
python3 scripts/prose_lint.py --summary      # il totale del catalogo, per il prima/dopo
```

`prose_lint` copre il criterio 10 (tranne la regola del tre, che in italiano una
regex non sa distinguere da un elenco normale) e la parte contabile del criterio
5, cioè quanti link interni ci sono. Il resto, dal nut graf al filo, è giudizio.

La suite copre altro ancora, e su quello non serve rileggere a mano: struttura,
punteggiatura vietata, vintage, cifre attribuite a una regione, soglie affermate
su un elenco di regioni, e i link interni (canonici, risolvono, anchor non
generica).

## Il prima e dopo

Il modo di usare la rubrica su un lotto, non su un pezzo:

1. `python3 scripts/prose_lint.py --summary` prima di toccare qualsiasi cosa, e
   si annota il numero.
2. Si riscrive il lotto.
3. Si rilegge il summary. Se il numero non si è mosso, il cambio di prompt non
   ha funzionato **sui tell che quel numero conta**, per quanto le singole pagine
   sembrino migliori.
4. Sui pezzi riscritti si assegnano i dieci criteri a mano, e i due o tre
   criteri più deboli diventano il lavoro del giro successivo.

**Il punto 3 non vale per il criterio 8.** `prose_lint` conta i tell del criterio
10 e i link del 5: non vede l'impilamento, e neanche `tic_count.py` lo vede (i
due estratti Openpolis di `content/esempi/` pesano 21,4 e 18,9 tic per mille
parole, contro i 2,2 di un nostro articolo giudicato illeggibile). Un cambio che
punta alla leggibilità lascia fermo ogni contatore per costruzione. Su quel
criterio il prima e dopo di un lotto è un confronto **cieco a due giudici**, nel
formato di
[`evals/scrittura-italiana/CONFRONTO-PROSA-2026-08-01.md`](../evals/scrittura-italiana/CONFRONTO-PROSA-2026-08-01.md):
versioni presentate come A e B con assegnazione mescolata, nessuna etichetta
prima/dopo, i dieci criteri. È più caro di un comando, ed è l'unica misura che
non mente su questo asse.

Il punto 3 è quello che questa rubrica esiste per rendere possibile. Il numero
di partenza, alla data in cui la rubrica è stata scritta: **340 articoli su 364
chiudevano un paragrafo con una domanda retorica, e 6 su 364 linkavano un altro
indicatore.**
