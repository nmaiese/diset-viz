# Piano per la qualità di scrittura delle pagine indicatore

> **Nota (2026-07-28, ri-architettura).** Questo piano cita gli agenti di stadio
> `indicator-writer.md` e `indicator-reviewer.md`: sono stati **fusi nel
> produttore** (`.claude/agents/producer.md`), che scrive e si rilegge in una
> sessione sola, e `source-scout`/`indicator-hunter` nell'**ammissione**
> (`.claude/agents/admissions.md`). I puntatori qui sotto valgono ancora come
> storia della qualità editoriale, ma la guida di scrittura vive ora in
> `producer.md`. Il resto del piano (rubrica, criteri, audit) e' invariato.

Documento di progetto. Obiettivo unico: portare la prosa delle pagine indicatore
al livello di un giornalista di dati di prima fascia, su **tutti gli agenti della
pipeline che toccano il testo**. Non è un piano di prodotto né di SEO in senso
largo, è un piano di qualità editoriale. Nasce da una richiesta precisa: i numeri
sono corretti ma alla scrittura mancano il tocco umano, l'imperfezione
controllata, il ragionamento ad ampio raggio, gli incroci con altri indicatori
(utili anche per l'internal linking) e la ricerca di fonti secondarie.

È corredato da una ricerca documentata (sezione 3 e appendici). Le raccomandazioni
sono tarate sul nostro codice reale, non generiche: l'audit in sezione 6 dice cosa
esiste già e cosa manca, con riferimenti `file:riga`.

---

## Stato: che cosa è già atterrato

**Questo documento non è più una lista di cose da fare.** Le fasi 1, 2 e 3 sono
implementate, la 4 è implementata nella forma che si è rivelata migliore di
quella proposta qui, e la 2d, che era opzionale, è stata fatta lo stesso perché
costava poco meno di quanto sembrava. Il testo che segue resta come il *perché*
delle scelte, con la ricerca che le sostiene, non come istruzioni da eseguire.

Dove vive adesso ciascuna cosa, che è l'unica riga di questo documento da cui
dipende del lavoro futuro:

| Cosa | Dove vive |
|---|---|
| voce editoriale, imperfezione controllata, tell estesi | [`content/STYLE.md`](../content/STYLE.md) |
| la rubrica a dieci criteri | [`docs/WRITING_RUBRIC.md`](WRITING_RUBRIC.md) |
| il registro delle fonti secondarie | [`docs/SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md) |
| i correlati e la forma del divario | `scripts/indicator_brief.py`, blocco `INDICATORI CORRELATI` |
| la misura meccanica, per articolo e per catalogo | `scripts/prose_lint.py` |
| il segnale `mestiere` nell'ordine di lettura | `scripts/review_queue.py` |
| le guardie sui link interni | `tests/integration/test_indicator_texts.py`, classe `InternalLinksInProse` |
| gli incroci, il linking, la ricerca di fonti | `.claude/agents/indicator-writer.md` (sezione "Cross-indicator links") |
| le verifiche di mestiere e di incrocio | la skill `.claude/skills/indicator-review/`, che revisore e verificatore caricano |
| la voce sulla descrizione in lingua piana | `.claude/agents/indicator-curator.md` |

Nota di manutenzione: i prompt agente sono stati snelliti e ora **puntano**
invece di ricopiare. Le sezioni del writer che il corpo di questo piano cita
con il loro vecchio titolo ("Write like a journalist", "Quotas, not options",
"Hunt your own tells") non esistono piu' come sezioni del prompt: il loro
contenuto normativo vive in `content/STYLE.md`, in `docs/WRITING_RUBRIC.md` e
nella skill `indicator-review`. Il corpo qui sotto resta il *perche'* storico
di quelle scelte, come dichiarato sopra.

I blocchi di testo "pronti" che il piano proponeva sono stati tolti da qui e
messi nei file sopra. Una regola scritta in due posti va fuori sincrono, e questo
progetto ha gia' pagato una volta per averlo fatto (`CLAUDE.md`).

**Il numero di partenza**, misurato il giorno in cui la misura è esistita:
340 articoli su 364 chiudevano un paragrafo con una domanda retorica, 25
usavano il lessico spia, e 6 su 364 linkavano un altro indicatore. Si rilegge con
`python3 scripts/prose_lint.py --summary`, ed è quello il modo di sapere se il
giro successivo è servito.

### Dove il piano è stato cambiato, e perché

Tre scostamenti, tutti in direzione di "misurabile invece di giudicato a naso":

1. **La 2d non è opzionale, è la 2a.** Il piano proponeva di partire dai
   correlati di tema in ordine alfabetico e di rimandare la correlazione
   statistica, perché `app/profiles.py:_percentile_matrix` copre solo la famiglia
   core. Calcolando lo Spearman direttamente sulle serie del catalogo quel limite
   non esiste (BES, Multiscopo ed esterni sono dentro), costa meno di un decimo
   di secondo, e senza di esso il blocco dei correlati non risponde alla domanda
   per cui esiste. Gli otto vicini in ordine alfabetico dicono che cos'altro è
   archiviato lì, non con che cosa questo numero viaggia.
2. **I correlati sono raggruppati per forma del divario, non ordinati per rho.**
   Ordinando per sola correlazione, i primi quattro fratelli dell'occupazione
   femminile erano la fascia 20-64, il tasso di attività, la partecipazione e gli
   over 54, tutti sopra 0,97: lo stesso fenomeno misurato quattro volte. Il brief
   ora separa "stessa mappa", "mappa opposta" e "mappa diversa", avverte sopra
   0,95 e mette i quasi-gemelli in fondo. Il gruppo editorialmente utile è il
   terzo, ed è quello che un ordinamento per rho non avrebbe mai mostrato.
3. **L'harness della fase 4b è uno script, non un agente giudice.** Un giudice
   LLM che assegna la rubrica in cieco misura bene i sei criteri interpretativi e
   costa una run per articolo. I quattro criteri meccanici li conta una regex a
   costo zero su tutti e 364, e sono quelli che marciscono in silenzio. Quindi
   `prose_lint` conta la metà meccanica su tutto il catalogo, la rubrica dichiara
   quali criteri restano a un lettore, e il giudice in cieco resta possibile ma
   non è la strada più corta a un numero che si muove.

Il giudice in cieco, che qui era dato per rimandabile, è stato poi eseguito. Il
lotto è girato per intero, scrittura e rilettura, ed è stato misurato. **Quello
che ha misurato sta nella [Parte seconda](#parte-seconda--il-flusso-dopo-averlo-misurato),
in fondo a questo documento, ed è il piano da cui parte il giro successivo.**
Le sezioni numerate da qui in avanti restano come erano: sono il ragionamento
che ha prodotto la Parte prima, non istruzioni ancora da eseguire.

---

## 0. In breve

Cinque leve, in ordine di rapporto valore/sforzo:

1. **Mestiere nel prompt** (Fase 1). Aggiungere al writer e a `content/STYLE.md`
   le tecniche che oggi mancano: il nut graf, la variazione contro lo stereotipo,
   la digressione controllata, il caveat inline, l'asimmetria strutturale, la
   caccia ai *tell* con una lista italiana di parole-spia, e la regola d'oro
   dell'imperfezione (libertà nella forma, disciplina assoluta sul dato). Solo
   testo, nessun codice. Impatto alto, rischio basso.

2. **Incroci tra indicatori** (Fase 2). La capacità esiste già a metà: la view
   calcola i correlati di tema (`related`/`siblings`) ma il brief li **scarta**.
   Basta inoltrarli nel brief, poi insegnare al writer a citarne 1-3 con un link
   interno canonico e una guardia che verifichi il link. Sblocca sia il
   ragionamento ad ampio raggio sia l'internal linking.

3. **Ricerca multi-fonte** (Fase 3). Un registro di fonti secondarie verificate
   (appendice A) e un passo di ricerca esplicito nel workflow del writer e del
   reviewer, con la disciplina anti-aggregazione (mai una media semplice contro un
   dato nazionale ponderato).

4. **Valutazione** (Fase 4). Una rubrica di qualità a punteggio e un harness
   prima/dopo (lo stesso schema del batch già girato) per misurare i progressi
   invece di giudicarli a naso.

5. **Riconciliazione con le guardie** (trasversale). Ogni tecnica di voce va
   accostata al suo limite di fattualità, così "sii umano" non diventi mai "sii
   meno vincolato".

---

## 1. Obiettivo e perimetro

### Obiettivo
Una pagina indicatore deve leggersi come l'avrebbe scritta un giornalista di dati
esperto: apre su un significato, tiene un filo, collega il numero al quadro
grande, cita con onestà gli indicatori vicini, porta un contesto da fonti reali, e
suona umana nel ritmo e nella struttura. Restando dentro le guardie di fattualità
non negoziabili (solo cifre riproducibili dal brief, niente causa che il dato non
mostra, niente eco del cruscotto, solo fonti verificate).

### Perimetro: quali agenti
La qualità della prosa non vive in un solo agente. Il piano tocca:

| Agente / file | Ruolo nella qualità del testo | Cambia in questo piano |
|---|---|---|
| `indicator-writer` | scrive l'intero articolo | Sì, il grosso (Fasi 1, 2, 3) |
| `indicator-reviewer` | fa rispettare ciò che le guardie non vedono | Sì, nuove verifiche di mestiere, incroci, fonti |
| `indicator-curator` | scrive la descrizione in lingua piana | Sì, la stessa disciplina di voce sulla descrizione |
| `content/STYLE.md` | fonte di stile condivisa (blog + indicatori) | Sì, tecniche positive + tell da evitare |
| `scripts/indicator_brief.py` | l'input da cui parte il writer | Sì, deve portare i correlati |
| `app/indicator_view.py` / `app/profiles.py` | calcolo dei correlati | Opzionale, per la correlazione statistica |
| `indicator-hunter`, `source-scout` | non scrivono prosa d'articolo | No, fuori perimetro |

Nota di sistema (da CLAUDE.md): una regola copiata in due posti va fuori sincrono.
Quindi la voce editoriale ha **una** sede di verità, `content/STYLE.md`, e i prompt
degli agenti puntano lì per le regole di fondo, aggiungendo solo ciò che è
specifico del loro stadio.

---

## 2. Diagnosi: cosa manca oggi

Base empirica: la lettura degli ultimi articoli scritti e il batch prima/dopo su
quattro indicatori (`ter-178`, `ter-12`, `ter-105`, `ter-142`). Il batch ha già
alzato l'asticella (quattro sezioni, incipit sul significato, niente domanda
retorica), ma resta sotto il livello richiesto su cinque fronti.

1. **Manca il "perché conta" come sostanza, non come accenno.** Gli articoli
   descrivono la forma della classifica ma raramente danno alla posta in gioco un
   paragrafo suo (il *nut graf*). Il lettore finisce sapendo com'è distribuito il
   dato, non perché dovrebbe importargliene.

2. **Manca il ragionamento ad ampio raggio.** Ogni articolo vive dentro il suo
   singolo indicatore. Non colloca il numero rispetto a una grandezza vicina, a un
   livello storico, a un altro pezzo del catalogo. È il limite strutturale: il
   brief è mono-indicatore e non offre appigli oltre la serie.

3. **Mancano gli incroci con altri indicatori.** Nessun articolo linka a un
   indicatore correlato, benché il contratto lo chieda
   (`docs/INDICATOR_PAGES.md:109-110`) e la pagina abbia già un blocco "Altri
   indicatori del tema". Il writer non li vede perché il brief non glieli passa.

4. **Manca la ricerca di fonti secondarie.** "Multi-fonte" oggi significa solo una
   citazione esterna in `fonti` quando c'è un claim comparativo. Non c'è un passo
   in cui il writer cerchi contesto e controprove in fonti autorevoli (SVIMEZ,
   Banca d'Italia, Eurostat, CPT, ISPRA, INVALSI...).

5. **Manca il tocco umano.** La prosa è levigata e simmetrica: quattro sezioni
   dello stesso peso, ritmo piatto (bassa *burstiness*), zero digressioni, zero
   caveat inline, zero asimmetria. Sopravvivono *tell* da bot che `STYLE.md` non
   nomina ancora (falsi intervalli, regola del tre, riassunti compulsivi, lessico
   spia). E il rischio speculare: quando si chiede "più umano", un LLM tende a
   diventare sciatto e a inventare.

---

## 3. Cosa dice la ricerca

Sintesi delle quattro ricerche condotte per questo piano. Le fonti complete sono
in appendice B. Qui i risultati che diventano decisioni.

### 3.1 Mestiere e voce umana

Fonti principali: John Burn-Murdoch (Financial Times), Jonathan Stray *The Curious
Journalist's Guide to Data*, ONS content style guide, Our World in Data, Poynter e
Nieman sul nut graf, la voce Wikipedia "Signs of AI writing".

- **La variazione batte lo stereotipo.** Il cervello collassa una distribuzione in
  uno stereotipo (per noi: il Nord-Sud). Il pezzo forte cerca il caso che rompe lo
  stampo. Stray: *"Variation tends to get collapsed into stereotypes."*
- **Il nut graf.** Il giornalismo esplicativo ha un paragrafo dedicato al "e
  allora?", che dà alla posta in gioco un posto fisico invece di lasciarla
  evaporare tra le cifre (Poynter, Nieman Storyboard).
- **Aprire sul significato, non sulla meccanica.** Burn-Murdoch: il titolo deve
  *rispondere* alla domanda del lettore, non descrivere il grafico. *"Text is
  where people's attention goes first."*
- **La scala umana è il significato.** Stray: *"Raw numbers are difficult to
  interpret without comparisons."* Il lettore non guarda se è 4,81 o 4,82, guarda
  cosa significa.
- **La burstiness.** Il segnale più forte del testo da bot è il ritmo piatto,
  frasi tutte della stessa lunghezza. Ma la frase corta è uno strumento raro di
  enfasi, non il default: un paragrafo di frasette secche è un tell speculare.
- **L'imperfezione è nella forma, la verità nel contenuto.** OWID cerca chi è
  *"genuinely obsessed with... the caveats, and honest communication of what the
  evidence actually shows"*: la digressione colta convive con l'onestà, non la
  sostituisce.
- **Non scrivere il numero due volte** (ONS): evitare "quasi la metà (48%)". O
  l'immagine o la cifra, non entrambe incollate.
- **Tassonomia dei tell più fine di STYLE.md** (Wikipedia): falsi intervalli
  ("dal Nord al Sud" quando non è un continuo), regola del tre sugli aggettivi,
  riassunti compulsivi ("Nel complesso"), lessico spia (in italiano: *cruciale,
  panorama, tessuto, plasmare, sottolineare, evidenziare, giocare un ruolo*).

Punto critico emerso: quando si chiede a un LLM di essere umano, sbaglia in due
direzioni, o resta levigato o diventa sciatto e inventa. La difesa è **separare
esplicitamente i due assi** e accostare a ogni tecnica di voce il suo limite di
fattualità.

### 3.2 Ragionamento ad ampio raggio e incroci tra indicatori

Fonti: Our World in Data (articolo sulla partecipazione femminile al lavoro),
Eurostat Statistics Explained, Openpolis, letteratura su correlazione vs causa.

- **Quale indicatore portare dentro.** Non "uno correlato a caso", ma la metrica
  che il lettore userebbe per interpretare la prima, con una relazione documentata
  in letteratura o nella statistica ufficiale. Ruoli chiari: una metrica a monte
  (leva plausibile), una a valle (conseguenza plausibile), un co-sintomo. In un
  atlante, l'incrocio più forte è spesso la **forma del divario**: dire se questo
  indicatore disegna lo stesso Nord-Sud di un altro, o uno diverso.
- **Come formulare il legame.** Scala di intensità crescente, verbo calibrato
  sulla prova che hai:
  1. solo co-occorrenza: "va di pari passo con", "si accompagna a", "è associato
     a", "nelle stesse aree in cui";
  2. regolarità senza prova causale: "tende a", "in genere";
  3. meccanismo ipotetico, marcato come tale: "una possibile spiegazione è", "può
     contribuire a";
  4. nesso causale: "la ricerca trova un nesso causale" solo con uno studio a
     disegno causale citabile.
- **Tre difese anti-correlazione-spuria:** nomina il confondente ovvio (spesso il
  reddito dell'area), usa il verbo giusto, cita almeno un'eccezione al pattern.
- **Massimo 1-3 incroci** in un pezzo da 500-700 parole, oltre diventa una lista.

### 3.3 Internal linking e topical authority (2025-2026)

Fonti: Google Search Central, Ahrefs, Search Engine Land, guide 2025-2026 sui
topic cluster.

- **Anchor text** (Google): descrittiva, concisa, autosufficiente ("leggendo solo
  le parole linkate si capisce dove portano"). Vietati "clicca qui" e "leggi di
  più".
- **Quantità** (Ahrefs): 3-5 link contestuali per articolo, nel corpo e in alto,
  non a tappeto in coda. Test: "questo link aiuta davvero a capire?".
- **Modello hub-and-spoke.** Il core update di giugno 2025 ha rafforzato la
  topical authority. Le pagine tema sono gli hub, le pagine indicatore gli spoke;
  gli spoke linkano lateralmente tra loro e verso l'hub. L'incrocio editoriale del
  punto 3.2 **è** esattamente il link laterale spoke-to-spoke che il modello
  premia.
- **Forma URL** (già regola nostra): solo `/indicatore/<slug>/<acronimo>-<id>`,
  mai `/?indicator=` né `/atlante?indicator=` (`tests/integration/test_url_migration.py`).

### 3.4 Fonti secondarie

Registro completo e verificato in **appendice A** (19 fonti con licenza, ultimo
anno, esempio). La trappola-chiave: **non confrontare mai un aggregato nazionale o
di ripartizione ponderato con la nostra media semplice delle regioni**. Quasi
tutte le fonti autorevoli pubblicano aggregati ponderati, la nostra pagina usa
medie aritmetiche dei valori regionali. I due numeri non sono la stessa grandezza.

---

## 4. Il piano, in fasi

Ogni fase ha interventi concreti e criteri di accettazione. Le fasi sono
ordinabili in modo quasi indipendente, ma l'ordine consigliato è 1, 4, 2, 3
(prima il mestiere e il metro di misura, poi le capacità).

### Fase 1 — Mestiere (solo prompt e stile)

**Cosa.** Aggiungere le tecniche di sezione 3.1 dove vivono le regole di voce.

- In `content/STYLE.md` (fonte condivisa), una sezione **"Imperfezione
  controllata"** e l'ampliamento dei tell da evitare (blocco pronto sotto).
- In `.claude/agents/indicator-writer.md`, sotto la sezione già esistente "Write
  like a journalist", una sottosezione operativa con **quote, non facoltà**: una
  digressione per pezzo, un caveat inline, un nut graf, la caccia ai tell, il
  controllo di burstiness auto-somministrato, il test della lettura ad alta voce
  come passo del workflow.
- In `.claude/agents/indicator-curator.md`, la stessa disciplina di voce applicata
  alla descrizione in lingua piana (oggi la scrive senza queste regole).

**Il testo è stato scritto**, nelle sezioni "Imperfezione controllata" e negli
"Altri tell da evitare" di [`content/STYLE.md`](../content/STYLE.md). Non è
ricopiato qui apposta.

**Criteri di accettazione Fase 1.**
- Un articolo campione contiene un nut graf identificabile, almeno una digressione
  dentro la serie, un caveat inline, sezioni di peso diverso.
- Nessuna delle parole-spia compare nei nuovi articoli.
- La suite resta verde, nessun trattino o punto e virgola vietato.

### Fase 2 — Incroci tra indicatori (capacità + prompt + guardia)

**Cosa.** Sbloccare il ragionamento ad ampio raggio e l'internal linking. Vedi
sezione 6 per il dettaglio tecnico.

- **2a. Inoltrare i correlati nel brief.** `scripts/indicator_brief.py` deve
  aggiungere una sezione "INDICATORI CORRELATI" leggendo `view["related"]` e
  `view["siblings"]` (già calcolati, oggi scartati), sia in `render()` sia nel
  payload `--json`. Per ciascun correlato: nome, `path` canonico, direzione,
  ultimo anno, e (utile) il valore/rango della **stessa regione a fuoco**.
- **2b. Regole di incrocio nel writer.** Blocco pronto (inglese, per coerenza col
  file) con: selezionare 1-3 correlati con relazione documentata e ruolo chiaro,
  la scala causa/associazione, il link interno canonico con anchor descrittiva,
  almeno un link all'hub tematico.
- **2c. Guardia.** Un test in `tests/integration/test_indicator_texts.py` che verifica: ogni
  link interno nella prosa punta a un indicatore esistente, ha forma canonica
  (mai `/?indicator=`), l'anchor non è generica.
- **2d (opzionale). Correlazione statistica.** Oggi i "correlati" sono solo
  stessa-tema, alfabetici, troncati a 8. Una funzione che calcoli i top-N per
  correlazione di Spearman sui vettori regionali (materia prima in
  `app/profiles.py:_percentile_matrix`) darebbe incroci più forti. Da estendere
  oltre la famiglia core (BES, Multiscopo, Eurostat oggi esclusi).

**Il testo è stato scritto**, nella sezione "Cross-indicator reasoning and
internal linking" di `.claude/agents/indicator-writer.md`, insieme alle quote di
mestiere ("Quotas, not options") e alla caccia ai tell.

**Criteri di accettazione Fase 2.**
- Il brief stampa i correlati con path e valore della regione a fuoco.
- Un articolo campione cita 1-3 correlati con link canonici e linguaggio calibrato.
- Il nuovo test fallisce su un link non canonico o su un id inesistente, passa sui
  link corretti.

### Fase 3 — Ricerca multi-fonte

**Cosa.** Dare al writer e al reviewer un passo di ricerca strutturato e un
registro di fonti fidate.

- **3a. Registro in repo.** Portare l'appendice A in un file citabile, es.
  `docs/SECONDARY_SOURCES.md`, che i prompt richiamano. Così il writer non parte
  da una ricerca a freddo ma da un elenco verificato per tema.
- **3b. Passo di ricerca nel writer.** Dopo il brief, prima di scrivere: cercare
  contesto e controprove nelle fonti del registro pertinenti al tema, e per ogni
  claim comparativo verificare l'URL con WebSearch/WebFetch. Regola
  anti-aggregazione esplicita.
- **3c. Reviewer.** Estendere il pattern `esterno` con la disciplina
  anti-aggregazione e la verifica che una fonte secondaria citi il numero giusto
  (non la nostra media semplice spacciata per dato nazionale).

**Il testo è stato scritto**, nei prompt dello scrittore, del revisore e del
curatore, e la trappola è spiegata per esteso in testa a
[`docs/SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md).

**Criteri di accettazione Fase 3.**
- `docs/SECONDARY_SOURCES.md` esiste ed è richiamato dai prompt.
- Un articolo campione porta un contesto da una fonte del registro, con URL
  verificato, senza confusione di aggregazione.

### Fase 4 — Valutazione (rubrica e harness prima/dopo)

**Cosa.** Smettere di giudicare a naso. Una rubrica e un harness ripetibile.

- **4a. Rubrica** (sezione 7), 10 criteri a punteggio 0-2.
- **4b. Harness.** Riusare lo schema del batch già girato (writer e reviewer in
  pipeline su N indicatori, output JSON, nessuna scrittura su file), aggiungendo
  un **agente giudice** che assegna il punteggio della rubrica a "prima" e "dopo"
  in cieco, così il miglioramento è un numero. Salvare i risultati per confronto
  fra iterazioni del prompt.

**Criteri di accettazione Fase 4.**
- La rubrica è scritta e condivisa.
- L'harness produce, per un lotto, punteggio medio prima/dopo e la lista dei
  criteri più deboli, che diventano il lavoro del giro successivo.

### Fase 5 (trasversale) — Riconciliazione con le guardie

Non è una fase a sé ma un vincolo su tutte. La regola, da ripetere accanto a ogni
nuova istruzione di voce: **l'imperfezione è nella forma, la disciplina resta
assoluta sul dato.** Ogni istruzione che chiede calore va chiusa, nella stessa
frase, dal limite ("nulla di questo autorizza una cifra assente dal brief o una
causa che l'indicatore non mostra"). È il pattern che il prompt del writer già usa
bene e che va esteso a ogni aggiunta.

---

## 5. Interventi per agente

| Agente / file | Aggiunte |
|---|---|
| `content/STYLE.md` | Sezione "Imperfezione controllata", ampliamento tell (falsi intervalli, regola del tre, riassunti, lessico spia), "non scrivere il numero due volte" |
| `indicator-writer.md` | Nut graf, quote (una digressione / un caveat inline per pezzo), controllo burstiness, test aloud nel workflow, blocco incroci+linking, passo di ricerca, disciplina anti-aggregazione |
| `indicator-reviewer.md` | Verifiche di mestiere (nut graf assente, tell da bot, numero doppio), verifica link interni (canonici, id esistente, anchor non generica), disciplina anti-aggregazione, verbo causa/associazione calibrato |
| `indicator-curator.md` | La descrizione in lingua piana segue le stesse regole di voce e la stessa disciplina anti-aggregazione |
| `scripts/indicator_brief.py` | Sezione "INDICATORI CORRELATI" (da `related`/`siblings`), con path e valore della regione a fuoco, in `render()` e `--json` |
| `app/indicator_view.py` / `app/profiles.py` | (Opzionale) correlazione statistica per un ranking dei correlati migliore dell'ordine alfabetico |
| `tests/integration/test_indicator_texts.py` | Nuova guardia sui link interni |
| `docs/SECONDARY_SOURCES.md` | Nuovo, il registro fonti (appendice A) |

---

## 6. Nuove capacità di codice (dettaglio tecnico)

Dall'audit del repo, fatto prima di scrivere il codice. Resta come fotografia del
punto di partenza: i riferimenti `file:riga` sono quelli di allora e le righe si
sono mosse, quindi vanno letti come "in questo file, in questa funzione", non
come coordinate. La 6.4 in particolare descrive un buco che adesso è chiuso.

### 6.1 I correlati esistono già, il brief li scarta
- La view li calcola: `app/indicator_view.py:119-126` mette `related` e
  `siblings` nell'output, via `_theme_neighbours` (`:465-474`) e `_theme_siblings`
  (`:477-492`). Ogni correlato porta `{id, name, path, direction, year_max}`.
  `RELATED_LIMIT = 8` (`:76`).
- La pagina li rende già (tabella "Altri indicatori del tema", navigazione
  prev/next in `app/templates/indicator_page.html`).
- Ma `scripts/indicator_brief.py:build_brief` (`:64-102`) usa solo `meta`,
  `levels`, `stats` e **non legge mai** `view["related"]`/`view["siblings"]`.
  L'intervento 2a è quindi piccolo: leggerli e stamparli in `render()`
  (`:137-241`) e nel payload `--json` (`:258-272`).

### 6.2 Il path canonico è già pronto
- `app/sources.py:indicator_url` (`:176-185`) costruisce
  `/indicatore/<slug>/<acronimo>-<id>`. Ma il writer non deve ricostruirlo: ogni
  correlato porta già il campo `path` (attenzione: `app/indicator_view.py:184`
  avverte di riusare `source_meta["path"]`, non ricalcolarlo, perché le famiglie
  troncano lo slug in modo diverso).

### 6.3 La tassonomia per l'internal linking verso l'hub
- `app/taxonomy.py`: `MACRO_AREAS` (`:159-181`), `category_metadata` (`:272-288`)
  danno tre livelli, `source_theme` -> `theme` (categoria pubblica) -> `macro_area`.
  L'hub tematico verso cui linkare esiste già come pagina tema.

### 6.4 La correlazione statistica non esiste, ma la materia prima sì
- `app/profiles.py:_percentile_matrix` produce
  `indicator_id -> {region: percentile}`, vettori regionali confrontabili. Era la
  strada proposta per la 2d, ed è quella che il codice **non** ha preso, perché
  copre la sola famiglia core e avrebbe lasciato fuori BES, Multiscopo ed esterni.
- **Fatto, per un'altra via.** `scripts/indicator_brief.py` calcola lo Spearman
  direttamente sulle serie regionali che `get_atlas_indicator` restituisce per
  ogni famiglia, con i ranghi medi sui pari merito e una soglia minima di regioni
  in comune sotto la quale non risponde. Sull'intero tema costa meno di un decimo
  di secondo, perché il catalogo è già in memoria. L'aritmetica è verificata in
  `tests/integration/test_indicator_brief.py`, che la pinza sia sui casi noti (monotono,
  invertito, pari merito) sia contro il catalogo vero.

### 6.5 API
- `/api/search?q=&theme=` (`app/views.py:249-256`) già filtra per tema, quindi "i
  fratelli di tema" sono ottenibili via API. Non esiste un `/api/indicator/<id>/
  related` né `/api/correlations`. Per la pipeline non serve un endpoint nuovo: il
  brief che porta i correlati (2a) è la via più diretta.

### 6.6 Cosa mancava, e dov'è finito
1. Il brief non porta i correlati (2a). Fatto, blocco `INDICATORI CORRELATI`.
2. Nessuna correlazione statistica (2d). Fatta, dentro il brief, vedi 6.4.
3. Nessuna convenzione/guardia per i link interni in prosa (2b, 2c). Fatte, nel
   prompt dello scrittore e in `tests/integration/test_indicator_texts.py`.
4. Nessun registro fonti in repo (3a). Fatto, `docs/SECONDARY_SOURCES.md`.
5. Nessun harness di valutazione a rubrica (4b). Fatta la metà meccanica,
   `scripts/prose_lint.py`, che gira su tutti gli articoli invece che su un lotto.
   Il giudice in cieco sui sei criteri interpretativi resta da fare.

---

## 7. Rubrica di qualità

Scritta, con i dieci criteri e la scala 0-2, in
[`docs/WRITING_RUBRIC.md`](WRITING_RUBRIC.md). Sotto 14 su 20 l'articolo non è
pronto, e i dieci criteri stanno su quattro assi con un pavimento ciascuno: un
asse sotto il pavimento boccia a prescindere dal totale. Quel file dice anche quali criteri conta uno script e quali restano a un
lettore, che è la parte che questo piano lasciava implicita.

---

## 8. Rischi

- **"Umano" letto come "meno vincolato".** Il rischio numero uno. Mitigazione:
  Fase 5, separare i due assi in ogni istruzione.
- **Correlazione spacciata per causa.** Gli incroci aumentano la superficie del
  rischio. Mitigazione: la scala causa/associazione e l'obbligo del confondente e
  dell'eccezione, più il pattern `causale` che il reviewer già cerca.
- **Aggregazione ponderata vs media semplice.** La ricerca multi-fonte lo
  amplifica. Mitigazione: il blocco anti-aggregazione in tre prompt.
- **Over-linking / cannibalizzazione SEO.** Mitigazione: cap 3-5 link, anchor
  variate, test sui link.
- **Sovraccarico del prompt.** Troppe regole rendono il prompt illeggibile e
  l'agente ne ignora una parte. Mitigazione: le regole di fondo stanno solo in
  `STYLE.md`, i prompt puntano lì e aggiungono solo lo specifico dello stadio.
- **Correlazione statistica su famiglie non-core.** `_percentile_matrix` copre
  solo la famiglia core. Mitigazione: 2d è opzionale, si parte dai correlati di
  tema che coprono tutte le famiglie.

---

## 9. Ordine di rollout ed effort

Stima grossolana, un intervento per volta, ognuno con la sua verifica e la sua PR.

| Ordine | Intervento | Effort | Dipendenze |
|---|---|---|---|
| 1 | Fase 1, mestiere in STYLE + writer + curator | Basso | nessuna |
| 2 | Fase 4a, rubrica | Basso | nessuna |
| 3 | Fase 2a, correlati nel brief | Basso | nessuna |
| 4 | Fase 2b + 2c, incroci nel writer + guardia link | Medio | 2a |
| 5 | Fase 3a + 3b + 3c, fonti | Medio | nessuna |
| 6 | Fase 4b, harness giudice | Medio | 4a |
| 7 | Fase 2d, correlazione statistica | Medio-alto | 2a, opzionale |

Dopo ogni intervento: rigirare l'harness prima/dopo su un lotto e leggere il
punteggio della rubrica. Il piano è iterativo, non un big bang.

---

## 10. Le decisioni, prese

Le quattro domande che il piano lasciava aperte, e la risposta che ha avuto ognuna.

1. **Ambito del primo giro.** Fase 1 più 2 più 3 insieme, non la sola Fase 1. Il
   mestiere nel prompt senza i correlati nel brief chiede allo scrittore un
   ragionamento ad ampio raggio e non gli dà niente su cui farlo, e il risultato
   sarebbe stato una prosa più calda intorno agli stessi contenuti.
2. **Correlazione statistica (2d).** Fatta subito, dentro il brief, sulle serie
   del catalogo invece che su `_percentile_matrix`. Vedi lo scostamento 1 in
   testa a questo documento.
3. **Il registro fonti.** File in repo,
   [`docs/SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md), richiamato dai prompt e
   non ricopiato dentro. Con gli URL verificati uno per uno e la nota sui due
   host che rispondono 403 a una richiesta automatica, che altrimenti un agente
   scarterebbe come fonti inesistenti.
4. **Dove vive la rubrica.** File suo,
   [`docs/WRITING_RUBRIC.md`](WRITING_RUBRIC.md). Dentro il prompt del revisore
   sarebbe invisibile allo scrittore, che è chi deve raggiungerla.

---

## Parte seconda — il flusso, dopo averlo misurato

La Parte prima è stata eseguita e poi messa alla prova su un lotto vero: dieci
articoli scelti tra i più deboli del catalogo, riscritti da dieci agenti in
parallelo, riletti da cinque revisori, e valutati alla fine da due giudici in
cieco che non avevano scritto niente. Questa parte non propone di rifare quel
giro. Propone di riparare le tre cose che quel giro ha mostrato rotte.

**Il criterio di questa parte: non aggiungere niente a ciò che è già misurato
bene.** Lo stadio di scrittura è misurato bene. Tutto il resto no.

### 1. Che cosa ha detto la misura

Il lotto: `ter-130`, `ter-167`, `ter-282`, `ter-285`, `ter-408`, `ter-429`,
`ter-920`, `bes-02IST007-N22`, `bes-06POL012`, `bes-10AMB004`. Nove temi, due
famiglie, quattro indicatori contestuali, un BES a due livelli.

**La misura deterministica**, `scripts/prose_lint.py`, sui tre stadi:

| | prima | scritto | riletto |
|---|---|---|---|
| sezioni scritte | 20/40 | 40/40 | 40/40 |
| parole | 1.517 | 6.998 | 7.392 |
| tell meccanici | 14 | 0 | 0 |
| domande retoriche | 10 | 0 | 0 |
| link interni | 0 | 33 | 33 |
| fonti verificate | 0 | 16 | 16 |

**Il giudizio in cieco**, due giudici indipendenti sulla rubrica a dieci criteri,
versioni presentate come A e B con l'assegnazione alternata:

| | prima | dopo | vittorie della versione nuova |
|---|---|---|---|
| giudice normale | 4,8 / 20 | 19,3 / 20 | 10 su 10 |
| giudice severo | 3,0 / 20 | 18,9 / 20 | 10 su 10 |

Accordo tra i due giudici: 1,2 punti di differenza media su 20, massima 3, e
**tutti i disaccordi sulle versioni vecchie, nessuno sulle nuove**. Il giudice
severo ha verificato tutte e dieci le coppie contro i dati e ha trovato cinque
affermazioni false: tutte e cinque nelle versioni vecchie.

Il salto di scrittura, quindi, è reale, grande e replicato da due misure
indipendenti. Non è quello il problema.

### 2. I tre buchi

**Buco 1. La misura deterministica vale zero sullo stadio che decide la verità.**
Guarda la terza colonna della prima tabella: la rilettura non muove nessuna
metrica. Zero tell prima e zero dopo, 33 link prima e 33 dopo, 16 fonti prima e
16 dopo. In quello stesso stadio i revisori hanno tolto, da dieci articoli su
dieci: un'affermazione geografica falsa, una citazione attribuita a un istituto
che non la fa, una cifra sbagliata di un centesimo, un controesempio che
confermava invece di smentire, "undici posizioni" per dodici, "un punto solo"
per due, "il massimo della serie" per uno di tre anni, un confronto in cui la
popolazione era travestita da fenomeno.

Non è un difetto di `prose_lint`, che fa esattamente quello che dichiara. È il
limite della sua categoria: conta forme, e una affermazione falsa ha la stessa
forma di una vera.

**Buco 2. L'ultimo stadio consegna lavoro che nessuno legge.** I revisori hanno
aggiunto 394 parole. `ter-920` è passato da 699 a 751, e le due frasi in più
sono proprio quelle che correggono l'errore sulle ripartizioni. Nessuno le ha
verificate. È strutturale, non un incidente: l'ultimo anello di qualunque catena
firma da solo.

**Buco 3. La rubrica è satura in alto.** Sei criteri su dieci danno 2,0 a
*entrambi* i giudici sulle versioni nuove. Il criterio 3, filo unico, è quello
che separa meno di tutti. I criteri 5 e 9, incroci e fonti, sono binari nei
fatti: 0,0 prima e 2,0 dopo, senza nessun valore in mezzo, perché misurano
presenza e non qualità.

La rubrica separa perfettamente "scheletro vuoto" da "articolo scritto". È la
distinzione che serviva quando è stata scritta e che tra qualche lotto non
servirà più. Non separa buono da migliore, che è la domanda del giro successivo.

### 3. Gli interventi

Tre, in ordine di valore, più uno che è solo cadenza.

#### 3.1 Un verificatore, il cui unico output è un numero

**Il problema che risolve:** il buco 1, e gratis anche il buco 2.

**Che cos'è.** Uno stadio nuovo, dopo il revisore, che non corregge niente. Legge
il testo **finale** e produce una sola cosa: quante affermazioni ha controllato e
quante il dato smentisce. Non riscrive, non firma, non apre pull request sulla
prosa. Se trova qualcosa, quella diventa una riga di coda per il revisore.

**Perché un agente e non uno script.** La forma di un'affermazione falsa è
identica a quella di una vera, ed è per questo che il buco esiste. Ma l'*output*
può essere strutturato e contabile anche se il giudizio non lo è.

**Il dato che produce**, una riga per run in un file di diario dedicato:

```json
{"data": "...", "lotto": ["ter-130", "..."], "affermazioni_controllate": 47,
 "smentite": 0, "dettaglio": []}
```

**La trappola da evitare, ed è la ragione per cui `affermazioni_controllate` sta
nello schema:** senza quel campo, "zero smentite" e "non ho guardato" sono lo
stesso numero. Un verificatore che non dichiara quanto ha controllato non
misura, rassicura.

**Vincoli.** Non può essere lo stesso agente che ha scritto o riletto quel
lotto. Deve leggere il testo pubblicato, non i draft.

**Criterio di accettazione.** Girato sui dieci appena pubblicati deve dare zero
smentite, girato su dieci articoli migrati e mai riletti deve darne più di zero.
Se entrambi danno zero, il verificatore non funziona e il numero è una bugia.
Questo doppio controllo va eseguito **prima** di credere alla prima cifra che
produce.

**Effort:** medio. È un prompt, uno schema e una riga di diario.

#### 3.2 Ritarare la rubrica dove satura

**Il problema che risolve:** il buco 3.

**Che cosa cambia**, criterio per criterio, e solo dove la misura dice che serve:

- **Criterio 2, nut graf.** Entrambi i giudici notano la stessa cosa: i pezzi
  buoni dicono *quale sistema regge* e quasi mai *quante persone tocca*. Il 2
  deve richiedere la grandezza, non solo la posta in gioco.
- **Criterio 5, incroci.** Oggi misura presenza. Deve misurare scelta: un
  correlato che è lo stesso fenomeno misurato due volte, cioè sopra `rho` 0,95,
  vale 1 e non 2. Il brief già segnala quei casi, quindi il dato per giudicare
  c'è.
- **Criterio 9, fonti.** Stessa correzione: una fonte citata per il numero che il
  cruscotto già stampa vale 1. Il 2 è per il contesto che la serie non può dare.
- **Criterio 3, filo unico.** È quello che separa meno. O il testo del criterio
  chiede qualcosa di più della coerenza fra due sezioni, o va assorbito nel
  criterio 8.

**Criterio di accettazione.** Rigiudicare in cieco gli stessi dieci con la
rubrica ritarata. **Lo scarto fra il migliore e il peggiore dei dieci deve
superare i tre punti.** Oggi è 17-20 per un giudice e 18-20 per l'altro, cioè la
rubrica non li ordina.

**Effort:** basso, è un file di testo. Ma va rimisurato, altrimenti si è solo
cambiata un'opinione.

#### 3.3 Il difetto residuo, già chiuso, e come si è trovato

Vale come metodo più che come intervento. Il segnale che i due giudici hanno
nominato indipendentemente, la stessa quantità detta due volte in due sezioni,
è diventato un controllo in `prose_lint` (`ripetuto`).

**La lezione riusabile:** il modo per far nascere un controllo deterministico
nuovo non è immaginarlo, è leggere che cosa due giudici indipendenti hanno
scritto nella stessa casella. Un difetto che due lettori diversi nominano da soli
è un difetto reale e spesso ha una forma.

**Il contro-esempio, che vale quanto l'esempio.** Ho provato a costruire una
guardia per le affermazioni ordinali, che sono la classe di errore più
frequente fra quelle che i revisori hanno corretto ("undici posizioni" per
dodici, l'eccezione attribuita alla regione sbagliata). Misurata: il frame
sintattico stretto trova 7 occorrenze in 364 articoli, e allargarlo produce
falsi. Gli errori veri erano formulati in modi che una regex non lega al dato.
**Quella guardia non va scritta**, e il fatto che sia stata misurata prima di
scriverla è il motivo per cui non è costata niente.

#### 3.4 L'arretrato, che è solo cadenza

Non serve un meccanismo nuovo. La catena funziona, va fatta girare.

Il catalogo oggi: **326 articoli su 364 chiudono un paragrafo con una domanda
retorica**, e 346 su 364 non linkano nessun altro indicatore. Un lotto da dieci
ha spostato gli articoli con almeno un link da 6 a 18.

A dieci per volta servono circa 35 lotti. La coda che li ordina esiste già
(`scripts.review_queue`), e ordina per rischio e per indicizzabilità, che è
l'ordine giusto: si comincia dalle pagine che qualcuno legge davvero.

### 4. Che cosa non fare

Tre cose che la misura dice esplicitamente di non fare, e vale la pena scriverle
perché sono tutte tentazioni ragionevoli.

- **Non aggiungere altre metriche deterministiche sullo stadio di scrittura.** È
  già misurato da due strumenti indipendenti che concordano, e satura. Ogni
  metrica nuova lì dentro misura una cosa che sappiamo già.
- **Non trasformare `prose_lint` in un cancello.** La sua precisione è alta e la
  sua copertura no, di proposito. Un cancello su un segnale incompleto sposta il
  lavoro dal migliorare la prosa al far tacere il linter, e la parte non coperta
  peggiora senza che nessuno se ne accorga.
- **Non regexare le affermazioni di conteggio e di posizione.** Vedi 3.3: è stato
  misurato, non funziona.

### 5. Rischi

- **Il verificatore che rassicura.** Il rischio numero uno, ed è per questo che
  il criterio di accettazione di 3.1 pretende un falso positivo prima di credere
  a uno zero.
- **La rubrica ritarata che sposta solo la scala.** Se alzare l'asticella porta
  tutti i punteggi da 19 a 15 senza separarli, non si è misurato di più. Il
  criterio è lo scarto interno al lotto, non la media.
- **La saturazione che torna.** Fra qualche lotto anche i criteri ritarati
  satureranno. È il destino di ogni rubrica e va accettato: si ritara di nuovo,
  guardando dove i giudici smettono di essere in disaccordo.
- **Il costo.** Un lotto da dieci sono dieci run di scrittura, cinque di
  rilettura e due di giudizio. Aggiungere il verificatore ne fa una in più, non
  dieci: legge un lotto intero.

### 6. Il debito di curatela trovato per strada

Tre difetti che non sono di scrittura e che nessuno stadio della catena può
toccare, elencati qui perché altrimenti si perdono. Sono decisioni da curatore.

- **`ter-282` ha `direction: lower_better`** mentre l'articolo argomenta che un
  valore basso non certifica niente, perché conta delitti denunciati e quindi
  anche l'attività di contrasto. Il cruscotto stampa "valori più bassi
  raccontano una situazione migliore" sopra un testo che dice il contrario.
  `contextual` sembra il verso giusto.
- **`ter-130` ha l'unità sbagliata nei metadati.** Il catalogo dice `milioni di
  euro`, la definizione Istat stampata sulla stessa pagina dice `migliaia di euro
  concatenati`. La pagina mostra "Unità di misura milioni di euro" e una
  variazione "in milioni di euro" che sono sbagliate di un fattore mille.
- **`ter-167` e `ter-471` sono la stessa serie pubblicata due volte**, 580 punti
  identici su 580, sotto due nomi diversi. Sono due pagine indicatore che
  mostrano gli stessi numeri, ed entrambe entrano nei conteggi del tema.

### 7. Che cosa ha insegnato la messa in opera

Tre difetti trovati non nella prosa ma negli strumenti, tutti dello stesso tipo:
si nascondevano dietro un aggiramento che non lascia traccia.

- **Il `\n` singolo.** Un a-capo semplice dentro un corpo è un a-capo morbido in
  Markdown, quindi la sezione produce un solo `<p>` e si legge come un muro
  unico. Trovato da un revisore che guardava la pagina resa, invisibile nel JSON
  e nel diff. Ora c'è una guardia.
- **`analyst_html` che spoglia il wrapper.** Giusto per il lead, che sta dentro
  un `<p>` già aperto; sbagliato per il corpo delle sezioni, che non ci sta. Una
  sezione di un paragrafo arrivava in pagina come nodo di testo nudo e perdeva la
  spaziatura, su 710 sezioni in 355 articoli. Ora sono due filtri.
- **`review_queue --show` che accettava solo l'id interno.** La forma URL, che è
  quella di ogni altro comando della catena e quella degli esempi nel prompt del
  revisore, rispondeva "nessun articolo" per ogni indicatore. Trovato da un
  revisore che ha aggirato usando il brief.

**La regola che ne esce:** un controllo che ricostruisce quello che deve
verificare non verifica niente. Il primo controllo del revisore sulla pagina resa
non aveva visto il difetto dei paragrafi perché spogliava i tag e risplittava
sulle righe, ricostruendo da sé i paragrafi che il browser non avrebbe mostrato.
Il controllo giusto conta i `<p>` che il filtro emette davvero.

E una nota sull'orchestrazione, che vale per i lotti e non per la catena in
produzione, dove gli stadi girano uno alla volta: **la presenza di un file non è
un segnale di completamento.** Dieci agenti in parallelo scrivono presto e
rifiniscono dopo, e integrare alla comparsa del file ha preso quattro versioni
intermedie su dieci. Il segnale è la chiusura dichiarata dall'agente.

### 8. Ordine consigliato

| # | Intervento | Effort | Dipende da |
|---|---|---|---|
| 1 | 3.1, il verificatore e il suo doppio controllo | Medio | niente |
| 2 | 3.2, ritarare la rubrica | Basso | niente, ma si rimisura con 1 in piedi |
| 3 | 3.4, i lotti dell'arretrato | Alto ma parallelo | 1 e 2, per sapere se stanno funzionando |
| 4 | 6, il debito di curatela | Basso | decisione umana sul verso di `ter-282` |

Il 3 è il lavoro vero e il 1 e il 2 esistono per sapere se il 3 sta andando bene
o male. Farlo nell'ordine inverso significa riscrivere trecento articoli e
scoprire alla fine di non avere un modo di dire se sono migliorati.

---

## Appendice A — Registro delle fonti secondarie

Spostato in [`docs/SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md) e verificato lì,
URL per URL. Non è ricopiato qui: due elenchi di fonti che divergono sono peggio
di uno solo, perché nessuno sa quale delle due versioni ha guardato l'agente.

---

## Appendice B — Fonti della ricerca

Mestiere e voce:
- Burn-Murdoch (FT), From data to storytelling: https://lab.imedd.org/en/from-data-to-storytelling-concept-and-design-tips-from-the-financial-times-john-burn-murdoch/
- Stray, The Curious Journalist's Guide to Data: https://towcenter.gitbooks.io/curious-journalist-s-guide-to-data/content/introduction/
- Wikipedia "Signs of AI writing" (sintesi): https://www.beutlerink.com/blog/how-to-spot-ai-writing
- Burstiness / segnali AI: https://seoengine.ai/blog/signs-of-ai-writing
- Nut graf: https://www.poynter.org/archive/2003/the-nut-graf-part-i/ , https://niemanstoryboard.org/2021/10/20/nut-grafs-or-graphs-how-five-sentences-can-help-a-writer-focus/
- ONS content style guide: https://analysisfunction.civilservice.gov.uk/policy-store/content-style-guide/
- Our World in Data (voce): https://ourworldindata.org/hiring-writer-2026
- The Economist, Off the Charts: https://datajournalism.com/read/newsletters/inside-the-economists-off-the-charts-newsletter

Incroci e internal linking:
- OWID, Female labor force participation: https://ourworldindata.org/female-labor-supply
- Association is not causation: https://rafalab.dfci.harvard.edu/dsbook-part-2/linear-models/association-not-causation.html
- Google Search Central, link best practices: https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- Ahrefs, internal links for SEO: https://ahrefs.com/blog/internal-links-for-seo/
- Search Engine Land, topic clusters: https://searchengineland.com/guide/topic-clusters
- Eurostat, What is Statistics Explained (PDF): https://ec.europa.eu/eurostat/documents/4031688/5930712/KS-32-12-526-EN.PDF

Fonti secondarie: gli URL verificati sono nell'appendice A e nel registro esteso.

---

## Parte terza, la verifica del piano e il piano di esecuzione

La Parte prima e' il ragionamento, la Parte seconda e' quello che il primo lotto
ha misurato. Questa parte e' una terza cosa: qualcuno che non ha scritto niente
di tutto cio' ha riaperto il codice, ha rieseguito le misure e ha controllato le
affermazioni una per una. Poi ha scritto che cosa fare adesso.

Il metodo, perche' un controllo che non si puo' rifare non e' un controllo: ogni
cifra qui sotto viene da un comando eseguito su questa branch, e il comando e'
scritto accanto al numero.

### 1. Che cosa regge

**Le misure sono giuste.** Rieseguite tutte, sui due file di testo, quello di
`master` e quello di questa branch.

```bash
python3 scripts/prose_lint.py --summary --texts <content/indicators/ di master>
python3 scripts/prose_lint.py --summary
```

| | dichiarato | verificato |
|---|---|---|
| domanda retorica, prima | 340 su 364 | 340 su 364 |
| lessico spia, prima | 25 | 25 |
| articoli con un link, prima | 6 su 364 | 6 su 364 |
| articoli con un link, dopo | 18 | 18 su 364, 43 link |

Anche la tabella del lotto regge, colonna per colonna, sui dieci codici
dichiarati: 20 sezioni scritte su 40 prima e 40 dopo, 1.517 parole prima, 14 tell
prima, 10 domande retoriche prima, zero link e zero fonti prima. Il salto e'
reale e le cifre che lo raccontano sono quelle.

**Le fonti citate esistono.** I sedici riferimenti in `fonti` dei dieci articoli
del lotto sono quindici URL distinti, tutti interrogati: quindici risposte 200,
nessun link morto, nessuna fonte inventata. Era l'unico errore da cui il piano
dice che non si torna indietro, e non e' stato commesso.

**La suite e' verde**, 468 test, e la correlazione di rango e' aritmetica
corretta: Pearson sui ranghi medi, pari merito gestiti, soglia di dodici regioni
in comune sotto la quale non risponde.

**I tre debiti di curatela sono tutti veri**, e uno e' piu' grave di come e'
scritto.

- `ter-282` ha davvero `direction: lower_better`, e il brief aggiunge una riga
  che la Parte seconda non ha: **`nel punteggio True`**. Non e' solo il cruscotto
  che stampa una frase in contrasto con l'articolo sotto, e' un verso sbagliato
  che entra nel punteggio di qualita' della vita. La graduatoria lo mostra da
  sola: nel 2023 l'Umbria sta sopra la Sicilia e le Marche pari con la Sicilia,
  che e' quello che succede quando si ordinano per merito i procedimenti
  conclusi invece del fenomeno.
- `ter-130` ha davvero l'unita' sbagliata. I valori del 2023 vanno da 41,17 della
  Calabria a 79,66 della Lombardia, cioe' migliaia di euro per addetto, e i
  metadati dicono `milioni di euro`. Il vecchio articolo su `master` scrive "dai
  41 mila euro della Calabria agli 80 mila della Lombardia", quindi la pagina
  pubblicata oggi stampa un'unita' che la propria prosa smentisce.
- `ter-167` e `ter-471` sono davvero la stessa serie, 580 chiavi in comune e 580
  valori identici su 580.

### 2. Che cosa non regge

Quattro cose. Tre sono piccole e sono state corrette in questa branch, la quarta
e' il motivo per cui esiste il piano di esecuzione qui sotto.

**2.1 Il lotto non aveva zero tell meccanici, ne aveva uno.** La tabella della
Parte seconda mette 0 nelle colonne "scritto" e "riletto". Rieseguendo il linter
com'e' oggi, `ter-408` porta un `ripetuto`: "quasi tre punti" nel lead e "2,79
punti" nel quadro, cioe' esattamente il caso che la docstring di `prose_lint`
cita come vero positivo. La tabella e' stata calcolata prima che quel controllo
esistesse e non e' stata rifatta dopo, che e' la forma piu' banale del difetto
che la Parte seconda descrive altrove: una misura che invecchia quando cambia lo
strumento. Il lead e' stato corretto, adesso lo zero e' vero.

**2.2 Il comando scritto nel prompt del revisore non funzionava.**

```
$ python3 scripts/prose_lint.py --show ter-63
nessun articolo per ter-63     # exit 1
```

`--show` indicizzava il dizionario dei testi, quindi accettava l'id interno e
rifiutava la forma URL, che e' quella dell'esempio nel prompt del revisore, in
`content/STYLE.md` e in ogni altro comando della catena. E' lo stesso identico
difetto che la Parte seconda, sezione 7, racconta di aver trovato e corretto in
`review_queue --show`, riscritto nello strumento nuovo pochi commit dopo. La
lezione era stata scritta, non era stata applicata al vicino di casa. Corretto,
con il test in tutti e due i moduli.

**2.3 Il segnale piu' prezioso non arrivava al revisore.** La coda di rilettura
costruisce il flag `mestiere` da `prose_lint.CHECKS`, che e' la meta' a pattern
del linter. `ripetuto` sta fuori da `CHECKS` perche' confronta due numeri invece
di cercare una forma, quindi la copia lo lasciava fuori: l'unico segnale nato
dall'accordo di due giudici indipendenti, quello che vale di piu' per
occorrenza, era l'unico che l'ordine di lettura non poteva vedere. Su `ter-408`
la coda diceva "nessun segnale di rischio" mentre il linter trovava il difetto.
Adesso il flag e' costruito per sottrazione, tutti i segnali tranne la domanda
retorica, cosi' un controllo aggiunto domani arriva al revisore senza che nessuno
se ne ricordi.

**2.4 L'arretrato non e' una questione di cadenza.** Questa e' l'unica
affermazione della Parte seconda che il codice smentisce, ed e' quella su cui
poggia tutto il resto del giro successivo.

La Parte seconda, punto 3.4, dice: "Non serve un meccanismo nuovo. La catena
funziona, va fatta girare", e conta 35 lotti. Il conto e' giusto sulla domanda
che si pone, e la domanda e' troppo stretta. Conta i 364 articoli che hanno gia'
della prosa. Il catalogo ne ha di piu':

```bash
.venv/bin/python -m scripts.text_queue      # prima riga
```

> 19 articoli completi su 658 pagine (indicatore piu' livello territoriale).

Cioe': 294 pagine con zero sezioni scritte, 345 con due su quattro, le note
migrate, e **19 complete**, dieci delle quali sono il lotto di cui parla la
Parte seconda. L'arretrato vero e' 639 pagine, non 350.

E soprattutto: la catena, girando come girava, non le chiude. Lo scrittore era
una Routine settimanale che scriveva **un** articolo per run, il revisore era
giornaliero e ne leggeva uno per volta. Seicentotrentanove pagine a una alla
settimana sono dodici anni.

> **Aggiornato al 2026-07-27.** I sei cron per stadio non ci sono piu': il lavoro
> lo assegna `scripts/pipeline_dispatch.py`, che gira a battito e lancia lo
> stadio in testa alla coda. Il conto qui sotto resta valido come ordine di
> grandezza, ma il ritmo non e' piu' fissato da un giorno della settimana: e'
> quanto spesso batte il dispatcher, e quello si cambia in un campo della
> Routine invece che in sei. Il vincolo di fondo, pero', non e' cambiato e resta
> quello che dice il paragrafo dopo: uno stadio per tick, un blocco per run.
Il lotto da dieci che ha prodotto tutte le misure di questa parte non e' la
catena che gira: sono dieci agenti in parallelo dentro una sessione condotta a
mano, un modo di lavorare che le Routine non hanno. La Parte seconda misura un
regime e poi programma il lavoro in un altro.

Da qui in avanti, quindi, il vincolo non e' la misura. La misura c'e', e' onesta
e concorda con due giudici. Il vincolo e' la portata.

### 3. Il piano di esecuzione

Cinque interventi in ordine. I primi due sbloccano, il terzo e' il lavoro vero,
il quarto e il quinto servono a sapere se il terzo sta andando bene.

#### 3.1 Portare in produzione il primo giro

Il primo lotto, il linter, la rubrica, il registro delle fonti e i correlati nel
brief **non sono su `master`**. Non c'e' nessuna pull request aperta. Il sito
serve oggi le versioni vecchie dei dieci articoli, quelle in cui il giudice
severo ha trovato cinque affermazioni false, e ne serve altre che hanno lo stesso
difetto: `ter-920` su `master` chiude il lead con "una media nazionale salita a
47,6 anni", dove 47,58 e' la media semplice delle venti regioni. E' la trappola
dell'aggregazione descritta in `docs/SECONDARY_SOURCES.md`, pubblicata.

Finche' questo non atterra, ogni giro successivo lavora su una base che i lettori
non vedono, e ogni misura di `prose_lint` racconta un catalogo che non e' quello
servito. E' il primo intervento perche' e' l'unico che vale qualcosa da solo.

**Criterio di accettazione.** `prose_lint --summary` su `master` deve dire 326 e
18, non 340 e 6.

**Effort:** nullo, e' una merge.

#### 3.2 Il lotto come modo di lavorare, non come sessione a mano

Il regime che ha prodotto i numeri della Parte seconda va reso ripetibile, perche'
e' l'unico che chiude l'arretrato in un tempo che ha senso.

Serve un comando che, dato un numero, restituisca il prossimo lotto: prende la
coda giusta (`text_queue` per le pagine mai scritte, `review_queue` per quelle da
rileggere), toglie quelle gia' in lavorazione, e stampa i codici piu' il comando
di brief per ciascuno. Niente di piu': l'orchestrazione degli agenti sta fuori
dal repo, la scelta di che cosa lavorare sta dentro.

Due cose che la Parte seconda ha imparato e che vanno nel comando, non nella
memoria di chi lo lancia:

- **la presenza di un file non e' un segnale di completamento** (sezione 7). Dieci
  agenti in parallelo scrivono presto e rifiniscono dopo, e integrare alla
  comparsa del file ha preso quattro versioni intermedie su dieci.
- **un lotto e' omogeneo per livello**. Un articolo dichiara `"level"` e le due
  code hanno una riga per coppia indicatore-livello, quindi mescolare regione e
  provincia dentro un lotto sposta il costo sul revisore.

**Ordine del lavoro.** Le code ordinano per rischio e per indicizzabilita', che e'
il criterio giusto in mancanza d'altro. Non e' pero' la lettura: indicizzabile
vuol dire che Google puo' vederla, non che qualcuno la apre. Se esiste un export
di Search Console, ordinare le prime dieci tornate per impressioni reali vale piu'
di qualunque altra rifinitura di questo piano. Se non esiste, si tiene l'ordine
attuale e si dice che e' un ripiego.

**Il conto, per decidere con un numero davanti.** 639 pagine, dieci per lotto,
sono 64 lotti. Al costo dichiarato dalla Parte seconda, dieci run di scrittura,
cinque di rilettura e due di giudizio, piu' il verificatore di 3.3, sono circa
1.150 run di agente. Un lotto a settimana chiude in quindici mesi, due lotti a
settimana in sette. La domanda da porsi prima di cominciare non e' se il flusso
funziona, e' quale di questi due ritmi si vuole pagare.

**Criterio di accettazione.** Due lotti consecutivi lavorati con il comando, senza
sovrapposizioni e senza pagine perse per strada, e `prose_lint --summary` che si
muove di venti articoli.

**Effort:** basso per il comando, alto e continuativo per il lavoro che apre.

#### 3.3 Il verificatore

La proposta della Parte seconda, 3.1, e' giusta e va fatta come la descrive, con
il suo doppio controllo: girato sui dieci appena pubblicati deve dare zero
smentite, girato su dieci articoli migrati e mai riletti deve darne piu' di zero,
e se tutti e due danno zero il numero e' una bugia. Il campo
`affermazioni_controllate` nello schema e' la parte che non si negozia, perche'
senza di esso "zero smentite" e "non ho guardato" sono lo stesso zero.

Due correzioni alla messa in opera, che la Parte seconda stima "medio, e' un
prompt, uno schema e una riga di diario".

**Non e' un prompt e una riga.** Uno stadio nuovo e' inchiodato in tre posti che
non si parlano: `pipeline_gate.STAGE_PATHS` piu' `MERGE_POLICY`,
`pipeline_log.STAGES`, `pipeline_status.STAGE_ORDER`. Il cancello valida lo stadio
contro `choices=sorted(STAGE_PATHS)`, quindi uno stadio non registrato non e'
degradato, e' rifiutato. Vanno toccati tutti e tre, piu' l'agente in
`.claude/agents/`, piu' la Routine, piu' `docs/AUTONOMOUS_PIPELINE.md` che dice
"i sei stadi".

**Il diario dedicato non va fatto.** La proposta parla di "un file di diario
dedicato". `data/pipeline/runs/` e' l'unico diario che il cancello pretende
e che `pipeline_log` e `pipeline_dashboard` sanno leggere, e un secondo file
sarebbe invisibile a tutti e tre. I contatori stanno benissimo dentro la riga
esistente, che ha gia' un campo `detail` libero. Un diario che nessuno strumento
legge e' il difetto che questo progetto ha gia' pagato una volta, con la Routine
che scriveva in `analyst_notes.json`.

**Il perimetro giusto.** `STAGE_PATHS["verificatore"] = (RUN_JOURNAL,)` e basta.
Uno stadio che non corregge niente non ha bisogno di toccare i testi, e un
perimetro di un solo file rende il cancello una tautologia verde invece di una
verifica: e' il caso in cui `check_journal` dice "nessun lavoro da registrare", e
va guardato prima di fidarsi del primo verdetto.

**Effort:** medio, ma su sei file, non su due.

#### 3.4 Ritarare la rubrica

Da fare come scritto nella Parte seconda, 3.2, con il criterio di accettazione che
propone, cioe' lo scarto interno al lotto sopra i tre punti e non la media. E'
l'intervento con il rapporto valore su sforzo piu' alto di tutti, un file di testo.

Una sola aggiunta ai quattro criteri che la Parte seconda ritara. **Il criterio 5
ha adesso il dato per essere giudicato senza aprire il brief**: il blocco
`INDICATORI CORRELATI` marca i quasi gemelli sopra `rho` 0,95 e li mette in fondo,
quindi "un correlato che e' lo stesso fenomeno misurato due volte vale 1" e'
verificabile e non solo enunciabile.

E un limite del brief da scrivere nella rubrica invece di lasciarlo implicito: la
correlazione si calcola sull'ultimo anno **di ciascuna** serie, che spesso non e'
lo stesso anno, e su venti regioni. Con venti punti un rho vicino a zero non
dimostra che due indicatori non c'entrano niente, dice solo che non si vede.
Il gruppo "mappa diversa" e' quello che il brief invita a scrivere ed e' anche
quello statisticamente piu' fragile, quindi la frase giusta e' "qui la geografia
non si somiglia", mai "questi due non hanno niente a che fare".

**Effort:** basso.

#### 3.5 Il debito di curatela

Tre voci, tre decisioni diverse, e nessuna appartiene a uno stadio della catena.

- **`ter-282`, il verso.** E' l'unica che ha bisogno di una decisione umana, ed e'
  la piu' urgente delle tre perche' l'indicatore e' nel punteggio. `contextual`
  toglie dal punteggio un verso che il dato non regge.
- **`ter-130`, l'unita'.** Non e' una decisione, e' un errore. La definizione Istat
  stampata sulla stessa pagina dice `migliaia di euro concatenati` e i valori lo
  confermano. Va corretto nei metadati.
- **`ter-167` e `ter-471`, il doppione.** Due pagine indicatore con gli stessi 580
  numeri, tutte e due dentro i conteggi del tema. Da decidere quale nome
  sopravvive e da far 301 all'altra, con la stessa logica delle URL legacy.

**Effort:** basso ciascuno, ma fuori dal perimetro di ogni agente, quindi non si
fa da solo.

### 4. Che cosa non fare, aggiunte alle tre della Parte seconda

- **Non aggiungere stadi finche' non e' aumentata la portata.** Il verificatore
  vale perche' misura un buco reale, non perche' la catena abbia bisogno di piu'
  pezzi. Un settimo stadio su una catena che pubblica un articolo a settimana
  aggiunge sorveglianza a un flusso che non scorre.
- **Non contare le pagine come articoli.** 364 e' il numero delle voci con della
  prosa, 658 quello delle pagine, 19 quello degli articoli veri. Il primo numero
  e' quello che `prose_lint` stampa e va bene per il prima e dopo, ma se diventa
  il denominatore dell'arretrato nasconde le 294 pagine che non hanno niente.
- **Non fidarsi di una tabella di misure senza rieseguirla.** Il caso 2.1 e'
  costato un numero sbagliato in un documento che sarebbe stato la base del giro
  successivo, e rieseguire il comando e' costato un decimo di secondo.

### 5. Ordine, e perche' e' questo

| # | Intervento | Effort | Sblocca |
|---|---|---|---|
| 1 | 3.1, portare in produzione il primo giro | nullo | tutto il resto |
| 2 | 3.5, l'unita' di `ter-130` e il verso di `ter-282` | basso | articoli corretti su dati corretti |
| 3 | 3.4, ritarare la rubrica | basso | il giudizio del lotto successivo |
| 4 | 3.2, il lotto come comando, e la decisione sul ritmo | basso il comando | l'arretrato |
| 5 | 3.3, il verificatore su sei file | medio | sapere se il 4 sta andando bene |

Il 2 sta prima del 4 di proposito. Riscrivere un articolo sopra metadati sbagliati
significa riscriverlo due volte, e `ter-130` e' gia' nel lotto che e' stato fatto.
Il 5 sta dopo il 4 e non prima, contrariamente alla Parte seconda: un verificatore
tarato su un lotto ogni tanto misura il rumore, e il suo doppio controllo ha
bisogno di dieci articoli appena pubblicati che solo il 4 produce con regolarita'.

---

### 6. Stato dell'esecuzione al 27 luglio 2026, e che cosa manca

Questa sezione esiste perche' il piano qui sopra e' stato eseguito a tappe e la
sessione che lo esegue finisce prima di lui. Chi riprende deve poter sapere dove
ci si e' fermati senza ricostruirlo dai commit.

**Dove vive tutto.** Branch `claude/article-improvement-plan-bz3qgm`, pull
request #46 aperta su `master`.

#### Fatto

- La verifica del piano, con le misure rieseguite, e' la Parte terza qui sopra.
- Tre strumenti riparati: `prose_lint --show` accettava solo l'id interno e
  rifiutava la forma URL scritta nel prompt del revisore, il flag `mestiere`
  della coda non vedeva `ripetuto`, il brief scriveva "le due estreme" anche
  quando ne colloca una sola.
- Il cancello riporta il verdetto della suite invece dell'ultima riga stampata
  da un test.
- **Lotto 2, scrittura: undici articoli su undici.** Gli undici a rischio piu'
  alto della coda, tutti partiti da due sezioni su quattro e circa 140 parole.
  Da 22 sezioni su 44 a 44 su 44, da 1.552 a 7.841 parole, da zero a 29 link
  interni, da zero a 19 fonti verificate, zero tell meccanici.
- **Lotto 2, rilettura: undici articoli su undici**, firmati. I sei rimasti
  (`ter-611`, `ter-72`, `bes-12SER003`, `ter-168`, `ter-432`, `ter-60`) sono
  stati riletti da sei agenti in parallelo su file separati e integrati in
  serie. I due file di review gia' sul disco per `ter-432` e `ter-60` non sono
  stati letti: l'agente che li aveva scritti non aveva dichiarato chiusura,
  quindi quelle due riletture sono state rifatte da capo.
- **Il verificatore, tutti e due i bracci.**
- **La guardia sulle definizioni**, che era la lacuna piu' larga e non era in
  nessuna parte del piano.

#### Che cosa hanno detto i numeri

La rilettura, sui sei ultimi: 205 affermazioni controllate, 39 rilievi, 15
affermazioni false. Sul lotto intero, undici articoli: **392 controllate, 57
rilievi, 19 false**, cioe' circa 1,7 per articolo.

Il verificatore, braccio positivo, sugli stessi undici gia' riletti e firmati:
**529 controllate, 7 smentite, 3 non verificabili**.

| stato dell'articolo | controllate | smentite | tasso |
|---|---|---|---|
| note migrate, mai rilette (braccio negativo) | 113 | 11 | 9,7% |
| scritte nel lotto 2, non ancora rilette | 392 | 19 | 4,8% |
| scritte nel lotto 2 e rilette | 529 | 7 | 1,3% |

**Il tasso torna sotto di un fattore sette**, quindi lo zero del braccio
positivo non era una bugia. Due avvertenze sul confronto, perche' la Parte terza
esiste per non fidarsi di una tabella: i tre numeri vengono da agenti diversi e
"affermazione controllata" resta un giudizio, non un conteggio oggettivo, quindi
il rapporto e' solido e i decimali no.

La conclusione, pero', **non e' "lo stadio di scrittura va bene"**. E' che a
togliere gli errori e' la rilettura. Un lotto che salta quello stadio pubblica
circa un'affermazione falsa ogni due articoli, e la Parte seconda aveva concluso
il contrario solo perche' misurava testi gia' passati di li'.

E 1,3% non e' zero. Su undici articoli scritti bene, riletti e firmati, restano
sette affermazioni false. **Tre delle sette sono della classe definizione**, che
e' esattamente la classe che sopravvive a una rilettura fatta bene, perche' una
rilettura controlla i numeri e i numeri erano giusti. Tutte e sette sono state
corrette, e le tre non verificabili tagliate.

#### La guardia sulle definizioni, che ora esiste

`scripts/xls_reader.py` (OLE2 e BIFF8 con la sola libreria standard),
`scripts/fetch_definitions.py` (il foglio `Metadati` di `Metainformazione.xls`
in `data/definitions/istat_territoriali.csv`, 378 definizioni, 362 dei 393 id
dell'archivio regionale) e `scripts/definition_check.py` (il confronto).

Il segnale `definizione` di `review_queue` pesa 50, sopra `rilettura`, e segnala
45 articoli. Il dettaglio dei quattro segnali e la loro affidabilita' stanno in
[`INDICATOR_PAGES.md`](INDICATOR_PAGES.md), che e' il documento che li possiede.

Due cose vale la pena registrare qui e non li'. La prima: la prima forma del
segnale `termini` era una lista di parole mancanti e segnalava 148 articoli su
179, che e' lo stesso che non segnalarne nessuno. Un segnale che copre l'82% del
campo non ordina niente, ed e' lo stesso difetto della domanda retorica su 340
articoli su 364. La seconda: il segnale `contraddizione` su tutti e 364 gli
articoli ne trova **uno**, `ter-72`, ed e' la stessa identica frase che un
revisore umano aveva trovato leggendo l'articolo, arrivata per una strada
indipendente. Una guardia lessicale che concorda con un lettore su un caso
solo e' un campione minuscolo, ma e' l'unico modo che si aveva di tararla.

#### Il secondo giro, sui rilievi non contati

Il verificatore registra a parte i rilievi che non vuole contare come smentite,
perche' l'affermazione era letteralmente vera, o l'imprecisione era di tono, o
l'errore era della fonte. Diciassette, su dieci articoli, rifatti i conti uno per
uno: **dieci corretti, sette lasciati**.

Il rapporto due a uno e' il numero che vale la pena ricordare, e vale in tutte e
due le direzioni. Trattare quel campo come una lista di cose da sistemare
avrebbe peggiorato sette frasi giuste: "sette punti e mezzo" per -7,64 e'
italiano normale, e "quattordici anni tra meno 0,2 e piu' 0,9" e' una banda vera
in entrambe le direzioni, non un record da limare. Ignorarlo invece avrebbe
lasciato in pagina la premessa rovesciata di `bes-02IST023` ("il denominatore
comprende tutti dai 6 anni in su, quindi qui non si misura una popolazione
scolastica": il denominatore la include, e a escluderla e' il numeratore) e il
"sempre meno" di `ter-432`, smentito quattro volte su nove passaggi dalla stessa
serie che l'articolo descrive due sezioni dopo.

Due rilievi hanno prodotto la classe piu' utile del giro, e non c'era nel piano:
**la rottura di serie che l'articolo attraversa senza nominarla.** `ter-60`
appoggia la sua tesi sulla finestra 1998-2004, cioe' esattamente quella che
precede la ricostruzione della serie del 2004, e non lo diceva. `ter-72` costruisce
una dinamica su ventidue anni attraverso il cambio di classificazione Ateco che
Istat dichiara. Nessuna guardia la vede, perche' non e' una cifra sbagliata e non
e' una definizione sbagliata: e' una finestra temporale che la fonte segnala come
non confrontabile. Il campo `note` di `data/definitions/istat_territoriali.csv`
ce l'ha per 470 indicatori e nessuno lo legge.

#### La coppia ter-167 / ter-471, chiusa per quanto si poteva

Il debito di curatela aveva una quarta voce, la sola verificata due volte. Letto
l'articolo, era peggio di un problema di etichette: `ter-471` costruiva tutto
sulla distinzione che i numeri non sostengono, "Qui contano i privati, non lo
Stato", e il suo lead notava la coincidenza con l'accumulazione presentandola
come una scoperta.

L'argomento non dipende da quale etichetta sia quella giusta: una frase che
distingue il privato dal totale ha bisogno che le due serie siano diverse, e sono
identiche. Le due pagine adesso lo dicono, ognuna dall'altro lato, con la prova.
Nessuna delle due e' soppressa, perche' quella e' una scelta con conseguenze
sugli URL pubblici e resta al curatore.

La guardia c'e': `tests/integration/test_data_quality.py` fa fallire la suite su due
indicatori con serie identica, con la coppia nota in una allow-list che porta
accanto la prova, piu' un secondo test che verifica che sia **ancora** duplicata.
Quando Istat sistemera' l'archivio quel test cade, ed e' l'avviso per togliere la
voce e rileggere i due articoli. Sul catalogo intero, 571 indicatori con serie,
la coppia resta una sola: un confronto esatto costa niente e scatta quasi mai.

#### Non fatto, e dove riprendere

1. **Le famiglie non territoriali non hanno una guardia sulle definizioni.**
   `definition_check` dice `scoperto` su 185 articoli su 364, che e' onesto e
   non e' una copertura. Il BES pubblica il suo glossario nel capitolo e nel
   `Metadata.xlsx` dell'annesso statistico, che un verificatore ha scaricato e
   letto durante questa sessione: la strada esiste, il parser no.
3. **Il debito di curatela** di 3.5, sotto, e' peggiorato.
4. **La rubrica non e' stata ritarata** (3.4).

#### Lo stadio verificatore, adesso registrato

Era il punto 1 di questo elenco e non lo e' piu'. Lo stadio esiste in tutti e tre
i posti che la 3.3 elenca (`pipeline_gate.STAGE_PATHS` piu' `MERGE_POLICY`,
`pipeline_log.STAGES`, `pipeline_status.STAGE_ORDER`), ha il suo agente in
`.claude/agents/indicator-verifier.md`, la sua coda in
`scripts/verification_queue.py` e il suo controllo di cancello.

Due scostamenti dalla 3.3, entrambi in direzione di "il cerchio si chiude".

**Il perimetro e' due file e non uno.** La 3.3 diceva
`STAGE_PATHS["verificatore"] = (RUN_JOURNAL,)` e basta, e avvertiva che con un
perimetro cosi' corto il cancello diventa una tautologia verde. Il problema vero
era piu' a monte: con il solo diario una smentita finisce in un campo che
`review_queue` non legge, quindi non torna a nessuno, ed e' esattamente il difetto
che la stessa 3.3 nomina due paragrafi dopo a proposito di `analyst_notes.json`.
Quindi il perimetro e' `(verifiche/, runs/)`: il registro delle verifiche
e' uno stato che serve a un altro stadio, non un diario parallelo.

**La scadenza e' un'impronta della prosa, non una data.** Una verifica e'
un'affermazione su un testo, quindi scade quando quel testo cambia e nient'altro
la fa scadere. La versione a date e' stata scritta e buttata: il revisore che
ripara una frase smentita firma il giorno in cui e' stata smentita, e due eventi
nello stesso giorno sono indistinguibili.

Il costo dello stadio, misurato: undici agenti, circa 900 mila token, 529
affermazioni controllate, 7 smentite.

Resta da armare la Routine, e non e' una dimenticanza: mette in moto un agente
che apre e fonde pull request da solo. Dal 27 luglio la Routine da armare e' una
sola per tutta la catena, quella del dispatcher, e il verificatore ci entra come
gli altri sei senza bisogno di una propria.

#### Tre cose piccole trovate per strada

- Il brief non consegna tutti i correlati. Su `ter-242` stampava il solo gruppo
  "mappa diversa", e lo scrittore si e' ricalcolato a mano `ter-241` (rho 0,50)
  e `ter-157` (0,06). Il brief esiste per impedire proprio quello.
- `docs/SECONDARY_SOURCES.md` non dice se e' una lista chiusa o un punto di
  partenza. Cinque scrittori su undici ne sono usciti. ARERA per le interruzioni
  elettriche e il MiC per il cinema sono piu' autorevoli di qualunque voce in
  elenco, `dati.trentino.it` per un indicatore Istat nazionale no.
- Lo stesso registro avverte dei 403 e non dei 503. `pnrr.salute.gov.it` e
  `salute.gov.it` rispondono 503 a una richiesta automatica e 200 a un browser,
  ed e' un blocco, non una fonte morta. Confermato due volte in questa sessione.

#### Il debito di curatela, che intanto e' diventato piu' caro

Le tre voci restano quelle di 3.5. La quarta, la coppia `ter-167` / `ter-471`,
e' descritta sopra: la prosa e la guardia sono a posto, la decisione su quale
pagina sopravvive no, e quella e' curatela.

Resta il meccanismo che l'ha prodotta. `ter-242` aveva gia' linkato `ter-471`
prima che qualcuno sapesse che cos'era, e ogni lotto cementa link verso pagine su
cui nessuno ha deciso. Il brief non aiuta, perche' la sua soglia di allarme
scatta a rho sopra 0,95 fra i correlati e i doppioni esatti passano da un'altra
parte: adesso li prende la suite, ma solo a valle, quando sono gia' in pagina.
