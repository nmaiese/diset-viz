# Proposta: una pipeline per gli articoli del blog guidati dai trend

Bozza di progettazione, non operativa. Non tocca `content/`, non tocca codice
applicativo, non sostituisce `docs/WORKFLOW_ARTICOLI_TREND.md` (che resta la
descrizione del processo storico finché qualcuno non decide di sostituirlo).
Indipendente dalla pipeline delle pagine indicatore, che vive nel repo
`nmaiese/redazione-ai` e che un altro worker sta riprogettando in parallelo:
qui non si nomina né si dipende da quell'agent, quel repo o la skill `voce`.

## 0. Come è stata scritta questa proposta

Letti `docs/WORKFLOW_ARTICOLI_TREND.md`, `docs/SECONDARY_SOURCES.md`,
`docs/LLM_QUERY_MAP.md`, `content/STYLE.md`, `.claude/rules/editorial.md`,
`.claude/rules/python.md`, `scripts/trend_articles/*.py`,
`config/trend_topics.json`, `tests/integration/test_blog_trend_articles.py`,
`data/articles/rebuild_2026-09-23.sh` e i quattro pezzi che ne sono usciti
il 23 settembre 2026. Provati gli `--help` di tutti i moduli con
`bin/py -m scripts.trend_articles.<nome> --help` (`DIVARIO_PYTHON` impostato
sul venv del repo). Cercati online pattern reali di pipeline editoriali
guidate da trend e di verifica pre-pubblicazione per contenuto assistito da
AI; le fonti sono citate dove usate.

## 1. Stato reale di `scripts/trend_articles/`: tenere, riusare, buttare

Verifica diretta, non supposizione: ogni modulo lanciato con `--help` sul
venv del repo (`bin/py`, quello che gira in produzione e in CI, non l'ambiente
usa-e-getta di `pytrends`).

| modulo | esito `--help` | motivo |
| --- | --- | --- |
| `interest.py` | **funziona** | non importa `requests` a livello di modulo |
| `rank.py` | **funziona** | idem |
| `dossier.py` | **funziona** | idem |
| `figures.py` | **funziona** | idem |
| `derive_province_mean.py` | **funziona** | idem |
| `collect.py` | **rotto**: `ModuleNotFoundError: No module named 'requests'` | |
| `photo.py` | **rotto**, stesso errore | |
| `verify.py` | **rotto**, stesso errore | |
| `derive_bes_areas.py` | **rotto**, stesso errore | |
| `derive_foreign_pupils.py` | **rotto**, stesso errore | |
| `derive_sector_injuries.py` | **rotto**, stesso errore | |

`requests` non è in `requirements.txt` né in `requirements-dev.txt`, e non è
importato da nessun modulo sotto `app/`: il sito parla HTTP con la libreria
standard apposta (`docs/SECONDARY_SOURCES.md`: "Nessun modello nel giro di
verifica" per `fetch_corpus`, con `urllib`). Sei moduli su undici della
pipeline trend sono quindi **non lanciabili oggi con `bin/py`**, non per una
scelta di design ma per una dipendenza mai fissata: nessuno l'ha notato
perché la pipeline non gira da un pezzo (`docs/WORKFLOW_ARTICOLI_TREND.md` la
chiama esplicitamente "un processo storico", e l'unica produzione committata è
del 23 settembre 2026). Questo non è un difetto della progettazione dei
moduli, è la prova che la catena è ferma da prima che qualcuno la spegnesse
di proposito: uno smoke test minimo (`--help` su ogni entrypoint in CI)
l'avrebbe preso.

### Giudizio, modulo per modulo

**Tenere e riusare, quasi così com'è:**

- `common.py`: legge gli stessi CSV che serve il sito
  (`app/static/data/Assoluti_*.csv`), non ne scarica una seconda copia. È il
  principio giusto ("un numero nel pezzo è lo stesso numero della scheda") e
  va tenuto come fondamento, non solo come modulo. Aggiungere solo i test che
  oggi mancano (nessun test unit dedicato in `tests/unit/` per `common.py`,
  a differenza del contratto che promette).
- `dossier.py`, `figures.py`, `rank.py`, `derive_province_mean.py`: lanciabili,
  autocontenuti, senza dipendenze esotiche. Il vincolo "ogni cifra nel testo
  deve stare nel dossier" (`verify.py`, quando funzionerà) è la difesa più
  forte contro le fonti inventate che questo progetto abbia mai scritto:
  **va tenuto, non reinventato**.
- `interest.py`: la logica di normalizzazione su un'ancora e la separazione
  fra "indice relativo" e "volume" è corretta e documentata bene nel
  workflow storico. Il problema non è il modulo, è la dipendenza da
  `pytrends`, non ufficiale e già fragile (temi in `TODO` sotto).

**Riparare, non riscrivere:** `collect.py`, `photo.py`, `verify.py`,
`derive_bes_areas.py`, `derive_foreign_pupils.py`, `derive_sector_injuries.py`.
Il fix più economico è sostituire `import requests` con `urllib.request`
della libreria standard, coerente con `.claude/rules/python.md` ("nessun LLM
dove basta un parser", tono deterministico) e con `fetch_corpus.py`, che
questo pattern lo usa già altrove nel repo. In alternativa, aggiungere
`requests` a `requirements-dev.txt` (non `requirements.txt`: questi script
non girano in produzione) se il porting a `urllib` costa più del previsto su
`photo.py`, che fa multipart upload e ridimensionamento immagini. Non è un
buttare: la logica dentro (fonti primarie, licenze Wikimedia ammesse,
soglia `z >= 1,8` per l'outlier, la trappola dell'aggregato ponderato) è
scritta bene e verificata sul campo (i quattro pezzi del 23/9). Buttarla
vorrebbe dire riscrivere da zero le stesse regole, con lo stesso rischio di
sbagliarle una seconda volta.

**Buttare:**

- La dipendenza da `pytrends` per `interest.py` **come oggi configurata**
  (ambiente `uv run --no-project`, 30 minuti in background, sensibile a
  risposte 429). Non è un buttare il modulo, è buttare l'unica fonte di
  "quanto cresce" che oggi esiste. Vedi sezione 2: è il punto più fragile di
  tutta la catena e va sostituito o reso opzionale, non solo riparato.
- Niente altro. Il resto della cartella non ha codice morto evidente: undici
  moduli, ognuno con un compito, nessuna duplicazione fra loro.

### Cosa manca e va scritto ex novo

- Uno smoke test in `tests/unit/` che importi ogni modulo di
  `scripts/trend_articles/` (non li esegua: solo l'import) e fallisca se
  manca una dipendenza. Costo: un file, meno di un'ora. Avrebbe preso questo
  esatto guasto un anno fa invece che oggi.
- Un `requirements-dev.txt` (o un venv usa-e-getta dichiarato) per gli
  script della pipeline trend che non deve inquinare le dipendenze del sito:
  il principio di `interest.py` ("`pytrends` non è una dipendenza del sito e
  non deve diventarlo") va esteso a `requests`, non aggirato copiandolo
  dentro `requirements.txt`.

## 2. Come si individua un trend con un dato solido dietro

Il principio del workflow storico è giusto e va tenuto integralmente: un
pezzo nasce solo se ci sono **insieme** un interesse di ricerca vero e
attuale e un dato solido con una storia dentro. La proposta cambia
l'infrastruttura sotto, non il criterio.

### 2.1 Segnali (fase 1, tenere)

`collect.py`, una volta riparato, resta il punto giusto: Google Trends RSS
(`trends.google.com/trending/rss?geo=IT`), Google News Italia, feed
pubblicazioni Istat. Tre fonti aperte, senza chiave, senza costo per
richiesta. Salvare ogni segnale con fonte, URL, data e **committarlo**
(`data/trend/<giorno>/signals.json`) resta la difesa giusta: è la prova
verificabile di perché un pezzo è nato quel giorno, non un'affermazione.

### 2.2 Interesse (fase 2, il punto più fragile)

`pytrends` è una libreria non ufficiale che imita l'interfaccia web di
Google Trends: non ha un contratto stabile, non ha SLA, e il workflow
storico lo sa già (429, ancora sbagliata al primo giro, 30 minuti di
attesa). Per una pipeline che deve girare "ogni mattina" questo è un
rischio operativo, non un dettaglio implementativo: se Google cambia il
markup della pagina che `pytrends` raschia, la fase 2 si rompe senza preavviso
e senza una release da tracciare.

Due strade, non esclusive:

1. **Tenere `pytrends` ma degradare bene.** Il workflow storico già lo fa
   ("il tema resta senza misura e la classifica ridistribuia il peso sugli
   altri segnali, non lo tratta come zero"): formalizzarlo con un test che
   verifica esplicitamente questo comportamento, non solo descriverlo in
   prosa.
2. **Ridurre il peso di "interesse misurato" nella classifica** a favore di
   "interesse osservato" (fase 1: presenza fra le tendenze, notizie dei
   sette giorni, che non dipendono da `pytrends`). La fase 3 (`rank.py`) già
   pesa entrambi; si può spostare il peso relativo senza cambiare la
   formula, e verificare se la classifica risultante è ancora utile su un
   giorno reale prima di deciderlo in modo permanente.

Raccomandazione: partire dalla strada 1 (costo più basso, cambia un test non
un'architettura), misurare quante volte `pytrends` fallisce su due o tre
settimane di run reali, e decidere la strada 2 solo se il tasso di guasto è
alto. Non indovinare la soglia adesso.

### 2.3 Dal tema all'indicatore (fase 3, tenere)

Il punteggio a tre componenti (interesse, dato, storia) di `rank.py` e il
limite noto già scritto nel workflow storico ("quasi ogni indicatore ha un
outlier da qualche parte, il punteggio storia distingue poco") sono onesti e
vanno tenuti così. Non aggiungere una quarta componente per compensare:
il workflow storico dice giusto che ordinare è compito di interesse e dato,
non di storia. La soglia dell'outlier (`z >= 1,8`) resta da ricalibrare dopo
qualche settimana di classifiche reali, non a tavolino: nessun dato oggi la
giustifica più di un altro numero.

### 2.4 Un tema senza indicatore non entra

`config/trend_topics.json` resta la mappa giusta: un tema che non ha un
indicatore del sito non può generare un pezzo ("è il sito che dà il
contesto, non la notizia"). Aggiungere un tema resta un'operazione a mano,
deliberata, non automatizzabile: sceglierlo bene è editoriale, non tecnico.

## 3. Chi scrive l'articolo, con quale prompt e quale contesto

Oggi non esiste un agent per il blog: la produzione si è spostata sulle
pagine indicatore (`content/STYLE.md`, riga 9-12) e l'agent che scriveva
articoli semplici (`scrittore`) è stato cancellato il 18 settembre 2026.
Questa proposta non riusa né dipende da `nmaiese/redazione-ai`: il progetto
è dichiarato autonomo (`CLAUDE.md`), e quel repo lo sta riprogettando un
altro worker per le pagine indicatore soltanto.

### 3.1 Modello e responsabilità

- **Un solo agent scrive**, chiamato per chiarezza `blog-writer` in questa
  proposta (nome provvisorio, non un impegno). Riceve in input **solo**
  quello che `dossier.py` ha già verificato: il dossier JSON (cifre ammesse,
  già scritte come compariranno), l'elenco delle figure disponibili con
  titolo e slug, la scheda foto (`.photo.json`), e **non** l'accesso libero
  al web. Questo è il vincolo più importante di tutta la proposta: un agent
  che può cercare in rete mentre scrive può anche citare quello che trova
  senza passare dal corpus verificato, ed è esattamente il rischio che
  `docs/SECONDARY_SOURCES.md` descrive già per le pagine indicatore
  ("un modello che riassume mentre copia").
- Il modello redige seguendo `content/STYLE.md` per intero: le regole
  tipografiche vincolanti, le sei mosse di "Tecniche da giornalista", uno
  degli esempi in `content/esempi/` scelto **prima** di scrivere (non dopo,
  non come rilettura), l'imperfezione controllata, gli schemi da evitare.
  Il prompt di sistema dell'agent deve incorporare per intero il contenuto
  di `content/STYLE.md`, non un riassunto: un riassunto diverge dal file nel
  tempo esattamente come le regole duplicate che questo repo ha già pagato
  (`CLAUDE.md`, cappello del repo).
- **Un secondo agent, separato, verifica.** Non lo stesso che ha scritto: lo
  standard AP 2025 per contenuto assistito da AI in redazione è che ogni
  output AI sia rivisto da un umano o da un secondo processo indipendente
  prima della pubblicazione, e che l'AI non sostituisca mai la verifica
  delle fonti ([AP updates AI newsroom standards with human
  oversight](https://mediacopilot.ai/ap-ai-newsroom-standards-update/)).
  Qui il secondo passaggio è **deterministico dove può esserlo**
  (`verify.py` riparato: niente cifra fuori dal dossier, niente fonte non in
  "## Fonti", niente licenza vietata) e **umano dove uno strumento non
  basta**: il nesso fra notizia e dato, una causa non attribuita a un dato
  che non la mostra, la definizione dell'indicatore detta giusta. Il
  workflow storico lo dice già per le pagine indicatore
  (`scripts/definition_check.py`) e vale identico qui.

### 3.2 Contesto del prompt

Il prompt per `blog-writer` porta, in ordine:

1. Il dossier completo (`data/articles/<slug>/dossier.json`): ogni cifra
   citabile, già formattata.
2. L'elenco delle fonti secondarie ammesse per il tema, prese da
   `data/corpus/sources.json` e `data/corpus/claims/` se questa proposta
   decide di riusare quel registro (vedi 4.2), altrimenti un registro
   proprio del blog con lo stesso contratto (`id`, `testo` verbatim, `url`,
   `data di lettura`).
3. Le figure disponibili: slug, titolo (che deve già dire la notizia, non il
   nome dell'indicatore), tipo.
4. La scheda foto: autore, licenza, alt consigliato.
5. Un esempio a scelta da `content/esempi/` (il worker sceglie, dichiara
   quale nel log, non lo decide il modello a caso).
6. Il frontmatter già compilabile per le parti non editoriali (`trend:`,
   `dataset:`, `cover_credit:`): il modello scrive il testo e i campi che
   richiedono giudizio (title, description, H2), non reinventa i campi che
   la fase 4 ha già calcolato.

Il modello **non riceve** accesso a WebFetch o WebSearch durante la
scrittura: se un pezzo ha bisogno di una fonte secondaria che il corpus non
ha ancora, quella ricerca è un passaggio separato, a monte, con verifica
verbatim, non un'improvvisazione dentro la scrittura.

## 4. Come si verificano fonti e cifre

Due garanzie distinte, da non confondere.

### 4.1 Le cifre: il dossier è l'unica fonte ammessa

`verify.py` (riparato secondo la sezione 1) resta la guardia giusta: **una
cifra che non sta nel dossier né fra le `external_figures` dichiarate ferma
il pezzo**. Questo è un controllo meccanico, sempre verde o sempre rosso,
niente giudizio. Va tenuto identico nella forma, con lo stesso principio
del workflow storico: un numero nel pezzo è lo stesso numero che il lettore
trova nella scheda dell'indicatore.

Aggiunta rispetto al workflow storico: **il controllo va eseguito anche in
CI**, non solo a mano prima della PR. Oggi `tests/integration/test_blog_trend_articles.py`
copre figure, crediti foto e schema `Dataset`, ma non invoca `verify.py` sui
pezzi committati. Un test che gira `verify.py` su ogni file di
`content/posts/` che dichiara `trend:` chiuderebbe il buco: un pezzo con una
cifra fuori dal dossier oggi può restare in `master` se nessuno rilancia lo
script a mano.

### 4.2 Le fonti secondarie: verbatim, non parafrasi, con la stessa disciplina delle pagine indicatore

`docs/SECONDARY_SOURCES.md` descrive per le pagine indicatore un pattern che
qui va riusato uguale, non reinventato: un registro di fonti aperte
(`data/corpus/sources.json`), un corpus di citazioni verificate **verbatim**
(`data/corpus/claims/`, un file per affermazione, con URL e data di
lettura), un riscarico con la sola libreria standard che cerca la stringa
esatta (niente modello nel giro di verifica, perché il rischio è proprio un
modello che riassume mentre copia), e la trappola dell'aggregato ponderato
contro la media semplice delle regioni.

Decisione da prendere, non da questa proposta da sola: **il blog riusa lo
stesso corpus delle pagine indicatore, o ne tiene uno separato?** Sono la
stessa fonte di verità (Istat, Inail, lavoce.info, Openpolis...) e un
corpus duplicato è esattamente il tipo di deriva silenziosa che
`CLAUDE.md` di questo repo nomina come già pagata. La raccomandazione è
**un corpus solo**, condiviso, perché il blog e le pagine indicatore citano
spesso le stesse istituzioni sugli stessi temi; ma la decisione finale
spetta a chi possiede `data/corpus/` oggi (verificare con l'altro worker o
con chi possiede il repo prima di duplicare struttura).

In ogni caso, tre regole assolute, senza eccezioni:

1. Ogni citazione nel testo ha un identificatore nel corpus, verificato
   verbatim, con URL aperto e letto (non preso dal registro senza controllo:
   `docs/SECONDARY_SOURCES.md`, "un URL di questo elenco va comunque aperto
   prima di citarlo").
2. Se non c'è una fonte secondaria pertinente, non se ne cita una debole.
   Il campo resta vuoto e si dichiara nella PR, come già oggi per le pagine
   indicatore.
3. Una media semplice delle regioni non diventa mai "media nazionale" nel
   testo: guardia meccanica in `verify.py` (già presente nel workflow
   storico) più controllo umano in rilettura.

## 5. Foto con licenza

Il pattern di `photo.py`, una volta riparato, è corretto e va tenuto senza
modifiche sostanziali: Wikimedia Commons come fonte primaria (API che
restituisce autore, licenza e URL della licenza in forma leggibile da
macchina), solo CC0, pubblico dominio, CC BY, CC BY-SA, scarto di mappe,
loghi, grafici, scansioni e foto troppo piccole, anteprime salvate per una
scelta umana (mai automatica: "la pertinenza la decide un occhio, non una
query"), scheda `.photo.json` con file, pagina originale, autore, licenza,
modifiche. Unsplash e Pexels restano un ripiego ammesso, a mano, quando
Commons non ha niente.

Unica aggiunta: la scelta della foto (`photo choose`) resta un passaggio
**umano**, non delegato a `blog-writer` né a un giudizio automatico di
pertinenza: i criteri elencati nel workflow storico (non un simbolo
generico, non una persona riconoscibile in una situazione sensibile, foto
italiana quando il tema è territoriale, tenuta del ritaglio 1200x630) sono
giudizi visivi che uno script non può fare, e va scritto esplicitamente
come passo del rollout (fase 6, sezione 7) chi lo fa: il worker o redattore
umano che segue il pezzo, non l'agent che scrive.

## 6. Cadenza

Vincoli esistenti, confermati e da tenere identici:

- **Niente prodotto cartesiano province × indicatori.** Un pezzo nasce da
  una storia (outlier, inversione, divario che si apre o si chiude), non da
  un ciclo su ogni combinazione territorio-indicatore. La fase 3
  (`rank.py`) esiste apposta per rendere questa scelta esplicita e
  ricontrollabile, e resta il gate giusto: nessuna automazione genera un
  pezzo senza passare da lì.
- **Massimo 8 pagine nuove a settimana**, blog e pagine indicatore insieme
  (il vincolo è del sito, non della singola pipeline: va coordinato con chi
  possiede la pipeline delle pagine indicatore, non sommato in aggiunta).
- **Un tema non torna prima di un mese**, salvo un fatto nuovo nei dati. La
  serie di run giornalieri di `collect.py` (fasi 1-3, "dieci minuti") resta
  utile anche nei giorni in cui non se ne ricava un pezzo: dice quali temi
  tornano, ed è da lì che si decide cosa aggiungere alla mappa. Questo va
  tenuto: un run quotidiano che non produce un articolo non è uno spreco, è
  osservazione.
- Il giro completo fasi 1-3 resta lanciabile ogni mattina (una volta
  riparato `collect.py`); fasi 4-8 (dossier, figure, foto, scrittura,
  verifica) restano deliberate, con un umano che decide quale coppia
  tema-indicatore della classifica diventa un pezzo, non un cron che
  pubblica da solo. Vedi rischi (sezione 8) sul perché questo non è
  negoziabile in questa fase.

## 7. Piano di rollout, a step verificabili

Ogni step ha un criterio di uscita controllabile da chi non ha scritto lo
step, non una descrizione di intenzione.

**Step 0. Riparare l'infrastruttura (nessuna scrittura editoriale).**
Portare `collect.py`, `photo.py`, `verify.py`, `derive_bes_areas.py`,
`derive_foreign_pupils.py`, `derive_sector_injuries.py` a `urllib.request` o
dichiarare `requests` come dipendenza dev. Criterio di uscita: gli undici
moduli rispondono tutti a `--help` con `bin/py`, e uno smoke test in CI lo
verifica da quel giorno in poi. Costo: basso, un giorno di lavoro stimato.

**Step 1. Un giro completo a mano, senza pubblicare.** Rilanciare
`rebuild_2026-09-23.sh` (o un giorno nuovo) fino alla fase 5 (figure), senza
fase 6 (foto) né fase 7 (scrittura). Criterio di uscita: dossier e figure
prodotti per almeno due coppie tema-indicatore nuove, letti da un umano, e
`verify.py` (riparato) lanciato sui dossier per controllare che non ci siano
regressioni nella logica delle cifre. Nessun testo, nessun commit in
`content/`.

**Step 2. Un pezzo scritto dall'agent, mai pubblicato.** Definire il prompt
di `blog-writer` (sezione 3.2), farlo scrivere su un dossier reale dello
step 1, farlo verificare da `verify.py` e da una lettura umana. Criterio di
uscita: un file Markdown che passa `verify.py` senza errori e che un umano
giudica pubblicabile per aderenza a `content/STYLE.md`, tenuto fuori da
`content/posts/` (in una cartella di lavoro, non committato) finché non si
decide di aprire una PR vera.

**Step 3. Un pezzo reale, PR, merge umano.** Stesso processo dello step 2,
ma con PR verso `master` e merge umano (come oggi: "il merge è la
pubblicazione"). Criterio di uscita: il pezzo pubblicato, la suite
`bin/py -m unittest discover -s tests -v` verde, nessuna cifra fuori dal
dossier, nessuna fonte non verificata.

**Step 4. Cadenza ridotta, osservata.** Un pezzo alla settimana per due o
tre settimane, sempre con revisione umana completa prima del merge.
Criterio di uscita: nessun incidente di fatto (cifra sbagliata, fonte
inventata, licenza foto non rispettata) sui pezzi pubblicati in questa
finestra, misurato da chi rilegge, non dall'assenza di segnalazioni.

**Step 5. Decisione su automazione parziale.** Solo dopo lo step 4, e solo
con dati reali sul tasso di errore del modello e sul tempo di revisione
umana, si valuta se ridurre il carico di revisione (per esempio: automatico
fino alla PR, mai oltre) o tenere la revisione integrale. Questa proposta
**non** raccomanda oggi un'automazione end-to-end: manca l'evidenza per
giustificarla, ed è il tipo di decisione che va presa con i numeri dello
step 4 in mano, non a tavolino.

Nessuno step comporta commit, push, merge o deploy eseguiti da questa
proposta: il piano descrive cosa farebbe un futuro worker operativo, non
esegue nulla.

## 8. Rischi e costi stimati

| rischio | probabilità | impatto | mitigazione |
| --- | --- | --- | --- |
| Fonte secondaria citata senza verifica verbatim (il modello "riassume mentre copia") | media, è il rischio già osservato una volta su due nel corpus delle pagine indicatore | alto: una citazione falsa è, per questo progetto, "l'unico errore da cui non si torna indietro" | `blog-writer` non ha accesso web durante la scrittura (sezione 3.2); verifica verbatim automatica sul corpus prima della PR |
| Cifra fuori dal dossier | bassa se `verify.py` gira sempre, alta se resta un controllo a mano dimenticabile | alto: rompe la promessa "stesso numero della scheda" | `verify.py` in CI su ogni pezzo con `trend:` (sezione 4.1), non solo a mano |
| `pytrends` si rompe senza preavviso (libreria non ufficiale) | media-alta nel tempo, già osservata nel workflow storico (429, ancora sbagliata) | medio: la fase 2 salta, non l'intera pipeline, se il degrado è gestito bene | degrado esplicito e testato (sezione 2.2); non bloccare la fase 3 se manca solo l'interesse misurato |
| Foto con licenza non conforme o persona riconoscibile in situazione sensibile | bassa se la scelta resta umana | alto, anche legale: uso non autorizzato di un'immagine, o un danno a una persona reale | scelta della foto resta un passo umano esplicito (sezione 5), mai delegato |
| Corpus di fonti duplicato fra blog e pagine indicatore | media, se le due pipeline si progettano senza coordinarsi (rischio reale: sono due worker paralleli in questo momento) | medio: deriva silenziosa, lo stesso guasto che `CLAUDE.md` del repo nomina come già pagato | decisione esplicita su corpus condiviso vs separato prima dello step 1 (sezione 4.2), da prendere con chi possiede `data/corpus/` |
| Cadenza che supera 8 pagine/settimana sommando blog e pagine indicatore | media, se le due pipeline non si parlano | medio: viola un vincolo esplicito del sito | il conteggio delle 8 pagine va centralizzato (un contatore condiviso o una checklist manuale prima di ogni PR), non lasciato al giudizio di ogni pipeline separata |
| Pubblicazione senza revisione umana per fretta operativa | bassa nel piano proposto (ogni step la richiede), ma è il rischio più facile da erodere nel tempo | alto | nessuno step del rollout (sezione 7) rimuove la revisione umana; lo step 5 è esplicitamente una decisione futura, non una promessa |

**Costi stimati** (ordini di grandezza, per chi pianifica, non un
preventivo):

- Step 0 (riparazione infrastruttura): **basso**, un giorno-persona.
- Step 1-2 (giro a mano + primo pezzo agent, mai pubblicato): **medio**,
  qualche giorno-persona, soprattutto nel definire e testare il prompt di
  `blog-writer` e nel verificare a mano il primo output.
- Step 3-4 (produzione reale a bassa cadenza): **costo ricorrente
  dominante è la revisione umana**, non il calcolo: ogni pezzo richiede una
  rilettura completa (struttura, cifre, fonti, nesso causale, definizione
  dell'indicatore), stimabile in un ordine di grandezza comparabile a
  scrivere il pezzo da zero, finché lo step 5 non è deciso con dati reali.
  Costo di calcolo (chiamate al modello, dossier, figure) trascurabile al
  confronto.
- Nessun costo di infrastruttura cloud nuovo: tutte le fonti (Google Trends
  RSS, Google News, Istat, Wikimedia Commons) sono gratuite e senza chiave;
  `pytrends` resta senza costo ma con il rischio operativo già descritto.

## Fonti citate

- [AP updates AI newsroom standards with human oversight](https://mediacopilot.ai/ap-ai-newsroom-standards-update/):
  conferma esterna del principio "nessuna pubblicazione AI senza revisione
  umana indipendente" usato in sezione 3.1.
- [Associated Press expands AI newsroom guidelines with human oversight — Digital Watch Observatory](https://dig.watch/updates/ap-ai-newsroom-rules):
  stesso standard, fonte indipendente.
- [Storytelling with Google Trends — Google News Initiative](https://newsinitiative.withgoogle.com/resources/trainings/storytelling-with-google-trends/):
  pattern di riferimento per l'uso editoriale di Google Trends come segnale,
  non come volume assoluto, coerente con la sezione 2.2 e con quanto già
  scritto nel workflow storico.
- [Data-Driven Journalism: Roundup of Recent Standout Stories — GIJN](https://gijn.org/stories/data-driven-journalism-standout-stories/):
  panoramica di pratiche reali di data journalism guidato da segnali e dati,
  usata come conferma generale che il principio "interesse più dato solido"
  è uno standard di settore, non un'invenzione di questo repo.
