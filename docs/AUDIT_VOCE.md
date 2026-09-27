# Audit della voce sulle schede indicatore

Quanto la voce di una scheda indicatore si ripete sulle altre 387, e se quella
ripetizione sia un difetto. La misura la fa `scripts/duplicazione.py`; qui c'è
quello che il numero dice davvero, perché la prima lettura era sbagliata due
volte: una per la conclusione, una per un controllo che non era stato eseguito.

## Il numero e la domanda che pone

Il 27 settembre 2026, sulle 388 pagine indicatore che il sito indicizza:

| Perimetro | Parole medie | Quota ripetuta | Sequenze condivise |
| --- | --- | --- | --- |
| racconto | 291 | 28,3% | 880 |
| racconto e metodo | 411 | 46,2% | 1779 |

Letto alla lettera, il 46,2% è un difetto: quasi metà delle parole di metà delle
pagine si ripetono. Prima di allarmarsi bisogna capire **quali** parole.

## Cosa misura lo script

`duplicazione.py` estrae la prosa di ogni scheda, la spezza in sequenze di 8
parole consecutive (`FINESTRA`), e conta una sequenza come condivisa quando
appare in più di 5 pagine (`SOGLIA_PAGINE`). Poi somma le parole cadute in
sequenze condivise.

Il misuratore è onesto, il suo nome no: il docstring dice «quanto testo di una
scheda indicatore si legge identico su altre schede», e non distingue una sequenza
di dati da una di raccordo. Se le parole ripetute sono un valore regionale, il
segnale è vero. Se sono gli anni di riferimento o una spiegazione di metodo, il
segnale è un artefatto.

## La ripetizione dei numeri: quanto pesa, e di che numeri

Ho contato quante sequenze condivise contengono una cifra, e cosa dicono.

| Perimetro | Sequenze condivise | Con una cifra | Esempi |
| --- | --- | --- | --- |
| racconto | 880 | **502 (57,0%)** | «e il 2024, il valore è diminuito in» (98 pagine), «Nell'ultimo passaggio disponibile, tra il 2022 e il 2023» (94) |
| racconto e metodo | 1779 | **632 (35,5%)** | «In parole semplici Un valore di 20 indica» (236), «condizione descritta riguarda 20 unità ogni 100 nel gruppo di riferimento» (162) |

I numeri che si ripetono sono **anni** e **l'esempio illustrativo del metodo**, non
i valori che costituiscono la notizia. «Il valore è diminuito» è la stessa frase
su 98 pagine perché la stessa frase dà l'informazione su 98 pagine: è il telaio.

La domanda che conta è se una pagina riporti il **dato** di un'altra, cioè se una
sequenza condivisa metta una cifra accanto al nome di un territorio. Su 880
sequenze condivise le risposte sono **6**, e tutte e sei sono la stessa frase: «Dal
2018 la distanza fra Trentino Alto Adige e …», su 24 pagine, e «Dal 2018 la
distanza fra Valle d'Aosta e …», su 10. Si ripetono i nomi delle due regioni
estreme, che sono le stesse in molti indicatori, mentre la distanza in punti che
segue sta fuori dalla finestra condivisa ed è diversa da pagina a pagina. Quindi
nessuna pagina riporta il valore di un'altra: il difetto che si cercava non c'è, e
le sei frasi sono un'unica sentenza da rivedere a parte, non un problema di dati.

La prova complementare: ripetendo la quota con ogni numero mascherato — cifre,
decimali e percentuali diventano `<n>` — la percentuale **sale** (28,3% → 33,4% e
46,2% → 49,9%). Questo conferma che a ripetersi è la cornice, ma con un avvertimento:
mascherare è un'operazione che può solo far salire la quota, perché trasforma
sequenze diverse in una sequenza sola. Una quota mascherata non può quindi scendere
sotto quella grezza, e non va mai usata come indicatore di rischio.

## Il blocco «come leggere» non è un boilerplate

Il 46,2% include il blocco che spiega come leggere l'indicatore, e quello sembrava
il posto dove il copia-incolla si nasconde. Non è così: le 388 pagine hanno **261
blocchi distinti**.

- **197** pagine usano l'esempio della percentuale («un valore di 20 indica che la
  condizione descritta riguarda 20 unità ogni 100 nel gruppo di riferimento»),
  **191** ne usano un altro: sono i indicatori la cui unità non è una
  percentuale, e l'esempio cambia di conseguenza.
- Il paragrafo «Il limite principale» è **specifico per indicatore**: per
  `ter-600` dice «non misura tutta la vita culturale informale, gratuita o locale»,
  per `ter-99` «il totale è una buona sintesi, ma può nascondere differenze forti
  tra uomini, donne, giovani e adulti».
- Quello che si ripete è la avvertenza di metodo, che è la stessa per tutte le
  schede e per tutti i territori: «il confronto tra regioni descrive una
  differenza osservata, ma non ne dimostra le cause».

Il blocco è dunque parametrizzato dove deve esserlo e uniforme dove deve esserlo.

## Cosa non è un difetto, e cosa resta una domanda aperta

Non è un difetto: nessun dato ripreso da una pagina all'altra, nessun esempio
sbagliato per l'unità dell'indicatore, nessun testo copiato. Il 46,2% misura
**consistenza**, e per un atlante la consistenza è una scelta, non un difetto: è
ciò che rende due schede confrontabili.

La domanda che resta è di percezione, non di verità: un lettore che apre dieci
schede di fila incontra la stessa frase quattro volte. Non l'hanno risolta tre
modelli free, chiesti separatamente e senza vedere le risposte reciproche. Sono
**giudizi, non misure**, e valgono per la convergenza:

- **`ling-3.0-flash-fin-free` (Zen free)**: metodo, non copia-incolla; rischio solo
  di percezione; suggerisce una frase di contesto in più per pagina.
- **`DeepSeek-V4-Flash` (Hugging Face)**: stesso verdetto, e la formulazione più
  disciplinata: la noia nasce se il resto della pagina non varia, non dal telaio;
  raccomanda di **non riscrivere tutto**, ma di scegliere un indicatore, provare
  una struttura diversa e misurare prima di estendere.

La seconda è la raccomandazione da tenere: «variare la voce» su 388 pagine
costerebbe una riscrittura e un peggioramento della comparabilità, per un
problema che nessuno ha ancora misurato. La prova giusta è una scheda, con una
misura prima e dopo.

## Cosa non è stato fatto

Nessuna frase riscritta, nessun file di `content/` toccato: la voce editoriale si
cambia solo con PR e merge. Il nome e il docstring di `duplicazione.py` dicono
ancora «testo identico», che è la formulazione che ha fatto leggere un difetto
dove c'è una scelta: correggerlo è una riga di codice e un test, quindi aspetta la
PR. Lo script di mascheramento con cui sono prodotte le tabelle qui sopra non è
nel repository, perché `scripts/` è codice. La correzione duratura è già preparata
nel ramo `nmaiese/duplicazione-due-quote`: le due quote, con e senza numeri, più il
conteggio delle sequenze che legano una cifra a un territorio, che è il numero che
serve davvero.

## Come riprodurre la misura

Su `master`, con le dipendenze del progetto:

```
bin/py scripts/duplicazione.py            # le due quote come sono oggi
bin/py scripts/duplicazione.py --frasi 8  # le sequenze più condivise
```

Per le due tabelle mancanti il metodo è questo, e sono poche righe: riusare
`_quota` e `_sequenze` sulle stesse pagine, poi (a) contare le sequenze condivise
che contengono `\d`, e (b) ricalcolare la quota dopo aver sostituito ogni
`\d+(?:[.,]\d+)?\s*%?` con `<n>`.

Il numero che indica un rischio è un altro, e non è una percentuale: quante
sequenze condivise contengono **una cifra e un nome di territorio** insieme, con i
nomi presi da `app.data.REGION_ORDER`. Le sei frasi della distanza fra regioni sono
il riferimento su `master`. Se quel numero cresce, una pagina sta riportando il
dato di un'altra e va guardata a mano; se resta a sei, è cornice.

La quota mascherata non va confrontata con quella grezza per decidere: come
scritto sopra, il confronto non può dare l'esito che sembra.
