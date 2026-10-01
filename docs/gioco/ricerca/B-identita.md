# Identità visiva e interazione per la sezione gioco (2025-2026)

Questo documento analizza le pratiche dello stato dell'arte per le sezioni di gioco web dentro marchi editoriali e definisce la proposta di identità visiva per la sezione gioco di Divario Italia.

## 1. Sub-brand giochi dentro testate editoriali

Le principali testate internazionali (New York Times, LinkedIn, The Guardian) hanno sviluppato sottomarchi dedicati al gioco per trasformare la lettura occasionale in un'abitudine quotidiana.

- **NYT Games** (https://www.nytimes.com/crosswords): Il marchio madre è presente nel carattere Gotico del logo e nella rigore tipografico. La sezione gioco acquisisce identità propria attraverso icone geometriche per ciascun titolo (Wordle, Connections, Spelling Bee, Pips), una tavolozza di colori distintiva per ogni gioco e una voce guida basata sul rilassamento cognitivo.
- **LinkedIn Games** (https://www.linkedin.com/games/): Lanciati nel maggio 2024 (titoli come Pinpoint, Queens, Crossclimb, Tango), i giochi utilizzano un linguaggio visivo pulito che rispetta l'ambiente professionale. Le schede hanno angoli ammorbiditi, una tipografia coordinata con i post della rete e contatori di striscia (streak) per stimolare il confronto tra colleghi.
- **The Guardian Games** (https://www.theguardian.com/crosswords): Mantiene il font di testata Guardian Headlines per i titoli dei cruciverba e dei puzzle, integrando una griglia minimalista e colori neutri con accenti sul tasto di invio o verifica.

Il bilanciamento tra brand madre e sub-brand si articola su sei dimensioni:
1. **Tipografia**: Il font primario del sito principale rimane per i titoli, mentre cifre e contatori usano varianti tabellari o semi-condensate.
2. **Colore**: Il sito madre usa colori neutri ed editoriali. Il sub-brand di gioco introduce tonalità d'accento dedicate per l'interfaccia interattiva senza alterare i colori dei dati.
3. **Forma**: Le schede di gioco adottano strutture modulari e contorni netti per differenziarsi dai blocchi di prosa.
4. **Icone**: Ogni gioco ha un monogramma o simbolo vettoriale proprietario identificabile nelle miniature e nella condivisione.
5. **Mascotte e simboli**: Piccoli elementi grafici guidano i momenti di successo o aiuto senza infantilizzare il tono.
6. **Tono di voce**: Frasi brevi, incoraggianti e trasparenti sulla difficoltà della sfida.

## 2. Micro-interazioni e movimento

Il movimento nei giochi web brevi deve comunicare lo stato dell'azione in modo immediato e leggero.

- **View Transitions API** (https://developer.mozilla.org/en-US/docs/Web/API/View_Transitions_API): Raggiunta la compatibilità Baseline standard nel 2025-2026 su Chrome, Firefox e Safari. Consente transizioni fluide tra stati di gioco o schermate di riepilogo senza librerie esterne pesanti.
- **Animazioni a molla (Spring Physics)**: Utilizzo di funzioni `cubic-bezier(0.175, 0.885, 0.32, 1.275)` per dare un effetto elastico alle tessere quando vengono posizionate o scosse in caso di errore.
- **Feedback di vittoria e sconfitta**: Rivelazione progressiva degli indizi tramite dissolvenza e scorrimento verticale. In caso di vittoria, un breve impulso visivo sull'elemento corretto attira l'attenzione.
- **Suono e vibrazione**: La Vibration API (`navigator.vibrate()`, https://developer.mozilla.org/en-US/docs/Web/API/Navigator/vibrate) offre un riscontro tattile immediato sui dispositivi Android. Nota tecnica: Safari su iOS non supporta la Vibration API per il web, quindi ogni riscontro tattile deve avere un equivalente visivo chiaro.
- **Gestione di `prefers-reduced-motion`** (https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion): Quando l'utente richiede una mobilità ridotta, tutte le animazioni di scuotimento, impulso e scorrimento vengono disattivate istantaneamente, sostituite da cambi di stato immediati.

## 3. Mobile a un pollice (Thumb Zone UI)

L'esperienza mobile dei giochi brevi si fonda sull'ergonomia ad una mano.

- **Posizione dei controlli**: I tasti di conferma, salto indizio o invio risiedono nella fascia inferiore dello schermo (bottom zone), facilmente raggiungibile dal pollice.
- **Tastiere virtuali**: Evitare l'apertura involontaria della tastiera di sistema quando si usano controlli personalizzati. Negli input di testo per nomi di regioni o province, la lista di completamento deve rimanere ancorata sopra la tastiera senza coprire l'indizio corrente.
- **Drag and Drop accessibile**: Il trascinamento delle tessere su mobile deve permettere sia il movimento continuo sia la modalità a due tocchi (seleziona prima la tessera, poi la posizione di destinazione).
- **Dimensioni dei bersagli**: Tutti i bottoni di gioco rispettano la dimensione minima di 44x44 pixel per evitare tocchi errati.

## 4. Accessibilità nei giochi web (WCAG 2.2)

I giochi interattivi rispettano i criteri di accessibilità della W3C Recommendation WCAG 2.2:

- **WCAG 2.2 Criterio 2.5.7 Dragging Movements (Level AA)** (https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html): Ogni funzionalità che richiede il trascinamento (come il gioco Ordina le regioni) mette a disposizione un'alternativa a tocco singolo con frecce o pulsanti Sposta su / Sposta giù.
- **WCAG 2.2 Criterio 2.5.8 Target Size (Minimum) (Level AA)** (https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html): Ogni elemento cliccabile garantisce un'area target di almeno 24x24 pixel con spaziatura adeguata, adottando il target consigliato di 44x44 pixel per le azioni principali di gioco.
- **WCAG 2.2 Criterio 2.2.1 Timing Adjustable (Level A)** (https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html): Per la modalità a tempo di Chi è maggiore (timer 10 s), viene offerta una modalità allenamento o la possibilità di disattivare/estendere il timer per utenti che necessitano di più tempo.
- **Feedback non solo cromatico**: Gli stati di risposta esatta o errata combinano il colore con icone dedicate (spunta, croce, frecce) e variazioni di forma dei contenitori.
- **Lettori di schermo su mappe e grafici**: Le mappe SVG interattive includono etichette `aria-label` aggiornate dinamicamente e tabelle dati nascoste o alternative accessibili da tastiera.

## 5. Condivisione e viralità organica

La diffusione dei giochi brevi si basa sul confronto dei risultati senza svelare la soluzione del giorno.

- **Immagine OG dinamica**: Generazione lato server delle schede Open Graph per le partite completate, mostrando il punteggio e la sequenza di tentativi.
- **Griglia di testo condivisa**: Formattazione del risultato tramite emojicube o caratteri testuali (es. blocchi quadrati pieni e vuoti) pronti per la copia negli appunti e l'invio su app di messaggistica.
- **Link diretto con parametro sfidante**: URL di condivisione che consente a un amico di giocare la medesima combinazione di dati o la sfida del giorno.

## 6. Proposta d'identità per Divario Italia: "Laboratorio Cronaca"

Sulla base dei sistemi registrati in `frontend/src/game/game.css`, `app/static/css/ds/system.css` e `design/v1/SISTEMA.md`, si propone la direzione visiva **Laboratorio Cronaca**.

La direzione mantiene l'impostazione giornalistica ed essenziale della 1.0 "Cronaca" (sfondo bianco, inchiostro #121519, font Sofia Sans), introducendo elementi distintivi per l'esperienza di gioco.

### Tonalità aggiuntive per l'interfaccia di gioco
I dati statistici continuano a utilizzare la rampa sequenziale blu senza giudizi cromatici. L'arancio bruciato (#a75001) resta l'accento di navigazione dell'intero sito. Per distinguere l'area interattiva di gioco vengono introdotti token dedicati all'interfaccia ludica:

1. `--game-accent`: Viola indaco per l'azione principale di gioco e i badge di stato interattivo.
   - Tema chiaro: `#5b3cc4`
   - Tema scuro: `#9d7dff`
2. `--game-accent-wash`: Sfondo tenue per i pannelli e i suggerimenti di gioco.
   - Tema chiaro: `#f1edfd`
   - Tema scuro: `#251c42`
3. `--text-on-game-accent`: Testo sopra i pulsanti con sfondo `--game-accent`.
   - Tema chiaro: `#ffffff`
   - Tema scuro: `#121417`

### Verifica del contrasto WCAG AA
Tutte le coppie testo e sfondo proposte rispettano i requisiti WCAG AA (minimo 4,5:1 per testo normale, 3:1 per componenti di interfaccia):

- **Tema chiaro**:
  - `--game-accent` (`#5b3cc4`) su sfondo pagina (`#ffffff`): contrasto **7.25:1** (Supera WCAG AA).
  - Testo inchiostro (`#121519`) su sfondo `--game-accent-wash` (`#f1edfd`): contrasto **16.0:1** (Supera WCAG AAA).
  - `--text-on-game-accent` (`#ffffff`) su `--game-accent` (`#5b3cc4`): contrasto **7.25:1** (Supera WCAG AA).

- **Tema scuro**:
  - `--game-accent` scuro (`#9d7dff`) su sfondo scuro (`#121417`): contrasto **6.00:1** (Supera WCAG AA).
  - Testo inchiostro scuro (`#eceef1`) su sfondo `--game-accent-wash` scuro (`#251c42`): contrasto **12.8:1** (Supera WCAG AAA).
  - `--text-on-game-accent` scuro (`#121417`) su `--game-accent` scuro (`#9d7dff`): contrasto **6.00:1** (Supera WCAG AA).

### Tipografia e Forme
- **Tipografia**: La voce principale resta Sofia Sans per le spiegazioni e i nomi dei territori. Sofia Sans Semi Condensed viene impiegata per i contatori a tempo, le serie di vittorie e le posizioni, impostando `font-variant-numeric: tabular-nums` per evitare oscillazioni del layout durante il conto alla rovescia.
- **Forme**: Mantenimento dei bordi netti della 1.0 Cronaca (`border-radius: 0`) per le tessere geografiche e le card indizio, con raccordi minimi a 4px (`--radius-control`) per i campi di input e le icone di comando.

### Icone distintive dei tre giochi
Ogni gioco adotta un monogramma vettoriale dedicato inserito in un riquadro da 34x34 pixel:

1. **Indovina la Regione** (`icon-game-guess`): Silhouette stilizzata dell'Italia con un punto interrogativo centrale in inchiostro.
2. **Chi è maggiore?** (`icon-game-compare`): Due barre verticali a confronto con un simbolo di confronto dinamico al centro.
3. **Ordina le regioni** (`icon-game-order`): Tre linee orizzontali di lunghezza graduata affiancate da frecce di scorrimento su e giù.

### Movimento e micro-interazioni
Transizioni guidate da `document.startViewTransition()` dove supportato. Al reveal dell'indizio, la card compare con uno scivolamento di 6px e dissolvenza in 180ms. Durante il conteggio alla rovescia di Chi è maggiore, la barra del timer fluisce con transizione lineare continua.

---

## Raccomandazioni per Divario Italia

In ordine di priorità operativa per il miglioramento della sezione `/quiz`:

1. **Introdurre i token visivi e le icone di gioco (P0 - Costo: S - Rischio: Basso)**
   - Integrare i token `--game-accent` e `--game-accent-wash` in `frontend/src/game/game.css` e assegnare le tre icone vettoriali alle intestazioni dei rispettivi giochi.
2. **Adeguamento accessibilità WCAG 2.2 sui controlli tattili e trascinamento (P0 - Costo: M - Rischio: Basso)**
   - Assicurare bersagli minimi di 44 pixel per i pulsanti di suggerimento e garantire l'alternativa a tocco singolo per il drag in Ordina le regioni (Criterio 2.5.7).
3. **Opzione di regolazione tempo per sfide cronometrate (P1 - Costo: S - Rischio: Basso)**
   - Aggiungere una modalità senza timer o estesa per Chi è maggiore per conformità al Criterio 2.2.1.
4. **Attuazione transizioni di stato con View Transitions API (P1 - Costo: M - Rischio: Basso)**
   - Implementare `startViewTransition` nel ciclo di rendering React dell'isola di gioco per il passaggio tra turni e schermata finale.
5. **Generazione ed esportazione della Share Card visiva (P2 - Costo: M - Rischio: Basso)**
   - Arricchire il modulo di condivisione con la generazione di un'immagine di riepilogo o griglia testuale formattata per i social media.
