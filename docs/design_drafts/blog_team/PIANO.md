# Piano: la redazione degli articoli del blog, un team orchestrato con Orca

Stato: **approvato da Nello il 29 settembre 2026 nelle sue scelte: tema e angolo li sceglie il leader in automatico e Nello rivede solo alla fine nella PR, gli agenti ruotano, il pilota è casa e affitti.** Non c'è ancora codice né skill: l'ordine è quello delle schede indicatore, prima il piano, poi gli strumenti, poi un pilota, poi i documenti normativi.

Sorella di `docs/design_drafts/team/PIANO.md`, che descrive il team per le schede indicatore (approvato il 28 settembre, pilota ter-12 unito). Qui si dice che cosa il blog prende da quel team, e in che cosa deve essere diverso.

## Perché rifarla

Il 29 settembre abbiamo provato la pipeline storica (`docs/WORKFLOW_ARTICOLI_TREND.md`, `scripts/trend_articles/`) su due pezzi, casa e rinnovabili. Il risultato, giudicato da Nello: **corretto e sterile**. I numeri tornavano, `verify` era verde, e i pezzi si leggevano come rapporti di verifica. Il pezzo di confronto, quello sui morti in strada del 23 settembre, ha un aggancio umano, una tesi e un finale che il lettore porta via.

Le cause, misurate quel giorno, sono quattro. Nessuna è il modello.

1. **Il brief chiedeva un tema, non una tesi.** La pipeline sceglie una coppia tema-indicatore (`rank.py`). Un tema non è un'idea: "casa e affitti" non dice niente a cui il lettore possa dare ragione o torto. Lo scrittore ha riempito il vuoto con quello che aveva, i numeri.
2. **La spec chiedeva di provare la tesi.** Ho scritto "metti alla prova le ipotesi" e "cosa non ha retto", e i worker hanno costruito il pezzo intorno al metodo: correlazioni di Pearson e Spearman nel corpo, un riferimento alla "nostra classifica automatica", sezioni che si chiamano "Dove pesa di più" e "Come cambia". Il test di un'ipotesi è materiale per chi coordina e va in "Dati usati", non è la struttura dell'articolo.
3. **Nessun modello di voce.** `content/STYLE.md` dice di scegliere **un** testo da `content/esempi/` prima di scrivere. La spec non lo diceva, e nessun worker lo ha scelto di sua iniziativa.
4. **Un solo giro di controllo, dello stesso tipo.** La guardia (`verify.py`) controlla cifre, link e caratteri. Non vede il senso, il registro, né una regressione. Nel pezzo sulla casa: OpenCode ha riscritto il testo e ha rimesso la frase su Foti che una review aveva appena fatto correggere, e ha lasciato un'espressione volgare ("sborra il bilancio") che `verify` e lo scrittore hanno lasciato passare. L'ha vista chi coordinava.

Cosa ha funzionato e va tenuto: la review di un secondo agente in sola lettura ha trovato in rinnovabili un errore alto vero (una tesi sulle interruzioni del servizio elettrico che cambiava segno cambiando il metodo di calcolo, +0,17 con Spearman contro -0,22 con Pearson), che la guardia non poteva vedere. Le figure, il dossier, la scelta della foto guardando le anteprime e la separazione fra scrivere e controllare sono a posto.

## Che cosa prende dal team degli indicatori

Tutto ciò che è meccanica, quasi tutto ciò che è ruolo.

| pezzo | dal team degli indicatori | nel blog |
| --- | --- | --- |
| Leader | Claude in questa sessione, coordina e non scrive | uguale, e in più **decide l'angolo** (sotto) |
| Stato | sezione `## Stato` nel corpo della issue | uguale |
| Un worktree, una issue, una PR draft per pezzo | sì | uguale, un ramo `nmaiese/blog-<slug>` |
| Worker in serie e rilasciati | scout, scrittore, grafico, revisore | scout, scrittore, grafico con foto, revisore |
| Il brief è materiale, non una scaletta | sì | sì, ma il blog **ha** una tesi, la sceglie il leader |
| Forma libera, titoli-affermazione | sì | sì |
| Revisore in un worktree nuovo, di famiglia diversa dallo scrittore | sì | sì |
| Verdetto `DA CORREGGERE` o `PRONTA PER NELLO`, con lo SHA | sì | sì |
| Tre giri di riparazione al massimo, poi va a Nello | sì | sì |
| Il merge è di Nello, ed è la pubblicazione | sì | sì |

Il runbook meccanico (`docs/design_drafts/team/04_orca_github.md`: issue senza Gate A, worktree senza agente, `worker-start`, `check`, `release`, `ack`, PR draft, revisore in worktree nuovo, ripresa dopo un'interruzione) si riusa senza riscriverlo. Il blog aggiunge un passo davanti, il giorno dei trend, e un cancello sull'angolo.

## Che cosa cambia, e perché è il cuore del piano

### 1. L'angolo lo decide chi coordina, prima dello scrittore

Per una scheda indicatore il brief non dà un angolo, perché la pagina spiega una misura e la notizia sta nei dati. Per il blog **l'angolo è il prodotto**. Il leader lo scrive nel brief in quattro righe:

- **La tesi**, in una frase con cui qualcuno potrebbe non essere d'accordo. Non "la casa pesa di più a Sud", che è un'etichetta, ma "chi rischia con la casa non è una regione, è chi paga un affitto di mercato".
- **Che cosa critica.** Un'affermazione, una politica o una convinzione diffusa **che esiste davvero**, citata alla lettera con URL e data (il titolo di una notizia, la frase di un ministro, il presupposto di un piano). Mai un uomo di paglia.
- **La prova più forte contraria**, e come il pezzo la tratta. Un'opinione sostenuta solo da chi la pensa già così non è un'idea.
- **Che cosa cambia per chi legge**, in parole semplici. È la chiusa del pezzo.

Il giudizio vive nella cornice e nella posta in gioco. Le **cause** vengono ancora solo dalle fonti, con l'istituzione nominata nella frase, come nelle schede.

**Nessun cancello umano prima del pezzo.** Nello rivede una volta sola, alla fine, nella PR. Poiché non c'è più qualcuno che ferma un'idea mediocre prima che diventi un pezzo, l'angolo si protegge in altri tre modi:

- **Due angoli candidati, scelti con il motivo scritto.** Il leader ne scrive due, diversi nella tesi e non solo nelle parole, ciascuno con tesi, bersaglio, prova contraria e chiusa. Sceglie uno e scrive perché, in tre righe. Il candidato scartato resta scritto.
- **Un secondo sguardo indipendente sull'angolo**, prima dello scout. Un worker Orca in sola lettura, di famiglia diversa dal leader, riceve i due candidati e i segnali e risponde a tre domande: il bersaglio esiste davvero alla lettera, la tesi è contestabile e non un'etichetta, la prova contraria è la più forte. Ha potere di veto solo sul bersaglio inventato o sull'uomo di paglia; sul gusto no. In caso di veto, il leader sceglie l'altro candidato o ne scrive un terzo.
- **Tutto è leggibile a fine corsa.** Rosa dei temi, scelta e motivo, i due angoli, il secondo sguardo e le scelte degli agenti stanno nel corpo della PR, in una sezione "Come è stato scelto", così Nello vede da dove viene il pezzo oltre al pezzo.

### 2. Lo scout porta materiale diverso

Lo scout di una scheda cerca il dato recente, le previsioni e i fattori che muovono l'indicatore. Lo scout del blog cerca in più:

- **L'aggancio**: la notizia o la ricerca di questi giorni, con la citazione letterale e la data, e che cosa dicono davvero i protagonisti (la frase esatta di chi fa la politica che si critica).
- **Le affermazioni bersaglio**, alla lettera, con URL aperto.
- **Chi altro ne ha scritto**, e che cosa non ha detto nessuno.
- **Una scena umana**, se c'è: un caso concreto verificabile che il lettore riconosce, come il bambino e l'autovelox del pezzo sulle strade. Se non c'è, "non trovata": non si inventa.

Restano le regole della scheda: una tabella `fonti.md` con istituzione, data, URL aperto, citazione letterale e limite d'uso, "non trovato" invece di riempire, e nessun accesso ai registri di fonti (le promuove il leader dopo il merge).

**Le prove di ipotesi** (correlazioni, robustezza al metodo, confronto fra gruppi) restano un lavoro dello scout, con uno script `derive_*` versionato in `data/derived/`, come oggi. Ma sono **materiale per il leader**, non un pezzo del brief. Il leader decide quale risultato regge la tesi e ne fa **una frase con una cifra**. Un test che fallisce è un'informazione utile al lettore, e diventa un paragrafo di racconto ("si pensa che X, ma i dati dicono che no"), mai una sezione né una tabella di coefficienti. I coefficienti, il metodo e la robustezza vanno in "Dati usati".

### 3. Lo scrittore ha una skill sua, non quella delle schede

`skills/editorial-team/scrittore/SKILL.md` vieta la sezione finale "## Fonti", non conosce `trend`, `dataset`, `external_figures` né i campi della copertina, e produce il frontmatter di una scheda (`h1`, `seo_title`, `level`). `verify.py` del blog richiede tutti i campi del blog. Serve un `scrittore-blog`, da scrivere dopo l'approvazione, che porta dalla skill delle schede:

- nessun accesso al web durante la scrittura;
- le cifre solo dal brief e dalle citazioni di `fonti.md`, scritte come lì;
- un modello di registro da `content/esempi/`, **scelto dal leader e scritto nel brief**, letto e tenuto aperto;
- niente scaletta, titoli che sono affermazioni.

E aggiunge quello che al blog serve:

- **il pezzo di riferimento** (oggi `content/posts/2026-09-23-giovani-morti-in-strada-nord-sud.md`) da leggere per intero, per la struttura: aggancio umano, tesi in una frase, cifra centrale, "che cosa cambia";
- **l'apertura sul significato**, non sulla meccanica; una scala umana per la cifra chiave; un ancoraggio concreto solo;
- **un lessico vietato nel corpo**: "correlazione", "Pearson", "Spearman", "dispersione", "ipotesi", "regge / non regge", "la nostra classifica", qualunque riferimento al dossier o al nostro processo;
- **la lunghezza**: 600-900 parole di corpo, esclusi "Dati usati" e "Fonti". Lo dice il pilota ter-12 (la lettura cieca preferiva la prosa del vecchio testo, più corto) e lo conferma questo giro;
- **le figure**: al massimo tre, ciascuna richiamata dal paragrafo che la precede e che dice una cosa che il testo dice;
- il frontmatter del blog, con `trend`, `dataset` ed `external_figures` già compilati dal leader dove sono calcolati, e il testo di `title`, `seo_title`, `description` scritto da lui.

La skill delle schede resta com'è. Alcune sue parti oggi sono false e vanno corrette a parte (sotto, "Da riparare prima").

### 4. Il grafico non fa funzioni nuove

Come nelle schede: **nessun tipo di grafico nuovo** nel pilota. Si usano i quattro di `figures.py` (`bars`, `extremes`, `lines`, `scatter`), il titolo dice la notizia, l'arancio non è mai un colore dei dati. La differenza col team delle schede è che nel blog i grafici non ridisegnano un cruscotto, quindi la scelta è libera fra i quattro.

La **foto** la sceglie un agente che vede le immagini, perché la pertinenza la decide un occhio. Oggi sono Claude e Antigravity. Il ruolo è il grafico, se è un Claude, oppure lo fa il leader. **Non** si affida a Codex né a un modello gratuito senza vista.

### 5. Il revisore ha domande in più

Le cinque domande del team delle schede restano (aggancio e significato, il perché con fonti, prosa e italiano, cifre che tornano, grafici richiamati). Per il blog se ne aggiungono quattro, che sono i difetti visti oggi:

6. **C'è una tesi?** Il lettore sa riassumere il pezzo in una frase, e il titolo la annuncia? La critica è rivolta a un'affermazione citata alla lettera, non a un uomo di paglia?
7. **Il registro.** Nessuna espressione volgare, nessun gergo statistico o interno nel corpo (lessico vietato), nessun "noi" che parla del nostro processo. Il revisore cerca le parole, non le legge di corsa.
8. **Si può togliere un terzo del pezzo senza perdere un'idea?** Domanda del pilota ter-12, qui obbligatoria.
9. **Regressioni.** Ogni riparazione passa con un elenco delle frasi già corrette, e il revisore controlla che nessuna sia tornata com'era.

Il revisore lavora in due tempi, come oggi: prima legge solo l'articolo (domande 1, 3, 6, 7, 8), poi apre dossier, brief e fonti (2, 4, 5, 9). Il verdetto è `DA CORREGGERE` o `PRONTA PER NELLO`, con lo SHA.

### 6. La riparazione elenca frasi, non intenzioni

La lezione è confermata due volte. Nel pilota ter-12 "correggi i rilievi" ha fatto saltare un rilievo. Oggi OpenCode ha rimesso un errore già corretto. La spec di una riparazione elenca ogni correzione come **la frase da cercare e la frase da scrivere**, e porta una lista delle frasi già corrette che non devono tornare indietro. E **una riscrittura intera, dopo una review, vale un giro nuovo di review**: non si committa una riscrittura senza che un revisore la legga.

### 7. Nessun passo headless

Le skill del team delle schede (`revisore` in particolare) e il suo PIANO prescrivono ancora `opencode run` e `agy -p` in headless per il secondo parere e per il giro web dello scout. Dal 29 settembre una guardia in `~/.claude/settings.json` le nega. **Nel blog ogni modello gira come worker Orca**, e il secondo parere e il giro web sono worker come gli altri (`orca-lancia.sh --agent ... --sola-lettura`). Quei passi del team delle schede vanno corretti a parte.

## Il team: ruoli fissi, agenti a rotazione

Decisione di Nello del 29 settembre: **si suppone che tutti gli agenti siano disponibili, e si ruotano secondo quota e necessità.** Il piano quindi non assegna un agente a un ruolo. Assegna a ogni ruolo **un profilo** (che cosa deve saper fare) e una **regola di scelta**, e il leader sceglie a ogni lancio.

`--attivita` da solo non basta: sceglie il primo agente con quota, ed è per questo che il 29 settembre tre lanci su quattro sono andati a Claude. Per il blog il leader sceglie con `--agent`, guardando lo stato, e scrive la scelta e il motivo nella sezione `## Stato` della issue.

**I ruoli e che cosa richiedono.**

| ruolo | dove | che cosa deve saper fare |
| --- | --- | --- |
| Leader | questa sessione | coordinare, scrivere il brief, decidere sui rilievi. Non si ruota |
| Scout | worker Orca nel worktree del pezzo | web con URL aperti e citazioni letterali, scrivere script `derive_*` |
| Scrittore | worker Orca, stesso worktree, dopo lo scout | italiano discorsivo, seguire un modello di registro, tenere i vincoli di `STYLE.md` |
| Grafico e foto | worker Orca, stesso worktree, dopo lo scrittore | `figures.py`, e **vedere le immagini** per la foto |
| Revisore | worker Orca in un worktree **nuovo** sul ramo della PR | leggere criticamente, verificare le cifre, italiano corretto |
| Secondo parere sul registro | worker Orca, sola lettura | leggere e dire se si legge bene; non bloccante |

**La regola di scelta, uguale per tutti i ruoli.**

1. **Vincoli duri.** Il revisore è di **famiglia diversa** dallo scrittore. Il grafico che sceglie la foto **vede le immagini** (oggi Claude, Antigravity). Uno scout deve avere il web. Un agente senza quota sufficiente nella finestra corrente non si lancia.
2. **Fra gli agenti che passano i vincoli, il meno usato negli ultimi pezzi.** La ripartizione si legge dalle ultime issue, e si registra a ogni lancio. È il modo di non far tornare tutto su un solo modello.
3. **Il ruolo più difficile prende il migliore disponibile.** Lo scrittore è il ruolo che decide la qualità del pezzo: a parità di quota, la sua scelta ha la precedenza.
4. **Una scelta che sorprende si scrive.** Se un agente ruota su un ruolo per cui non è stato provato, il pilota lo dice, così la prova diventa un dato.

**Lo stato degli agenti oggi (29 settembre), da rileggere prima di ogni lancio** con `orca-stato.sh` e `agent-probe.sh`, non da questa riga:

- **Codex** ha circa l'11% della quota settimanale fino al 3 ottobre. Con tutti disponibili rientra a rotazione, ma non come scrittore né revisore finché non risale.
- **Antigravity** chiede il login di Nello. Rientra a rotazione quando il login è fatto; ha dato citazioni letterali 8 su 8 come scout (pilota ter-12).
- **OpenCode** funziona (big-pickle e i gratuiti), ma chiede il permesso fuori dal worktree: gli allegati stanno nel worktree e si prepara un `opencode.json`. Il 29 settembre, come scrittore, ha rimesso un errore già corretto e ha lasciato una volgarità, quindi **non è il primo candidato scrittore**. Come revisore ha trovato rilievi giusti nel pilota.
- **Claude** ha un segfault di Bun noto al primo lancio: si rilancia una volta.

Le prove di ruolo che la rotazione produce vanno annotate in `agents/ruoli.tsv` di dev-tools, dove vivono le quote, non in questo repo.

## Il flusso di un pezzo

1. **Il giorno dei trend.** `collect` e `rank`, fasi 1-3, committati. Il leader legge la classifica e i segnali e **sceglie il tema**, scrivendo la rosa dei tre-cinque migliori con, per ciascuno, l'aggancio (il titolo vero con data), il punteggio e le motivazioni, il rischio (un aggancio debole, un tema già scritto nel mese, un dato che non tiene una storia) e se c'è già un pezzo su `content/posts/`. Sceglie con il motivo scritto. Regola del mese: un tema non torna prima di 30 giorni. Tetto: 8 pagine nuove a settimana, blog e schede insieme. Un aggancio che è una tragedia con una vittima riconoscibile non si usa come appiglio per un tema di dati.
2. **Due angoli candidati e il secondo sguardo.** Il leader apre la issue (`gh issue create --label run:blog`) con la rosa, il tema scelto, i **due angoli** e la scelta motivata, poi lancia il secondo sguardo (sopra). Se non c'è veto parte lo scout. Nessun worker aspetta una risposta di Nello.
3. **Worktree e scout.** Worktree senza agente (`--base-branch origin/master`), poi lo scout. Consegna: `dossier.json` (`scripts.trend_articles.dossier`, con le aree ufficiali Istat da `derive_bes_areas`), `fonti.md`, e le eventuali prove di ipotesi in `data/derived/`. Verifica delle citazioni: si scaricano gli URL e si cerca la stringa normalizzata, con lo script del pilota. Una citazione non ritrovata esce dalla tabella.
4. **Brief.** Lo scrive il leader: la tesi scelta, il bersaglio, la prova contraria, la cifra centrale in scala umana, la scena umana, il modello di registro, le cifre ammesse (**una per idea**), le figure proposte. Se ne pubblica una copia sulla issue.
5. **Scrittore**, poi **grafico e foto**, in serie, rilasciando ogni worker.
6. **Guardia e PR draft.** `verify.py` (riparato) e i test del blog. Il leader controlla a occhio il lessico vietato e il registro, poi apre la PR draft con il trend d'origine, la classifica, le figure, la foto con la licenza.
7. **Revisore** (worktree nuovo, famiglia diversa), con le nove domande. Verdetto sulla PR.
8. **Riparazione** con frasi da cercare e frasi da scrivere, e un nuovo revisore. Tre giri al massimo, poi va a Nello.
9. **`PRONTA PER NELLO`.** Nello legge in locale, gli strumenti sono già pronti per l'anteprima (un gunicorn sul worktree), e unisce.
10. **Pulizia** con `orca_clean.py`, e il leader promuove nel registro le fonti nuove dopo il merge.

Il tetto di quota e RAM del team delle schede vale identico: un solo worker vivo alla volta, controllo della quota prima di aprire la issue, otto GB di RAM in WSL.

## Il tetto sui costi

Un pezzo costa al massimo: uno scout, uno scrittore, un grafico, fino a tre revisori e due riparazioni, più il secondo parere a ogni giro. Nel pilota di oggi la parte cara non è stata il calcolo ma i turni di coordinamento. Il vincolo vero è la rilettura umana: Nello legge il pezzo una volta sola, al termine, più le due scelte iniziali, tema e angolo.

## Da riparare prima (passo 0)

Niente di questo è editoriale, tutto blocca la pipeline così com'è:

1. **`requests` e `pillow` mancano dal venv.** `collect.py`, `photo.py`, `verify.py` e i `derive_*` importano `requests`, e `photo.py` importa PIL: `verify.py` ne dipende perché importa `photo`. Oggi si aggira con `PYTHONPATH=$HOME/.cache/divario-req`. Va dichiarato come dipendenza di sviluppo, o le chiamate HTTP portate a `urllib`, con uno smoke test `--help` su tutti i moduli.
2. **`verify.py` non gira in CI** sui pezzi che dichiarano `trend:`: un pezzo con una cifra fuori dal dossier può restare in `master`.
3. **Il campo `author` delle schede foto** riporta a volte una nota o un URL Flickr. `photo.py` deve estrarre il nome, altrimenti si corregge a mano ogni volta.
4. **`fact-checker`** è citato in `WORKFLOW_ARTICOLI_TREND.md` (4b.5) e non esiste. Lo sostituisce il revisore.
5. **`interest` (pytrends) non è stato lanciato** e la classifica ne ha ridistribuito il peso. È sempre stato il punto più fragile: la fase 2 diventa opzionale, con degrado esplicito scritto nella PR, e non blocca.
6. **Il corpus di fonti** (`data/corpus/`) è uno solo per schede e blog, come dice `pipeline_blog_PROPOSTA.md`: nessun registro parallelo.
7. **Le skill delle schede** (`revisore`, `scout`) prescrivono `opencode run` e `agy -p` in headless, ora vietati.

## Che cosa tengo dalla proposta di ieri (`pipeline_blog_PROPOSTA.md`)

Il documento del 28 settembre proponeva un singolo `blog-writer` che riceve **solo** il dossier, senza web e senza brief, e un rollout in sei passi con revisione umana integrale. È ciò che ha prodotto i pezzi sterili di oggi. Quello che rimane vale:

- **Tengo**: `rank.py` come gate e il tetto di 8 pagine a settimana, la regola del mese, il divieto del prodotto cartesiano, `verify.py` come guardia meccanica sempre attiva e in CI, il corpus di fonti unico, la foto scelta da chi la vede, il degrado esplicito di pytrends, nessuna automazione end-to-end oggi.
- **Sostituisco**: il singolo scrittore senza brief con il team di quattro ruoli, e il divieto di web per lo scrittore, che resta ma diventa "il web lo fa lo scout, con le citazioni verificate".
- **Non adotto**: lo step 2 (un pezzo dell'agent mai pubblicato, fuori da `content/`): è il pilota, con le stesse regole di questo piano.

Il documento vecchio non si cancella. Va marcato "superata da `blog_team/PIANO.md`" quando questo si approva.

## Rischi

| rischio | perché | cosa lo tiene basso |
| --- | --- | --- |
| Angolo mediocre o contro un uomo di paglia | il modello scrive quello che gli si dà, e nessun umano lo ferma prima | due candidati con motivo scritto, secondo sguardo indipendente con veto sul bersaglio inventato, domanda 6 del revisore, sezione "Come è stato scelto" nella PR |
| Il giudizio scivola in una causa non dimostrata | un'opinione è più facile di un dato | le cause solo da `fonti.md`; il revisore ha la domanda 2 e 6 |
| Voce ancora sterile | il modello media | modello di registro scelto dal leader, lessico vietato, tetto di parole, "togliere un terzo" |
| Regressione dopo la riparazione | visto oggi, visto nel pilota | frasi da cercare e da scrivere, lista delle frasi già corrette |
| Quota e disponibilità degli agenti | Codex all'11%, Antigravity senza login | rotazione con vincoli duri, quota letta prima di ogni lancio, scelta scritta nella issue |
| Foto scelta da chi non vede | pertinenza e persone riconoscibili | solo Claude, Antigravity o il leader |
| Il team costa più della scrittura | troppi turni | un worker per volta, tre giri al massimo, tetto per ruolo |

## Da non fare ancora

- **Nessuna cadenza quotidiana e nessuna automazione** che pubblichi: c'è un pilota, poi si vede.
- **Nessun tipo di grafico nuovo.**
- **Nessun pytrends** in bloccante.
- **Nessuna modifica ai documenti normativi** (`CLAUDE.md`, `STYLE.md`, `WORKFLOW_ARTICOLI_TREND.md`) prima dell'esito del pilota.
- **Nessuna skill né strumento scritto** prima dell'approvazione di questo piano.

## Il pilota

Riprodurre **casa e affitti** con la pipeline nuova e confrontarlo alla cieca con la versione di oggi, come si è fatto per ter-12. Il dato è già costruito (dossier, aree Istat, figure, foto), quindi il confronto misura la pipeline e non l'argomento. Lettori ciechi: Claude sonnet, gpt-oss, gemma4. Criterio: l'articolo nuovo vince sulla domanda "quale ti fa venire voglia di leggere fino in fondo", non solo su quella delle fonti; il tempo dalla scelta dell'angolo al verdetto sta sotto le due ore.

La seconda prova è il tema di energia, ma solo se la prima passa.

## Raccomandazione

**Costruire il team, in cinque passi e in quest'ordine: il passo 0 (le riparazioni), le skill dei ruoli, il secondo sguardo sull'angolo al posto di un cancello umano, il pilota su casa, poi i documenti.** Tutto il resto si prende dal team delle schede senza riscriverlo. Il rischio maggiore non è tecnico, è la tentazione di tenere la vecchia pipeline "solo per i trend veloci": produce numeri corretti e nient'altro, ed è proprio ciò che non vogliamo.

## Le decisioni di Nello, 29 settembre

1. **Tema e angolo si scelgono in automatico.** Nello rivede solo alla fine, nella PR. *(Una prima lettura del piano aveva messo due cancelli umani, sul tema e sull'angolo: era un fraintendimento, corretto lo stesso giorno.)* Il rischio che un umano avrebbe fermato è tenuto dal secondo sguardo sull'angolo e dalla sezione "Come è stato scelto".
2. **Nessuna tabella fissa di agenti.** Ruoli con profilo, agenti a rotazione per quota e necessità, vincoli duri e registro della scelta nella issue.
3. **Pilota su casa e affitti**, confrontato alla cieca con la versione del 29 settembre, come per ter-12. Approvato, e parte senza pause per Nello.
