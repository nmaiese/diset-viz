# La rubrica: come si misura un articolo indicatore

Dieci criteri, da 0 a 2, massimo 20. Serve a tre cose e a nessun'altra:

- lo **scrittore** ci passa sopra la bozza prima di aprire la PR,
- il **revisore** la usa come lista di cosa deve saper correggere in loco,
- un **lotto** di articoli si legge prima e dopo un cambio di prompt, e il
  punteggio medio dice se il cambio ha funzionato invece di lasciarlo all'occhio.

**Sotto 14/20 l'articolo non e' pronto.** Non e' una soglia morbida: sotto quel
punteggio la pagina descrive una classifica invece di raccontare un dato, che e'
esattamente lo stato da cui questa rubrica esiste per uscire.

La voce editoriale sta in [`content/STYLE.md`](../content/STYLE.md), che resta
l'unica fonte di verita'. Qui non si ripetono le regole, si misura se sono state
seguite.

## I dieci criteri

| # | Criterio | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | **Apertura sul significato** | il lead descrive il grafico o la meccanica ("la distanza si e' ridotta di 0,22 punti") | apre su una cifra ma ne dice il senso | apre su una tesi, la cifra arriva dopo, e la prima frase regge da sola come meta description |
| 2 | **Nut graf** | la posta in gioco non c'e' o e' un accenno di mezza riga | c'e' una frase che dice perche' conta | un paragrafo suo, che dice chi tocca e quanto, senza importare una causa che l'indicatore non misura |
| 3 | **Filo unico** | quattro sezioni riempite a turno | due sezioni si parlano | una tesi attraversa lead, quadro, dinamica e limiti, e i limiti dicono dove smette di valere |
| 4 | **Ragionamento ad ampio raggio** | l'articolo vive dentro la sua sola serie | un aggancio generico | almeno un aggancio a una grandezza vicina, a un livello storico o a un'altra voce del catalogo, dentro il dato o con fonte |
| 5 | **Incroci e link** | nessun link interno | un link, o un link a un indicatore che e' lo stesso fenomeno misurato due volte | da 1 a 3 correlati con un ruolo chiaro, link canonici, anchor che dice dove porta, piu' l'hub del tema |
| 6 | **Scala umana** | decimali nudi, gli stessi che stampa il cruscotto | qualche rapporto tradotto | i rapporti diventano immagini che restano, e nessuna cifra ripete il cruscotto |
| 7 | **Onesta' causale** | una causa che l'indicatore non mostra | verbo prudente ma nessun confondente nominato | verbo calibrato sulla prova, confondente nominato, almeno un'eccezione al pattern |
| 8 | **Leggibilita'** | clausole impilate, tre idee in una frase tenute insieme dalle virgole, il paragrafo si rilegge per capirlo, oppure il difetto opposto, frasi brevi slegate accostate come un elenco | si legge al primo passaggio, ma gli incisi tornano frase dopo frase | ogni frase si prende al primo passaggio e nasce dalla precedente, ogni cautela ha la sua frase invece di essere agganciata alla precedente, le clausole stanno nell'ordine in cui si pensano |
| 9 | **Fonti** | un claim comparativo senza fonte, o una fonte inventata | fonte presente e verificata | fonte verificata, usata per contesto e non per il numero che il cruscotto gia' mostra, senza confondere un aggregato ponderato con la nostra media semplice |
| 10 | **Igiene anti-tell** | piu' di un tell | un tell | nessun falso intervallo, regola del tre, riassunto compulsivo, lessico spia, domanda retorica in chiusura, numero scritto due volte |

## Perche' il criterio 8 non premia piu' il ritmo

Fino al 2026-08-04 il criterio 8 si chiamava **Ritmo e imperfezione** e dava 2 a
"ritmo vero, sezioni di peso diverso, una digressione". Premiava cioe' la
varieta' del periodare, e il produttore la produceva: gli articoli firmati
suonavano scritti, e si leggevano due volte.

Il difetto vero non era il ritmo, era l'**impilamento**. Da `ter-167`, un
articolo che questa rubrica avrebbe dato per buono:

> "In alto due regioni si staccano, la Basilicata e il Piemonte, e fra il
> Piemonte e la terza, la Valle d'Aosta, corrono gia' due punti e mezzo, il
> salto piu' largo dell'intera graduatoria."

Tre idee, una frase, cinque virgole. Nessuna regola violata, e il lettore torna
indietro. La varieta' di ritmo **resta lecita** e nessuna riga di
`content/STYLE.md` la vieta: ha smesso di essere il punteggio. Si puo' variare
il ritmo scrivendo frasi che si prendono al primo passaggio, ed e' quello che il
criterio ora misura.

Il pavimento del criterio vecchio pero' resta, ed e' scritto nella colonna dello
zero: **spezzare non vuol dire sminuzzare.** Un paragrafo di frasette secche
accostate come voci di elenco e' illeggibile quanto una frase con cinque virgole,
ed e' il modo tipico in cui si sbaglia questo criterio inseguendo il 2. Le frasi
restano corte quando serve e collegate sempre.

Il metro sta nei testi veri di [`content/esempi/`](../content/esempi/), non in
questa descrizione: chi assegna il punteggio ne legge uno prima, cosi' il 2 e'
ancorato a della prosa esistente invece che alla parola "leggibile".

Attenzione a due strumenti che su questo criterio **non aiutano**. La
`burstiness` di `evals/scrittura-italiana/tic_count.py` misura la varianza della
lunghezza delle frasi, che sotto il criterio nuovo non e' ne' un bene ne' un
male. E le categorie `mente` e `gerundite` dello stesso contatore possono salire
su un testo piu' leggibile. Restano indicative, il cancello che vale li' dentro
e' il solo campo `vietati`.

## Cosa si misura da solo, e cosa no

Quattro criteri, o meta' di essi, li conta uno script. Gli altri vogliono un
lettore, e dirlo e' parte della rubrica: un punteggio che finge di essere
automatico dove non lo e' e' peggio di nessun punteggio.

```bash
python3 scripts/prose_lint.py --show 178     # i tell del criterio 10, su un articolo
python3 scripts/prose_lint.py --summary      # il totale del catalogo, per il prima/dopo
```

`prose_lint` copre il criterio 10 (tranne la regola del tre, che in italiano una
regex non sa distinguere da un elenco normale) e la parte contabile del criterio
5, cioe' quanti link interni ci sono. Il resto, dal nut graf al filo, e' giudizio.

La suite copre altro ancora, e su quello non serve rileggere a mano: struttura,
punteggiatura vietata, vintage, cifre attribuite a una regione, soglie affermate
su un elenco di regioni, e i link interni (canonici, risolvono, anchor non
generica).

## Il prima e dopo

Il modo di usare la rubrica su un lotto, non su un pezzo:

1. `python3 scripts/prose_lint.py --summary` prima di toccare qualsiasi cosa, e
   si annota il numero.
2. Si riscrive il lotto.
3. Si rilegge il summary. Se il numero non si e' mosso, il cambio di prompt non
   ha funzionato **sui tell che quel numero conta**, per quanto le singole pagine
   sembrino migliori.
4. Sui pezzi riscritti si assegnano i dieci criteri a mano, e i due o tre
   criteri piu' deboli diventano il lavoro del giro successivo.

**Il punto 3 non vale per il criterio 8.** `prose_lint` conta i tell del criterio
10 e i link del 5: non vede l'impilamento, e neanche `tic_count.py` lo vede (i
due estratti Openpolis di `content/esempi/` pesano 21,4 e 18,9 tic per mille
parole, contro i 2,2 di un nostro articolo giudicato illeggibile). Un cambio che
punta alla leggibilita' lascia fermo ogni contatore per costruzione. Su quel
criterio il prima e dopo di un lotto e' un confronto **cieco a due giudici**, nel
formato di
[`evals/scrittura-italiana/CONFRONTO-PROSA-2026-08-01.md`](../evals/scrittura-italiana/CONFRONTO-PROSA-2026-08-01.md):
versioni presentate come A e B con assegnazione mescolata, nessuna etichetta
prima/dopo, i dieci criteri. E' piu' caro di un comando, ed e' l'unica misura che
non mente su questo asse.

Il punto 3 e' quello che questa rubrica esiste per rendere possibile. Il numero
di partenza, alla data in cui la rubrica e' stata scritta: **340 articoli su 364
chiudevano un paragrafo con una domanda retorica, e 6 su 364 linkavano un altro
indicatore.**
