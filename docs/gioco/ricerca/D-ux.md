# D-UX: revisione UX e contenuto dei giochi attuali

Nessuna affermazione di questo rapporto fa leva su fonti esterne: è tutto
verificato nel codice del repository, con riferimenti file:riga. Nessuna
affermazione "da verificare" dunque. Se serve un confronto con prassi
esterne (gamification, quiz a raffica, accessibilità), va detto: qui non ci
sono, quindi le fonti 2025-2026 richieste dal contesto comune non sono citate.

## 1. Percorso del giocatore nuovo (dall'arrivo su /quiz alla fine della prima partita di ogni gioco)

### Hub /quiz (app/templates/game_hub.html, frontend/src/game/hub.jsx)

- Arrivo: template mostra doppia breadcrumb (riga 18: `{{ breadcrumb.trail(percorso) }}`, riga 19: `<nav class="breadcrumb"><a href="/">Divario Italia</a></nav>`) — confonde il percorso. file:app/templates/game_hub.html:18,19
- Testo introduttivo lungo (27-28, 31-33): due blocchi esplicativi prima delle card, aumento frizione per primo accesso.
- Card server-rendered (37-57): tre giochi, CTA "Gioca ora →" ripetuto; hub.jsx aggiunge tracking (click sugli <a class="hub-card">, riga 84-94) ma nessun "già giocato oggi" né "serie", né "gioco del giorno in evidenza". file:frontend/src/game/hub.jsx:84-94
- React sidecar (#hub-root) carica statistiche locali (73-80, StatsPanel 109-140) e Top5 settimanale (96-104, 142-176), achievements (7-59, 190). Stati: "Caricamento delle statistiche..." (60) e stato vuoto "Gioca una prima partita..." (126-129). file:app/templates/game_hub.html:60; frontend/src/game/hub.jsx:126-129
- Auth opzionale visibile (AuthControl renderizzato, hub.jsx:185) — può distrarre, ma non bloccante.

### 1.1 Indovina la Regione (/quiz/indovina-la-regione)

Template (app/templates/game.html): doppia breadcrumb (30-31), lead descrittivo (37), mappa SVG inclusa (42), noscript + loading "Preparazione della sfida..." (51-56), sezione "Come si gioca" (59-63). file:game.html:30-31,51-56,59-63

Frontend (frontend/src/game/main.jsx):
- Stato iniziale: loading (407-422) con skeleton, tabbar (364-403), onboarding automatico se mai mostrato? STORAGE_ONBOARDED_KEY letto in useState (119-125) → mostra modal OnboardingModal (612-636) su primo accesso (store "1" onClose 616-623). file:main.jsx:119-125,612-636
- Modal "Come si gioca" (726-747): testo (730-745). Frizione ridotta (mostrato solo una volta), ma copy verboso.
- Avvio: daily default (mode "daily"). fetch regions + daily (148-156, 200-235). Se progress salvato (localStorage per puzzle_id) ripristina stato/guesses/clues (208-223); altrimenti clue 0 (220), status playing (222). file:main.jsx:200-235
- Input: combobox con suggerimenti (503-556), suggerimenti filtrano già provate (142-147), highlight con frecce, invio seleziona (517-536). Suggest 6 max (145). file:main.jsx:142-147,503-556
- Tentativi: barra segmenti (438-445), guess feedback (558-590) mostra confronto ↑/↓/= e rank misteriosa/guess (566-577). Ripartizione hint dal 3° errore (581-587). file:main.jsx:438-445,558-590
- Fine partita (593-607 ResultPanel): mostra soluzione regione con link a scheda `/regione/{region_key}` (670, 683-686). Tabella recap con indicatori e link per ogni riga a path indicatore (700-709) — usa `row.path` (profiles.indicator_path). Non mostra link canonico `/indicatore/<slug>/<acronimo>-<id>` specificato nella spec. file:main.jsx:670,683-686,700-709; backend app/game.py:216-230
- Attributi: fine partita won/lost (finished), recap costruito (344 in evaluate_guess) con path indicator via profiles.indicator_path. file:app/game.py:216-230,344

Attriti osservati (nuovo giocatore):
1. Due breadcrumb (server+hardcoded) su tutte pagine gioco (hub/game/compare/order/leaderboard). file:game*.html, leaderboard
2. Onboarding dettagliato ma letto dopo caricamento; utente può cliccare ? (395-403) per riaprirlo. file:main.jsx:395-403
3. Suggerimenti mostrano solo 6 regioni, nessun hint testuale se vuoto query. file:main.jsx:142-147
4. Dopo errore, focus resta su input (513), shake (505) — feedback ok. file:main.jsx:505,513
5. Fine partita: no link esplicito alla "scheda indicatore canonica `/indicatore/<slug>/<acronimo>-<id>`" (spec 3); mostra solo link a scheda regione e link a path indicatore generico (profiles.indicator_path). Manca anche link diretto alla regione? ResultPanel linka soluzione a `solution.path` = `/regione/{region_key}` (game.py:340-344). Vedi punto 3.

### 1.2 Chi è maggiore? (/quiz/chi-e-maggiore)

Template (game_compare.html): breadcrumb manuale (38), doppio in senso di nav; JSON-LD Game corretto ma "creator": Istat (19) — spec 6 chiede verifica. file:game_compare.html:19,38

Frontend (compare.jsx):
- Idle/start (222-243): onboarding inline (224-240) vs modal in daily. file:compare.jsx:222-243
- Round: barra stato (257-271) con Round/Serie/Punti/Livello, timer 10s (42, formatClock 42-45), barra width (263-270). file:compare.jsx:42-45,257-271
- Tastiera ←A, B→ (105-120) leggendo stateRef — buono. file:compare.jsx:105-120
- Revealed (324-338): verdict, mostra vincitore. link a scheda? Nessun link alla regione/indicatore canonico a fine round (solo passa avanti). Streak cresce (168), sessionBest (180-188) può aprire SubmitScoreModal (373-382). file:compare.jsx:324-382
- Attributi: dopo reveal, nextRound (199) carica nuovo round con difficultyForStreak (34). file:compare.jsx:34,199

Attriti: nessun "what you learned" a fine partita/serie (modal classifica si apre solo se best>=3 e non perfect? riga 184-188: apre se !correct && best>promptedBestRef e best>=3). Nessun recap dati/indicatori linkati canonici.

### 1.3 Ordina le regioni (/quiz/ordina)

Template (game_order.html): breadcrumb doppio (30-31), JSON-LD (21) creator Istat. file:game_order.html:21,30-31

Frontend (order.jsx):
- Start (209-231), count selector 3/5 (183-196). file:order.jsx:183-196,209-231
- Ordering: drag/drop (110-131 handle ⋮⋮ 326) + frecce ↑↓ (308-325), shuffle (97-107), verifica (336-346). file:order.jsx:97-107,110-131,308-346
- Revealed (349-376): verdict (351-357), soluzione classifica reale con valori (361-371), link indicatori? Nessuno. file:order.jsx:349-376
- SubmitScoreModal apre solo su condizioni (161-166) — non immediato a fine round.

Attriti: fine round solo punteggio, nessun learning path.

## 2. Coerenza testi con content/STYLE.md (voce, assoluti: niente em-dash, en-dash, punto e virgola, puntini)

Regole STYLE.md: vietano em-dash (—), en-dash (–), punto e virgola (;), puntini come … e sequenze --; usare tre punti ... solo se necessari, virgolette dritte. file:content/STYLE.md:19-29

Verifica automatizzata (grep):
- frontend/src/game/main.jsx:470: `<td className="v">—</td>` → viola (em-dash). file:main.jsx:470
- Altri: nessun —/–/;/… nei game templates/JSX (solo ... in loading strings e spread operator ... in codice JS, non testo visibile). file:game.html:55, game_compare.html:52, game_hub.html:60, game_leaderboard.html:30, game_order.html:45, main.jsx/spread, shared.jsx spread/toasts.

Violazioni trovate (testo visibile):

1. frontend/src/game/main.jsx:470 — `—` nella cella indizio bloccato ("Indizio da svelare" → valore `—`). Testo visibile. Violazione: em-dash vietato. file:main.jsx:470
2. Loading strings usano `...` (tre punti normali) — OK secondo regola 3 (ammette tre punti normali). OK.
3. Template hardcoded breadcrumb in game_hub.html:19 `<a href="/">Divario Italia</a>` (singolo link) vs trail — non stile ma markup; testo ok.
4. Voce: in generale testi italiani, tone descrittivo. Alcuni "·" usati come separatori (main.jsx:480, 490) — accettabile, non tra caratteri vietati.

Altre possibili violazioni non trovate (nessun ;, –, …). Solo riga 470.

## 3. Fine partita: cosa impara il giocatore del dato? Link alla scheda indicatore canonica /indicatore/<slug>/<acronimo>-<id> e alla regione? Manca qualcosa?

### Indovina la Regione (main.jsx ResultPanel 593-723)

- Soluzione: linka regione a `solution.path` = `/regione/{mystery_key}` (game.py:340-343). OK per regione. file:main.jsx:670,683-686; game.py:340-343
- Recap tabella (695-709): ogni riga mostra indicatore con link `row.path` = `profiles.indicator_path(clue["id"], clue["name"])` (game.py:216-230 in _recap_entry). Verificato: `profiles.indicator_path` (app/profiles.py:103) chiama `sources.indicator_url("territorial", id, indicator_slug(name))` e `indicator_url` (app/sources.py:245-258) costruisce esattamente `/indicatore/<slug>/<acronimo>-<id>` (codice = `ter-<id>`, vedi app/sources.py:240-242). **Il link canonico richiesto dalla spec c'è ed è corretto, solo a fine partita.** file:main.jsx:700-709; app/game.py:216-230; app/profiles.py:97-104; app/sources.py:240-258
- Cosa impara: vede valori regione vs media (703-704), nome+link indicatore, anno/unità. Spiegazioni (description/value_explanation/reading) presenti nei clue ma **non mostrate nel recap**: `_recap_entry` le passa (game.py:227-229) e ResultPanel non le renderizza (695-709). Il giocatore vede il numero ma non "cosa misura". file:app/game.py:216-230; main.jsx:695-709
- Durante la partita l'indicatore **non** è linkabile: `_clue_fields` (app/game.py:127-143) non espone `path`, quindi nessun link alla scheda né durante né dopo il singolo tentativo. Solo il recap di fine partita lo rende cliccabile. file:app/game.py:127-143; main.jsx:476-497
- Mancante: spiegazione breve "cosa misura" per ogni riga nel recap; link all'indicatore durante il gioco; nessun link alla pagina tema/categoria (macro_area esiste in `_clue_fields` ma non è usato in UI). file:app/game.py:127-143; main.jsx:476-497

### Chi è maggiore? (compare.jsx)

- Fine round: verdict (324-338) rivela vincitore + valori (299,317). Nessun recap degli indicatori usati oltre info round (question block 273-286 mostra name, description, value_explanation, SourceStrip). Dopo reveal passa avanti (340-343). Nessun "learning panel": non mostra confronto valori in tabella, non linka indicatore canonico, non linka regioni a schede. file:compare.jsx:273-343
- Sessione finisce implicitamente (errore azzera streak) — nessun end-of-game screen con apprendimenti cumulativi, solo punteggio/sessionBest.
- **Causa profonda, non solo frontend**: `_indicator_fields` (app/quiz.py:330-345) non include `path`, e nemmeno `evaluate_compare` (app/quiz.py:450-464) né `evaluate_order` (app/quiz.py:554-561) lo restituiscono. Le famiglie BES/Multiscopo/Eurostat costruiscono già `path` nei payload (app/quiz.py:95, 131, 166) ma `_indicator_fields` lo scarta. Quindi per questi due giochi il link canonico **non esiste a livello dati**: va aggiunto lato backend, non solo UI. file:app/quiz.py:330-345,450-464,554-561,95,131,166

### Ordina le regioni (order.jsx)

- Revealed (361-371): "La classifica reale" con valori (ol, row.region + value). Nessun link a regioni/indicatori, nessuna spiegazione cosa significa l'ordine, nessun recap. file:order.jsx:361-371
- Nessun learning path.
- Stessa causa backend di sopra: `evaluate_order` (app/quiz.py:554-561) non espone `path` né acronimo dell'indicatore. Le righe `positions` e `correct_order` (app/quiz.py:534-541, 548-551) portano solo `region`, `region_key`, `value`: manca del tutto il riferimento all'indicatore, quindi la UI non può neppure linkare `/indicatore/...` senza modificare il contratto. file:app/quiz.py:534-541,548-551,554-561

Conclusione punto 3:
- Indovina la Regione: recap presente, link indicatore canonico presente e corretto, link regione presente. Manca la spiegazione "cosa misura" a fine partita (già disponibile nei dati, non renderizzata) e il link all'indicatore durante il gioco.
- Compare e Order: quasi assenti dal punto di vista "cosa impara il giocatore del dato". Manca il link canonico indicatore e il link alle regioni in entrambi, inoltre il backend non espone affatto `path` (cfr. sotto). Nessun blocco "Cosa misura questo indicatore" oltre il testo già mostrato a inizio round.

## 4. Stati vuoti, errori di rete, caricamenti: sono gestiti ovunque?

### Hub (hub.jsx, game_hub.html)
- Loading: template `<p class="game-loading">Caricamento delle statistiche...</p>` (hub.html:60), React skeleton anche in StatsPanel/LeaderboardPanel (120-124, 151-156). OK.
- Vuoto: StatsPanel "Gioca una prima partita..." (126-129), LeaderboardPanel "Ancora nessun punteggio questa settimana..." (157-159). OK.
- Errori rete: fetchJson in useTop5 catch → setEntries([]) (100-102) — gestisce come vuoto, non mostra errore. fetch in useAccountAchievements catch silenzioso (25-27). fetch /api/events in shared trackGameEvent catch silenzioso (137-141). file:hub.jsx:25-27,100-102; shared.jsx:137-141
- Auth: mergeLocalStatsOnce può fallire? chiamata async (18) senza try/catch visibile nel flusso (notifyAchievements chiamato se unlocked). Potenziale silenzio su errore.

### Indovina la Regione (main.jsx)
- Loading: skeleton (407-422). OK.
- Error: `status==="error"` mostra `error` string (423). startGame catch imposta messaggi specifici per archive vs altri (225-235). fetchJson regions catch → regions[] (149). OK.
- Vuoto suggerimenti: se query vuota array vuoto (143), nessun messaggio "nessun suggerimento". OK (non necessario).
- Progress save/load: try/catch silenzioso (50-72 load/save progress/stats) — non mostra errore a utente, mantiene giocabilità. OK (come commentato).

### Compare (compare.jsx)
- Idle (222-243), loading (360-372), error (246-253) con retry. OK.
- Round fetch catch → error (145). Answer postGame catch → error (195). Timer gestisce timeout (88-99). OK.

### Order (order.jsx)
- Idle, loading (405-417), error (233-240), retry. Round fetch (76-83), answer (142-169) con catch. OK.
- Drag/drop con preventDefault (115-117), stato drag (110-131). Accessibile via tastiera (frecce). OK.

### Leaderboard (leaderboard.jsx, game_leaderboard.html)
- Loading: template (30), skeleton (106-112). Error (104) "Impossibile caricare la classifica. Riprova." OK. Vuoto (114-118). OK.

Generale: errori di rete gestiti con messaggi italiani e retry dove possibile. Stati vuoti presenti. Caricamenti con skeleton/loading. Alcuni fetch secondari (events, account) silenziosi (non bloccanti) — accettabile.

## 5. Hub: organizzazione, cosa manca (gioco del giorno in evidenza, stato "già giocato oggi", serie, prossimo puzzle)

Hub template (game_hub.html):
- Hero (24-34): titolo + lead + panel "Come funziona". OK.
- Sezione "I tre giochi" (37-57): card statiche server-rendered. Nessuna evidenziazione dinamica (nessun badge "Gioco del giorno", nessun stato "già giocato oggi").
- React hub.jsx non modifica markup card (usa tracking solo). file:hub.jsx:84-94
- Stats locali mostrano serie/miglior serie (bestStreak 112, 132) e partite (133). Serie è per giochi (max tra compare.daily streak? 112 calcola Math.max(stats.compare.bestStreak, stats.daily.maxStreak)). OK ma non mostra "serie attuale" né "prossimo puzzle" (Indovina la Regione ha countdown solo in ResultPanel, mai sull'hub).
- Nessun "prossimo puzzle" visibile sull'hub (countdown daily solo in main.jsx 179-181, mostrato in ResultPanel 688-692). Nessun richiamo orario.
- "Già giocato oggi": Indovina la Regione salva progress per puzzle_id daily (208-223) — stato persistito localmente ma non comunicato all'hub. Hub non legge progress daily, mostra solo stats aggregate.

Mancanze (punto 5):
- Gioco del giorno in evidenza: card "Indovina la Regione" non riceve badge/CTA diverso (es. "Gioca oggi" vs "Già giocato"). Nessuna logica client-side.
- Stato "già giocato oggi": non mostrato. Potrebbe controllare localStorage per `di-game-progress:daily:{YYYY-MM-DD}` (main.jsx usa prefix STORAGE_PROGRESS_PREFIX + puzzle_id). Hub non fa questo controllo.
- Serie: mostrate nelle stats (miglior serie) ma non "serie attuale" per daily/compare; hub mostra bestStreak aggregato (132). Non evidenzia.
- Prossimo puzzle: assente dall'hub.

## 6. Doppie briciole di pane e JSON-LD: verifica nei template se ci sono due breadcrumb e "creator": Istat nei blocchi Game

### Breadcrumb doppi

- game_hub.html:18 `{{ breadcrumb.trail(percorso) }}` + 19 `<nav class="breadcrumb">...</nav>` (hardcoded più corto). Doppio. file:hub.html:18-19
- game.html:30 trail + 31 nav hardcoded. Doppio. file:game.html:30-31
- game_compare.html:38 solo hardcoded (nessun trail). Unico nav. file:compare.html:38
- game_order.html:30 trail + 31 hardcoded. Doppio. file:order.html:30-31
- game_leaderboard.html:19 solo hardcoded. Unico. file:leaderboard.html:19
- _game_subnav.html: nessun breadcrumb. OK.

Pattern: hub/daily/order usano sia macro `breadcrumb.trail(percorso)` (app/templates/_breadcrumb.html genera nav completo con aria-label) sia nav hardcoded ridotto. Compare/leaderboard usano solo hardcoded. Risultato: doppio nav in 3 pagine, nav ridotto in altre 2. Incoerenza + markup duplicato.

### JSON-LD Game

- game.html:13-24: Game con "creator": {"@type":"Organization","name":"Istat"} (riga 21). file:game.html:21
- game_compare.html:11-22: Game creator Istat (19). file:compare.html:19
- game_order.html:13-24: Game creator Istat (21). file:order.html:21
- game_hub.html: nessun JSON-LD Game (solo breadcrumb.jsonld). file:hub.html:13
- leaderboard: nessun Game JSON-LD.

Spec punto 6 chiede: verifica se ci sono due breadcrumb e `"creator": Istat` nei blocchi `Game`.

Trovato:
- Due breadcrumb: SÌ in game_hub.html, game.html, game_order.html. NO in compare/leaderboard (uno solo).
- "creator": Istat nei blocchi Game: SÌ in game.html, game_compare.html, game_order.html (tutti e 3). game_hub/leaderboard non hanno blocco Game.

Nota: in altri template (es. region_page, quality_life_*) si usa `organization_ref_jsonld`/pattern diverso; qui esplicito "Istat". Secondo spec 6 va verificato — non necessariamente errato, ma da confermare coerenza con policy sito (creator dei dati vs creator del gioco). Spec stessa cita vincoli stile/dati.

## Raccomandazioni per Divario Italia

Priorità P0 = attrito visibile al primo giocatore o rischio dati/SEO. P1 = profondità di apprendimento e ritorno. P2 = rifinitura. Costo S/M/L in giornate di sviluppo su una persona. Rischio: basso quasi ovvero, medio dove cambia un contratto API.

1. **[P0][S][rischio basso]** Breadcrumb duplicati. In `game_hub.html`, `game.html`, `game_order.html` ci sono due `<nav class="breadcrumb">`: quello del macro `breadcrumb.trail(percorso)` e uno hardcoded subito sotto. Due nav con lo stesso ruolo landmark, testo diverso, doppio nell'aria. Togli l'hardcoded (righe 19, 31, 31) e tieni il macro, che è anche quello che genera il JSON-LD. file:app/templates/game_hub.html:18-19, app/templates/game.html:30-31, app/templates/game_order.html:30-31
2. **[P0][S][rischio basso]** Uniforma i due template che hanno solo la nav hardcoded (`game_compare.html:38`, `game_leaderboard.html:19`): o passano al macro `trail` come le altre tre, o le altre tre passano all'hardcoded. Lo stato attuale è incoerente. file:app/templates/game_compare.html:38, app/templates/game_leaderboard.html:19
3. **[P0][S][rischio basso]** Stile: `main.jsx:470` usa `—` (em-dash) come segnaposto del valore dell'indizio non ancora svelato. `content/STYLE.md:19` lo vieta nel testo visibile. Sostituisci con la stringa vuota o con un trattino normale. È l'unica violazione di questo tipo in tutta la sezione. file:frontend/src/game/main.jsx:470; content/STYLE.md:19-25
4. **[P0][M][rischio medio]** Espungi `path` dal contratto di "Chi è maggiore?" e "Ordina le regioni". `_indicator_fields` (`app/quiz.py:330-345`) scarta il `path` che i payload BES/Multiscopo/Eurostat già calcolano (`app/quiz.py:95, 131, 166`), e `evaluate_compare` / `evaluate_order` non lo restituiscono. Aggiungi `path` (canonico `/indicatore/<slug>/<acronimo>-<id>`, costruito come in `app/profiles.py:103` e `app/sources.py:245-258`) a `_indicator_fields`, `evaluate_compare` (`app/quiz.py:450-464`) ed `evaluate_order` (`app/quiz.py:554-561`). Rischio medio: cambia il payload di tre endpoint, quindi tocca anche `app/quiz_tokens.py` se il token firma l'indicatore. file:app/quiz.py:95,131,166,330-345,450-464,554-561; app/profiles.py:103; app/sources.py:240-258
5. **[P0][M][rischio medio]** Learning block a fine round in `compare.jsx` e `order.jsx`. Con il `path` del punto 4: nome indicatore cliccabile, tabella dei due valori con unità, link alle due schede regione `/regione/<key>`, e la `description` già presente nel payload (`app/quiz.py:462`) resa con etichetta "Che cosa misura", come fa già `order.jsx:259-273` a inizio round. Oggi il giocatore di questi due giochi esce dalla partita con un punteggio e nessun dato portato via. file:frontend/src/game/compare.jsx:273-343; frontend/src/game/order.jsx:259-273,349-376
6. **[P0][S][rischio basso]** Fine partita di "Indovina la Regione": il recap riceve già `description`, `value_explanation` e `reading` dal backend (`app/game.py:227-229`) e non li mostra. Renderizzali, almeno la riga `description`, sotto il valore di ogni indicatore. Il link canonico e il link alla regione ci sono già e sono corretti, qui si tratta solo di mostrare il testo. file:app/game.py:216-230; frontend/src/game/main.jsx:694-709
7. **[P1][S][rischio basso]** Indizio linkabile durante la partita. `_clue_fields` (`app/game.py:127-143`) non espone `path`, quindi l'indicatore è cliccabile solo a fine partita. Aggiungere `path` e rendere il nome dell'indizio un link: è il momento in cui la curiosità è alta e il sito ha già la pagina. file:app/game.py:127-143; frontend/src/game/main.jsx:476-497
8. **[P1][M][rischio basso]** Hub: stato "già giocato oggi". Il daily salva il progresso sotto `di-game-progress:<puzzle_id>` (`main.jsx:20, 57-72`, con `puzzle_id` = `daily:<ISO>` da `app/game.py:79-81`). L'hub può ricavare la chiave di oggi e leggere quel record per cambiare la card in "Già giocata" invece di "Gioca ora", senza toccare il backend. Oggi la card è statica e identica per tutti (`app/templates/game_hub.html:39-44`). file:app/templates/game_hub.html:39-44; frontend/src/game/main.jsx:20,57-72; app/game.py:79-81
9. **[P1][M][rischio basso]** Hub: gioco del giorno in evidenza. La terza parte del layout (`hub-layout__hero` a sinistra, `hub-layout__main` a destra, `app/templates/game_hub.html:23-62`) è spesa metà per spiegare il quiz a parole, metà per tre card uguali. Dai peso all'hero una card protagonista per la sfida del giorno, con numero del giorno, countdown alla prossima (il dato `next_puzzle_at` esiste già in `daily_payload`, `app/game.py:247-255`, e il countdown è già implementato in `main.jsx:688-692`), e usa lo spazio liberato per le altre due modalità più in piccolo.
10. **[P1][S][rischio basso]** Hub: errori secondari visibili. `useTop5` trasforma un errore di rete in "nessun punteggio questa settimana" (`hub.jsx:100-102, 157-159`), cioè un errore di rete si presenta all'utente come un dato vero. Separa i due stati: `null` = caricamento, `[]` = vuito, errore = messaggio con retry. Stesso principio per `useAccountAchievements` (`hub.jsx:25-27`). file:frontend/src/game/hub.jsx:25-27,96-104,157-159
11. **[P1][S][rischio basso]** Hub: la serie è mostrata solo come "Miglior serie" aggregata sui due giochi (`hub.jsx:111, 132`), che mescola due metriche diverse. Mostra la serie del daily separata, o etichetta la miscela. file:frontend/src/game/hub.jsx:111,132
12. **[P1][S][rischio basso]** Onboarding di "Indovina la Regione": contraddice il template. `game.html:61` parla di "quattro aree del catalogo: economia e opportunità, persone e conoscenza, territorio e servizi, comunità e benessere", che sono le quattro macro-area reali (`app/taxonomy.py:160-181`). Il modal in-app elenca invece sei etichette diverse ("economia, lavoro e istruzione, società, ambiente, demografia e salute, istituzioni", `main.jsx:731-733`) che non corrispondono a nessuna tassonomia del sito. Due fonti di verità diverse per la stessa idea, entrambe visibili nella stessa partita. Allinea una delle due, meglio il modal alle quattro macro-area. file:app/templates/game.html:61; frontend/src/game/main.jsx:731-733; app/taxonomy.py:160-181
13. **[P1][S][rischio basso]** Connetti il tab `?` di "Indovina la Regione" (`main.jsx:395-403`) all'hub. Oggi il pulsante "Come si gioca" spiega solo le regole di un gioco, mentre sulla pagina dell'hub si spiega il sistema dei tre giochi. Nessuna delle due duevie rimanda all'altra.
14. **[P1][S][rischio medio]** JSON-LD: verifica `"creator": Istat` nei tre blocchi `Game`. Presente in `game.html:21`, `game_compare.html:19`, `game_order.html:21`. In `Game`, `creator` è l'autore del gioco, e il gioco è di Divario Italia, non di Istat: Istat è la fonte dei dati, che va in `isBasedOn` come `Dataset` (il pattern che il sito usa già in `region_page.html:27-28` e `v1/regione.html:47-48`). Aggiungi `isBasedOn` con licenza e fonte, come fanno le altre pagine, e correggi il `creator`. Rischio medio: modificare lo structured data di tre pagine indicizzate richiede un re-test in Rich Results. Verificato anche che non ci sono blocchi `Game` su hub e classifica, quindi la lacuna è solo sui tre giochi. file:app/templates/game.html:21; app/templates/game_compare.html:19; app/templates/game_order.html:21; app/templates/region_page.html:27-28; app/templates/v1/regione.html:47-48
15. **[P2][S][rischio basso]** Riduci la prosa sopra la piega sull'hub. Il blocco "Come funziona il quiz" (`game_hub.html:29-33`) ripete quasi parola per parola le tre card che stanno subito sotto (37-57). Chi arriva per la prima volta deve leggere due volte la stessa idea. Tieni il testo utile (si gioca senza registrazione, dove finiscono i record) e taglia il resto. file:app/templates/game_hub.html:29-33,37-57
16. **[P2][S][rischio basso]** "Come si gioca" in fondo alle pagine di compare, order e classifica è utile per la SEO ma duplica l'onboarding già mostrato in-app a inizio partita. Tieni il testo, accorcia le due righe di cross-link finale che ripetono il subnav. file:app/templates/game_compare.html:58; app/templates/game_order.html:51; app/templates/game_leaderboard.html:37
17. **[P2][S][rischio basso]** Fine partita di "Ordina le regioni": il giocatore vede la classifica reale con i valori ma non una frase che dica cosa ne ricava. Una riga "cosa misura" più il link alla scheda dell'indicatore copre il vuoto editoriale che l'ordine numerico da solo non riempie. file:frontend/src/game/order.jsx:359-371
18. **[P2][M][rischio basso]** L'archivio chiama ogni giorno "Sfida #<numero>" e lo mette in una modale senza data leggibile nel titolo (`main.jsx:778-789` mostra il numero e la data ISO grezza). Un nuovo giocatore non sa cosa sia "Sfida #78". Metti la data in chiaro e rinomina in "Sfida del <giorno>". file:frontend/src/game/main.jsx:778-789
19. **[P2][S][rischio basso]** Il pulsante "Condividi il risultato" esiste solo in modalità giornaliera (`main.jsx:673-677`), e il testo condiviso è un blocco di quadratini (`main.jsx:312-317`) senza il numero della regione né il link dell'indicatore. Chi vede il risultato su un social non ha modo di sapere di che si tratta né di raggiungere il dato. Aggiungi titolo e link.
20. **[P2][S][rischio basso]** Sotto la legenda della mappa manca il significato del confino. Le quattro aree della mappa hanno una funzione nei colori ma nessuna etichetta, mentre il gioco dà tre risposte diverse sullo stesso concetto: "ripartizione geografica" (`game.html:61`), `geo_area` Nord/Centro/Sud/Isole come etichetta sotto il nome (`compare.jsx:297`), e Nord/Centro/Mezzogiorno nell'indizio (`app/game.py:39-52`). Sono due partizioni diverse con lo stesso nome in due punti diversi della stessa partita. file:app/templates/game.html:44-48,61; frontend/src/game/compare.jsx:297; app/game.py:39-52