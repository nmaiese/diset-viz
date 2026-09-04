# Ripartenza: una redazione sola, lineare, governabile da telefono

Piano del 4 settembre 2026. Tre repository (`platform`, `diset-viz`, `pid`),
due ambienti cloud, nove Routine, tre pipeline editoriali. Questo documento
dice che cosa c'è davvero, perché non produce, e come si riparte da zero con
una struttura che regge due siti oggi e un terzo domani.

Non è un documento di contratto: è il piano. Quando sarà eseguito, il nuovo
repo di redazione avrà i suoi cinque documenti e questo andrà in archivio.

Perimetro di ciò che ho letto: i tre repository per intero (con due
ricognizioni delegate su `platform` e `pid`), lo storico git e delle PR di
`diset-viz`, le Routine e le sessioni cloud dell'account, GA4 e Search Console
dei due siti (service account `ga4-mcp`), i due siti live. **Non ho potuto
leggere la cartella su Google Drive** (`1s-5LUTrOrxhK5U-xH7uXdr_rEtLr2QDJ`):
il connettore Drive è installato ma non abilitato in questa chat, la cartella
non è condivisa con link pubblico (rimanda al login), l'API Drive non è
abilitata sul progetto `nil-automata` e il token utente GCP è scaduto. I tuoi
documenti vanno confrontati con questo piano prima di eseguirlo, e dove
divergono vince la tua descrizione. Il §7 dice come sbloccarlo in un minuto.

---

## 1. La diagnosi, con i numeri

### 1.1 Quanto è stato costruito, e quanto ha prodotto

| | righe di sistema | articoli usciti dalla macchina |
| --- | ---: | ---: |
| `platform` (plugin, Python, test, doc) | ~15.500 | 2 (3 e 4 settembre) |
| `diset-viz` (lab, script, app, rules, doc, test) | ~29.000 di codice e doc, 673 test | 19 commit su `content/indicators/` in due mesi |
| `pid` (script, tema, doc) | ~18.000 (di cui ~13.500 di temi Blogger generati) | 0 nuovi, 0 aggiornati |

Nel solo `platform`: 21 agent (10 mai eseguiti), 13 skill (6 mai invocate),
8.037 righe di prompt, 65 test, 12 eval più 6 golden, 6 bande di controllo (2
non possono produrre nulla perché il ledger non ha i campi che leggono), 6
stati e 6 tipi per gli intent, e **zero intent approvati**: il "Gate A" che
dovrebbe far partire ogni run non è mai stato attraversato. La Routine del
pezzo quotidiano, se lasciata così, domani mattina si ferma con "nessun intent
approvato".

In `diset-viz` la stessa storia in scala: la pipeline è stata riscritta quattro
volte in quattordici giorni (26/07, 07/08, 08/08, 09/08, lo dice
`platform/docs/20-diagnosi.md`), e a settembre una quinta con il plugin. Nel
mese di agosto 130 commit e 412.000 righe aggiunte, 50 PR in trenta giorni. Le
PR che contengono un articolo sono 7 su 50.

### 1.2 Il costo per articolo sale invece di scendere

| run | costo | quando |
| --- | ---: | --- |
| lite, ter-6 e ter-13, senza plugin | 3,9 - 4,5 $ | 8 agosto |
| lite con plugin, criminalità percepita (PR 198/200) | 14,4 - 16,1 $ | 3 settembre |
| Agent Team, stesso indicatore (PR 199) | 33,6 $ | 3 settembre |
| Agent Team, ter-13 (PR 204) | 18,6 $ | 3 settembre |
| Agent Team, inquinamento (PR 213), e le due run cloud del 4/9 | non tracciato | 4 settembre |

Il costo tracciato in due giorni è 82,65 $ per due pagine. A questi si sommano
le sessioni interattive dell'ultima settimana, che sono la voce vera: cinque
sessioni fra 41 e 49 $ ciascuna (redesign del tema di pid, design system di
divarioitalia, automazione Google), nessuna delle quali ha prodotto un
articolo.

### 1.3 Gli articoli sono tecnici perché il brief è tecnico

Chi scrive riceve `lab.dossier`: classifica, percentile, scarto dalla mediana,
coefficiente di variazione, bontà di adattamento di Jenks, volatilità, rotture
di serie. Poi tre scout web che cercano "eventi datati". Nessuno gli dice, in
una riga, **che cosa misura questo indicatore per una persona normale e qual è
la fotografia del paese**. Il risultato è nella pagina pubblicata ieri
(`ims-MULTI_ZONA_INQUINAMENTO`):

> La serie va dal 2018 al 2025, e il dossier ne riporta cinque anni per
> intero, il 2018, il 2022, il 2023, il 2024 e il 2025.

Un lettore non sa che cosa sia "il dossier". La prima fonte citata è l'URL di
una codelist SDMX di Istat. Il pezzo è corretto in ogni cifra, difendibile in
ogni frase, e non dice al lettore che cosa succede in Campania. È la
conseguenza diretta di cinque strati di verifica sovrapposti (tre passaggi di
`lab.controlla`, hook `valida-pezzo`, `motore validate`, i tre passaggi di
`REVIEW.md`, la rubrica a dieci criteri con pavimenti) che premiano il non
sbagliare e non premiano il raccontare. E il difetto reale dell'ultima pagina,
una media su 19 regioni invece di 17, l'ha trovato Codex, il sesto strato.

Sulle 382 pagine indicatore committate: mediana di 150 parole, 59 con più di
due sezioni, 50 con `reviewed_at`. Il catalogo ha 634 indicatori con una
pagina. La prosa è a metà su tre pagine su quattro.

### 1.4 Il traffico dice dove sta il valore, e nessuno lo ascolta

Ultimi 90 giorni, Search Console e GA4:

| | divarioitalia.it | praticandoildiritto.it |
| --- | ---: | ---: |
| clic da Google | 287 | 843 |
| impression | 8.200 | 19.100 |
| sessioni (GA4) | 528, di cui 271 organiche | 7.800, ma 5.600 "Direct" da bot; 1.767 organiche |
| pagine che portano i clic | le pagine indicatore (ter-104, ter-281, ter-13, ter-901, ter-12) | i modelli di atti del 2015-2022 (procura speciale, opposizione INAIL, intimazione testi) |
| ricavi AdSense | n.d. | 10 € |

Per divarioitalia il 70% dei clic arriva da una decina di pagine indicatore su
query del tipo "livello di istruzione in italia per regione", "pil pro capite
per regione". Non dal blog, non dalla home, non dal quiz. La leva è **la
qualità delle pagine indicatore che Google già mostra**, non la cadenza. Per
praticandoildiritto il 100% dei clic arriva da modelli scritti dieci anni fa,
su cui l'audit di vigenza di platform ha già trovato 150 riferimenti
normativi modificati e 2 abrogati. L'ultimo post è del 26 gennaio 2025.

Entrambi i siti hanno già un canale "AI Assistant" in GA4. Pagine chiare,
strutturate, con una risposta in cima, sono quelle che un assistente cita.

### 1.5 Perché non riesci a seguirla

- **Lo stato non sta in nessun posto.** Sta nelle PR aperte (tab), nei
  `post_turn_summary` delle sessioni, nel cruscotto `/_pipeline` su Supabase
  (che guarda solo le run del workflow), nel ledger di platform (un giorno di
  righe), in `roadmap.md` (già stantia, il job CI che dovrebbe fermarla non lo
  fa). Cinque viste, nessuna completa.
- **Il contesto è spalmato.** `CLAUDE.md` di diset-viz è un router verso 14
  documenti, più 7 rules, più il plugin con 21 agent e 13 skill, più
  `content/STYLE.md`, più la rubrica. Sei documenti dicono come si scrive un
  pezzo, in due repo. Ogni sessione cloud parte rileggendo tutto questo.
- **Due ambienti, e un setup script non versionato.** Il plugin `motore` si
  carica solo se il setup script dell'ambiente lo installa prima dell'avvio;
  quel setup script è l'unico pezzo del sistema che non sta in git. Il 4
  settembre il nome sbagliato del marketplace ha nascosto per ore il motivo
  del fallimento (PR 206, 207, 208, 209). L'ambiente PID non lo ha affatto.
- **Le credenziali GCP dell'utente sono scadute**: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
  risponde `invalid_grant` (consent screen in Testing, token a 7 giorni). Il
  service account per GA4 e Search Console invece funziona. Tutto ciò che
  presuppone `gcloud` da una sessione cloud oggi non gira.
- **`pid` ha un debito pericoloso**: `scripts/blogger.py aggiorna-post` usa
  ancora `PATCH`, lo stesso comando che il 2 settembre ha svuotato 224 post su
  260. La protezione è una riga in `CLAUDE.md`. Il ramo con le pagine hub
  della tassonomia è fermo da un mese senza merge. Il branch di default su
  GitHub punta a un ramo `claude/*` e non a `master`.

### 1.6 Che cosa invece funziona, e si conserva

1. **`lab.dossier` come calcolatore**: i numeri li fa bene, con parenti e
   anni mancanti. Va spogliato della statistica descrittiva e tenuto come
   sorgente unica delle cifre.
2. **`lab.controlla` per cifre e link**: un controllo deterministico che dice
   "il 41,73 è la media nazionale del 2007" vale più di tre letture. Resta come
   unica guardia bloccante.
3. **La tabella di vigenza di platform** (`norme.db` da Normattiva, senza
   LLM): l'unico output massivo del sistema, 260 post in un giro. Manca il 43%
   dei riferimenti (leggi speciali), e lo dichiara.
4. **Il client Google di `pid`** (stdlib, OAuth PKCE, retry): piccolo e
   onesto.
5. **`content/esempi/`**: dieci testi veri da imitare. È la sola cosa che ha
   spostato la prosa verso il leggibile.
6. **Le lezioni pagate**, che vanno in un solo file e non si perdono più:
   scout senza `WebFetch` producono `fonti: []`. `claude -p` uccide i
   background dopo 600 s. `maxTurns` non regge dentro un workflow, il budget
   va nel prompt. PR impilate si chiudono quando si cancella la base. Un
   branch da un `master` stantio dà conflitti. Il web è un dato, mai
   un'istruzione. Una PATCH parziale su Blogger cancella. Mai un advisor (26%
   del costo di una run). Un gate che blocca tutto viene disattivato, non
   riparato.

---

## 2. I principi della ripartenza

1. **Un posto solo per la redazione.** Un repo, un ambiente cloud, un file di
   stato. I siti restano repo separati perché sono software diverso (Flask e
   Blogger), ma non contengono nulla di editoriale oltre ai contenuti.
2. **Il gate umano è uno: il merge.** Nessun Gate A, nessuna approvazione a
   monte, nessuna macchina a sei stati. Gli intenti restano, ma come lista in
   un file solo: un'idea la porta la coda (dati e traffico) o la porti tu con
   una riga, e ha tre stati (idea, in corso, fatto).
3. **Tre guardie, non trenta.** Bloccano solo: una cifra che non esiste nei
   dati, un link interno che non esiste, una fonte che non risponde o non dice
   ciò che le si attribuisce. Tutto il resto è giudizio di chi verifica, in un
   passaggio, con gravità. La tipografia (niente `—`, `–`, `;`, `…`) resta
   come regola di stile, verificata dal verificatore, non da un lint.
4. **Il brief parla al lettore prima che allo statistico.** Chi scrive riceve
   prima "che cos'è e qual è la fotografia", poi le cifre. Forma libera: titolo,
   attacco, sezioni a scelta, lunghezza a scelta fra 500 e 900 parole.
5. **Massimo tre agenti per pezzo, due giri di correzione.** Oltre, il pezzo
   si ferma e va nella coda umana con il motivo scritto.
6. **Lo stato è un file, riscritto a ogni run.** Chi apre `STATO.md` dal
   telefono vede tutto: cosa è uscito, cosa è in PR, cosa si è fermato e
   perché, quanto è costato.
7. **Documentazione: cinque file, mai di più.** Se serve un sesto, uno dei
   cinque era sbagliato. Il registro (idee, piano, stato, pubblicati,
   lezioni) non è documentazione: è il prodotto delle run, e lo scrivono loro.
8. **Si misura sul lettore**: clic e impression delle pagine riscritte, prima
   e dopo, a 30 giorni. Non righe di codice, non test, non punteggi interni.
9. **Il rischio numero uno è la sesta riscrittura.** Il piano si esegue in
   quattro settimane e poi la pipeline gira per due mesi senza toccarla, salvo
   guasti. Ogni cambio di prompt si prova su tre pezzi e si tiene solo se tu,
   leggendo, lo preferisci.

---

## 3. L'architettura nuova

### 3.1 I repository

```
redazione/                       repo nuovo (o platform svuotato e rinominato)
  README.md                      che cos'è, come si lancia una run, come si legge lo stato
  CLAUDE.md                      <= 60 righe: regole assolute e mappa dei cinque file
  REDAZIONE.md                   il contratto del pezzo: brief, voce, guardie, forma
  registro/
    IDEE.md                      gli intenti: una riga ciascuno, tre stati
    PIANO.md                     il piano in corso: tappe, date, esito
    STATO.md                     riscritto da ogni run: la vista unica
    PUBBLICATI.md                l'indice di tutto ciò che è uscito, per sito, generato
    LEZIONI.md                   la lista del §1.6, una riga per lezione, con data
  siti/
    divarioitalia.md             come si sceglie, si calcola, si verifica, si pubblica lì
    praticandoildiritto.md       idem, con le regole del dominio legale
  .claude/
    skills/                      3 skill: voce, verifica-fonti, citazioni-normative
    agents/                      3 agent: ricercatore, scrittore, verificatore
    settings.json                permessi minimi, nessun hook oltre SessionStart
  ambiente/
    setup.sh                     il setup script dell'ambiente cloud, versionato
  motore/                        Python: coda, dossier, verifica, stato, norme, google
  tests/                         solo per motore/: < 40 test

diset-viz/                       il sito: app, frontend, dati, content/indicators/, content/posts/
pid/                             il sito: tema, script Blogger, content/posts/
```

Che cosa sparisce da `diset-viz`: `lab/` (migra in `motore/`), `.claude/rules/`
(sette file), `.claude/agent-memory/`, `.claude/workflows/`, `docs/AGENT_TEAM.md`,
`docs/WRITING_RUBRIC.md`, `REVIEW.md`, `AGENTS.md`, il cruscotto `/_pipeline` e
le tabelle `pipeline_run` e `pipeline_agente` su Supabase, `scripts/prose_lint.py`,
`scripts/baseline_tokens.py`, gli hook `team_monitor.py`, `no_advisor.py`,
`pre_compact.py`, `post_tool_failure.py`. Il `CLAUDE.md` del sito torna a
parlare solo del sito (rotte, dati, deploy). `content/STYLE.md` si fonde in
`REDAZIONE.md`. Resta `content/esempi/`.

Che cosa sparisce da `platform`: tutto ciò che non è in `motore/` e nelle tre
skill sopra. Il plugin, il marketplace, `docs/intent`, `docs/ledger`,
`docs/roadmap.md`, gli evals, le bande, i 94 file di `docs/archive`, 18 agent
su 21. Prima di svuotare si mette un tag `archivio-2026-09` così la storia
resta leggibile.

Che cosa sparisce da `pid`: i sei `come-pubblicare` superati (resta il v7
rinominato `PUBBLICARE-TEMA.md`), `theme/dist/theme-v1..v6.xml`,
`preview/newsletter.html` (vuoto), `preview/etichette.json` (tassonomia
vecchia), `docs/02-piano.md`. Il branch di default torna `master`.

**Niente plugin.** Le skill e gli agent stanno in `redazione/.claude/` e si
caricano perché il repo è agganciato a ogni sessione: è il meccanismo nativo
che Claude Code usa per i repo aggiuntivi di una sessione, non passa da
marketplace, non ha bisogno di un setup script che installi nulla, e non può
divergere per copia. Le rules (che i plugin non supportano e che oggi si
copiano con `sync-rules`) non esistono più: le tre regole vere stanno in
`CLAUDE.md`.

### 3.2 L'ambiente cloud

Un ambiente solo, `redazione`, con tre sorgenti agganciate: `redazione`,
`diset-viz`, `pid`. Setup script in `redazione/ambiente/setup.sh`, che fa:
`pip install` di `motore/`, `npm ci` di diset-viz se serve la build, le
variabili pubbliche. Nessuna installazione di plugin.

Le credenziali che l'ambiente deve avere e che oggi mancano o sono scadute:

- `GA4_SA_CREDENTIALS_JSON`: c'è e funziona (GA4 di entrambi i siti, Search
  Console `sc-domain:` di entrambi).
- Un token OAuth **non scaduto** per Blogger e AdSense: il consent screen va
  portato da Testing a Production, altrimenti ogni sette giorni si rompe. Da
  fare a mano una volta, è la sola cosa che richiede te.
- `gcloud` con un service account (non ADC utente) se una run deve toccare
  Cloud Run. Oggi nessuna run editoriale ne ha bisogno: il deploy di
  divarioitalia lo fa Cloud Build al push su `master`, quello di pid è un
  incolla manuale. Si può rinviare.

Gli ambienti `divarioitalia` e `PID` si archiviano quando l'ultima Routine è
migrata (fine della settimana 3).

### 3.3 La pipeline, una sola, lineare

```
coda  ->  brief  ->  ricerca  ->  scrittura  ->  verifica  ->  PR  ->  merge (tu)  ->  pubblicazione
 py       py        agent 1      agent 2       agent 3      py         GitHub         py o Cloud Build
```

Ogni run è una sessione cloud (Routine o lanciata da te) che esegue nell'ordine:

1. **Coda** (`motore coda <sito>`): sceglie il pezzo. Per divarioitalia ordina
   le pagine indicatore per impression in Search Console negli ultimi 90
   giorni, filtrate su dati aggiornati e prosa incompleta o mai riscritta. Per
   praticandoildiritto ordina i post per clic, incrociati con l'audit di
   vigenza (riferimenti modificati o abrogati). Puoi forzare un codice o un
   post con un argomento. La coda non calcola priorità interne: usa i lettori.
2. **Brief** (`motore brief <sito> <pezzo>`): un file Markdown di una pagina
   che chi scrive legge per primo. Contiene, in quest'ordine:
   - **una frase su che cosa misura**, scritta per un lettore, non la
     definizione Istat (che va in fondo);
   - **la fotografia**: le tre o quattro cifre che contano (primo, ultimo,
     valore di mezzo, distanza Nord-Mezzogiorno, il movimento dell'ultimo anno
     e di dieci anni), già arrotondate come si scrivono;
   - **le domande che i lettori fanno** a Google su quella pagina (le query
     reali di Search Console, con impression);
   - **i parenti** nel catalogo, con link canonico e valori;
   - **le cifre complete** in appendice, con l'anno di ognuna;
   - per pid: il post attuale, i riferimenti normativi con stato di vigenza e
     URI ELI, i post collegati.
3. **Ricerca** (agent `ricercatore`, sonnet, web): risponde a tre domande
   scritte nel brief, non "cerca eventi". Che cosa spiega questa fotografia
   secondo le fonti istituzionali (Istat rapporto annuale, Banca d'Italia,
   Svimez, Eurostat, ministeri; per pid: Normattiva, Cassazione con estremi,
   Consiglio nazionale forense)? Che cosa cambia per chi ci vive? Che cosa è
   successo nell'ultimo anno che il lettore deve sapere? Restituisce al massimo
   cinque fonti, ognuna con: URL, data, la frase che dice, e **il contesto che
   dà**. Una fonte senza contesto non entra. Budget nel prompt: quattro
   ricerche, sei fetch.
4. **Scrittura** (agent `scrittore`, opus): un pezzo, forma libera, 500-900
   parole, che risponda alla domanda del lettore nelle prime tre righe e
   racconti la fotografia prima delle classifiche. Legge un esempio da
   `content/esempi/` prima di scrivere. Cifre solo dal brief, fonti solo dalla
   ricerca. Riceve la skill `voce` (le regole assolute e cinque regole di
   mestiere, non trenta divieti).
5. **Verifica** (agent `verificatore`, opus, con `motore verifica` in Bash):
   un passaggio. Il comando deterministico controlla cifre, anni, link e che
   ogni URL risponda. L'agent rilegge una volta sola con quattro domande: c'è
   una cifra fuori dai dati, una causa che le fonti non danno, una fonte che
   non dice quello che il testo le attribuisce, una frase che un lettore non
   prende al primo passaggio? Rilievi con gravità. `alta` torna allo scrittore
   (massimo due giri), `media` e `bassa` viaggiano nel corpo della PR.
6. **PR** (`motore pr`): branch da `origin/master` fresco, un commit, una PR
   con il pezzo leggibile nel corpo (non solo il JSON), i rilievi aperti, il
   costo, e il link alla pagina di anteprima. Nessun trailer nei commit.
7. **Merge**: tu, dal telefono, dall'app GitHub. Se non fai merge in sette
   giorni la PR resta e `STATO.md` te lo dice.
8. **Pubblicazione**: per divarioitalia è il merge stesso (Cloud Build
   deploya). Per praticandoildiritto è una Routine che, dopo il merge, fa
   `PUT` del post intero su Blogger e verifica la lunghezza del corpo
   restituito; finché `aggiorna-post` usa `PATCH` non si sblocca.

Costo atteso per pezzo: fra 3 e 6 $, il livello delle run di agosto senza
plugin. Sopra i 10 $ la run scrive un rilievo in `STATO.md` e non si ripete
finché non lo leggi.

### 3.4 Il contratto del pezzo (`REDAZIONE.md`)

Un documento solo, tre pagine, per entrambi i siti. Contiene:

- **A chi scriviamo.** Per divarioitalia: chi ha cercato "X per regione" e
  vuole capire dove sta la sua regione e perché. Per praticandoildiritto:
  l'avvocato o il praticante che deve depositare un atto domani mattina.
- **La domanda a cui ogni pezzo risponde nelle prime tre righe**, e la
  fotografia subito dopo. Poi il perché, con fonti. Poi che cosa cambia per le
  persone. Poi i limiti. L'ordine è consigliato, non imposto.
- **La voce**, in cinque regole e non trenta: frasi che si prendono al primo
  passaggio; una cifra ogni volta che serve e non una in più; nessun termine da
  statistico nel testo; nessuna causa che le fonti non danno; il lettore non
  sente mai parlare di "dossier", "serie", "dati riportati".
- **Le regole assolute**: cifre solo dai dati, fonti solo verificate, link
  canonici, niente `—` `–` `;` `…`, nessun consiglio sul caso concreto (pid),
  nessuna norma dichiarata vigente senza la tabella (pid).
- **Le tre guardie** e la scala di gravità.
- **Per pid, il formato "Modello" in otto parti** già scritto in
  `docs/04-piano-seo-contenuti.md`: a che cosa serve, quando sì e quando no,
  termini e scadenze con l'articolo che li stabilisce, riferimenti con URI
  ELI, fac-simile, errori frequenti, tre domande, atti collegati.

Quello che non contiene più: la rubrica a dieci criteri, i quattro assi, i
pavimenti, il lint, la `burstiness`, il conteggio dei tell, la skill
`scrittura-italiana` da 429 righe più nove reference. Gli esempi in
`content/esempi/` fanno il lavoro che quelle regole non hanno fatto.

### 3.5 Il registro: intenti, piani, attività, monitoraggio, pubblicati

Oggi queste cinque cose stanno in cinque posti in tre repo (intent e roadmap
in platform, PR e cruscotto in diset-viz, i doc `00-stato` in pid, le sessioni
nell'app). Domani stanno in `redazione/registro/`, cinque file, e le run li
tengono aggiornati. Tu li leggi dall'app GitHub, in ordine:

| file | che cosa contiene | chi lo scrive |
| --- | --- | --- |
| `STATO.md` | la vista unica: da fare tu, ultime run, la settimana, la coda | ogni run, e la Routine "Stato" alle 08:00 |
| `IDEE.md` | gli intenti, una riga ciascuno: `- [ ] sito, cosa, perché, chi l'ha proposta, data`. Tre stati: idea (casella vuota), in corso (link alla PR), fatto (link alla pagina). La coda ne propone, tu ne aggiungi dal telefono modificando il file | tu, la coda, le run |
| `PIANO.md` | il piano in corso: questo documento ridotto alle tappe, con data e esito di ognuna. Un piano solo alla volta | tu e la Routine "Settimanale" |
| `PUBBLICATI.md` | l'indice di tutto ciò che è uscito, per sito: data, pezzo, URL, PR, costo, clic a 30 giorni. Generato dai contenuti dei due siti e da Search Console | la Routine "Stato" |
| `LEZIONI.md` | una riga per lezione, con data e la run che l'ha pagata | le run quando si fermano, tu |

Le attività in volo restano dove GitHub le mostra meglio: **una PR per pezzo**,
con il testo leggibile nel corpo, e **un'issue per ogni run fermata**
(template già esistente in diset-viz, da spostare qui). `STATO.md` le elenca
con il link. Non serve un project board, non serve una tabella su Supabase:
un file per lo stato, una PR per il lavoro, un'issue per il guasto.

`STATO.md`, una schermata:

```
# Redazione, 4 settembre 2026, 08:00

## Da fare tu
- PR diset-viz#213 aperta da 1 giorno: ims-MULTI_ZONA_INQUINAMENTO (2 rilievi media)
- pid: token Blogger scaduto il 3/9, rifare il consenso
- IDEE.md: 3 idee proposte dalla coda, da confermare o cancellare

## Ultime run
| quando | sito | pezzo | esito | costo | PR |
| 4/9 07:30 | divarioitalia | ter-104 | PR aperta | 4,2 $ | #215 |
| 3/9 07:30 | divarioitalia | ter-13 | pubblicato | 3,8 $ | #204 |
| 3/9 07:30 | praticandoildiritto | procura-speciale-querela | fermato: 2 fonti non rispondono | 1,1 $ | issue #7 |

## Questa settimana
- divarioitalia: 4 pubblicati, 1 in PR, 1 fermato. Clic 30 gg: 96 (+12%)
- praticandoildiritto: 0 pubblicati (bloccato), audit: 83 da rivedere

## Piano: settimana 2 di 4, tappa "cinque pezzi letti da te": 3 su 5

## La coda (prossimi 5)
...
```

Tre canali verso il telefono, tutti senza codice nuovo:

1. **`registro/`** nell'app GitHub: la vista completa in cinque file, il primo
   basta quasi sempre.
2. **Le PR** nell'app GitHub, con il pezzo leggibile nel corpo: il merge è un
   tocco. Un'idea nuova è una riga in `IDEE.md`, modificabile dall'app.
3. **Le notifiche push delle Routine** (l'opzione esiste per le Routine che
   creano una sessione nuova): una riga a fine run, "ter-104: PR aperta, 4,2 $".

Il cruscotto `/_pipeline` su Supabase, con battito e consuntivo, si spegne: era
una vista sulle run del workflow, e il workflow non c'è più. Se dopo un mese
vuoi un grafico dei clic per pagina riscritta, si fa una pagina statica
generata da `motore stato --html` a partire da `PUBBLICATI.md`, non un'app.

### 3.6 Le Routine

Cinque, tutte nell'ambiente `redazione`, tutte con sessione nuova a ogni run:

| Routine | quando (Roma) | che cosa fa |
| --- | --- | --- |
| Pezzo divarioitalia | ogni giorno 07:30 | la pipeline del §3.3 su un pezzo dalla coda |
| Pezzo praticandoildiritto | lun, mer, ven 07:30 | la pipeline su un post da aggiornare (dopo lo sblocco) |
| Stato | ogni giorno 08:00 | `motore stato`: riscrive `STATO.md` e `PUBBLICATI.md`, push su `redazione/master` (solo `registro/`) |
| Metriche | ogni giorno 05:00 | GA4 e Search Console dei due siti in `redazione/dati/metriche/` (CSV, un file al giorno). Sostituisce il Cloud Run Job `motore-notturno` e BigQuery |
| Settimanale | venerdì 17:00 | un commento su un'issue fissa "Settimana": cosa è uscito, clic prima e dopo, costo, cosa si è fermato. Nessun postmortem, nessun direttore |

Le altre nove Routine di oggi si eliminano. Quelle disattivate da agosto pure.

---

## 4. Le due pipeline, sito per sito

### 4.1 divarioitalia

**Priorità editoriale**, che nessun documento di oggi dice: riscrivere per il
lettore le pagine che Google già mostra. Sono circa cento indicatori con
impression, e i primi venti fanno la maggior parte dei clic. La coda parte da
lì, non dai 634.

**Il pezzo tipo** (esempio di struttura, non uno schema): titolo che contiene la
query ("Livello di istruzione per regione: dove l'Italia si ferma alla terza
media"); tre righe di risposta con la fotografia; una sezione su che cosa vuol
dire (un lettore campano, uno trentino); una sul perché secondo le fonti; una
sul movimento (dieci anni in tre frasi); una sui limiti; le fonti. Fra 500 e
900 parole. La tabella dei valori e la serie storica le rende già la pagina.

**Dati**: `motore dossier` è `lab.dossier` senza Jenks, coefficiente di
variazione, volatilità e rotture di serie. Restano: classifica, media semplice
delle regioni (dichiarata come tale), macroaree, delta a 1, 5 e 10 anni,
massimo e minimo storici, anni mancanti, parenti con valori.

**Pubblicazione**: `content/indicators/<key>.json` come oggi, con `lead`,
sezioni libere con `h` e `role` (il renderer già accetta ordine e ripetizioni),
`fonti`, `vintage`, `scritto_il`, `costo`. Il file diventa anche il record: non
serve una tabella.

**SEO tecnica**: resta quella di `.claude/rules/app.md`, che va in
`diset-viz/CLAUDE.md` in dieci righe. Un audit SEO settimanale automatico non
serve finché le pagine non sono riscritte.

### 4.2 praticandoildiritto

**Priorità editoriale**: aggiornare, non scrivere. I 20 post che portano i
clic, nell'ordine dei clic, riscritti nel formato "Modello" con vigenza
verificata. Un post nuovo al mese, sulle query in posizione 8-20 di Search
Console. Regola del piano SEO che resta valida: tre aggiornati per ogni nuovo.

**La tabella di vigenza** si estende prima di tutto alle leggi speciali che
contano per i post con traffico (d.lgs. 149/2022 Cartabia, d.P.R. 115/2002
spese di giustizia, d.P.R. 1124/1965 INAIL, l. 89/2001, d.lgs. 28/2010
mediazione). Sei atti coprono la maggior parte dei 294 riferimenti
`fuori-tabella`. Normattiva li espone in open data come i codici.

**Giurisprudenza**: si cita solo con sezione, data e numero, e solo se il
ricercatore ha aperto la pagina che la riporta (Cassazione, Corte
costituzionale, Consiglio di Stato, o la rivista che la pubblica per esteso).
Una sentenza senza pagina aperta non entra. Non esiste ancora una tabella
interrogabile: la regola è la fonte aperta, e sta fra le guardie bloccanti.

**Responsabilità**: ogni post porta autore, data di ultimo aggiornamento, riga
"verificato su Normattiva il <data>" e l'avvertenza che descrive il diritto e
non il caso concreto. Il merge è sempre tuo. Un post con riferimento abrogato
resta online con un avviso in testa, come già previsto.

**Sblocco della pubblicazione**, in ordine: (1) `blogger.py` passa a `PUT`
del corpo intero con verifica della lunghezza, con un test che lo prova su un
post di prova; (2) consent screen in Production e token nuovo; (3) tre post
aggiornati e pubblicati a mano da te dal JSON che la pipeline produce; (4) da
lì la Routine pubblica dopo il merge. Fino al punto 3 `pubblicazione_bloccata`
resta vero.

**Il tema Blogger** resta manuale, come documenta bene `docs/05`. Non si
automatizza il pannello con un browser pilotato.

### 4.3 Un terzo sito domani

Aggiungere un sito costa un file `siti/<nome>.md` e tre funzioni in `motore/`
(coda, dossier o brief, pubblica). Vecchio Conio, che platform già misura, è
il candidato naturale: gli articoli sono Markdown in un repo, la pubblicazione
è un commit.

---

## 5. Le tappe

Oggi è giovedì 4 settembre. Quattro settimane, e poi due mesi senza toccare la
struttura.

### Settimana 1, fino all'11 settembre: fermare e fondare

- Disattivare tutte le Routine tranne "Pezzo del giorno", che passa a un
  prompt di sei righe senza Gate A (parte dalla coda, apre la PR, si ferma).
- Creare `redazione` (svuotare `platform` con tag `archivio-2026-09`, o repo
  nuovo: consiglio il repo nuovo, così la storia di platform resta intatta e
  il nome smette di promettere un orchestratore).
- Scrivere i cinque documenti. `REDAZIONE.md` lo scrivo io, tu lo correggi:
  è il file che decide la qualità.
- Portare `lab/dossier.py`, `lab/controlla.py`, `lab/coda.py`, il client
  Google di pid e `norme/` di platform in `motore/`, spogliati. Meno di 2.000
  righe in tutto.
- Ambiente `redazione` con setup script versionato. Consent screen Google in
  Production e token nuovo (tu, dieci minuti).
- Confrontare questo piano con i documenti su Drive e correggerlo.

### Settimana 2, fino al 18 settembre: la pipeline su divarioitalia

- Brief nuovo, tre agent, `motore verifica`, `motore pr`.
- Cinque pezzi sui cinque indicatori con più impression (ter-104, ter-281,
  ter-13, ter-901, ter-12), lanciati a mano, letti da te. Si aggiusta il brief
  e la skill `voce` finché due pezzi su tre ti convincono alla prima lettura.
  Questo è l'unico "eval" che resta.
- Routine "Pezzo divarioitalia" sul nuovo prompt.

### Settimana 3, fino al 25 settembre: lo stato e la pulizia

- `motore stato`, `STATO.md`, Routine "Stato" e "Metriche", notifiche push.
- Spegnere `/_pipeline`, le tabelle Supabase, il Cloud Run Job `motore-notturno`,
  gli ambienti `divarioitalia` e `PID`.
- Togliere da `diset-viz` tutto ciò che il §3.1 elenca, in una PR sola,
  con i test del sito ancora verdi.

### Settimana 4, fino al 2 ottobre: praticandoildiritto

- `blogger.py` in `PUT` con test. Estensione della tabella di vigenza a sei
  atti. Formato "Modello" nella skill.
- Tre post aggiornati (procura speciale per querela, opposizione INAIL,
  intimazione testi: i tre con più clic), pubblicati a mano da te.
- Routine "Pezzo praticandoildiritto" e sblocco.

### Poi: ottobre e novembre, non si tocca

- Si guardano i clic delle pagine riscritte a 30 giorni, nel report del
  venerdì.
- Un cambio di prompt al mese al massimo, provato su tre pezzi.
- A fine novembre si decide sul terzo sito.

---

## 6. Che cosa si butta, in una tabella

| oggi | domani | perché |
| --- | --- | --- |
| plugin `motore`, marketplace, `sync-rules`, setup script non versionato | `redazione/.claude/` caricato come repo agganciato | ha rotto le Routine il 4/9, e le copie divergono (già successo a `team_monitor.py`) |
| 21 agent, 13 skill, 8.037 righe di prompt | 3 agent, 3 skill, < 600 righe | 10 agent e 6 skill mai eseguiti |
| intent a 6 stati e 6 tipi, Gate A, roadmap, ledger, evals, golden, bande | `registro/` (idee a 3 stati, piano, stato, pubblicati, lezioni), coda dai lettori, PR | zero intent approvati, ledger di un giorno, roadmap stantia, 2 bande cieche |
| `indicatore-lite` (9 agenti) + Agent Team (5 teammate + lead) + memorie | una pipeline lineare a 3 agent | il confronto lite/team non è mai stato misurato; il team costa 2-8 volte tanto |
| 5 strati di verifica, rubrica a 10 criteri con pavimenti, lint | 3 guardie deterministiche + 1 lettura con gravità | il difetto vero l'ha trovato il sesto strato |
| `content/STYLE.md` + rubrica + 4 skill di scrittura | `REDAZIONE.md` + `content/esempi/` | sei documenti sulla stessa cosa |
| cruscotto `/_pipeline`, Supabase, battito, consuntivo, `team_monitor.py` | `STATO.md` + PR + push | guarda run che non esistono più |
| 14 documenti + 7 rules + archive in diset-viz, 32 + 94 in platform, 18 in pid | 5 in redazione, 1 `CLAUDE.md` per sito | il contesto di ogni sessione |
| Cloud Run Job + BigQuery per le metriche | una Routine e CSV in git | due siti, due numeri al giorno |
| 2 ambienti cloud, 9 Routine | 1 ambiente, 5 Routine | |

---

## 7. Che cosa mi serve da te

1. Farmi leggere la cartella Drive, in uno di due modi: abilitare il
   connettore Google Drive nelle impostazioni connettori di questa chat
   (il più rapido), oppure abilitare l'API Drive sul progetto `nil-automata`
   e condividere la cartella in lettura con
   `ga4-mcp@nil-automata.iam.gserviceaccount.com`. Con uno dei due
   correggo il piano dove sbaglia e porto i tuoi documenti in `registro/`.
2. Dire se `redazione` è un repo nuovo o `platform` svuotato. Consiglio nuovo.
3. Consent screen Google in Production e un token nuovo per Blogger e AdSense
   (dieci minuti nella console, una volta).
4. Un sì sulla settimana 1. Da lì eseguo: repo, documenti, migrazione del
   codice, ambiente, prime cinque pagine da leggere.
