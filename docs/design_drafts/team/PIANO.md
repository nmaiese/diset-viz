# Piano: la redazione delle schede indicatore, un team orchestrato con Orca

Stato: proposta del team leader, 28 settembre 2026, da approvare. Nessuna riga di
codice o di `content/` cambia finché Nello non dice sì.

Materiale da cui nasce, tutto in questa cartella:

| file | chi l'ha prodotto | modello |
| --- | --- | --- |
| `01_ricerca_esterna.md` | Antigravity, headless | gemini-3.1-pro-high |
| `01b_casi_ai_redazioni.md` | OpenCode, headless | huggingface/zai-org/GLM-5.3-Flash |
| `02_audit_capacita.md` | Codex, worker Orca | gpt-5.6-sol, effort high |
| `03_diagnosi_qualita.md` | Claude, worker Orca | opus, effort high |
| `04_orca_github.md` | Codex, worker Orca | gpt-5.6-sol, effort medium |
| `05_modelli_ruoli.md` | OpenCode, headless | opencode/nemotron-3-ultra-free |
| `06_revisione_avversaria.md` | revisione del piano, più modelli | vedi il file |

## 0. In una riga

Una scheda indicatore alla volta, in un worktree suo, con una issue e una PR:
uno scout prepara numeri e contesto, uno scrittore scrive un pezzo discorsivo
partendo da un brief che spiega prima di contare, un grafico mette nel testo i
grafici che lo illustrano, un revisore lanciato da Orca sulla PR controlla cifre
e leggibilità, e Nello fa il merge.

### Decisioni già prese da Nello, 28 settembre

1. L'oggetto è la **scheda arricchita**: la stessa pagina `/indicatore/...`,
   testo più lungo e discorsivo con i grafici dentro. Non un pezzo del blog.
2. Il primo giro è su una **pagina ad alto traffico** con più dimensioni.
3. Le skill Codex della vecchia catena sono **in quarantena**, già fatto:
   `~/.codex/skills-quarantena/` (`editorial-pipeline`,
   `italian-editorial-quality-gate`). Si rimettono con un `mv`.
4. Gli agenti aprono issue, pushano rami e aprono PR. **Il merge resta di
   Nello**, perché su `master` il merge è la pubblicazione.
5. **I revisori sono sempre agenti lanciati da Orca sulla PR o sulla issue**,
   mai un controllo fatto dentro il worktree di chi ha scritto.
6. **Nessuna sezione predefinita nell'articolo.** Niente definizione, quadro,
   dinamica e limiti come fermate obbligate: il pezzo prende la forma di quello
   che c'è da dire su quell'indicatore. Vedi la sezione 3 bis.

## 1. Perché non rifacciamo il vecchio Agent Team

Il vecchio team di settembre è documentato in `RIPARTENZA.md`, tolto dal repo e
ancora leggibile con `git show 9730a3fc:docs/RIPARTENZA.md`. I numeri:

- 18,6-33,6 dollari a pagina con l'Agent Team, contro 3,9-4,5 della catena
  semplice sullo stesso tipo di pagina
- 21 agent, 10 mai eseguiti, 13 skill, 6 mai invocate, 8.037 righe di prompt
- la pipeline riscritta cinque volte in quattordici giorni
- zero intent approvati: il Gate A umano non è mai stato attraversato, e la
  Routine si fermava per quello
- articoli corretti in ogni cifra e illeggibili, perché il brief era statistica
  descrittiva e cinque strati di verifica premiavano il non sbagliare

Il pilota di oggi ha rifatto in piccolo lo stesso errore: 39 fatti statistici
nel dossier, nessuna riga su che cosa significa il numero per una persona,
nessun modello di registro, e un titolo costruito su Fermo al 358%, che il sito
stesso tiene fra gli estremi non verificati (`UNVERIFIED_EXTREMES` in
`app/seo_titles.py`). Tutti i gate erano verdi. La diagnosi completa è in
`03_diagnosi_qualita.md`.

Da qui cinque regole, che il resto del piano applica.

1. **Il brief spiega prima di contare.** Lo scrittore parte da cinque parti
   scritte in chiaro (sezione 3), non da una tabella di fatti.
2. **Una sola guardia bloccante, deterministica.** Cifre, link, fonti,
   marcatori dei grafici e assoluti tipografici. La leggibilità la giudica il
   revisore con criteri passa/non passa, non una rubrica a punti e non cinque
   strati.
3. **Pochi ruoli, una skill ciascuno, versionata nel repo.** Quattro ruoli più
   il team leader. Niente agent che non girano.
4. **Lo stato sta in un posto solo: la issue GitHub.** Ogni passaggio lascia un
   commento sulla issue, leggibile dal telefono. La scheda Orca del worktree
   dice la fase.
5. **Nessun gate umano all'ingresso.** Il Gate A lo decide il team leader su una
   lista di indicatori che Nello approva una volta sola. Nello può fermare una
   issue commentando, ma il lavoro non aspetta il suo sì per partire. L'unico
   gate umano è il merge.

## 2. Il team

| ruolo | che cosa fa | che cosa consegna | file che possiede | modello primario | ripiego |
| --- | --- | --- | --- | --- | --- |
| **Team leader** | apre la issue, scrive la riga "per una persona normale", lancia e segue i worker, integra, esegue la guardia, committa, apre la PR, lancia il revisore, porta il pezzo a Nello | issue, PR, commenti di stato | `lavoro/<chiave>/TASK.md`, Git | Claude (questa sessione) | nessuno |
| **Scout dossierista** | due metà. La prima è codice, non un LLM: il dossier deterministico. La seconda è ricerca: fonti istituzionali, chi altri ne ha scritto, il dato più recente, anteprime e previsioni 2026, l'economia delle regioni in cima e in fondo, i posti dove cercare il perché | `lavoro/<chiave>/brief.md` (parti 2-5 del brief) e `dossier.json` | `lavoro/<chiave>/` | Claude sonnet, worker Orca, con WebSearch e WebFetch | Codex gpt-5.6-sol medium |
| **Scout, secondo giro web** | la ricerca di "chi altri ne ha scritto" e delle previsioni 2026, in parallelo, su un motore diverso | `lavoro/<chiave>/scout_web.md` | quel file | Antigravity gemini-3.1-pro-high, headless | GLM-5.3-Flash headless |
| **Scrittore** | scrive la scheda in forma `libera`, senza sezioni predefinite, con un solo modello di registro da `content/esempi/`. Quante sezioni, in che ordine, con quali titoli e quanto lungo lo decide il materiale | `content/indicators/<chiave>.md` | quel file | Claude opus high, worker Orca | Codex gpt-5.6-sol high |
| **Grafico** | legge il testo finito, decide quali grafici lo spiegano e dove, inserisce i marcatori, verifica che si disegnino. Se serve un tipo di grafico che il sito non ha, apre una PR di codice separata | marcatori nel testo e, se serve, PR su `app/charts.py` | i marcatori, dopo il passaggio di proprietà dallo scrittore | Codex gpt-5.6-sol high, worker Orca | Claude sonnet |
| **Revisore** | nasce da Orca in un worktree nuovo sul ramo della PR, di un'altra famiglia rispetto allo scrittore. Esegue la guardia, poi la rubrica in due passaggi (testo da solo, poi testo con brief e dossier). Pubblica l'esito sulla PR e sulla issue | commento di review sulla PR, commento sulla issue | niente nel repo | Codex gpt-5.6-sol high, worker Orca su PR | Claude opus, se ha scritto Codex |
| **Secondo parere sul revisore** | ricontrolla che ogni frase citata dal revisore esista e rifà da zero i due criteri dove il giudizio pesa (L1, L2) | commento sulla PR | niente | `ollama-cloud/gpt-oss:120b` headless (una richiesta alla volta, quindi mai due secondi pareri insieme) | `ollama-cloud/gemma4:31b`. GLM-5.3-Flash è fuori fino al rinnovo mensile: il 28 settembre i crediti Hugging Face sono finiti a metà di un lavoro |
| **Riparatore** | è lo scrittore, nel suo stesso terminale: corregge solo i rilievi bloccanti | nuovo commit sul ramo | i soli file indicati | come lo scrittore | come lo scrittore |

Perché questa assegnazione, in breve. La scrittura italiana è il punto dove la
qualità conta di più, e va al modello migliore per la prosa. Il revisore deve
essere di un'altra famiglia, perché un modello rilegge male gli errori che fa
lui stesso. Il codice dei grafici va a Codex. La ricerca web ha due motori
diversi, perché uno scout solo trova quello che il suo motore di ricerca gli
mostra. I secondi pareri costano zero quota a pagamento. Il confronto con la
proposta alternativa di nemotron è in `05_modelli_ruoli.md`.

Dove nemotron propone altro, e perché qui no. Mette lo scout su Codex high: ma
Codex regge già grafico e revisore ed è il ripiego dello scrittore, con una
finestra di cinque ore che il 27 settembre era al 98%, e lo scout è il ruolo che
consuma più turni. Sonnet ha ricerca web nativa e costa meno quota di Opus. Mette
il secondo parere su `ling-3.0-flash-fin-free`, adatto ai refusi ma non a
rifare da zero un giudizio di leggibilità. Concordiamo sul resto: scrittore
Opus, revisore di un'altra famiglia, OpenCode solo in headless, un indicatore
alla volta per la RAM, i modelli Zen gratuiti trattati come banda in più e mai
come percorso critico.

Una nota su Antigravity. In orchestrazione ha oggi quattro difetti misurati:
trust dialog, prompt incollato ma non inviato, `orca-ide` fuori dal `PATH`, e il
prompt che arriva prima che l'interfaccia sia pronta. Finché non sono risolti,
non possiede nessun passaggio critico e lavora solo in headless, con l'output
salvato dal team leader.

## 3. Il brief: che cosa riceve lo scrittore, e che cosa no

Il dettaglio con l'esempio completo sulle carceri è in `03_diagnosi_qualita.md`,
sezione 2. In sintesi, cinque parti in quest'ordine.

1. **Che cosa misura, per una persona normale, in una riga**, con la soglia che
   serve per leggere il numero. La scrive il team leader, una volta per
   indicatore, e la rilegge Nello nella issue.
2. **La fotografia del paese**, tre o quattro frasi calcolate dal codice: com'è
   oggi rispetto alla soglia, da dove viene, chi esce dal quadro e con quale
   cautela. La forma della serie, non solo primo e ultimo anno.
3. **Un solo modello di registro** da `content/esempi/`, scelto per la forma
   della storia, con la riga che dice quale movimento copiare.
4. **Le dimensioni disponibili**, calcolate dal catalogo: genere, età,
   regione e provincia, ripartizione, tempo. Per ciascuna, sì o no a "emerge una
   differenza che vale una frase".
5. **Il contesto dello scout**: da una a tre frasi, ognuna con istituzione, data,
   URL aperto e la frase esatta della fonte. È il posto del perché.

Lo scrittore **non** riceve: le frasi fatte del dossier (`scope`, `reading`,
`caveat`), l'esempio generico "un valore di 20 indica...", la polarità come
giudizio, le cifre di servizio (distanza fra estremi, variazione percentuale di
una percentuale, copertura in frazione), numeri non arrotondati, il gergo
interno, un angolo già deciso, una scaletta.

Le cinque parti sono il materiale, non l'indice dell'articolo. Il brief non
dice in quante sezioni dividere il pezzo né con quali titoli.

## 3 bis. La forma dell'articolo: libera, decisa da quello che c'è da dire

Decisione di Nello del 28 settembre. Oggi 300 schede passano dalle stesse
quattro fermate, definizione, quadro, dinamica, limiti, nello stesso ordine,
qualunque cosa i dati abbiano da dire. ter-12 è una di queste. Il nuovo team non
le usa più.

- **Sempre forma `libera`.** Il meccanismo esiste già ed è in produzione:
  `app/indicator_texts.py`, documentato in `docs/INDICATOR_PAGES.md` ("La forma
  libera"), usato da ter-901. Con una sola sezione `libera` l'articolo è
  esattamente quello che l'autore ha scritto, nel suo ordine, e la pagina non
  compone nessun ruolo mancante. Non serve codice nuovo.
- **La struttura la decide lo scrittore**, dopo aver letto il brief: una
  sezione sola se il pezzo ha un filo solo, quattro se ha quattro cose da dire.
  Un titolo va messo dove il pezzo cambia argomento, non per scandire.
- **Ogni titolo è un'affermazione che la sezione dimostra**, come in ter-901
  ("Il conto si divide fra tutti, non fra chi lavora"). Un titolo che è
  un'etichetta ("Il quadro", "I limiti del dato", "La dinamica") non passa.
- **I limiti stanno nella prosa**, nel punto dove cambiano la lettura di una
  cifra, come nei modelli di `content/esempi/`, non in una sezione di cautele in
  fondo. Un limite che vale per qualunque indicatore non si scrive.
- **La definizione non apre per forza.** Il blocco "Come leggere il dato" la
  pagina lo compone comunque dai metadati, dopo l'articolo. Lo scrittore la
  porta nel testo solo se serve a capire la tesi, e dove serve.
- **Restano fissi solo i pezzi della pagina**, non dell'articolo: il cruscotto
  in alto, il blocco "Come leggere il dato" e l'apparato (fonti, citazione,
  correlati) in fondo. Li compone il template e lo scrittore non li scrive.

Che cosa cambia negli altri ruoli. Il revisore boccia i titoli-etichetta e la
sezione di cautele generiche (criterio aggiunto alla rubrica di
`03_diagnosi_qualita.md`, accanto a L10), e non chiede mai una sezione che
manca. La guardia deterministica non conta le sezioni: blocca solo una sezione
`libera` senza titolo, che oggi il renderer scarta in silenzio.

## 4. Il flusso di un indicatore

I comandi esatti sono in `04_orca_github.md`, sezione 1. Qui la sequenza.

1. **Issue.** Il team leader apre `Indicatore ter-12: <domanda editoriale>` con
   label `run:team`, la riga del brief, i file attesi, i criteri di
   accettazione. Nessun gate: se l'indicatore è nella lista approvata, si parte.
2. **Worktree.** Orca crea il worktree collegato alla issue (`--issue`), dal
   `master` aggiornato. Un indicatore alla volta nel pilota. Due al massimo dopo,
   perché con 8 GB di RAM reggono il team leader e due agenti vivi.
3. **Scout.** Worker Orca sul worktree. In parallelo, il giro web headless di
   Antigravity. Il team leader unisce i due in `brief.md` e lo pubblica come
   commento sulla issue.
4. **Scrittore.** Worker Orca sullo stesso worktree, dopo lo scout. Un solo
   agente che scrive alla volta, come chiede `docs/WORKFLOW_ORCA.md`.
5. **Grafico.** Dopo lo scrittore, sullo stesso worktree, con passaggio di
   proprietà registrato in `TASK.md`. Legge il testo e mette i grafici dove
   spiegano qualcosa.
6. **Guardia e PR.** Il team leader esegue la guardia deterministica, committa
   con un messaggio in italiano, e apre la PR con `scripts/orca_review.py`
   (`Closes #<issue>`).
7. **Revisore.** Orca lo lancia in un worktree nuovo sul ramo della PR
   (`worker-start --worktree new-top-level --base-branch origin/<ramo>`). Pubblica
   l'esito con `gh pr review --comment`: GitHub non permette di approvare né di
   chiedere modifiche sulla propria PR, e tutti gli agenti usano l'identità di
   Nello, quindi il verdetto (`DA CORREGGERE` o `PRONTA PER NELLO`) sta nel
   testo del commento. Il secondo parere si aggiunge come commento.
8. **Riparazione.** Se il verdetto è `DA CORREGGERE`, lo scrittore corregge nel
   suo terminale, il team leader ripassa la guardia e pusha, e Orca lancia **un
   revisore nuovo**, mai lo stesso. Tre giri al massimo, poi il conflitto va a
   Nello.
9. **Nello.** Label `gate-b`, la PR pronta, il vecchio testo accanto al nuovo nel
   corpo della PR. Nello legge, commenta o fa il merge.
10. **Pulizia.** Dopo il merge, `scripts/orca_clean.py` sul worktree e sui
    worktree dei revisori.

Orca oggi non ha trigger su eventi GitHub, solo automazioni a orario: il
revisore lo lancia il team leader dopo `gh pr ready` e dopo ogni push
correttivo.

## 5. Che cosa serve prima del pilota

Cinque cantieri, in quest'ordine. Il 2, il 3 e il 4 sono codice e passano da PR:
li faccio fare a worker Codex, ognuno con la sua issue, il suo worktree e la sua
PR. È anche il primo collaudo del flusso issue-PR-revisore, su un terreno meno
delicato del contenuto.

1. **Documenti allineati** (commit diretto, sono documenti). `INDICATOR_PAGES.md`
   dice ancora "quattro sezioni in ordine fisso" e documenta anche la forma
   libera: va detta una cosa sola, e cioè che le schede nuove sono libere e le
   300 a quattro ruoli restano finché il team non le riscrive. `STYLE.md`
   rimanda alla redazione esterna dismessa: va tolto. `WORKFLOW_ORCA.md` riceve
   la deroga (più ruoli nel worktree di un indicatore, uno che scrive alla
   volta, revisore sempre fuori) e il quarto difetto di Antigravity. Il
   `CLAUDE.md` del repo dice "la pipeline automatica non è attiva" e "non c'è un
   lint della prosa": va aggiornato insieme agli altri file che istruiscono gli
   agenti (`AGENTS.md`, `.claude/rules/`, le istruzioni globali di dev-tools per
   la parte Orca). L'elenco riga per riga è in `07_documenti_da_aggiornare.md`.
   Si scrivono quando il piano è approvato, non prima: un `CLAUDE.md` che
   descrive un flusso non ancora collaudato è lo stesso errore dei documenti
   che oggi descrivono una guardia che non esiste più.
2. **Il costruttore del brief** (`scripts/editoriale/brief.py`, PR). Parte da
   `app/indicator_view.py` e aggiunge quello che al pilota mancava: il conteggio
   sopra la soglia anno per anno, la forma della serie, le dimensioni (fratelli
   per genere da `config/indicator_families.csv`, gemello di livello, ripartizioni
   calcolate), l'avviso sugli estremi non verificati, gli indicatori di contesto
   economico già nel catalogo (`ter-901`, `ter-902`, `ter-13`, `ter-345`), cifre
   già arrotondate nella forma in cui si scrivono.
3. **La guardia deterministica** (PR). Il test che verificava i testi autorati,
   `tests/integration/test_indicator_texts.py`, non esiste più, e i documenti lo
   descrivono ancora come attivo. Va rifatta una guardia sola: cifre contro il
   dossier (confrontando i valori assoluti quando la direzione è detta a parole,
   difetto trovato oggi), link canonici, marcatori dei grafici che si
   disegnano davvero (oggi un marcatore sbagliato sparisce senza errore),
   assoluti tipografici.
4. **I grafici che mancano** (PR su `app/charts.py`). Oggi le schede hanno solo
   dispersione e ritratto. Per spiegare una scheda servono almeno: l'andamento
   nel tempo con la soglia e la media, gli estremi con la soglia, il confronto
   fra dimensioni (donne e uomini sulla stessa misura). Grafici disegnati dal
   sito, quindi sempre aggiornati con i dati e coerenti col tema scuro e con i
   token, non SVG salvati a mano.
5. **Le skill di ruolo e il modello di issue** (commit). `skills/editorial-team/`
   con `scout`, `scrittore`, `grafico`, `revisore`, una pagina ciascuna, e
   `.github/ISSUE_TEMPLATE/indicatore-team.yml`. La rubrica del revisore è
   quella di `03_diagnosi_qualita.md`, sezione 3.

## 6. Il pilota

**ter-12, tasso di disoccupazione.** È fra le cinque pagine con più clic, ha la
dimensione di genere (`ter-175` maschi, `ter-176` femmine), e mette alla prova
tutto quello che Nello chiede allo scout: l'economia delle regioni in cima e in
fondo, il dato recente, le previsioni 2026 di Istat e Banca d'Italia. Il testo
attuale, 636 parole in quattro sezioni, è il termine di confronto: la PR mostra
vecchio e nuovo affiancati.

Il secondo pilota, se il primo passa, è **ter-281, tasso di omicidi**: 266 parole
e due sezioni, la pagina più sottile fra le cinque, con una gemella provinciale.

Dopo tre schede approvate da Nello, e solo allora, si parla di lotti.

## 7. Come sappiamo se funziona

Si misura per ogni scheda, e si scrive nella issue alla chiusura:

- **minuti di Nello** fra PR pronta e merge. Obiettivo: meno di 15
- **giri di revisione**. Obiettivo: al massimo due
- **consumo di quota**: turni per agente, finestra Codex usata, token dove il
  provider li restituisce
- **tempo a orologio** dall'issue alla PR pronta
- **disaccordi** fra revisore e secondo parere
- **lettura cieca**: il vecchio e il nuovo testo di ter-12, senza dire quale è
  quale, a due modelli diversi e a Nello

Regole di stop. Se due delle prime tre schede vengono respinte da Nello, ci si
ferma e si rilegge il brief, non si aggiungono controlli. Se una scheda supera
tre giri di revisione, si ferma quella scheda. Un gate che blocca tutto si
ripara, non si spegne.

## 8. Che cosa non fare ancora

- Non partire con lotti né con più di un indicatore alla volta prima di tre
  schede approvate.
- Non automatizzare con Routine o automazioni Orca a orario: il flusso si
  lancia a mano finché non ha dimostrato di funzionare.
- Non dare ad Antigravity un passaggio critico in orchestrazione.
- Non aggiungere ruoli, agenti o skill oltre ai quattro, finché i quattro non
  producono schede approvate.
- Non toccare `content/` fuori dalle PR del team.

## 9. Domande aperte per Nello

Sono in fondo alla risposta in chat, non qui.
