# Revisione avversaria del piano del team editoriale

Prodotta da Codex `gpt-5.6-sol`, effort high, worker Orca, 28 settembre 2026, sulla
prima stesura di `PIANO.md` (commit `8a94de01`).

**Nota del team leader.** Il piano approvato da Nello
(`~/.claude/plans/sequential-seeking-brooks.md`, riportato in `PIANO.md`) accoglie
20 rilievi su 23 così come sono. Diverge in tre casi, per scelta di Nello:
- **11, 12 e 13.** Antigravity e il secondo parere di gpt-oss restano fissi,
  come chiede "largo da subito". Li lancia però un worker Orca, non bloccano,
  e un disaccordo va a Nello senza aprire un altro giro.
- **20.** È accolto nella forma proposta qui: strumenti su rami non uniti, un
  pilota impilato sopra, documenti normativi solo dopo.

## Verdetto

Il piano non è pronto per il pilota. L'obiettivo è corretto, ma il flusso
operativo contiene contratti incompatibili, comandi incompleti e più agenti di
quanti il budget di memoria e quota possa sostenere. La libertà formale promessa
allo scrittore viene inoltre ridotta dal brief e dalla rubrica, che prescrivono
di nuovo contenuti, posizione e ordine delle risposte.

La verifica è stata fatta sul runtime Orca attivo, versione 1.4.215, e su GitHub
CLI 2.101.0. I comandi citati sotto sono stati controllati con il rispettivo
`--help`, non ricostruiti a memoria.

## Rilievi

### 1. Il Gate A è ancora nel runbook dichiarato esatto

**Gravità: bloccante.** Il piano elimina il gate umano iniziale, ma rimanda ai
comandi di `04_orca_github.md`, che impongono `gate-a`, vietano l'avvio prima
dell'approvazione e rimuovono la label solo dopo la decisione.

**Prova:** `PIANO.md:76-79`, `PIANO.md:172-176` e
`04_orca_github.md:9-72`. `gh label list --repo nmaiese/diset-viz` conferma che
`gate-a` esiste ancora e che `run:team` è descritto come prodotto del vecchio
Agent Team.

**Correzione proposta:** eliminare Gate A da documento operativo, issue form e comandi, facendo partire solo indicatori presenti nella lista già approvata da Nello.

### 2. Il dispatcher crea un coordinatore concorrente non previsto

**Gravità: bloccante.** Claude dovrebbe orchestrare il team, ma il primo comando
del flusso usa `scripts/orca_dispatch.py --role worker`, che crea nel nuovo
worktree un altro Codex con prompt e `TASK.md`. Restano quindi due coordinatori,
prima ancora di scout, scrittore e grafico.

**Prova:** `PIANO.md:83-90`, `04_orca_github.md:76-95` e
`scripts/orca_dispatch.py:269-287`.

**Correzione proposta:** creare il worktree indicatore senza agente iniziale e lasciare a Claude coordinatore l'unica regia del run.

### 3. Scrittore e grafico vengono avviati insieme nello stesso checkout

**Gravità: bloccante.** Il testo dice di attendere lo scrittore, ma i due
`worker-start` sono consecutivi e non c'è un `check --wait` fra loro. In Orca
1.4.215 ogni `worker-start` su un worktree esistente crea un nuovo terminale
agente, quindi la sequenza mostrata avvia davvero due mutatori nello stesso
checkout.

**Prova:** `04_orca_github.md:130-165` e
`docs/WORKFLOW_ORCA.md:85-125`. L'output di
`orca-ide orchestration worker-start --help` dice che sui worktree correnti o
esistenti viene creato un terminale agente nuovo se non si passa `--terminal`.

**Correzione proposta:** attendere `worker_done`, riconoscere la delivery e liberare lo scrittore prima di avviare il grafico, oppure usare due child worktree e un'integrazione esplicita.

### 4. Il loop Orca non riconosce le delivery

**Gravità: bloccante.** Il runbook avverte che ogni `check` va processato e
riconosciuto, ma nessun comando della sequenza usa `--ack <deliveryId>`. Orca
ripresenta la stessa delivery finché non viene riconosciuta, quindi il
coordinatore può rileggere un vecchio `worker_done` e non avanzare sul messaggio
successivo.

**Prova:** `04_orca_github.md:155-170`. L'output di
`orca-ide orchestration check --help` dice che il batch FIFO viene ripetuto fino
a `--ack` o alla marcatura dei messaggi come letti.

**Correzione proposta:** inserire dopo ogni attesa un ciclo che processa l'intero batch e richiama `check --ack <deliveryId>` prima di avviare la dipendenza successiva.

### 5. La riparazione nello stesso terminale è incompatibile con il ciclo di vita

**Gravità: importante.** Il piano vuole richiamare lo scrittore nel suo stesso
terminale dopo grafico e review, ma un worker concluso deve essere riusato,
rilasciato o trattenuto. Trattenerlo per tutta la review consuma RAM, mentre
rilasciarlo chiude proprio il terminale che la riparazione presume ancora vivo.

**Prova:** `PIANO.md:90-92`, `04_orca_github.md:168-170` e
`04_orca_github.md:279-304`. Gli output di
`orca-ide orchestration worker-retain --help` e `worker-release --help`
confermano che retain conserva il terminale vivo e release lo chiude archiviando
l'output.

**Correzione proposta:** rilasciare ogni worker concluso e avviare una nuova riparazione nel worktree indicatore con rilievi, SHA e soli path autorizzati.

### 6. Orca non lancia un revisore sulla PR

**Gravità: importante.** Orca 1.4.215 non offre un selettore PR per
`worker-start`. Il comando proposto crea un worktree da `origin/<ramo>` e mette
il numero PR nella spec, senza legare la Dispatch alla head SHA. Un push fra la
risoluzione del ramo e la review può quindi far giudicare un commit diverso da
quello dichiarato.

**Prova:** `04_orca_github.md:196-224`. L'output di
`orca-ide orchestration worker-start --help` ammette selettori di worktree,
issue, branch e path, ma nessun selettore PR.

**Correzione proposta:** risolvere prima `headRefOid` con `gh pr view`, registrarlo nella Task e imporre al revisore di confrontare lo SHA checkout con quello GitHub prima di pubblicare l'esito.

### 7. Il comando per chiedere modifiche fallisce con l'identità unica

**Gravità: bloccante.** Tutti gli agenti usano l'identità GitHub di Nello e il
piano riconosce che GitHub non consente di approvare o chiedere modifiche sulla
propria PR. Il runbook conserva però come percorso normale
`gh pr review --request-changes` quando trova bloccanti.

**Prova:** `PIANO.md:191-196` e `04_orca_github.md:260-276`. L'output di
`gh pr review --help` conferma che `--request-changes`, `--approve` e `--comment`
sono tre azioni distinte.

**Correzione proposta:** usare sempre `gh pr review --comment` con verdetto testuale finché autore e revisore condividono la stessa identità GitHub.

### 8. La PR diventa pronta prima della review agentica

**Gravità: importante.** La sequenza esegue `gh pr ready` e aggiunge `gate-b`
prima di creare il task del revisore. Nello può quindi vedere come pronta una PR
che il controllo indipendente non ha ancora letto.

**Prova:** `04_orca_github.md:196-220` e `PIANO.md:201-202`.

**Correzione proposta:** mantenere la PR draft durante tutte le review agentiche e chiamare `gh pr ready` insieme a `gate-b` solo dopo il verdetto `PRONTA PER NELLO` sullo SHA corrente.

### 9. La PR creata non contiene ciò che il piano promette

**Gravità: importante.** Il piano promette vecchio e nuovo testo affiancati e la
label `run:team` su issue e PR, ma `scripts/orca_review.py` mette nel corpo solo
`TASK.md` e `Closes #<issue>`, senza confronto e senza label.

**Prova:** `PIANO.md:201-202`, `04_orca_github.md:44-54` e
`scripts/orca_review.py:87-94,121-137`. L'output di `gh pr create --help`
conferma che il comando supporta `--body-file` e `--label`.

**Correzione proposta:** far generare allo script un body versionato con testo precedente, testo proposto, evidenze e SHA, aggiungendo `--label run:team` alla creazione della PR.

### 10. Lo stato non vive in un posto solo

**Gravità: importante.** La issue è dichiarata fonte unica, ma fase e decisione
sono distribuite fra commenti issue, commenti PR, label, scheda Orca e `TASK.md`.
È la stessa frammentazione che la ripartenza attribuiva a cinque viste
incomplete.

**Prova:** `PIANO.md:73-75`, `PIANO.md:174-204`,
`04_orca_github.md:341-364` e `git show 9730a3fc:docs/RIPARTENZA.md`, righe
112-122.

**Correzione proposta:** rendere stato e prossimo passo campi canonici della issue e trattare PR, TASK.md e card Orca come prove o viste derivate, senza duplicare il verdetto completo.

### 11. Il secondo parere viola il vincolo dei revisori Orca

**Gravità: bloccante.** Nello ha deciso che ogni revisore nasce da Orca sulla PR
o sulla issue, ma il secondo parere è un modello headless e pubblica un commento
sulla PR. Chiamarlo secondo parere non cambia la sua funzione di revisione.

**Prova:** `PIANO.md:34-37` e `PIANO.md:90-92`.

**Correzione proposta:** eliminare il secondo parere dal percorso normale oppure lanciarlo come worker Orca supervisionato sullo stesso SHA della PR.

### 12. Quattro ruoli diventano una catena di sette passaggi agentici

**Gravità: importante.** Alla squadra richiesta si aggiungono secondo scout,
secondo parere e riparatore, oltre a un coordinatore Codex creato dal dispatcher.
Con tre revisioni possibili una scheda può consumare molti più turni di quelli
che il piano chiama quattro ruoli.

**Prova:** `PIANO.md:71-72`, `PIANO.md:83-92` e
`PIANO.md:197-200`. Il vecchio piano fissava massimo tre agenti e due giri proprio
per contenere il costo, in `git show 9730a3fc:docs/RIPARTENZA.md`, righe 164-194.

**Correzione proposta:** nel pilota usare solo scout, scrittore, grafico e revisore in serie, senza secondo scout fisso né secondo parere automatico.

### 13. La rubrica ricrea i cinque strati che avevano promosso prosa illeggibile

**Gravità: importante.** La nuova review ha undici criteri L, sei criteri S, una
guardia deterministica, un secondo modello che rifà L1 e L2 e infine Nello. Il
fatto che gli esiti non abbiano punti non riduce numero di passaggi, costo o
incentivo a scrivere per il controllo.

**Prova:** `03_diagnosi_qualita.md:407-550`. La diagnosi storica dice che cinque
strati e una rubrica a dieci criteri premiavano il non sbagliare e non il
raccontare, in `git show 9730a3fc:docs/RIPARTENZA.md`, righe 64-83.

**Correzione proposta:** tenere guardia deterministica più una review editoriale con massimo cinque domande e rilievi localizzati, chiamando un secondo parere solo su un disaccordo reale.

### 14. La forma libera è contraddetta da posizione e completezza obbligatorie

**Gravità: importante.** Il brief ha cinque parti in ordine fisso, L1 impone
cinque risposte e colloca le prime due nel lead, S1 pretende tutte le frasi della
fotografia e S2 pretende ogni dimensione segnata sì. Le sezioni possono cambiare
nome, ma il contenuto torna a una scaletta obbligatoria.

**Prova:** `PIANO.md:118-144`, `03_diagnosi_qualita.md:440-452` e
`03_diagnosi_qualita.md:512-519`.

**Correzione proposta:** trasformare fotografia e dimensioni in materiale disponibile e far giudicare al revisore una tesi comprensibile, non presenza e posizione di blocchi predeterminati.

### 15. La rubrica spinge verso un referto tecnico e una prosa a singhiozzo

**Gravità: importante.** Il revisore deve parafrasare ogni paragrafo, enumerare
affermazioni di ogni frase e motivare ogni cifra, poi restituire un oggetto per
criterio. Questa procedura trasforma la lettura in contabilità e irrigidisce lo
scrittore, mentre la guida vieta frasi corte e slegate che sembrano un elenco
travestito.

**Prova:** `03_diagnosi_qualita.md:454-473`,
`03_diagnosi_qualita.md:539-546` e `content/STYLE.md:166-178`.

**Correzione proposta:** chiedere al revisore solo punti di rilettura effettivi con citazione e correzione minima, senza mappe esaustive di paragrafi, frasi e cifre.

### 16. Il contratto dello scout non contiene il lavoro promesso

**Gravità: importante.** Il ruolo promette fonti istituzionali, dato più recente,
chi ne ha scritto, previsioni 2026 ed economia delle regioni in cima e in fondo,
ma il brief ammette da una a tre frasi di contesto. Il costruttore previsto
aggiunge indicatori economici dal catalogo, non una matrice di fonti e non
criteri di accettazione per previsioni e territori estremi.

**Prova:** `PIANO.md:85-87`, `PIANO.md:123-135` e
`PIANO.md:241-247`.

**Correzione proposta:** definire per lo scout una tabella obbligatoria con dato osservato più recente, previsione 2026, economia della regione alta, economia della regione bassa, istituzione, data, URL, citazione e limite d'uso.

### 17. Fonti nuove e previsioni non hanno proprietario né tipo

**Gravità: importante.** La diagnosi impone di aggiungere al registro le fonti
istituzionali mancanti, ma lo scout può scrivere solo sotto `lavoro/<chiave>/` e
nessun passaggio possiede `data/corpus/sources.json`. Inoltre i modelli di
registro dicono che ogni numero viene dal brief deterministico, mentre le
previsioni 2026 sono numeri esterni con data, orizzonte e incertezza diversi dai
dati osservati.

**Prova:** `03_diagnosi_qualita.md:360-380`, `PIANO.md:83-92` e
`content/esempi/README.md:51-59`.

**Correzione proposta:** assegnare al coordinatore la promozione delle fonti nel registro e codificare le previsioni come claim esterni separati con istituzione, data di pubblicazione, orizzonte, territorio e cautela.

### 18. I grafici proposti duplicano il cruscotto

**Gravità: importante.** Il piano vuole costruire andamento nel tempo ed estremi,
ma il contratto vigente vieta nel testo grafici che ridisegnano serie, mappa e
classifica già presenti nel cruscotto. L'audit raccomanda prima tre schede pilota
e poi solo i tipi di grafico resi necessari dalle storie.

**Prova:** `PIANO.md:245-250`, `docs/INDICATOR_PAGES.md:326-375` e
`02_audit_capacita.md:353-366`.

**Correzione proposta:** fare il primo pilota con i due grafici runtime esistenti o senza grafico e implementare poi solo una figura che mostri una relazione assente dal cruscotto.

### 19. Il grafico non ha un contratto di qualità visiva e dati

**Gravità: importante.** Verificare che il grafico si disegni non prova unità,
assi, fonte, anni, valori mancanti, didascalia autonoma, resa mobile, tema scuro
o accessibilità. La PR separata di un nuovo tipo crea inoltre una dipendenza non
ordinata, perché il marcatore della PR contenuto può sparire finché il codice non
è stato fuso.

**Prova:** `PIANO.md:89`, `PIANO.md:245-250`,
`02_audit_capacita.md:217-282` e `docs/INDICATOR_PAGES.md:361-375`.

**Correzione proposta:** richiedere una spec per figura con provenienza, unità, anni, missing data, caption, viewport 375 e 768, temi chiaro e scuro, poi fondere per prima la PR del renderer e ribasare la PR contenuto.

### 20. I cantieri sono nell'ordine sbagliato

**Gravità: importante.** Il piano aggiorna subito i documenti normativi, usa il
nuovo flusso per tre PR di codice e crea skill di ruolo e issue form solo al
quinto passo. Descrive quindi come attivo un processo non ancora eseguibile e
pretende di collaudarlo senza gli strumenti che ne definiscono i ruoli.

**Prova:** `PIANO.md:210-254`. Lo stesso piano riconosce il rischio di documentare
una guardia inesistente in `PIANO.md:227-230`.

**Correzione proposta:** preparare prima issue form, skill minime, brief e guardia su rami non pubblicati, eseguire una canary completa e aggiornare i documenti normativi solo dopo l'esito.

### 21. Il budget RAM non copre i processi previsti

**Gravità: importante.** Il limite dichiarato è coordinatore più due agenti, ma
il flusso aggiunge il coordinatore del dispatcher, trattiene lo scrittore per le
riparazioni, avvia grafico e revisore e può eseguire Antigravity headless. Sul
sistema durante questa revisione 7,8 GiB totali avevano già 3,2 GiB usati e 1,0
GiB di swap occupato.

**Prova:** `PIANO.md:177-200`, `04_orca_github.md:402-416` e output di `free -h`
con `swapon --show` del 28 settembre 2026.

**Correzione proposta:** limitare la canary a coordinatore più un solo worker vivo, rilasciare ogni terminale concluso e registrare RSS e swap prima di ammettere qualsiasi sovrapposizione.

### 22. La quota è misurata dopo, non protetta prima

**Gravità: importante.** Il piano sa che Codex ha sfiorato il 98 per cento,
Hugging Face ha esaurito i crediti e Ollama Cloud ammette una richiesta alla
volta, ma non mette probe, budget di turni o soglia di stop nella sequenza. Il
consumo di quota compare solo fra le metriche finali.

**Prova:** `PIANO.md:91-110`, `PIANO.md:270-286` e
`docs/WORKFLOW_ORCA.md:23-38`.

**Correzione proposta:** eseguire il probe prima della issue, fissare un tetto di turni e un costo massimo per scheda e interrompere senza fallback a catena quando il modello primario non è disponibile.

### 23. Il trigger manuale non ha una procedura di ripresa

**Gravità: importante.** È corretto dire che Orca non ha webhook GitHub, ma il
piano si limita a dire che il team leader osserva e rilancia. Se la sessione di
Claude termina fra push e review non esiste una query canonica per trovare PR,
SHA e Dispatch rimasti in sospeso.

**Prova:** `PIANO.md:206-208` e `04_orca_github.md:308-320`. L'output di
`orca-ide automations create --help` conferma che i trigger ammessi sono preset
temporali, cron o RRULE, non eventi GitHub.

**Correzione proposta:** aggiungere un comando di ripresa che elenca issue `run:team`, PR draft, head SHA e ultima review valida, lasciando l'automazione a eventi fuori dal pilota.

## I tre cambiamenti da fare per primi

1. Riscrivere `04_orca_github.md` come runbook realmente eseguibile, senza Gate A,
   coordinatore duplicato, review sulla propria PR o concorrenza nello stesso
   checkout, includendo ack, release e controllo dello SHA.
2. Ridurre il pilota ai quattro ruoli richiesti in serie, con una guardia e una
   review breve, eliminando secondo scout e secondo parere automatici.
3. Definire prima della canary i contratti mancanti di scout e grafico, poi
   provare una sola scheda senza nuovi tipi di grafico e aggiornare i documenti
   normativi soltanto dopo il risultato.
