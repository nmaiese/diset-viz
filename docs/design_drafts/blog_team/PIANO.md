# Piano: la redazione degli articoli del blog, un team orchestrato con Orca

Stato: **proposta del 29 settembre 2026, da approvare.** Non c'è ancora codice né skill: l'ordine è quello delle schede indicatore, prima il piano, poi gli strumenti, poi un pilota, poi i documenti normativi.

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

**Cancello sull'angolo, economico.** Il leader propone **due** angoli candidati sulla issue, ciascuno con tesi, bersaglio della critica e prova contraria. Nello ne sceglie uno, o li corregge, con una riga. Costa a Nello dieci secondi e evita l'errore più caro della pipeline, un pezzo intero scritto su un'idea mediocre. È l'unico cancello nuovo: gli altri due, revisore e merge, ci sono già.

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

## Il team, con un agente per ruolo

`--attivita` sceglie il primo agente con quota, ed è per questo che il 29 settembre tre lanci su quattro sono andati a Claude. Per il blog ogni ruolo ha un `--agent` esplicito e un solo ripiego. Fatti di oggi che il piano incorpora:

- **Codex** ha circa l'11% della quota settimanale fino al 3 ottobre: fuori dal percorso critico questa settimana.
- **Antigravity** non parte senza un login che fa Nello a mano (schermata "not signed in"): non è un ruolo finché non c'è il login.
- **OpenCode** funziona (big-pickle), ma chiede un permesso quando esce dal worktree: si mettono nel worktree gli allegati e si prepara un `opencode.json`, oppure si accetta una volta.
- **Claude** ha un segfault di Bun noto al primo lancio: si rilancia una volta.

| ruolo | dove | agente | ripiego |
| --- | --- | --- | --- |
| Leader | questa sessione | Claude | nessuno |
| Scout | worker Orca nel worktree del pezzo, con web | Claude sonnet | OpenCode big-pickle (solo per la pista, le citazioni si verificano scaricando l'URL) |
| Scrittore | worker Orca, stesso worktree, dopo lo scout | Claude opus | Claude sonnet |
| Grafico e foto | worker Orca, stesso worktree, dopo lo scrittore | Claude sonnet (vede le immagini) | il leader |
| Revisore | worker Orca in un worktree **nuovo** sul ramo della PR | OpenCode big-pickle o Antigravity, **mai la famiglia dello scrittore** | Codex se ha quota |
| Secondo parere sul registro | worker Orca, sola lettura | OpenCode gpt-oss:120b o gemma4:31b | nessuno, non bloccante |

Il revisore di famiglia diversa dallo scrittore è la regola già in vigore; con uno scrittore Claude, il revisore è OpenCode o Antigravity. Nel pilota di oggi OpenCode big-pickle ha fatto una riscrittura leggibile ma ha commesso due errori, quindi **la riscrittura non si affida a OpenCode**: OpenCode fa il controllo, non la scrittura del pezzo. Se in un giro Antigravity funziona, entra come secondo revisore.

## Il flusso di un pezzo

1. **Il giorno dei trend.** `collect` e `rank`, fasi 1-3, committati. Il leader legge i segnali e le prime righe, scarta un tema il cui aggancio non regge o che non aggiunge niente a una scheda che c'è già. Regola del mese: un tema non torna prima di 30 giorni, e lo si controlla in `content/posts/`. Tetto: 8 pagine nuove a settimana, blog e schede insieme.
2. **Due angoli candidati.** Il leader apre la issue (`gh issue create --label run:blog`) con i due angoli, la coppia tema-indicatore, il perché oggi, e lo stato. **Nello sceglie.** Senza la scelta non parte nessun worker.
3. **Worktree e scout.** Worktree senza agente (`--base-branch origin/master`), poi lo scout. Consegna: `dossier.json` (`scripts.trend_articles.dossier`, con le aree ufficiali Istat da `derive_bes_areas`), `fonti.md`, e le eventuali prove di ipotesi in `data/derived/`. Verifica delle citazioni: si scaricano gli URL e si cerca la stringa normalizzata, con lo script del pilota. Una citazione non ritrovata esce dalla tabella.
4. **Brief.** Lo scrive il leader: la tesi confermata da Nello, il bersaglio, la prova contraria, la cifra centrale in scala umana, la scena umana, il modello di registro, le cifre ammesse (**una per idea**), le figure proposte. Se ne pubblica una copia sulla issue.
5. **Scrittore**, poi **grafico e foto**, in serie, rilasciando ogni worker.
6. **Guardia e PR draft.** `verify.py` (riparato) e i test del blog. Il leader controlla a occhio il lessico vietato e il registro, poi apre la PR draft con il trend d'origine, la classifica, le figure, la foto con la licenza.
7. **Revisore** (worktree nuovo, famiglia diversa), con le nove domande. Verdetto sulla PR.
8. **Riparazione** con frasi da cercare e frasi da scrivere, e un nuovo revisore. Tre giri al massimo, poi va a Nello.
9. **`PRONTA PER NELLO`.** Nello legge in locale, gli strumenti sono già pronti per l'anteprima (un gunicorn sul worktree), e unisce.
10. **Pulizia** con `orca_clean.py`, e il leader promuove nel registro le fonti nuove dopo il merge.

Il tetto di quota e RAM del team delle schede vale identico: un solo worker vivo alla volta, controllo della quota prima di aprire la issue, otto GB di RAM in WSL.

## Il tetto sui costi

Un pezzo costa al massimo: uno scout, uno scrittore, un grafico, fino a tre revisori e due riparazioni, più il secondo parere a ogni giro. Nel pilota di oggi la parte cara non è stata il calcolo ma i turni di coordinamento. Il vincolo vero è la rilettura umana: Nello legge il pezzo una volta sola, al termine, più le due righe della scelta dell'angolo.

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
| Angolo mediocre o contro un uomo di paglia | il modello scrive quello che gli si dà | due candidati, scelta di Nello, bersaglio citato alla lettera |
| Il giudizio scivola in una causa non dimostrata | un'opinione è più facile di un dato | le cause solo da `fonti.md`; il revisore ha la domanda 2 e 6 |
| Voce ancora sterile | il modello media | modello di registro scelto dal leader, lessico vietato, tetto di parole, "togliere un terzo" |
| Regressione dopo la riparazione | visto oggi, visto nel pilota | frasi da cercare e da scrivere, lista delle frasi già corrette |
| Quota e disponibilità degli agenti | Codex all'11%, Antigravity senza login | un agente per ruolo con un ripiego solo, controllo della quota prima di aprire la issue |
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

**Costruire il team, in cinque passi e in quest'ordine: il passo 0 (le riparazioni), la skill dello scrittore del blog, un solo cancello nuovo (l'angolo), il pilota su casa, poi i documenti.** Tutto il resto si prende dal team delle schede senza riscriverlo. Il rischio maggiore non è tecnico, è la tentazione di tenere la vecchia pipeline "solo per i trend veloci": produce numeri corretti e nient'altro, ed è proprio ciò che non vogliamo.

## Le tre decisioni per Nello

1. **Il cancello sull'angolo.** Due candidati sulla issue, scegli tu, o preferisci che il leader decida e tu legga solo alla fine? Raccomando il cancello: costa dieci secondi e cambia il pezzo.
2. **Un agente per ruolo.** Va bene la tabella (scout e grafico Claude sonnet, scrittore Claude opus, revisore OpenCode o Antigravity, mai la famiglia dello scrittore)? Serve sapere se puoi rifare il login di Antigravity, e se Codex rientra dal 3 ottobre.
3. **Il tema del pilota.** Casa e affitti, per il confronto alla cieca sullo stesso dato? Raccomando sì.
