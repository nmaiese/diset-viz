# Valutazione del pilota ter-12, 28 settembre 2026

Pilota della fase 3 di `PIANO.md`. Issue #292, PR #293 (draft, base la 2c). La scheda è
`/indicatore/tasso-di-disoccupazione/ter-12`.

## Come è stato fatto

Nello ha chiesto di accelerare con i provider rimasti, senza Claude e senza Codex. Tutti i
ruoli hanno girato in headless, lanciati dal team leader, con `timeout` e `< /dev/null`. Le
quote sono state misurate prima, con un ping per modello (`ripresa/ping_quote.sh`).

| ruolo | modello | esito |
| --- | --- | --- |
| scout | Antigravity gemini-3.1-pro-high, due giri | 8 citazioni letterali su 8, ritrovate nella pagina. Il perché strutturale: "non trovato", detto apertamente |
| giro web parallelo | OpenCode nemotron-3-ultra-free | 1 citazione letterale su 18. Le altre sono parafrasi o frasi composte, più un 403. Utile solo come pista: due frasi vere, prese dalle pagine che ha indicato |
| verifica delle fonti | team leader, `ripresa/verifica_fonti.py` | 15 citazioni in `fonti.md`, tutte ritrovate nel testo della pagina o del PDF |
| brief | team leader | 148 righe di materiale, non una scaletta |
| scrittore | Antigravity gemini-3.1-pro-high | prima stesura in circa 10 minuti, guardia verde, 5 frasi che dicevano una cosa diversa dal dato |
| grafico | OpenCode big-pickle | didascalia corretta e resa verificata con curl. Ha dichiarato due ritagli "con la figura" che non la contenevano |
| resa della figura | team leader, `ripresa/shot_figura.py` (Playwright su Chrome) | figura resa a 375 e 768 px, tema chiaro e scuro, 20 punti, nessuno scroll orizzontale |
| revisore | OpenCode big-pickle, una sessione nuova per giro | tre giri, rilievi giusti e localizzati |
| secondo parere | ollama-cloud gpt-oss:120b | debole: non ha visto nessuno degli errori di senso |
| lettura cieca | gpt-oss:120b, gemma4:31b, nemotron-3-ultra | 3 su 3 scelgono il pezzo nuovo |

Tempi, dagli orari dei commit: dossier, fonti e brief alle 20:08, prima stesura alle 20:19,
riparazione 1 alle 20:30, riparazione 2 alle 20:43, verdetto PRONTA alle 20:55. Lo scout era
partito alle 19:47: poco più di un'ora dalla prima ricerca al verdetto.

## Che cosa hanno trovato i revisori

La guardia è rimasta verde a ogni giro: tutte le cifre tornavano con il dossier e con
`fonti.md`. I difetti veri erano tutti di senso e di lingua, e li ha trovati il revisore, non la
guardia.

- **Review 1.**
  - Cinque frasi dicevano una cosa diversa dal dato: "Nel 2025 scende in tutte le regioni"
    (nel 2025 sei regioni salgono), "le donne cercano lavoro più degli uomini" (è un tasso, e la
    fonte dice che le donne partecipano meno), "meno di una persona su due" riferito anche alla
    Puglia (51,0%), "meno disoccupati in assoluto" per un tasso, e una citazione sulla Campania
    che si leggeva come se parlasse della disoccupazione.
  - Tre errori di italiano.
  - Una causa scritta come fatto misurato (l'emigrazione).
  - Il team leader ha alzato a rilievo la classifica letta ad alta voce.
- **Review 2.**
  - Lo scrittore aveva saltato senza dirlo il rilievo sull'emigrazione.
  - La riparazione aveva introdotto una duplicazione.
  - Il revisore ha trovato una citazione Istat privata del suo termine di confronto ("rispetto
    ai disoccupati").
  - Il team leader ha alzato a rilievo una citazione non più letterale e un "pur chiarendo"
    senza soggetto.
- **Review 3.** PRONTA PER NELLO: tutti i rilievi risolti, nessun rilievo nuovo, solo Note (la più utile: i 394 mila sono "in un anno", e il testo non lo dice).

Una lezione per il flusso: la riparazione 2 ha funzionato solo quando la spec ha elencato le
correzioni una per una, con la frase da cercare e quella da mettere. Con "correggi i rilievi
della review" lo scrittore ne ha saltato uno.

## La lettura cieca

Il vecchio testo (A, 667 parole) e il nuovo (B, 1036) sono stati dati senza frontmatter e senza
marcatori. Tutti e tre i lettori scelgono B, e tutti e tre per la stessa ragione: fonti vere, e
la distinzione fra quello che è documentato e quello che non lo è. Ma tutti e tre dicono che A
fa capire meglio che cosa misura il numero e qual è la notizia, e due su tre preferiscono la
prosa di A, "più asciutta e incisiva". I giudizi integrali sono in `ripresa/cieca/`.

**Che cosa ne ricavo, per Nello.** Il pezzo nuovo è più giusto e più documentato. Il vecchio è
scritto meglio. La causa sta in due punti del flusso, non nel modello:
- il brief dava troppe cifre, e lo scrittore le ha usate quasi tutte;
- nessuno dei controlli misura la lunghezza né il ritmo.

Prima di ter-281 proporrei:
- un brief più corto, con al massimo una cifra per idea;
- un tetto di parole indicativo, fra 600 e 800;
- la domanda 3 del revisore estesa a "si può togliere un terzo del pezzo senza perdere
  un'idea?".

## Il costo

Zero euro di API: Antigravity, OpenCode Zen e ollama-cloud gratuiti. Nessuna quota Claude o
Codex usata dai ruoli. Il team leader (Claude) ha scritto il brief, verificato fonti e figura,
e deciso sui rilievi.
