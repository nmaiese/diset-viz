# Feature request: contesto verificato nel workflow dell'officina

**Stato:** proposta, 2026-08-07  
**Proprietario:** officina editoriale  
**Workflow interessato:** `.claude/workflows/produci-indicatori.js`  
**Decisione richiesta:** approvare il canary, non l'attivazione diretta in
produzione.

## Problema

L'officina sa descrivere la geometria di una serie, ma il corpus contestuale è
ancora troppo piccolo per spiegare in modo verificabile eventi, discontinuità e
dinamiche. Il caso guida è un cambiamento nel 2020: il pacchetto può vedere la
rottura nei dati, ma senza una fonte non può collegarla alla pandemia, neppure
come semplice coincidenza documentata.

La ricerca non deve entrare nello scrittore. Deve produrre memoria durevole e
verificata prima che le bozze vengano generate.

## Decisione architetturale

Estendere il dynamic workflow esistente, senza introdurre un secondo workflow
editoriale.

```text
preflight
  -> pacchetti preliminari
  -> acquisizione del solo contesto mancante
  -> verifica e registrazione dei claim
  -> pacchetti definitivi
  -> due bozze
  -> giudizio cieco
  -> revisione
  -> pubblicazione e lint
```

Questa forma segue il contratto dei dynamic workflow di Claude Code: lo script
possiede branching, parallelismo e risultati intermedi; i subagent ricevono un
compito stretto. Il workflow non legge o scrive direttamente il filesystem e
non richiama un altro workflow.

Riferimenti ufficiali:

- [Dynamic workflows](https://code.claude.com/docs/en/workflows)
- [Subagent](https://code.claude.com/docs/en/sub-agents)
- [Hook](https://code.claude.com/docs/en/hooks)
- [Best practice Claude Code](https://code.claude.com/docs/en/best-practices)

La versione verificata durante la proposta è Claude Code 2.1.224.

## Contratto di invocazione

Conservare la lista di codici attuale e aggiungere un oggetto facoltativo:

```js
["ter-30", "ter-105"]
```

```js
{
  codes: ["ter-30", "ter-105"],
  contextMode: "auto"
}
```

Modalità:

- `auto`: usa il corpus e cerca soltanto ciò che manca o è scaduto;
- `reuse`: nessuna rete, usa soltanto il corpus corrente;
- `refresh`: forza una nuova acquisizione;
- `shadow`: misura candidati e decisioni senza mostrarli agli scrittori.

Se `CLAUDE_CODE_SUBAGENT_MODEL` forza un modello diverso da quello sottoposto a
canary, il preflight registra l'override e interrompe la run.

## Fasi nuove

### Pacchetti preliminari

Il preparatore esistente monta i pacchetti e restituisce percorsi più un
riepilogo piccolo e strutturato:

- fingerprint di vintage, anni e angoli;
- claim già pertinenti;
- angoli che richiedono contesto;
- stato `ready`, `missing`, `stale` o `blocked`;
- fabbisogni con tema, anni e territori.

Il contenuto completo resta su disco: non deve transitare nell'output del
subagent.

### Acquisizione

Per ogni indicatore `missing` o `stale`:

1. uno scout restituisce al massimo tre candidati;
2. un curatore indipendente prova a respingerli;
3. un verificatore deterministico controlla schema, URL e citazione;
4. un registratore meccanico salva in modo seriale solo i claim ammessi;
5. il preparatore ricostruisce i pacchetti definitivi.

Un errore di rete o di esecuzione produce `unverified`, mai `rejected`. Un 403,
un 503 o un PDF non verificabile non dimostrano che la fonte non esista.

### Angoli eleggibili

Il pacchetto definitivo associa i claim ai singoli angoli:

- due o più angoli eleggibili: due bozze, come oggi;
- un solo angolo eleggibile: una bozza e nessun confronto artificiale;
- nessun angolo eleggibile: blocco prima della scrittura;
- un angolo dinamico privo del contesto necessario non arriva allo scrittore.

Giudizio, revisione, giro di ritorno sul lint e contabilità degli esiti restano
quelli del workflow corrente.

## Subagent

### `scout-contesto`

- modello Haiku;
- strumenti `Read`, `WebSearch`, `WebFetch`, `Skill`;
- applica `untrusted-web`;
- non ha Bash, Edit o Write;
- scopre ed estrae, ma non ammette e non salva.

### `curatore-contesto`

- modello Opus 4.8;
- solo Read;
- riceve fabbisogno e candidati congelati;
- non torna sul web;
- restituisce `accept`, `reject` o `unverified` con pertinenza temporale,
  territoriale e uso massimo consentito.

### `registratore-contesto`

- solo Bash;
- riceve il comando completo;
- un hook `PreToolUse` permette soltanto il comando dedicato di verifica e
  scrittura del corpus;
- non prende decisioni editoriali.

I prompt permanenti seguono la regola locale `ricevi, restituisci, vietato`. Il
background vive nei fabbisogni e nei pacchetti generati.

## Memoria del contesto

La memoria è `data/corpus/`, non la sessione Claude. Il resume di un dynamic
workflow conserva risultati soltanto nella stessa sessione, quindi ogni fatto
destinato a run future deve essere versionato su disco.

Ogni claim aggiunge ai campi attuali:

- `kind`: `event`, `analysis`, `benchmark`;
- `usage`: `coincidence`, `attributed_analysis`, `causal_attribution`,
  `external_comparison`;
- periodo e territori;
- data di pubblicazione e verifica;
- eventuali numeri con misura, unità, periodo, territorio e aggregazione;
- `event_key` facoltativo per il riuso fra indicatori.

Regole:

- una testata può sostenere un'analisi attribuita;
- una testata da sola non autorizza un nesso causale;
- la causalità richiede una fonte primaria o uno studio che la dichiari;
- un evento autorizza la coincidenza, non la causa;
- un aggregato nazionale ponderato non è la media semplice delle regioni;
- nessuna conversione numerica viene affidata al modello;
- la prima versione ammette automaticamente soltanto HTML verificabile.

Una nuova testata non può essere ammessa e sostenere un claim nella stessa
run: diventa utilizzabile dal tick successivo.

## Trasparenza e provenienza

Ogni articolo con `origine: officina` deve portare meccanicamente:

- `ai_generated: true`;
- workflow e versione;
- modello effettivo;
- identificatore della lavorazione;
- fingerprint del pacchetto;
- claim usati e timestamp.

Il renderer mostra alla prima esposizione:

> Testo generato con intelligenza artificiale da dati e fonti verificati
> automaticamente. Nessun controllo editoriale umano prima della pubblicazione.

La disclosure è necessaria per il testo AI su questioni di interesse pubblico
senza revisione umana sostanziale. I controlli automatici della pipeline non
sono revisione umana.

Riferimenti:

- [Commissione europea, articolo 50](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [Icone UE per contenuti AI](https://digital-strategy.ec.europa.eu/en/policies/eu-icons-labelling-ai-generated-content)
- [Codice europeo di trasparenza](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)

Una smentita critica nasconde la prosa, mantiene disponibile la pagina dati,
pubblica la nota di correzione e rimette l'indicatore nello stesso workflow.

## Fuori perimetro

- agent team;
- un secondo workflow richiamato dall'officina;
- web nello scrittore;
- filesystem o shell usati direttamente dallo script del workflow;
- C2PA nella prima iterazione;
- estrazione automatica da PDF non riproducibile;
- ampliamento autonomo illimitato del registro delle testate.

## Canary e criteri di accettazione

Prima di cambiare il default:

1. aggiungere un'eval congelata per eventi, analisi, geografia, periodo,
   aggregazioni e causalità;
2. eseguire `contextMode: "shadow"` su 8-10 indicatori, incluso `ter-30` e un
   caso con rottura nel 2020;
3. eseguire una canary reale su 2-3 indicatori;
4. annotare modello, prompt, costo ed esito in `docs/CANARY.md`;
5. eseguire suite completa, lint globale, audit frontend e `git diff --check`.

Il canary passa soltanto con:

- zero URL o citazioni inventati;
- zero abbinamenti errati di anno o territorio;
- zero causalità oltre l'uso autorizzato;
- ogni claim ammesso verificato testualmente;
- guasti tecnici distinti dalle smentite;
- nessuna regressione nelle eval esistenti;
- disclosure e provenienza presenti in pagina, anteprime e feed;
- costo e token leggibili per fase in `/workflows`.

## Esito atteso

L'officina riceve contesto più ricco senza perdere le proprietà che la prima
run ha dimostrato utili: pacchetti congelati, pochi strumenti, risultati
strutturati, selezione misurabile e cancello deterministico. La ricerca viene
pagata soltanto quando la memoria non basta e il suo risultato diventa
riutilizzabile da articoli futuri.
