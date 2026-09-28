# Test completo del pilota, bes-06POL012P, e valutazione di qualità

Round 2 del pilota, con un dossier vero (39 fatti, dal view model reale del sito,
`app.indicator_view.build_indicator_view`, non più dati grezzi estratti a mano) e l'intera
catena della proposta: dossier -> scrittore -> Gate 2 deterministico -> compilatore nel
formato reale dello store -> Gate 5 (linter di prosa del repository). Niente in `content/`:
tutto in `docs/design_drafts/pilot_carceri/`.

## Che cosa è stato eseguito per davvero

1. **Dossier** (`dossier_v2.json`, `bin/py` deterministico, nessun LLM): 39 fatti con id stabili,
   dal view model unificato del sito. A differenza del primo pilota, include la serie storica
   2015-2024, il confronto 2023-2024, gli estremi di lungo periodo.
2. **Scrittore** (Claude, via orchestrazione Orca): ha prodotto `draft_v2.json` nello schema
   esatto della proposta (lead + sezioni + `support` per frase).
3. **Gate 2** (`gate2_verify.py`, script deterministico scritto per questo test, non un LLM):
   confronta ogni cifra del testo con i fatti citati in `support`. Il worker stesso ha trovato
   ed eseguito lo script, ha corretto id inventati e cifre senza supporto esatto, e alla fine
   ha passato. **Verificato di nuovo in modo indipendente dopo**, non solo sulla parola del
   worker: 17 frasi, 0 problemi.
4. **Compilatore** (`compile_and_lint.py`, deterministico): la bozza compilata nel formato
   reale di `scripts/indicator_store.py` (lo stesso che genera i file in `content/indicators/`).
5. **Gate 5** (`bin/py scripts/prose_lint.py`, il linter vero del repository, non uno nuovo):
   0 tell meccanici su 7 categorie, 296 parole.

Tempo reale del passaggio 2 (scrittura + autocorrezione dopo il gate): **218 secondi**,
un solo ciclo di repair, in linea con l'ipotesi della proposta ("una sola chiamata repair,
prevista sul 25% delle bozze").

## Valutazione di qualità, lettura avversaria (dalla checklist della proposta stessa)

**Passa:**
- Mai "media nazionale": sempre "media semplice delle province", coerente col Gate 3.
- Correlazione non diventata causa: "descrive una differenza osservata, non ne dimostra le cause"
  è testuale, non implicito.
- Anno precedente reale (2023), non un anno civile presunto.
- Livello (provincia) mai confuso con regione.
- L'unica fonte citata è vera e verificabile (`istat.it/notizia/bes-dei-territori-edizione-2025`),
  presa dal registro del sito, non generata.
- Il pezzo dice qualcosa di reale: il salto di Fermo (116,3% a 358,1% in un anno) è un fatto
  genuinamente notiziabile, non un riempimento di quattro contenitori.

**Non passa, un difetto reale trovato a mano, che nessun gate automatico intercetta:**
- "Sopra la media si contano 45 province, sotto sono 60, su 107 osservate in tutto." 45+60=105,
  non 107. Non è un errore aritmetico (105 è il numero giusto, è il conteggio 2024 con dato), ma
  un lettore attento fa la somma e si chiede perché non torna: la frase non dice che 2 province
  non hanno un dato quell'anno, cosa che il pezzo spiega solo dopo, nei limiti. Va riscritta
  citando 105, non 107, in quella frase.

**Rilievo strutturale, non del testo ma dell'apparato:**
- **0 link interni.** `docs/INDICATOR_PAGES.md` chiede indicatori correlati nell'apparato; questo
  pilota ha testato solo l'articolo (dossier + scrittore + gate + compilatore), non l'apparato
  intero. Il gate 5 vero del sito include anche l'audit dei link interni su tutte le pagine
  indicizzabili: una scheda con zero link a un altro indicatore abbasserebbe quella misura se
  pubblicata così com'è.

**Osservazione minore:** 296 parole è più corto della media delle schede già scritte (l'esempio
di riferimento, `content/indicators/13.md`, è più denso). Non è un difetto della bozza, è un
dossier con meno dimensioni (nessun genere, nessun confronto europeo) rispetto a un indicatore
come il tasso di occupazione.

## Verdetto

La catena **funziona come descritto nella proposta**: il dossier ricco elimina il problema che il
primo pilota aveva avuto (cifre derivate non presenti nel dossier, sezione dinamica rifiutata per
mancanza di dati), lo scrittore rispetta il contratto, il gate deterministico intercetta davvero
gli errori (id inventati, cifre senza supporto) prima che un umano li veda, e il testo compilato
supera il linter vero del repository. Resta un difetto di chiarezza che nessun gate automatico
prende (105 vs 107) e un buco di apparato (link interni) che questo test non copriva. Nessuno dei
due è un difetto strutturale della proposta: sono esattamente il tipo di cosa che, per disegno,
"resta compito dell'editor" (principio "Automatizzare la prova, non il giudizio").
