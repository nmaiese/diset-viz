# Sfida Italia: il gioco sotto `/quiz`

Il sottomarchio dei giochi di Divario Italia si chiama **Sfida Italia**. Cinque giochi brevi sui dati territoriali (regioni e province), tutti sotto `/quiz`. Il nome l'ha scelto Nello il 30 settembre 2026. L'URL è rimasto `/quiz` perché le quattro pagine già indicizzate avevano 6 clic e 170 impression in 90 giorni, in posizioni da 6 a 9 (Search Console, 30 settembre 2026): cambiare indirizzo avrebbe buttato quel poco.

Questo documento è il contratto della sezione e **possiede l'argomento**. Chi tocca `app/game*.py`, `app/quiz*.py`, `frontend/src/game/` o `config/game_indicators.csv` lo legge prima e lo aggiorna quando cambia un fatto. Dove il documento e il codice non tornano, ha ragione il codice: si corregge il documento. Le regole visive stanno in `design/v1/SISTEMA.md`, gli eventi in `docs/tracking_spec.md`, l'account in `docs/ACCOUNT.md`, i passi di rilascio in `DEPLOY.md`.

Ogni numero che qui compare o viene dal codice (dove c'è una costante si nomina quella, e il valore si scrive solo per dare l'ordine di grandezza) o è datato e attribuito. I conteggi di province, indicatori, traguardi e test **non si scrivono a mano**: un numero scritto invecchia in silenzio, e si legge dal codice (`len(province_pool())`, `game_indicators()`, `achievements.CATALOG`).

## I giochi

| Gioco | URL | Template | Modulo Python | React (ingresso Vite) |
| --- | --- | --- | --- | --- |
| Indovina la Regione | `/quiz/indovina-la-regione` | `game.html` | `app/game.py` | `main.jsx`, `guess/GiocoRegione.jsx` (`quiz-indovina`) |
| Indovina la Provincia | `/quiz/indovina-la-provincia` | `game_provincia.html` | `app/game_provincia.py` | `guess/GiocoProvincia.jsx` (`quiz-provincia`) |
| Chi è maggiore? | `/quiz/chi-e-maggiore` | `game_compare.html` | `app/game_compare.py`, più `app/quiz.py` per le serie | `compare.jsx`, `compare-logica.js` (`quiz-compare`) |
| Ordina le regioni | `/quiz/ordina` | `game_order.html` | `app/game_order.py`, più `app/quiz.py` per le serie | `order.jsx`, `order.puri.js` (`quiz-order`) |
| Dov'è la provincia? | `/quiz/province-italiane` | `game_mappa.html` | `app/game_mappa.py`, `app/game_mappa_page.py` | `mappa/GiocoMappa.jsx` (`quiz-mappa`) |

Intorno ai giochi: l'hub `/quiz` (`game_hub.html`, `hub.jsx`, `quiz-hub`) e la classifica `/quiz/classifica` (`game_leaderboard.html`, `leaderboard.jsx`, `quiz-leaderboard`). I sorgenti React stanno in `frontend/src/game/`, un ingresso per pagina in `frontend/vite.config.js`, e il bundle finisce in `app/static/dist/assets/` (da ricostruire con `cd frontend && npm run build` dopo ogni modifica). Le tre rotte vecchie `/gioco`, `/gioco/chi-e-maggiore` e `/gioco/ordina` fanno 301 verso `/quiz`.

Quello che i giochi hanno in comune sta in pochi posti: `app/game_daily.py` (giorno, seed, pool dei territori, elenco curato), `app/quiz_tokens.py` (token e round monouso), `frontend/src/game/shared.jsx` (componenti `FinePartita`, `Condividi`, `SfidaCondivisa`, e `trackGameEvent`), `frontend/src/game/oggi.js` (lo stato di oggi e la serie locale) e `frontend/src/game/puri.js` (funzioni pure che `node --test` prova senza DOM).

**Due scelte di struttura da non disfare.** Il gioco **non è una pagina della 1.0**: non passa da `design.render` e non va spostato in `app/templates/v1/`, perché ha il suo sottomarchio (vedi sotto). E la sfida di oggi è **prerenderizzata nell'hub** con gli attributi `data-oggi-*` di `game_hub.html`: la pagina indicizzabile non deve dipendere da React, che aggiunge solo lo stato (numero, conto alla rovescia, "giocata oggi", serie).

### Come funziona ciascun gioco

- **Indovina la Regione.** Una regione misteriosa, indizi Istat che si sbloccano a ogni tentativo sbagliato, `MAX_ATTEMPTS` tentativi (uguali agli indizi, `CLUES_PER_PUZZLE`). Tre modalità: sfida del giorno, allenamento (`practice:<hex>`, seme casuale) e archivio dei giorni passati (`archive_list`, mai oltre oggi). Le soluzioni e gli indizi si ricostruiscono dal `puzzle_id` a ogni richiesta (`build_puzzle`).
- **Indovina la Provincia.** Una provincia al giorno, `ATTEMPTS` tentativi, indizi di dato BES provinciale. La mappa dice quanto si è vicini con una distanza e una direzione fra centroidi (`game_daily.distance_km_direction`): sono **stime**, e il testo deve dirlo. Due livelli sullo stesso rompicapo: `province` (si sceglie fra tutte) e `stessa_regione` (si sa la regione, si sceglie fra le sue province).
- **Chi è maggiore?** Due territori e un indicatore, si sceglie quello col valore più alto. La sfida del giorno ha `COMPARE_PAIRS` coppie, stesse per tutti. In più c'è la **serie** (`/api/game/compare/round`): round a caso uno dopo l'altro, con la serie di risposte giuste di fila che si azzera all'errore, il timer e la classifica.
- **Ordina le regioni.** Si mettono in fila `ORDER_TERRITORIES` territori dal valore più alto al più basso, un punto per ogni posizione giusta. In serie si ordinano 3 o 5 territori (`quiz.ORDER_COUNTS`).
- **Dov'è la provincia?** `QUESTIONS` province da trovare su una mappa muta, stesse per tutti, 2 punti per la provincia giusta e 1 per una provincia della stessa regione (`game_mappa.POINTS`). Due livelli (`italia`, `regione`: qui la regione è detta nella domanda e la mappa si stringe) e due modalità (`map`, e `list` solo a `italia`: si risponde con la regione, 1 punto). Le tre combinazioni hanno ciascuna la propria conta (`SCORE_GAMES`).

## I livelli e i dati

I tre livelli di Chi è maggiore e Ordina (`game_daily.LEVELS`) sono `regioni`, `stessa_regione` (due territori provinciali della stessa regione) e `province` (province d'Italia). "Stessa regione" esiste solo per le regioni con abbastanza province: `MIN_PROVINCES_COMPARE` per Chi è maggiore e `MIN_PROVINCES_ORDER` per Ordina, e `game_daily.eligible_regions(minimo)` dice quali sono. La stessa soglia (`MIN_PROVINCES_COMPARE`) vale per la regione di Indovina la Provincia, e `game_mappa.REGION_LEVEL_MIN` per il livello `regione` della mappa: con una provincia sola la domanda si risponderebbe da sola.

**L'elenco curato** è `config/game_indicators.csv`, letto da `game_daily.game_indicators()`. Separatore `;`, colonne `id`, `famiglia`, `nome_leggibile`, `unita`, `livello_regione`, `livello_provincia`, `note`. È il solo posto dove si decide quali indicatori entrano nei giochi, con il nome leggibile e l'unità che il giocatore vede (non quelli lunghi della fonte). I due `livello_*` sono flag `1` e `0`: l'`id` è quello del pool regionale del quiz quando `livello_regione` è 1, e l'id BES delle province quando l'indicatore esiste solo lì. L'anno non si sceglie: è sempre l'ultimo disponibile. Un indicatore nuovo si aggiunge al CSV e passa dai test del gioco, che ne guardano fonte, anno e giocabilità. Il nome della fonte viene sempre da `app/sources.py` e mai scritto a mano nel codice del gioco: una scrittura a mano ha già pubblicato una serie sotto il nome sbagliato.

Per **Indovina la Provincia** l'indicatore è anche filtrato per copertura: entra solo se ha un valore per tutte le province nell'ultimo anno (`EXPECTED_PROVINCES`) e l'ultimo anno non è prima di `MIN_YEAR` (`game_provincia.allowed_clues`). Chi è maggiore e Ordina chiedono solo abbastanza valori distinti fra i territori in gioco (`game_daily._candidates`).

**La difficoltà.** Nelle sfide del giorno la fissa il giorno della settimana, `WEEKDAY_DIFFICULTY` (lunedì indice 0, domenica la più dura). In Chi è maggiore e Ordina è una finestra sulla distanza fra i valori in gara, espressa come frazione dei valori distinti (`_COMPARE_WINDOW`, `_ORDER_WINDOW`): bassa la coppia è lontana in classifica, alta è quasi adiacente. Nella mappa la fissa la composizione per dimensione della sagoma (`game_mappa.MIX`: quante province grandi, medie e piccole). Nelle **serie** di Chi è maggiore la fa salire la serie corrente, lato server, `min(serie // 3, quiz.MAX_DIFFICULTY)`: il client non manda una difficoltà e se la manda non si legge.

**Le province e la mappa.** Il pool (`game_daily.province_pool()`) unisce i codici (`province_codes.csv`) con i centroidi di `app/static/data/province_centroidi.json`, che lo script `design/v1/tools/centroidi_province.py` calcola dai tracciati in `app/design/province_paths.json` (centroide pesato per area sul poligono più grande, così le isole minori non lo spostano). Alcune sagome sono troppo piccole per essere toccate a 390 px: sotto `PLAYABLE_THRESHOLD` (lato minore, in unità del viewBox) una provincia **non può essere quella misteriosa** ma resta fra le opzioni (`excluded_provinces()` dice quali). I chilometri fra centroidi usano `KM_PER_UNIT`, e il viewBox è un Mercatore: la scala cambia con la latitudine, quindi sono stime.

## La sfida del giorno

**Il giorno è quello di Roma.** Il server gira in UTC (Cloud Run): senza una funzione unica, la sfida nuova uscirebbe all'una o alle due di notte e ogni punto che usasse la data di sistema darebbe un giorno diverso da quello del giocatore. Per questo c'è solo `game_daily.today_rome()`, il numero della sfida viene da `challenge_number()` (con `GAME_EPOCH`, il giorno di lancio, come numero 1) e il conto alla rovescia da `next_challenge_rome()`, la mezzanotte di Roma in UTC. I test fissano l'orologio alle 23:30 UTC (a Roma, d'estate, è già il giorno dopo) e a 21:59 UTC (è ancora lo stesso): `tests/unit/test_game_daily.py`.

**Il `puzzle_id` è `daily:<ISO>` e deve essere quello di oggi.** Nessuna rotta accetta una data scelta dal client per una sfida seminata: chi risponde a una sfida di ieri riceve un errore: `puzzle_changed` (400) in Chi è maggiore e nella mappa, 410 su Regione (se la partita si dichiara del giorno), `sfida_scaduta` (410) su Provincia, e in Ordina una risposta che non combacia con la sfida di oggi (`bad_request` o `token_invalid`). Il payload non rivela mai soluzioni di domani. Fa eccezione solo l'archivio di Indovina la Regione, che per costruzione mostra giorni già passati.

### Il seed

Il repository è pubblico, quindi il vecchio seed di Indovina la Regione (un `random.Random` su una stringa col numero del ciclo) lo calcola chiunque legga il codice: la soluzione di domani non era un segreto. Per questo ogni sfida seminata esce da `HMAC-SHA256(GAME_SEED_KEY, "<gioco>|<data>")` (`game_daily.day_seed`), con una chiave che **non sta nel repo**. Lo stesso giorno produce la stessa sfida per tutti e su ogni istanza.

- **Senza la variabile** in locale e nei test si usa `DEV_SEED_KEY`, scritta nel codice e quindi **non segreta**: va bene per provare, mai in produzione, e un avviso nel log lo ricorda. Dove `K_SERVICE` è impostata (Cloud Run) la chiave deve esserci: senza, `game_daily.seed_key()` solleva `SeedKeyMissing` e il gestore di `app/views.py` (`game_seed_key_missing`) risponde **503** `seed_unavailable` e scrive l'errore nel log. È voluto: meglio una sfida che non si apre di una sfida prevedibile.
- **Quali rotte rispondono 503** senza chiave: tutte quelle che compongono una sfida seminata, cioè `compare/daily`, `compare/daily/{session,answer,next}`, `order/daily`, `order/daily/{session,answer}`, `provincia/{daily,guess}`, `map/daily/{session,answer}`, e quelle di Indovina la Regione (`daily`, `daily/<iso>`, `guess`) **solo per i giorni dal cutover in avanti**. Non rispondono mai 503 le pagine (nessuna chiama il seed, e la pagina della mappa lo dichiara apposta: un errore di deploy non deve togliere dall'indice la pagina che porta traffico), le serie a round, l'allenamento di Regione, l'archivio e l'elenco regioni.
- **Ruotare la chiave** cambia tutte le sfide seminate da quel momento: **anche quella di oggi**, e per Regione anche i giorni d'archivio dal cutover in poi. Chi sta giocando prende un errore al prossimo invio. Si fa solo di proposito e mai a metà giornata. Le sfide di Regione prima del cutover non cambiano mai. Ruotare `SECRET_KEY` è un'altra cosa: invalida i token in volo, che aprono una sessione nuova.

### `SEED_CUTOVER`: perché esiste e che cosa non si deve fare

Indovina la Regione è l'unico gioco già in produzione prima dell'HMAC, con soluzioni già servite, salvate nel `localStorage` per `puzzle_id` e nell'archivio. Il passaggio non può riscriverle. `SEED_CUTOVER` è la data da cui Regione esce dall'HMAC: **i giorni prima tengono il ciclo vecchio** (`_legacy_cycle`), così archivio e `puzzle_id` già salvati restano coerenti, e dal cutover in avanti la regione del giorno viene da un mescolamento HMAC con la stessa garanzia di prima (nessuna ripetizione dentro il ciclo, `daily_region`). Gli altri quattro giochi non hanno storia da difendere e usano l'HMAC dal primo giorno.

Cose da non fare:

- **Non spostare `SEED_CUTOVER` indietro** a un giorno già servito: cambierebbe la soluzione di un giorno che qualcuno ha già giocato o salvato.
- **Non fissarlo prima del rilascio.** Si fissa nell'ultimo commit prima del merge, al **giorno del deploy più uno**: fra la data scritta e il merge la produzione serve ancora il codice vecchio, e un cutover anticipato darebbe a quei giorni soluzioni diverse da quelle servite. Finché nel codice c'è il segnaposto del 2099 il rilascio non è fatto.
- **Non cambiarlo dopo il rilascio.** Una volta fissato resta lì per sempre. `tests/unit/test_game_daily.py` guarda che sia dopo il lancio e che i giorni prima producano le soluzioni di prima.

### La storia della mappa e il test d'oro

Nella mappa una provincia non torna prima di `WINDOW_DAYS` giorni, e per saperlo bisogna conoscere le sfide dei giorni prima, che a loro volta dipendono dai precedenti. Nessuno le ha salvate, quindi la sfida di oggi si ricalcola **in avanti da `MAP_EPOCH`** con `game_mappa._history`, una funzione pura in cache per giorno, livello e chiave (con la chiave risolta *prima* della cache, perché una sfida già calcolata non aggiri il 503). `MAP_EPOCH` è un'ancora di calcolo, non la data di lancio.

Conseguenza che si rompe in silenzio: **qualunque cambio di dati** (le aree in `province_centroidi.json`, le regioni di `province_codes.csv`, `MIX`, `WINDOW_DAYS`, la regola delle fasce) **cambia la storia ricalcolata e quindi la sfida di oggi**, e chi sta giocando prende `token_invalid`. Il **test d'oro** (`tests/unit/test_game_mappa_puro.py`, classe `GoldenTest`) rende il cambio visibile: fissa l'impronta delle tre fasce di dimensione (`bands_fingerprint`), tre giorni con una chiave di prova, e le costanti. Se fallisce, un dato o una regola ha spostato le sfide. Se il cambio è voluto, `MAP_EPOCH` passa al giorno del cambio, la storia riparte da lì (al più con una ripetizione al confine) e si aggiorna il test.

## Anti-barare

Il principio: la risposta giusta non parte dal browser prima del suo momento, e il browser non decide mai un punteggio. Chiunque può aprire gli strumenti del browser, e va bene così: il server rifà la valutazione. Il resto del modello difende la classifica e l'account, non il piacere di chi gioca da solo. Il repository è pubblico: qui si descrivono le difese e i loro limiti, non le procedure per aggirarle.

### Il token di round, versione 2

`app/quiz_tokens.py` firma con `itsdangerous` (chiave `SECRET_KEY`) uno stato che il client si passa avanti e indietro, senza stato lato server. È **firmato, non cifrato**: il client può leggerlo, quindi non contiene mai una soluzione. I campi (`_REQUIRED_KEYS`):

| Campo | Che cos'è |
| --- | --- |
| `v` | versione (2): un token di un'altra versione apre una sessione nuova, senza codice di compatibilità |
| `m` | modalità: `compare`, `order` (le serie), `compare_daily`, `order_daily`, `mappa_daily` (le sfide del giorno) |
| `sid` | id della sessione |
| `s`, `b`, `r` | serie corrente, la migliore, round giocati |
| `c` | quanti territori (Ordina) |
| `q` | numero progressivo del round legato |
| `fp` | impronta del round aperto, calcolata dal server (indicatore, anno, territori, nonce): `None` se nessun round è aperto |
| `x` | il parametro del round, ad esempio il livello |
| `iat` | quando il server ha emesso il round, il tempo lo misura sempre lui |
| `n` | nonce del round |
| `t` | timer sì o no, deciso all'apertura della sessione |
| `st` | quando è nata la sessione |

Vale 12 ore (`_MAX_AGE_S`). Un token scaduto, manomesso o di un'altra modalità apre una sessione nuova: il gioco resta giocabile, solo senza serie né classifica. Chi è maggiore e la mappa mettono nel token anche il conto della sfida (campi `sfida` e `mappa`), firmato come tutto il resto: il client non può scriverlo. **Indovina la Provincia ha un token tutto suo** (sale propria, `app/game_provincia.py`), con il `puzzle_id`, il livello e le province già tentate: il numero del tentativo lo decide quel token, mai il client.

### Round monouso e il fallimento aperto

Un round si risponde una volta sola. `quiz_tokens.claim_round(sid, q)` scrive la coppia in `quiz_answered` (chiave primaria `(sid, q)`) e la seconda risposta alla stessa coppia riceve **409** `round_already_answered`. Sta nel database e non in `app.cache` perché Cloud Run scala su più istanze: una cache per processo non vedrebbe le risposte date altrove. Ogni scrittura cancella anche le righe più vecchie della durata del token. `close_open_round` completa il disegno: chiedere un round nuovo mentre ce n'è uno aperto conta quello aperto come sbagliato, altrimenti scartare una domanda costerebbe zero.

**Il fallimento è aperto, di proposito.** Se il database non risponde `claim_round` dice che la risposta è nuova, e l'errore va nel log. Il compromesso: un guasto di Supabase non deve spegnere il gioco, e con il database fermo non si scrive comunque niente di persistente (punteggi e classifica stanno nello stesso database), quindi si gonfia al più quello che il giocatore vede. Il caso che conta è un altro: **con il database vivo ma senza la migrazione `0010` la tabella non c'è**, il monouso non fa niente senza segnalarlo, e la classifica delle serie torna esposta al difetto che il monouso era nato per chiudere (un round che conta più volte). Sulle rotte del gioco non c'è un 500 a dirlo, solo righe nel log, e i punteggi del giorno non si salvano. Per questo la migrazione va applicata prima del merge (`DEPLOY.md`).

### Il tempo, deciso dal server

Un round **con il timer** dura `ROUND_TIME_S` (10 secondi) più `ROUND_TOLERANCE_S` (2, per la rete), e lo applica `round_timing()` guardando `iat`. Nelle serie una risposta oltre il limite è un errore (`late`). Nella sfida del giorno di Chi è maggiore una risposta tardiva **vale come tempo scaduto**: il server fa il claim del round, la conta sbagliata e risponde 200 con `late: true`, perché un 400 lasciava il round aperto e la partita non si poteva più finire (telefono bloccato per due secondi durante una domanda). Un `timeout` che arriva prima dei 10 secondi non vale (`timeout_too_early`). Il controllo del tempo c'è solo in Chi è maggiore (serie e sfida), e `t` nel token lo rende disattivabile: **senza timer è allenamento, non va in classifica e il punteggio della sfida non entra in `daily_scores`** (la risposta porta `training_session`). Ordina, la mappa e i due giochi indovina non hanno un controllo del tempo (il token di una serie di Ordina porta comunque `t`, e il cancello della classifica lo legge).

La **plausibilità** (`is_plausible`) è un controllo sulla sessione intera: `r` round non possono essere durati meno di `r * MIN_ROUND_TIME_S` (1,5 secondi) dalla prima apertura. Si applica a chi invia il punteggio in classifica e al punteggio della mappa che finisce nell'account: una sessione troppo veloce resta giocabile ma non conta. Nella classifica il rifiuto si chiama `score_missing`, un nome che non dice cosa è successo: chi legge i log lo interpreta come "non plausibile".

Due regole delle serie, nate dalla revisione finale. **Una valutazione senza round legato a un token non si serve**: `/api/game/compare/answer` e `/api/game/order/answer` senza un token che lega quella coppia rispondono 400, perché prima valutavano qualsiasi coppia e quindi fungevano da oracolo anche per la sfida del giorno, le cui coppie la sessione mostra in chiaro. **Chiedere un secondo round con lo stesso token già risposto è un reroll** (`quiz_tokens.open_round`) e azzera la serie, come cambiare domanda a round aperto. Chi perde la risposta in rete e preme "Riprova" perde quindi la serie: è il prezzo del controllo.

### Che cosa va in classifica

**La classifica (`/quiz/classifica`, `leaderboard.MODES` = `compare` e `order`) si alimenta solo con le serie.** Chi invia (`POST /api/game/leaderboard`) manda il token e un soprannome, mai un punteggio: il punteggio è la miglior serie del token (`b`), `peek_state` accetta solo le modalità `compare` e `order`, e rifiuta le sfide del giorno. Le sfide del giorno non hanno una classifica pubblica. Per Chi è maggiore e Ordina è una scelta rimandata a dopo il primo rilascio. Per la mappa è di principio: **la pagina porta la risposta** (le sagome sono disegnate dal server con il loro nome), quindi una classifica pubblica non sarebbe onesta. Il punteggio della sfida vive nell'account (`daily_scores`) e nel contatore. Anche Indovina la Regione è senza classifica del giorno: la ritirò la review del 30 settembre.

I soprannomi passano da `moderation.validate_nickname`. Per togliere una riga non c'è un pannello: `POST /api/game/leaderboard/admin/delete` vuole `X-Admin-Key` uguale a `SECRET_KEY` e risponde 404 se non torna, e serve alla moderazione occasionale. Cancella per modalità e soprannome (`leaderboard.delete_entry`).

### Indovina la Regione non ha un token di sessione

Il puzzle si ricostruisce dal `puzzle_id` a ogni richiesta e la regione misteriosa non viaggia mai nel payload, ma il numero del tentativo lo dichiara il client. È un compromesso accettato per un gioco non competitivo, e ha una conseguenza che va ricordata: **nessuna classifica e nessun traguardo competitivo deve poggiare su Regione**. Il suo risultato entra nell'account (storico e serie), ma vale come diario di chi gioca, non come prova.

### I limiti di frequenza e l'IP

Il limite è a finestra fissa, per processo (`views._rate_limit_ok`, appoggiato alla cache dell'app). Con più istanze Cloud Run è più lasco di come si legge, mai più stretto: frena uno script, non un attacco distribuito.

| Dove | Limite |
| --- | --- |
| le risposte di Chi è maggiore (serie e sfida, `next` compreso), di Ordina e della mappa, più l'apertura di sessione di Ordina e della mappa | **un solo secchio** da 120 al minuto per IP (`_ip_answer_limited`), condiviso da tutte queste rotte. Per le risposte c'è in più `_SID_ANSWERS_PER_MIN` (45) al minuto per sessione firmata (`_answer_rate_limited`) |
| Indovina la Provincia (`daily` e `guess`) | 60 al minuto per IP (`_provincia_rate_limited`) |
| invio alla classifica | 5 al minuto per IP |
| `POST /api/events` (log) | 30 al minuto per IP |

Non hanno limite: `/api/game/guess` e le altre rotte di Indovina la Regione, le due rotte `round` delle serie, `compare/daily/session` e le rotte di sola lettura. Il limite per `sid` non basta da solo, perché chi butta il token ne apre uno nuovo: per questo ci sono tutti e due. Per lo stesso motivo il controllo `token_superato` di Indovina la Provincia, che vive nella cache del processo, con più istanze non è garantito.

**L'IP dietro Cloudflare** (`app/client_ip.py`, `views._client_ip`). Nei log di Cloud Run l'ultimo indirizzo di `X-Forwarded-For` (aggiunto dal frontend di Google e non falsificabile) è sempre un edge Cloudflare, verificato il 30 settembre 2026 su 40 richieste: usarlo darebbe a tutti i giocatori di uno stesso edge un unico limite. La regola: se l'ultimo hop è un IP Cloudflare (`CLOUDFLARE_NETWORKS`, gli intervalli pubblicati, copiati il 30 settembre 2026), il client è quello di `CF-Connecting-IP`, che Cloudflare riscrive. Altrimenti (chiamata diretta a `run.app`, test, locale) il client è l'ultimo hop e `CF-Connecting-IP` non si legge, perché lo potrebbe aver scritto chiunque. Se Cloudflare aggiunge un intervallo nuovo, un edge nuovo cade nel secondo caso: il limite torna condiviso, non aggirabile. Gli intervalli si ricontrollano ogni tanto contro `https://www.cloudflare.com/ips-v4` e `ips-v6`. Fuori da Cloud Run (`K_SERVICE` assente) l'IP è quello della connessione.

Cosa non c'è, e va detto se qualcuno lo chiede: nessun CAPTCHA, nessuna impronta del browser, nessuna prova di umanità oltre il tempo di risposta. Sono scelte, non dimenticanze.

## Punteggi e serie

Le tabelle sono in `app/models.py` e le migrazioni in `migrations/versions/`. `daily_scores` e `quiz_answered` sono della `0010_quiz_monouso_punteggi`, `daily_counter` della `0011_daily_counter`. Le tabelle dell'account (`player_stats`, `daily_results`, `achievements`) e `scores` sono precedenti. La RLS sta in `scripts/supabase_setup.sql` e va rieseguita a mano ogni volta che una tabella cambia (`DEPLOY.md`): le tre tabelle nuove sono solo del backend, senza policy per il browser.

| Tabella | Che cosa contiene | Chi la scrive |
| --- | --- | --- |
| `quiz_answered` | i round già risposti, `(sid, q)` | `claim_round` |
| `daily_scores` | il punteggio di una sfida del giorno: `(auth_id, gioco, data)`, un solo tentativo | `player_stats.record_daily_score`, solo con un JWT valido |
| `daily_results` | la sfida del giorno di Indovina la Regione: tentativi e vinto | `player_stats.record_daily`, solo la sfida di oggi |
| `player_stats` | gli aggregati per modalità (`compare`, `order`, `daily`) | `record_quiz_answer`, `record_daily` |
| `achievements` | solo gli sblocchi | `achievements.evaluate` |
| `scores` | la classifica delle serie | `leaderboard.submit` |
| `daily_counter` | quante sfide del giorno sono finite, per gioco, data e punteggio | `daily_counter.record` |

Il **nome del gioco** in `daily_scores` e nel contatore dice anche il livello: `indovina` (1 vinto, 0 perso), `provincia` e `provincia_regione` (1 o 0: i due livelli sono sfide diverse), `compare` (risposte giuste), `order` (posizioni giuste), `mappa`, `mappa_regione`, `mappa_elenco` (punti). Si scrive per un account solo se ha il token valido e solo a partita finita: Chi è maggiore **solo con il timer acceso**, la mappa solo se la sessione è plausibile, e tutte con il `try` suo: un punteggio non scritto non deve far cadere la risposta. Prima la tabella, poi i traguardi: "Giro d'Italia" e "Fedele" devono vedere il punteggio di oggi. Una partita di allenamento o di archivio di Regione **non** entra nello storico (`views.game_guess_api` ammette solo `daily:<oggi>`), e un secondo risultato dello stesso giorno non sovrascrive il primo.

### La serie: due definizioni, e chi usa quale

1. **`player_stats.play_streak`**: i giorni di fila in cui l'account ha giocato **almeno una sfida del giorno di qualunque gioco**. Un giorno di riposo è automatico: la serie continua se fra due giorni giocati manca un solo giorno, e quel perdono si usa al massimo una volta ogni `REST_EVERY_DAYS` giorni. La serie conta i giorni giocati, non quelli perdonati, e vale ancora se l'ultimo giorno giocato è oggi o ieri. Legge `daily_results` e **tutte** le righe di `daily_scores` (quindi anche mappa e `provincia_regione`: nel suo docstring si dice "quattro sfide", ma il codice non filtra). La usano `fedele`, il profilo (`stats.play_streak` di `GET /api/player/me`) e l'hub.
2. **`player_stats._daily_streaks`**: le **vittorie** di Indovina la Regione in giorni consecutivi, senza riposo. È `stats.daily.current_daily_streak` e `max_daily_streak`, e la usa `daily_streak_7`. Il vecchio `max_daily_streak` salvato nella riga è un dato storico (vittorie di fila di prima, non giorni) e si espone a parte come `historic_best_streak`.

La serie non si salva mai come valore unico: si ricalcola dai giorni a ogni lettura, così chi rientra dopo un giorno non la trova azzerata a metà.

**Il client ha la sua copia**, per chi non ha un account. `playStreak` in `frontend/src/game/oggi.js` ricalcola la prima definizione dai giorni giocati su quel dispositivo (chiavi `di-oggi:<gioco>:<ISO>` nel `localStorage`, scritte da `segnaGiocata` a fine partita, lette da `statoOggi` e `serieLocale`). La serie di sole vittorie di Regione ha la sua nel client, `guess/serie.js`, e rispecchia la seconda. **Le due copie di `play_streak` si provano sugli stessi vettori**, `tests/fixtures/play_streak_cases.json`, letti da `tests/integration/test_player_stats.py` e da `oggi.test.mjs`: se cambi la regola, cambi i vettori e passano tutte e due, altrimenti server e browser danno numeri diversi alla stessa persona.

### I traguardi

Il catalogo è dichiarativo e vive nel codice (`achievements.CATALOG`): ogni voce ha un criterio, una funzione pura sugli aggregati di `player_stats.stats_map`. Il database conserva solo gli sblocchi, quindi un traguardo nuovo o un criterio ritoccato non vuol dire migrazione. Si valutano a fine partita (`achievements.evaluate`) e arrivano nella risposta del gioco. La valutazione è tollerante: se il database non risponde, nessuno sblocco e la risposta non cade. **Solo con un account**: i traguardi non hanno un secondo percorso non fidato nel browser. Alcuni hanno una soglia e un progresso (`PROGRESS`), che la vetrina mostra. Le icone sono SVG (`app/static/img/gioco/traguardi/<id>.svg`) e il catalogo conserva anche l'emoji (`icon`).

Quali guardano le sfide del giorno: `daily_solver`, `daily_streak_7` (la serie di Regione, la seconda definizione), `fedele` (`LOYAL_DAYS` giorni di gioco, la prima), `geografo` e `giro_ditalia`. Quest'ultimo vuole le sfide del giorno risolte di **quattro** giochi nello stesso giorno (`DAILY_GAMES`): non c'è la mappa, che è arrivata dopo. E vale solo il livello difficile della Provincia (`provincia`, non `provincia_regione`): il livello facile svela la regione. `first_correct` guarda la prima risposta giusta in assoluto, quindi arriva anche da Chi è maggiore e da Ordina.

## Il fatto "da portarti via"

A fine partita Chi è maggiore e Ordina dicono una frase vera sul dato (`app/game_facts.py`, la guida completa è nel docstring del modulo). Il contratto, che il client legge in un punto solo (`campoFatto`, `fattoPresentabile`):

- **Il campo si chiama `fact`**, è una stringa e c'è **solo a fine partita**: in Chi è maggiore dentro `summary` (e `summary.fact_path` col link della scheda di quel fatto), in Ordina in cima al risultato della risposta. Che manchi prima della fine lo garantisce la forma del payload, non un'attesa.
- **Se una regola non è soddisfatta il campo manca**: meglio nessuna frase che una falsa. Una frase sola, al massimo `MAX_LEN` caratteri, un solo punto finale, mai `;`, trattini lunghi, puntini o "n.d." (`validate`: se la guardia fallisce si torna a niente, **mai si tronca**).
- **Parte dall'errore del giocatore** se ne ha fatto uno, altrimenti dal caso più distante. In Chi è maggiore il server non ricorda le coppie sbagliate in una tabella: la prima coppia sbagliata (con una scelta vera, un tempo scaduto non conta) va nel token firmato come indice (`sfida.e`, `signed_error`) e la coppia si ricostruisce dalla sfida del giorno.
- **I numeri vengono dai valori che la risposta già porta**, mai da una fonte esterna, scritti come li scrive il sito (`app/design/numfmt`).
- **"Volte" solo se regge**: valori tutti positivi, rapporto grezzo almeno `TIMES_THRESHOLD`, il più piccolo almeno `SMALL_THRESHOLD` della mediana, mai su un saldo. Un'unità percentuale dice sempre lo scarto in punti percentuali.
- **Il piazzamento ("18ª su 20")** solo con direzione dell'indicatore nota, copertura completa, stesso anno per tutti e graduatoria a pari merito. Per le indagini campionarie (BES, Multiscopo, e tutto il livello provinciale) il numero esatto non si dà: si scrive "fra le ultime cinque" se il territorio vi sta davvero, altrimenti niente.
- **Nessun giudizio**: nessun verbo di causa e nessun "migliore" o "peggiore" dedotto dall'ordine dei numeri. La direzione serve solo al piazzamento.

## La sfida condivisa

Chi finisce una sfida a punteggio (Chi è maggiore, Ordina, la mappa) può condividerla, e chi apre quel link vede "La sfida condivisa: 7 su 10. Riesci a superarla?" e a fine partita il confronto. Il link porta il punteggio nel **frammento** `#sfida=<punteggio>-<numero>`, **non in una query**: una query finisce nei log del server accanto all'IP, e questo gioco non vuole quel dato. Il frammento non parte mai verso il server.

Le regole, in `useSfidaCondivisa`, `leggiSfida` e `Condividi` (`shared.jsx`, `puri.js`):

- Il frammento si valida: il punteggio non supera `MASSIMI_SFIDA` del gioco e il numero è quello della sfida di oggi (dal server, mai dalla data del browser). Un frammento fuori scala o di un altro giorno non fa comparire il riquadro.
- Il punteggio **non è firmato**, quindi il testo non dice mai "un amico ha fatto": è un obiettivo condiviso, non un'attribuzione. Il frammento si toglie dall'URL (`history.replaceState`) alla prima risposta, e il punteggio resta in memoria per il confronto finale.
- Chi ricondivide non ripropaga il punteggio di un altro: `Condividi` toglie sempre un frammento che ci fosse già.
- Gli eventi `challenge_open` e `challenge_finish` non portano il punteggio ricevuto, perché ogni evento finisce anche nel log del server. Nell'evento c'è il confronto (`outcome`) e il tuo punteggio.
- Il testo da condividere non contiene mai un nome di territorio né un valore da indovinare (`testoCondivisione`), e il risultato si mostra con forme e parole, non solo con il colore.

Per un frammento non esiste una rotta né un'anteprima social dinamica.

## Il territorio del giocatore

Sulle schede di regione e provincia c'è un "È la mia" che il sito ricorda **solo nel browser** (`localStorage`, chiave `di:mio`, scritta da `app/static/js/v1.js`): il server non lo vede e la pagina che rende è la stessa per tutti. I giochi lo **leggono e basta**, con lo stesso formato (JSON con `level`, `key`, `name` e per una provincia anche `region` e `regionName`): `territorioMio()` e `useTerritorioMio()` in `shared.jsx`, `parseTerritorioMio` in `puri.js`, che scarta tutto quello che non è nel formato (un livello fuori elenco, una chiave che non è uno slug, un nome con markup, un JSON rotto, un campo in più). Il gioco non scrive mai `di:mio`. Se il giocatore lo cambia in un'altra scheda o nella stessa, l'evento `storage` e l'evento `di:mio` di `v1.js` lo aggiornano. A fine partita lo usano Chi è maggiore, Ordina, la mappa e Indovina la Provincia per dire "C'era anche il tuo territorio" (`trovaTerritorioMio` e `fraseTerritorioMio` in `puri.js`, `territorioMioFra` in `mappa/partita.js`). Una provincia scelta accende anche la sua regione, come fa il resto del sito.

## L'identità del sottomarchio

Il gioco ha un accento suo, `--game-accent` (viola) con la sua famiglia (`--game-*`), e giusto e sbagliato hanno token propri (`--game-right`, `--game-wrong`), separati anche in luminosità e con forma e parola oltre al colore. È un colore di interfaccia e **mai un colore dei dati**. Il movimento ha una scala sua, `--mo-*` (`--mo-fast`, `--mo-base`, `--mo-slow`, `--mo-out`, `--mo-in`), dichiarata in `frontend/src/game/game-base.css`, e **sta solo dentro `prefers-reduced-motion: no-preference`**, senza suono, vibrazione né coriandoli (il tono è quello della Cronaca). Le icone di gioco e di traguardo sono SVG in `app/static/img/gioco/`.

I valori e le regole di contrasto stanno nel posto che possiede l'argomento, `design/v1/SISTEMA.md` (sezione "Il gioco: un sotto-marchio, di proposito"), e si provano con `design/v1/tools/check_tokens.py`. Qui non si ricopiano. Una cosa vale per chiunque scriva CSS di gioco: **mai un colore scritto a mano**, solo token, perché il tema scuro li ridefinisce e un esadecimale cotto tiene quell'elemento sulla palette chiara (è già successo in Ordina).

## Gli eventi

Tutti gli eventi del gioco passano da `trackGameEvent()` in `shared.jsx`, e ognuno porta il parametro `game` (uno di `GIOCHI_EVENTO`: `regione`, `provincia`, `compare`, `order`, `mappa`). `parametriEvento` toglie un valore fuori elenco e l'evento parte lo stesso: una misura incompleta vale più di una persa. La lista degli eventi e dei loro parametri è in `docs/tracking_spec.md` e **non si duplica qui**. Due cose da ricordare: la misura non blocca mai la partita, e un sesto gioco va aggiunto a `GIOCHI_EVENTO`, a `GIOCHI` in `oggi.js`, a `_home_quiz_games` e alla sitemap in `app/views.py`, al JSON-LD `ItemList` di `game_hub.html` (il suo `numberOfItems` è scritto) e a `tests/integration/test_game_pages.py`.

## La Sardegna, i confini e l'attribuzione

**I tracciati e i dati sono quelli in vigore fino al 31 dicembre 2025**, con i confini Istat del 2023: la Sardegna è quella di prima. Dal 1 gennaio 2026 ha un assetto nuovo (due città metropolitane e sei province) e l'Istat conta 110 unità (`game_mappa_page.ISTAT_UNITS_2026`, un fatto dell'Istat che non si ricava dal pool). Per questo le province sarde **compaiono sulla mappa ma non si chiedono mai** (`game_mappa.QUESTION_EXCLUDED_REGIONS`): "Dov'è Sud Sardegna?" chiederebbe una provincia che non esiste più. La frase che lo dice (`game_mappa_page.sardinia_note`, col numero di province preso dal pool) sta nella pagina della mappa.

**L'attribuzione dei confini è un obbligo di licenza** (CC BY 4.0): "Confini delle province: Istat (CC BY 4.0), ridistribuiti da openpolis, semplificati e riproiettati da Divario Italia", con i tre link. Si compone da `sources.PROVINCE_BOUNDARIES` (`game_mappa_page.attribution`) e non si scrive a mano. "Semplificati e riproiettati" è vero: `design/v1/tools/province_map.py` semplifica e proietta i tracciati nel viewBox. Il JSON-LD della mappa dichiara i confini come `isBasedOn` (`game_mappa_page.boundaries_dataset`).

## Che cosa si misura e che cosa no

- **GA4** misura gli eventi di gioco solo con il consenso. Al 1 ottobre 2026, su 90 giorni, c'erano circa 11 utenti con eventi di gioco, 12 `game_finish` da 6 utenti e nessun `game_share`, e nei log di Cloud Run al massimo 4 IP distinti al giorno sulle API di gioco (validazione V1 dell'orchestrazione, fuori dal repository: ricontrollare prima di citarli).
- **Il contatore lato server** (`app/daily_counter.py`, tabella `daily_counter`) nasce da qui: non passa dal browser, quindi conta anche chi ha rifiutato il consenso. Una riga per gioco, data e punteggio con quante sfide finite così, senza account, sessione, IP o identificativo. `record` non solleva mai. Si legge con `bin/py scripts/partite_giocate.py` (`--giorni`, `--gioco`, `--punteggi`, e con `DATABASE_URL` in ambiente legge il Postgres di produzione).
- **Che cosa conta il contatore**: Chi è maggiore, Ordina, Indovina la Provincia (i due livelli) e la mappa (le tre conte). **Indovina la Regione non è contata**: `views.game_guess_api` non chiama il contatore. Chi guarda quel numero per capire quanta gente gioca ha la risposta per quattro giochi su cinque.
- **Che cosa non dice**: non dice quante persone, perché non c'è identificativo e due partite possono essere della stessa persona. Non conta le partite iniziate e non finite, né le serie a round.

## Le cose congelate di proposito

Idee valutate e **non** fatte, con il motivo, perché qualcuno le riproporrà:

- **Una classifica del giorno per Indovina la Regione**: ritirata dalla review del 30 settembre, perché Regione non ha stato di sessione. Chi la rimette deve prima rifare il modello.
- **Classifica per la mappa**: vedi sopra, la risposta è nella pagina.
- **"Hai fatto meglio del X%"** (un istogramma dei punteggi del giorno): taglio deciso il 1 ottobre. Servirebbero almeno una decina di giocatori al giorno, e la misura ne vede da zero a quattro: non scatterebbe mai.
- **Traguardi calcolati sul browser per chi non ha account**, **"La tua settimana"**, una scheda del territorio ricca, il promemoria di calendario (`.ics`), il feed e le notifiche: congelati dalla stessa valutazione: con da zero a quattro giocatori al giorno il problema è arrivare, non restare.
- **L'immagine del risultato** (con Pillow), **la condivisione con un file**, **il "freeze" della serie**: rimandati dopo il primo rilascio.
- **Un sesto gioco, "Più vicino"** (si stima un numero vero, 5 domande al giorno): ondata opzionale, non decisa.
- **Pagine per ogni regione o provincia del gioco**, `FAQPage` o schema `Quiz`, una newsletter, la modalità per le classi: scartati perché sarebbero pagine sottili o promesse senza pubblico. Nessuna variante con le sigle automobilistiche: non sono nel repository.
- **CAPTCHA e impronta del browser**: esclusi per principio, vedi "Anti-barare".

## I rischi noti

Cose vere oggi che non sono state corrette. Non sono un elenco di impegni.

- **Il limite di frequenza e `token_superato` sono per processo.** Con più istanze Cloud Run il limite è più lasco di quanto sembri. È un freno, non un muro.
- **La sessione di Chi è maggiore? porta tutte e dieci le coppie** (indicatore e territori, mai i valori) già all'apertura. Si può quindi guardare la coppia dopo mentre scorre il timer della precedente, e il timer non misura più la sola conoscenza. Per ora conta poco (il punteggio della sfida non ha una classifica pubblica, e la sessione porta già `Avanti` senza richiamare il server), ma se la sfida del giorno avrà una classifica la sessione dovrà mandare solo la domanda 0 e far arrivare le altre con `next`. Decisione della revisione finale del 1 ottobre 2026: non si fa ora.
- **Il fallimento aperto di `claim_round`** (sopra): con la migrazione `0010` mancante il monouso è spento senza un 500 a dirlo, e la classifica delle serie perde la sua difesa.
- **I punteggi del giorno stanno nell'esportazione e nella cancellazione dell'account** (`app/account.py`, tabella `daily_scores`, dal 1 ottobre 2026). Una tabella nuova che porta `auth_id` va aggiunta lì: lo prova `tests/integration/test_account.py`.
- **Indovina la Regione non ha stato di sessione** (sopra): non farci poggiare nessuna classifica.
- **`app/templates/game_provincia.html`** ha la riga di attribuzione dei confini scritta a mano (senza "semplificati e riproiettati") e non ha la frase sulla Sardegna: le due cose vivono composte solo nella pagina della mappa. Andrebbero allineate.
- **iOS non è provato su un dispositivo vero**: il tocco sulle sagome della mappa e il focus da tastiera sono stati verificati con un browser automatizzato, non su un iPhone. La prova su un iPhone vero è un passo manuale di Nello.
- **La pulizia della classifica dopo il deploy** non ha un criterio automatico: le righe nate prima del monouso e del timer lato server vanno guardate a mano (`DEPLOY.md`) e cancellate solo con la conferma di Nello.

## Come si prova

```bash
# test del gioco (a blocchi: la suite intera può cadere, vedi la nota)
bin/py -m unittest tests.unit.test_game_daily tests.unit.test_game_facts \
  tests.unit.test_game_mappa_puro tests.unit.test_game_mappa_pagina_puro \
  tests.unit.test_game_compare_testi tests.unit.test_game_motion
bin/py -m unittest tests.integration.test_game tests.integration.test_game_sicurezza \
  tests.integration.test_game_hub tests.integration.test_game_pages \
  tests.integration.test_game_compare_daily tests.integration.test_game_order_daily \
  tests.integration.test_game_provincia tests.integration.test_game_mappa \
  tests.integration.test_game_mappa_pagina tests.integration.test_game_facts_payload \
  tests.integration.test_leaderboard tests.integration.test_player_stats \
  tests.integration.test_daily_counter

# logica del frontend, senza DOM
cd frontend && node --test

# token di design e link interni
bin/py design/v1/tools/check_tokens.py
bin/py -m unittest tests.unit.test_css_tokens
PYTHONPATH=. bin/py scripts/audit_link_interni.py
```

I test del gioco avvisano nel log che `GAME_SEED_KEY` non è impostata e vanno avanti con la chiave di sviluppo: nei test è voluto.

A mano, su `gunicorn` locale, per ogni gioco: una partita a livello regione e una a livello provincia, tema scuro, `prefers-reduced-motion`, solo tastiera, 390 px senza scorrimento orizzontale. Con l'orologio alle 23:30 UTC la sfida deve essere quella di Roma. In GA4 DebugView (o GTM Preview) `compare_answer` deve produrre un solo invio.

Nota d'ambiente: sulla macchina di sviluppo la suite intera è caduta in segfault a caso, anche su `master`, in punti diversi di codice Python puro (osservato il 30 settembre e il 1 ottobre 2026), e `tests.unit.test_trend_articles_cli` e `test_foto_autore` falliscono perché nel virtualenv manca `requests`. Quando la suite cade, si esegue a blocchi, e il crash non è un difetto del gioco.

## Dove sta il codice

| File | Che cosa c'è |
| --- | --- |
| `app/game_daily.py` | giorno di Roma, seed, finestre di difficoltà, pool dei territori, elenco curato, payload di Chi è maggiore e Ordina, fonti per il JSON-LD |
| `app/game.py` | Indovina la Regione: sfida del giorno, allenamento, archivio, valutazione |
| `app/game_provincia.py` | Indovina la Provincia: indizi, token, valutazione |
| `app/game_compare.py`, `app/game_order.py` | le sfide del giorno di Chi è maggiore e Ordina, valutate dal server |
| `app/quiz.py` | i round a serie (casuali) e la valutazione sui dati regionali |
| `app/game_mappa.py`, `app/game_mappa_page.py` | Dov'è la provincia?: contratto, storia, pagina |
| `app/game_facts.py` | il fatto da portarti via |
| `app/quiz_tokens.py` | token v2, monouso, timer, plausibilità |
| `app/client_ip.py` | l'IP del client dietro Cloudflare |
| `app/player_stats.py`, `app/achievements.py`, `app/leaderboard.py`, `app/daily_counter.py` | serie e statistiche, traguardi, classifica, contatore |
| `app/models.py`, `migrations/versions/0010_*`, `0011_*`, `scripts/supabase_setup.sql` | tabelle, migrazioni, RLS |
| `app/views.py` | rotte delle pagine e delle API, limiti di frequenza, 503 senza chiave |
| `app/__init__.py` | `noindex` della classifica (`_NOINDEX_EXACT_PATHS`) |
| `app/page_types.py` | `/quiz` e `/gioco` hanno `page_type = "game"` |
| `config/game_indicators.csv` | gli indicatori giocabili |
| `frontend/src/game/` | l'interfaccia: `shared.jsx`, `oggi.js`, `puri.js`, `guess/`, `mappa/`, `compare.jsx`, `order.jsx`, `hub.jsx`, `leaderboard.jsx` |
| `design/v1/tools/centroidi_province.py` | genera `app/static/data/province_centroidi.json` |
| `design/gioco/` | il prototipo statico del sottomarchio |
| `scripts/partite_giocate.py` | legge il contatore |
| `docs/gioco/ricerca/` | i rapporti di ricerca (`README.md` dice quali) |

Il repository è pubblico: **le ricette per imbrogliare i giochi non vanno in nessun documento**, né qui né nei rapporti di ricerca. I rapporti che si versionano stanno in [`docs/gioco/ricerca/`](gioco/ricerca/README.md).
