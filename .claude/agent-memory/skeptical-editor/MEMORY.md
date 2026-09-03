# Memoria dello skeptical editor

## Contratto

Questa memoria serve a riconoscere difetti editoriali ricorrenti senza
trasformare una vecchia decisione in un verdetto automatico.

Conservare soltanto:

- errori osservati in più run
- criteri stabili per distinguere gravità alta, media e bassa
- falsi positivi già verificati
- correzioni minime che hanno risolto un'intera classe di problemi
- limiti metodologici ricorrenti nelle famiglie di indicatori

Non conservare gusti stilistici, rilievi isolati, testo di singole bozze,
giudizi su persone e agenti, segreti, token o dati personali.

## Pattern editoriali

```yaml
- categoria: classe di errore che il controllo deterministico non vede
  apprendimento: >-
    Le affermazioni di conteggio ("le uniche tre regioni sotto i sei punti",
    "solo due superano", "nessuna regione sotto") passano il controllo
    automatico anche quando sono false, perché il controllo verifica che ogni
    cifra citata esista e sia attribuita al territorio giusto, e in queste
    frasi le cifre sono tutte vere: falso è il quantificatore, che non è una
    cifra. Vanno ricontate a mano dal blocco `ultimo` a ogni revisione.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA, 2026-09-03: "le uniche tre regioni sotto
    i sei punti" con quattro regioni sotto sei nel dossier, e il valore che
    smentisce la frase era citato dall'articolo stesso in un'altra sezione.
    Controllo deterministico passato pulito.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: revisione di qualunque articolo indicatore
  limiti: se il controllo imparasse a leggere i quantificatori, la voce va rivista.

- categoria: criterio di gravità, angolo costruito sull'ultimo anno
  apprendimento: >-
    Un angolo che descrive la classifica dell'ultimo anno va riapplicato agli
    altri anni della matrice prima di accettarlo. Se regge in meno della metà
    degli anni osservabili non è una struttura dell'indicatore, ed è un rilievo
    alta finché la frase resta al presente generico: diventa bassa appena ogni
    occorrenza porta l'anno e viene nominato un anno in cui non vale. Lo stesso
    controllo, letto al contrario, fa emergere il fatto stabile che l'angolo
    stava ignorando.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA: "massimo e minimo entrambi nel
    Mezzogiorno" vale in due anni su cinque osservabili. Lo stesso controllo ha
    fatto emergere il fatto poi diventato l'angolo pubblicato, la salita del
    2025 in quattordici regioni su diciassette.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: conferenza d'angolo di qualunque indicatore con matrice pluriennale
  limiti: serve una matrice con abbastanza anni a panel confrontabile.

- categoria: limite metodologico ricorrente, medie di macroarea
  apprendimento: >-
    Le medie per macroarea sono medie semplici delle sole regioni presenti in
    quell'anno, e il numero di regioni per area è molto diverso. Il Centro sono
    al massimo quattro regioni, quindi una sola ne decide la posizione rispetto
    a Nord e Mezzogiorno. Prima di lasciar scrivere quale area sta peggio,
    ricontare i territori per area e togliere la regione più estrema: se
    l'ordine non tiene, l'ordine delle aree non è un fatto. Lo stesso concetto
    si dice senza medie e senza statistica: dentro ogni area c'è quasi tutta la
    distanza fra la prima regione e l'ultima.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA 2025: Centro su 4 regioni, Nord su 6 di 8,
    Mezzogiorno su 7 di 8. Senza il Lazio il Centro scende sotto il Nord.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: qualunque dossier con il blocco macroaree, soprattutto famiglie a copertura regionale incompleta
  limiti: su famiglie con venti regioni piene la fragilità è minore.

- categoria: difetto ricorrente del dossier, media chiamata nazionale
  apprendimento: >-
    `dinamica.nazionale.ultimo` coincide con `sintesi.media`: il dossier
    etichetta come nazionale la media semplice delle regioni disponibili, e chi
    scrive la prende per un dato Istat nazionale. Verificare l'uguaglianza dei
    due campi e vietare "in Italia" davanti a quella cifra fa parte del
    controllo di base. E la cautela va ripetuta in ogni sezione che usa quella
    media: dichiararla una volta non basta, perché il lettore che salta a una
    sezione più avanti non l'ha letta.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA: i due campi valgono entrambi 9,19. Nella
    bozza la cautela c'era nella sezione dinamica e mancava nella sezione dei
    parenti, dove la stessa media tornava a fare la parte del dato italiano.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: tutti i dossier con il blocco dinamica.nazionale
  limiti: non verificato su ogni famiglia, va ricontrollato dossier per dossier.

- categoria: metodo, chiudere una definizione quando il dossier ce l'ha nulla
  apprendimento: >-
    Quando il dossier ha la definizione nulla, il registro dei metadati SDMX
    (dataflow con references=all) è la prima cosa da chiedere: dà nome della
    codelist, voci sorelle e unità di misura dichiarata. Le dimensioni di
    scomposizione del DSD sono un indizio sull'unità contata, non una prova:
    anche una serie che conta persone può scomporsi per numero di componenti o
    reddito della famiglia. Il denominatore si afferma solo se il registro o un
    documento Istat lo dichiara (docs/INDICATOR_PAGES.md: non dedurre numeratore
    o denominatore che la fonte non dà); altrimenti il testo dice "famiglie" o
    "persone" solo se l'etichetta della serie lo dice, e il limite si dichiara.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA, dataflow 33_291_DF_DCCV_PROBLZONRES_2_6:
    l'etichetta della serie dice famiglie; il DSD da solo non sarebbe bastato.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: qualunque serie Istat SDMX con definizione nulla nel dossier
  limiti: >-
    provato una volta, su una serie familiare. Su una serie individuale la
    lettura simmetrica va verificata prima di fidarsi.

- categoria: punto cieco del blocco fonti
  apprendimento: >-
    Una cifra tolta dal corpo per una decisione editoriale sopravvive dentro il
    testo di una voce di `fonti`, che la pagina rende comunque al lettore.
    Quando si decide di non accostare due misure, la decisione va applicata
    anche alle fonti: una voce che non sostiene nessuna affermazione del corpo
    va tolta o ridotta al nome della pagina, altrimenti riporta davanti al
    lettore proprio i numeri che si erano rimossi.
  evidenza: >-
    multiscopo:MULTI_ZONA_CRIMINALITA: l'accostamento con una seconda misura
    Istat era stato tolto dal corpo, e la voce di fonti conservava tutte le
    percentuali, di un anno diverso da quello dell'articolo.
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: qualunque articolo in cui una fonte esterna viene ridimensionata in revisione
  limiti: non è un divieto di citare fonti di contesto, vale quando la voce porta cifre che il corpo ha deciso di non usare.
```

Ogni pattern va verificato contro la bozza corrente. La memoria può aprire una
domanda, non chiuderla.
