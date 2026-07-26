# Piano per la qualità di scrittura delle pagine indicatore

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
| le guardie sui link interni | `tests/test_indicator_texts.py`, classe `InternalLinksInProse` |
| gli incroci, il linking, la ricerca di fonti | `.claude/agents/indicator-writer.md` |
| le verifiche di mestiere e di incrocio | `.claude/agents/indicator-reviewer.md` |
| la voce sulla descrizione in lingua piana | `.claude/agents/indicator-curator.md` |

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

Resta non fatto, e consapevolmente: il giudice in cieco della 4b, e la
riscrittura dell'arretrato. Il secondo è lavoro del revisore, un lotto alla
volta, e adesso ha una coda che lo ordina e un numero che dice se sta funzionando.

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
  mai `/?indicator=` né `/atlante?indicator=` (`tests/test_url_migration.py`).

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
- **2c. Guardia.** Un test in `tests/test_indicator_texts.py` che verifica: ogni
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
| `tests/test_indicator_texts.py` | Nuova guardia sui link interni |
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
  `tests/test_indicator_brief.py`, che la pinza sia sui casi noti (monotono,
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
   prompt dello scrittore e in `tests/test_indicator_texts.py`.
4. Nessun registro fonti in repo (3a). Fatto, `docs/SECONDARY_SOURCES.md`.
5. Nessun harness di valutazione a rubrica (4b). Fatta la metà meccanica,
   `scripts/prose_lint.py`, che gira su tutti gli articoli invece che su un lotto.
   Il giudice in cieco sui sei criteri interpretativi resta da fare.

---

## 7. Rubrica di qualità

Scritta, con i dieci criteri e la scala 0-2, in
[`docs/WRITING_RUBRIC.md`](WRITING_RUBRIC.md). Sotto 14 su 20 l'articolo non è
pronto. Quel file dice anche quali criteri conta uno script e quali restano a un
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
