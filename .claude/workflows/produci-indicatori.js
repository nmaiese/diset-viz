export const meta = {
  name: 'produci-indicatori',
  description: 'Scrive gli articoli indicatore: pacchetti su disco, due bozze da due angoli, giudizio cieco, selezione deterministica, lint',
  whenToUse: 'Per smaltire l\'arretrato degli indicatori senza articolo, o per riscrivere quelli scaduti sui dati. Prende la lista dei codici in args.',
  phases: [
    { title: 'Pacchetti', detail: 'un agente per tutta la run: scrive i pacchetti su disco' },
    { title: 'Scrittura', detail: 'due bozze per indicatore, dai due angoli piu\' forti' },
    { title: 'Giudizio', detail: 'due giudici ciechi, ordine invertito fra loro' },
    { title: 'Revisione', detail: 'la diagnosi si applica, o si dichiara perche\' no' },
    { title: 'Lint', detail: 'cancello deterministico, nessuna decisione editoriale' },
  ],
}

// La regola da cui discende tutto il resto: **un agente riceve, non cerca.**
//
// Non e' un principio, e' una misura. Prima run, dieci agenti, contratto di
// misura in scripts/baseline_tokens.py (deduplica per requestId, e conta le
// iterazioni advisor che nessun campo aggregato porta):
//
//   ruolo         turni  prompt/turno   costo
//   scrittori       162        71.568   $2,90-3,66 ciascuno
//   pubblicatori     58        66.841   $1,78-1,80 ciascuno
//   giudici           4        30.434   $0,14 ciascuno
//
// Il prompt di un giudice e' PIU' GRANDE del prompt d'apertura di uno
// scrittore (26.676). Stesso modello, stesso schema. La differenza non e' il
// contesto: sono i turni, e i turni erano ricerca. Quattro turni a scrittore
// per trovare l'interprete, poi lo stesso grep ripetuto da tutti e quattro per
// scoprire quali `role` fossero legali.
//
// E il costo dei turni e' quadratico, non lineare: la lettura di cache cresce
// di ~1.950 token a turno, perche' ogni risultato di tool resta in coda e
// viene riletto da tutti i turni dopo. Il modello n*base + n^2*g/2 prevede
// 3,90 M contro 3,70 M osservati. Dimezzare i turni divide il costo per
// quattro.
//
// Da qui: i pacchetti si montano una volta sola e vanno su disco, gli agenti
// ricevono percorsi assoluti e comandi esatti, e nessuno ha piu' strumenti di
// quanti gliene servano (i tipi stanno in .claude/agents/).

const INTERPRETE = 'bin/py'
const CARTELLA_PACCHETTI = 'data/packs'

function listaCodici(input) {
  let raw = input
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw)
    } catch (errore) {
      raw = raw.split(/[\s,]+/).filter(Boolean)
    }
  }
  if (Array.isArray(raw)) return raw.map(String)
  if (raw && Array.isArray(raw.codes)) return raw.codes.map(String)
  return []
}

const codes = listaCodici(args)
log(`indicatori richiesti: ${codes.length ? codes.join(', ') : 'nessuno'}`)
if (!codes.length) {
  log(`args e\' arrivato come ${typeof args}: ${JSON.stringify(args)}`)
  log('passa una lista di codici, es. ["ter-105","ter-16"]')
}

// I tipi di agente stanno in .claude/agents/ e sono meta' del disegno: il
// prompt dice che cosa fare, il tipo dice che cosa e' **possibile**. Un
// divieto scritto nel prompt e' un suggerimento, un tool assente e' un fatto.
//
// Il registro dei tipi viene fotografato all'avvio della sessione, quindi una
// sessione aperta prima che i file esistessero non li vede e `agent()` muore.
//
// **Si ferma, non si degrada.** Una prima versione ripiegava su un agente
// senza tipo, e la prova ha mostrato perche' e' sbagliato: senza restrizione,
// due scrittori con prompt identico hanno fatto 2 e 26 turni, e l'advisor e'
// rientrato per il 29% del costo. Cioe' il ripiego toglieva esattamente il
// perimetro che il tipo esiste per imporre, e la run continuava sembrando
// riuscita. Una catena autonoma non degrada il proprio perimetro di sicurezza:
// se non puo' girare come e' stata disegnata, non gira.
function conTipo(prompt, opzioni, tipo) {
  return agent(prompt, { ...opzioni, agentType: tipo }).catch((errore) => {
    if (String(errore && errore.message).includes('not found')) {
      throw new Error(
        `il tipo di agente '${tipo}' non e' nel registro di questa sessione. `
        + `I file stanno in .claude/agents/, ma il registro si legge all'avvio: `
        + `serve una sessione nuova. Non si prosegue senza, perche' senza tipo `
        + `l'agente ha tutti gli strumenti e l'advisor, cioe' proprio cio' che `
        + `il tipo toglie.`)
    }
    throw errore
  })
}

const RUOLI = ['definizione', 'quadro', 'dinamica', 'limiti']

const BOZZA = {
  type: 'object',
  required: ['lead', 'sections', 'corpus', 'angolo'],
  properties: {
    angolo: { type: 'string', description: 'il tipo di angolo su cui apre' },
    lead: { type: 'string' },
    corpus: { type: 'array', items: { type: 'string' } },
    sections: {
      type: 'array',
      items: {
        type: 'object',
        required: ['role', 'h', 'body'],
        properties: {
          // L'enum e' la correzione di un difetto vero: senza, la prima run ha
          // prodotto bozze con ruoli inventati (`scala`, `distribuzione`) che
          // la pagina non sa rendere. Quelle bozze hanno perso il giudizio, ma
          // per fortuna, non per disegno. Piatto e corto di proposito: uno
          // schema complesso costa turni di rivalidazione.
          role: { type: 'string', enum: RUOLI },
          h: { type: 'string' },
          body: { type: 'string' },
          // Gli identificatori di corpus su cui **questa sezione** si appoggia.
          // Sta qui e non in coda all'articolo perche' un'attribuzione senza un
          // posto non e' verificabile, e perche' e' da qui che la pagina deriva
          // le fonti che mostra: `ter-176` scriveva "Eurostat scrive che..." e
          // il blocco fonti visibile portava solo Istat, cioe' un'attribuzione
          // che il lettore non poteva controllare.
          claims: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

// La bozza scelta, piu' il conto di che cosa e' stato fatto della diagnosi.
//
// Esiste perche' una diagnosi che il passo dopo puo' ignorare in silenzio non
// e' un input del processo, e' un commento. Finora il paragrafo freddo veniva
// passato al **pubblicatore**, che nello stesso momento aveva istruzione di non
// migliorare la prosa: due ordini opposti allo stesso agente, e nessun modo di
// sapere quale dei due avesse vinto. Qui la risposta e' obbligatoria e ha tre
// esiti, uno dei quali e' "non l'ho fatto, ed ecco perche'".
const REVISIONE = {
  type: 'object',
  required: ['lead', 'sections', 'corpus', 'angolo', 'feedback'],
  properties: {
    ...BOZZA.properties,
    feedback: {
      type: 'object',
      required: ['stato', 'dettaglio'],
      properties: {
        stato: { type: 'string', enum: ['applicato', 'rifiutato', 'non_applicabile'] },
        dettaglio: { type: 'string', description: 'che cosa hai cambiato, oppure la ragione per cui non lo hai fatto' },
      },
    },
  },
}

const VERDETTO = {
  type: 'object',
  required: ['vince', 'paragrafo_piu_freddo', 'perche'],
  properties: {
    // `pari` esiste perche' un pareggio dichiarato e' un dato e un pareggio
    // travestito da scelta e' rumore. **Non** perche' i pareggi siano il 66,5%:
    // quel numero, in Landesberg (arXiv:2603.12520), misura lo scoring
    // *pointwise* con ~20 valori distinti, e nello stesso paper il giudizio
    // pairwise scende al **3,9%** di pareggi. Citarlo qui era un errore, ed e'
    // il motivo per cui la citazione sta scritta invece che ricordata.
    vince: { type: 'string', enum: ['A', 'B', 'pari'] },
    paragrafo_piu_freddo: { type: 'string' },
    perche: { type: 'string' },
  },
}

// Cio' che il pubblicatore riporta indietro. I `segnala` non fermano niente,
// ed e' giusto: sono misure nuove che il catalogo ancora non rispetta. Ma
// finora venivano calcolati e **persi**, perche' il pubblicatore aveva
// istruzione di ignorarli e restituiva prosa libera. Un segnale che nessuno
// aggrega non e' un segnale: dopo dieci-venti articoli questa lista dice se le
// regole nuove stanno migliorando o se abbiamo solo spostato il difetto.
const PUBBLICATO = {
  type: 'object',
  required: ['scritto', 'rilievi'],
  properties: {
    scritto: { type: 'boolean', description: 'il file esiste in content/indicators/' },
    // Perche' il comando di scrittura ha rifiutato, testuale. `officina.pubblica`
    // esce 2 e nomina la riga che lo ferma (un ruolo doppio, una sezione senza
    // corpo, un livello che l'indicatore non ha): senza questo campo quel
    // motivo moriva nel terminale dell'agente, e il workflow vedeva soltanto un
    // `scritto: false` muto, che non si puo' rimandare a chi scrive.
    errore_scrittura: { type: 'string' },
    parole: { type: 'number' },
    giri_di_lint: { type: 'number' },
    rilievi: {
      type: 'array',
      description: 'ogni rilievo residuo del lint, blocca e segnala, testuale',
      items: {
        type: 'object',
        required: ['rule', 'severity'],
        properties: {
          rule: { type: 'string' },
          severity: { type: 'string', enum: ['blocca', 'segnala'] },
          detail: { type: 'string' },
        },
      },
    },
  },
}

const PACCHETTI = {
  type: 'object',
  required: ['packs'],
  properties: {
    soglia_paragrafi_scoperti: { type: 'number' },
    packs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['code', 'path'],
        properties: {
          code: { type: 'string' },
          path: { type: 'string', description: 'percorso ASSOLUTO del pacchetto' },
        },
      },
    },
  },
}

// --------------------------------------------------------------------------
// stadio 0: i pacchetti, una volta sola per tutta la run
// --------------------------------------------------------------------------
//
// Restituisce **percorsi, non pacchetti**. Cio' che un agente restituisce e'
// output, a venticinque dollari per milione di token: un pacchetto pesa 6-12
// mila token, quindi cinquanta indicatori sarebbero mezzo milione di token di
// puro transito da un agente solo, oltre i limiti pratici di una risposta.
// Un percorso ne pesa venti.

async function prepara(codici) {
  const risposta = await conTipo(
    `Monta i pacchetti per questi indicatori: ${codici.join(' ')}.

Esegui esattamente questi due comandi, dalla radice del repo:

    ${INTERPRETE} -m officina.pacchetti ${codici.join(' ')} --out ${CARTELLA_PACCHETTI} --json
    cat officina/calibrazione_prosa.json

Il primo stampa una riga JSON con i percorsi. Il secondo porta la soglia
\`soglia_paragrafi_scoperti\`, che serve al workflow per scegliere fra le bozze.

Restituisci i percorsi ASSOLUTI e la soglia. Non leggere i pacchetti, non
riassumerli, non scrivere altro: il loro contenuto lo legge chi scrive.
Se un codice non ha un indicatore, omettilo dalla lista invece di inventarlo.`,
    { label: 'pacchetti', phase: 'Pacchetti', schema: PACCHETTI },
    // Ha il suo tipo, e non e' un dettaglio di igiene. Prima girava come
    // `pubblicatore`, cioe' lo stadio che monta i pacchetti aveva il permesso
    // di scrivere in content/indicators/: un perimetro piu' largo di quanto
    // serva e' un perimetro che prima o poi qualcuno usa. Questo tipo ha solo
    // Bash e nemmeno Read.
    'preparatore-pacchetti',
  )
  return (risposta && risposta.packs) ? risposta : { packs: [], soglia_paragrafi_scoperti: 0 }
}

// --------------------------------------------------------------------------
// scrittura
// --------------------------------------------------------------------------

function scrivi(pack, quale) {
  return conTipo(
    `Scrivi la bozza dell'articolo indicatore per ${pack.code}.

Il pacchetto e' qui, e contiene tutto:

    ${pack.path}

Aprilo con Read e leggilo per intero prima di scrivere.

Apri sull'angolo numero ${quale} dell'elenco ANGOLI, non sul primo che ti
viene.${quale === 2 ? ' Il primo angolo lo sta usando un\'altra bozza: tu devi raccontare l\'altra storia, non una variante della stessa.' : ''}

Restituisci la bozza come oggetto strutturato. Non scrivere file.`,
    { label: `scrivi:${pack.code}:${quale}`, phase: 'Scrittura', schema: BOZZA },
    'scrittore-indicatore',
  )
}

// --------------------------------------------------------------------------
// giudizio: due lenti, e l'ordine invertito fra loro
// --------------------------------------------------------------------------
//
// Il bias di posizione e' molto peggio di come l'avevo scritto. Zheng et al.
// (NeurIPS 2023 D&B, MT-Bench), tabella 2, su coppie di risposte simili:
// GPT-4 come giudice e' **coerente allo scambio nel 65% dei casi** e preferisce
// la prima posizione nel 30%; Claude-v1 scende al 23,8% di coerenza con il 75%
// verso la prima. Il "10-15 punti" che avevo citato non sta in quel paper e non
// l'ho ritrovato da nessuna parte.
//
// E la mitigazione raccomandata non e' questa. Testuale: *"call a judge twice
// by swapping the order of two answers and only declare a win when an answer is
// preferred in both orders. If the results are inconsistent after swapping, we
// can call it a tie."* Cioe' **lo stesso giudice, la stessa coppia, i due
// ordini**.
//
// Qui i giudici sono due, con lenti diverse E ordini diversi: i due effetti
// variano insieme, quindi un disaccordo non dice se e' la lente o la posizione.
// Bilancia, non isola. Resta cosi' per una ragione dichiarata e non per
// distrazione: la selezione non poggia sul loro voto (vedi `scegli`), e cio'
// che chiediamo davvero ai giudici e' la diagnosi, dove la posizione conta
// molto meno. Se un giorno il voto tornasse a decidere, questa e' la prima riga
// da riscrivere.

function giudica(code, bozze, lente, inverti) {
  const [prima, seconda] = bozze
  if (!prima || !seconda) return Promise.resolve(null)
  const a = inverti ? seconda : prima
  const b = inverti ? prima : seconda
  return conTipo(
    `Sei un lettore ${lente}.

Due versioni dello stesso articolo su dati pubblici italiani.

--- A ---
${JSON.stringify(a, null, 1)}

--- B ---
${JSON.stringify(b, null, 1)}

1. quale leggerebbe fino in fondo un cittadino curioso ma non esperto?
   Se non c'e' una differenza vera, rispondi \`pari\`.
2. qual e' il paragrafo piu' freddo fra i due testi, cioe' quello corretto e
   senza nessuna ragione per cui a qualcuno importi? Citane un pezzo testuale.`,
    { label: `giudica:${code}:${lente.split(',')[0]}`, phase: 'Giudizio',
      schema: VERDETTO, effort: 'low' },
    'giudice-cieco',
  ).then((verdetto) => {
    if (!verdetto) return null
    // Riporta il voto nell'ordine vero, non in quello che ha visto il giudice.
    const vince = verdetto.vince === 'pari' ? 'pari'
      : (verdetto.vince === 'A') === !inverti ? 'prima' : 'seconda'
    return { ...verdetto, vince, invertito: inverti }
  })
}

// --------------------------------------------------------------------------
// selezione: la misura decide, il modello fa da spareggio
// --------------------------------------------------------------------------
//
// La divisione viene da due misure opposte sullo stesso giudice. Sulla scelta
// e' debole: correlazione entro-prompt 0,27 e accuratezza top-1 31,6%
// (Landesberg, arXiv:2603.12520). Sulla diagnosi funziona: nella prima run
// quattro giudici indipendenti hanno indicato tutti e quattro lo stesso
// paragrafo come il piu' freddo, e da li' e' uscita una correzione vera.
//
// Quindi sceglie la misura, e il modello decide solo quando la misura non
// discrimina. La misura e' la quota di paragrafi sostanziali senza nemmeno una
// cifra: sugli esempi veri di content/esempi/
// sta a 0,25 di mediana e 0,33 di massimo, sui nostri 376 articoli a 0,67,
// con 313 su 376 sopra il massimo degli esempi. Le due distribuzioni quasi non
// si toccano.
//
// (L'ipotesi di partenza era la densita' numerica, il mediatore misurato da
// Thäsler-Kordonouri et al. su 3.135 lettori. Provata su questo corpus non
// regge: i nostri articoli sono MENO densi degli esempi. Sta scritto qui
// perche' altrimenti qualcuno la riprova.)

const PARAGRAFO_MIN_PAROLE = 25
const PARAGRAFI_MIN = 3

function quotaScoperti(bozza) {
  if (!bozza) return null
  const blocchi = [bozza.lead, ...(bozza.sections || []).map((s) => s.body)]
    .flatMap((testo) => String(testo || '').split(/\n\s*\n/))
    .filter((blocco) => (blocco.match(/[^\W\d_]+/gu) || []).length >= PARAGRAFO_MIN_PAROLE)
  if (blocchi.length < PARAGRAFI_MIN) return null
  // "Senza una cifra", e basta: deve essere **identico** a
  // `officina.lint.check_unsupported_paragraphs`, perche' la soglia che usiamo
  // qui e' calibrata su quel conteggio. Una versione precedente lasciava
  // passare anche i paragrafi con un identificatore fra parentesi quadre:
  // due metri diversi confrontati con la stessa soglia, e su 376 articoli quel
  // caso ricorre zero volte, perche' gli identificatori stanno nel campo
  // `corpus` e non nel testo.
  const nudi = blocchi.filter((blocco) => !/\d/.test(blocco))
  return nudi.length / blocchi.length
}

function scegli(bozze, verdetti, soglia) {
  const [prima, seconda] = bozze
  const quote = bozze.map(quotaScoperti)
  const voti = verdetti.filter((v) => v && v.vince !== 'pari')
  const perPrima = voti.filter((v) => v.vince === 'prima').length
  const perSeconda = voti.length - perPrima

  let indice = null
  let motivo = ''
  const [qa, qb] = quote
  if (soglia && qa !== null && qb !== null && (qa > soglia) !== (qb > soglia)) {
    indice = qa > soglia ? 1 : 0
    motivo = `misura: ${(quote[indice] * 100).toFixed(0)}% di paragrafi scoperti contro ` +
      `${(quote[1 - indice] * 100).toFixed(0)}%, soglia ${(soglia * 100).toFixed(0)}%`
  } else if (perPrima !== perSeconda) {
    indice = perPrima > perSeconda ? 0 : 1
    motivo = `giudici ${perPrima}-${perSeconda} (la misura non discrimina)`
  } else if (qa !== null && qb !== null && qa !== qb) {
    indice = qa < qb ? 0 : 1
    motivo = `misura come spareggio: ${(quote[indice] * 100).toFixed(0)}% contro ` +
      `${(quote[1 - indice] * 100).toFixed(0)}%`
  } else {
    indice = 0
    motivo = 'pari su tutto: vince l\'angolo piu\' forte'
  }

  return {
    bozza: indice === 0 ? prima : seconda,
    // Si registrano entrambe le decisioni, sempre. Dopo dieci articoli si
    // potra' misurare quanto il giudice concorda con la misura, invece di
    // assumerlo: se l'accordo e' basso, il giudice esce anche dallo spareggio.
    scelta: { indice, motivo, quote, voti: { perPrima, perSeconda },
              pareggi: verdetti.filter((v) => v && v.vince === 'pari').length },
  }
}

// --------------------------------------------------------------------------
// revisione: la diagnosi si applica dove c'e' ancora il pacchetto
// --------------------------------------------------------------------------
//
// E' lo stadio che chiude la contraddizione peggiore di questa macchina.
// `pubblicatore.md` diceva "se il lint non blocca niente, hai finito: non
// rileggere, non migliorare, non riordinare", e il prompt del workflow diceva
// allo stesso agente, nello stesso momento, "un giudice ha indicato come piu'
// freddo: ... riscrivilo perche' dica perche' importa". Un compito editoriale
// affidato al ruolo definito come meccanico, e nessun modo di sapere quale
// delle due istruzioni avesse vinto.
//
// Lo fa un turno del tipo `scrittore-indicatore`, non un tipo nuovo: ha gia' il
// perimetro giusto (solo Read, nessuna scrittura) e gli serve il pacchetto per
// avere sotto mano il corpus, che e' l'unica cosa con cui un paragrafo freddo
// si puo' riscaldare senza inventare una causa.
//
// Costa un agente in piu' per indicatore, e vale il prezzo solo se la diagnosi
// dei giudici serve a qualcosa: se dopo dieci articoli `feedback.stato` e'
// quasi sempre `non_applicabile`, allora i giudici stanno diagnosticando testi
// che nessuno cambia, e va tolto uno dei due stadi, non tenuti entrambi.

// Cio' che entra nel file, e nient'altro. `feedback` e' contabilita' di
// lavorazione: si registra nell'esito della run, non nella pagina pubblica.
// (`officina.pubblica` scarta comunque i campi che non conosce, ma un comando
// che porta in giro un campo di troppo invita qualcuno a scriverlo.)
function bozzaDaScrivere(bozza) {
  const { lead, sections, corpus, angolo } = bozza
  return { lead, sections, corpus, angolo }
}

// Quante sezioni sono cambiate. "Non toccare nient'altro" e' una frase in un
// prompt, cioe' la categoria di vincolo che questa macchina ha smesso di
// credere sulla parola: qui non blocca niente, ma rende visibile una revisione
// che si allarga invece di restare sul rilievo. Costa zero token.
function sezioniToccate(prima, dopo) {
  const chiavi = (bozza) => (bozza.sections || []).map((s) => `${s.role}\u0000${s.body}`)
  const vecchie = new Set(chiavi(prima))
  return chiavi(dopo).filter((s) => !vecchie.has(s)).length
}

function rivedi(scelto, rilievo) {
  if (!rilievo.voci.length) {
    return Promise.resolve({ ...scelto.bozza,
      feedback: { stato: 'non_applicabile', dettaglio: rilievo.vuoto } })
  }
  return conTipo(
    `Rivedi la bozza gia' scelta per ${scelto.pack.code}, su cio' che segue e su nient'altro.

Il pacchetto e' qui, e resta l'unica fonte di cifre e di contesto citabile:

    ${scelto.pack.path}

Aprilo con Read. Poi guarda il rilievo:

${rilievo.testo}

${JSON.stringify(rilievo.voci, null, 1)}

${rilievo.istruzione}

Non toccare nient'altro. Restituisci la bozza intera, cambiata solo dove serve,
piu' il campo \`feedback\`.

La bozza:
${JSON.stringify(scelto.bozza, null, 1)}`,
    { label: `rivedi:${scelto.pack.code}${rilievo.suffisso || ''}`,
      phase: 'Revisione', schema: REVISIONE },
    'scrittore-indicatore',
  ).then((rivista) => {
    // Un agente che non risponde e' un **guasto**, non un giudizio. Una prima
    // versione ripiegava su `non_applicabile`, cioe' scriveva nel registro dei
    // feedback la frase "il rilievo non si applicava" al posto di "la
    // revisione non e' avvenuta": indistinguibili a valle, e proprio sul campo
    // che serve a decidere se lo stadio vale il suo prezzo. Un guasto contato
    // come esito e' peggio di un guasto, perche' sposta la statistica.
    //
    // `pipeline()` porta l'indicatore a null e lascia gli altri correre: e'
    // esattamente il comportamento voluto, un articolo perso invece di un
    // articolo falsamente a posto.
    if (!rivista) throw new Error(`revisione muta per ${scelto.pack.code}: nessuna risposta dallo scrittore`)
    return rivista
  })
}

// Il rilievo del giudizio: il paragrafo inerte.
function ilFreddo(scelto) {
  return {
    voci: (scelto.freddo || []).filter(Boolean),
    vuoto: 'nessun giudice ha indicato un paragrafo freddo',
    testo: 'due lettori hanno indicato questo come il paragrafo piu\' freddo, '
      + 'cioe\' corretto e senza nessuna ragione per cui a qualcuno importi:',
    istruzione: 'Se quel passaggio e\' nella bozza, riscrivilo perche\' dica perche\' importa, '
      + 'appoggiandoti al corpus del pacchetto. **Se non hai un identificatore per farlo, '
      + 'non riscriverlo e non inventare una fonte**: rispondi `rifiutato` e di\' che il '
      + 'corpus non ha niente su cui appoggiarsi. Se quel passaggio non esiste nella bozza, '
      + 'rispondi `non_applicabile`.',
  }
}

// Il rilievo del comando di scrittura. `officina.pubblica` rifiuta invece di
// scrivere male, e cio' che rifiuta e' sempre una proprieta' della bozza, mai
// un problema di ambiente: quindi torna a chi la bozza l'ha fatta.
function ilRifiuto(motivo) {
  return {
    voci: motivo ? [motivo] : [],
    vuoto: 'il comando di scrittura non ha detto perche\' ha rifiutato',
    suffisso: ':rifiuto',
    testo: 'il comando che scrive l\'articolo ha rifiutato la bozza:',
    istruzione: 'Correggi esattamente cio' + '\' che il messaggio nomina, e nient\'altro. '
      + 'Non e\' un giudizio sul testo: e\' una regola di forma, e il messaggio dice quale.',
  }
}

// Il rilievo del cancello. Torna qui e non al pubblicatore: riparare un
// `blocca` vuol dire riscrivere una frase, e il pubblicatore e' definito come
// meccanico. Senza questo giro l'unico modo che avrebbe di ripararlo sarebbe
// ribattere l'articolo intero come una riga JSON, oppure aprire `sed` sul file
// appena scritto, che e' esattamente l'editoria che gli abbiamo tolto.
function ilBlocco(rilievi) {
  return {
    voci: (rilievi || []).filter((r) => r && r.severity === 'blocca'),
    vuoto: 'il lint non ha bloccato niente',
    suffisso: ':blocca',
    testo: 'il cancello deterministico ha bocciato l\'articolo su questi rilievi:',
    istruzione: 'Riscrivi solo i passaggi che li causano. La regola nominata dice gia\' '
      + 'che cosa non va: non aggirarla, non inventare una fonte per farla tacere, e se '
      + 'non si puo\' rispettare senza inventare, rispondi `rifiutato` con la ragione.',
  }
}

// --------------------------------------------------------------------------
// la catena
// --------------------------------------------------------------------------

const preparati = codes.length ? await prepara(codes) : { packs: [], soglia_paragrafi_scoperti: 0 }
const soglia = preparati.soglia_paragrafi_scoperti || 0
log(`pacchetti pronti: ${preparati.packs.length}, soglia paragrafi scoperti ${soglia}`)

const esiti = await pipeline(
  preparati.packs,

  // Due bozze dai due angoli piu' forti, che sono diversi per costruzione. La
  // scrittura e' la parte economica: la regressione alla media si rompe
  // scegliendo, non prescrivendo.
  //
  // **Sempre due, anche quando l'angolo 2 non esiste**, e non e' una svista: su
  // 11 pacchetti su 594 l'elenco ne ha meno di due. Il ramo non si stringe qui
  // perche' questo lato non sa quanti angoli abbia il pacchetto: il conteggio
  // sta su disco, e portarlo fin qui vorrebbe dire allargare lo schema del
  // preparatore e la sua istruzione, cioe' un cambio di prompt (e un giro di
  // canary) per un ramo di controllo. Il caso e' chiuso dove il numero si sa
  // gia': `packs/build.render` scrive nel pacchetto che l'angolo chiesto non
  // esiste e che cosa fare invece, e `officina/lint.check_angle_was_detected`
  // blocca l'articolo che ne dichiara uno mai rilevato. Restano due bozze e il
  // giudice sceglie lo stesso, il che su quegli 11 e' comunque meglio di una.
  (pack) => parallel([() => scrivi(pack, 1), () => scrivi(pack, 2)]),

  // Due lenti diverse invece di due giudici identici: la ridondanza scopre gli
  // errori di un tipo solo, la diversita' ne scopre di piu'. L'ordine A/B e'
  // invertito fra i due, che bilancia il bias di posizione senza isolarlo:
  // la procedura che lo isola e' lo stesso giudice sui due ordini, e sta
  // scritto sopra perche' non e' quello che facciamo.
  async (bozze, pack) => {
    if (!bozze || !bozze[0] || !bozze[1]) return null
    const verdetti = (await parallel([
      () => giudica(pack.code, bozze, 'distratto, che legge sul telefono', false),
      () => giudica(pack.code, bozze, 'attento, che vuole capire il paese', true),
    ])).filter(Boolean)
    const { bozza, scelta } = scegli(bozze, verdetti, soglia)
    log(`${pack.code}: ${scelta.motivo}`)
    return { pack, bozza, scelta,
             freddo: verdetti.map((v) => v.paragrafo_piu_freddo) }
  },

  // La diagnosi dei giudici si applica qui, con l'obbligo di dire che cosa ne
  // e' stato fatto: `applicato`, `rifiutato` o `non_applicabile`, sempre con la
  // ragione. Vedi `rivedi`.
  async (scelto) => {
    if (!scelto) return null
    const bozza = await rivedi(scelto, ilFreddo(scelto))
    const toccate = sezioniToccate(scelto.bozza, bozza)
    log(`${scelto.pack.code}: feedback ${bozza.feedback.stato}, ${toccate} sezioni toccate `
        + `(${bozza.feedback.dettaglio})`)
    return { ...scelto, bozza, revisione: { ...bozza.feedback, sezioni_toccate: toccate } }
  },

  // Il lint e' l'unico cancello, ed e' deterministico. L'agente qui non
  // giudica e non scrive prosa: scrive il file, esegue il lint, e ripara solo
  // cio' che il lint nomina come `blocca`.
  //
  // Niente `isolation: 'worktree'`, ed e' una decisione con due ragioni. Due
  // agenti che scrivono due file diversi non collidono, e qui non si fa
  // nessuna operazione git, che e' quella che nella catena vecchia faceva
  // collidere gli agenti paralleli. E la cache di prompt e' legata alla
  // directory: un worktree in piu' e' un cache miss pieno per agente.
  async (scelto) => {
    if (!scelto) return null
    let corrente = scelto
    let esito = await pubblica(corrente)
    // Un solo giro di ritorno, e solo per i `blocca`. Uno, non due: se la
    // riscrittura mirata non basta, il problema non e' una frase, ed e' meglio
    // che l'articolo esca con il rilievo scritto nell'esito della run che
    // vederlo girare a spese piene finche' qualcuno se ne accorge.
    const blocchi = (esito) => ((esito && esito.rilievi) || [])
      .filter((r) => r.severity === 'blocca')
    // Due modi di non essere pubblicabile, e vanno trattati uguale: il comando
    // di scrittura ha rifiutato la bozza, oppure il lint l'ha bocciata. Il
    // primo era invisibile: `scritto: false` non lo guardava nessuno, quindi un
    // articolo mai scritto contava fra gli scritti.
    const rifiutato = esito && esito.scritto === false
    const primi = blocchi(esito)
    if (rifiutato) {
      log(`${scelto.pack.code}: la bozza e' stata rifiutata dal comando di scrittura `
          + `(${esito.errore_scrittura || 'senza motivo dichiarato'}), torna a chi scrive`)
      try {
        const bozza = await rivedi(corrente, ilRifiuto(esito.errore_scrittura))
        corrente = { ...corrente, bozza }
        esito = await pubblica(corrente, ':2', true)
      } catch (errore) {
        log(`${scelto.pack.code}: la correzione della bozza e' fallita (${errore.message})`)
      }
    } else if (primi.length) {
      log(`${scelto.pack.code}: il lint blocca (${primi.map((r) => r.rule).join(', ')}), torna a chi scrive`)
      // Qui il guasto della revisione non puo' far cadere l'indicatore, come
      // fa allo stadio prima: l'articolo e' **gia' su disco**, e sparire dagli
      // esiti lo lascerebbe li' con un rilievo bloccante e nessuna riga che lo
      // dica. Si tiene il primo esito, e finisce fra i `bloccati`.
      try {
        const bozza = await rivedi(corrente, ilBlocco(esito.rilievi))
        corrente = { ...corrente, bozza }
        esito = await pubblica(corrente, ':2', true)
      } catch (errore) {
        log(`${scelto.pack.code}: la revisione del blocco e' fallita (${errore.message})`)
      }
    }
    // Cio' che il cancello dice **alla fine**, non all'inizio. Un residuo qui
    // vuol dire che il giro di ritorno non e' bastato, e l'articolo resta su
    // disco con un rilievo bloccante: non e' pubblicabile, e la run non deve
    // contarlo fra gli scritti. "Il lint e' l'unico cancello" e' vero solo se
    // un cancello rosso arriva fino all'esito.
    const residui = blocchi(esito)
    const nonScritto = esito && esito.scritto === false
    if (residui.length || nonScritto) {
      log(`${scelto.pack.code}: BLOCCATO anche dopo la revisione `
          + `(${nonScritto ? (esito.errore_scrittura || 'bozza rifiutata')
                           : residui.map((r) => r.rule).join(', ')})`
          + ': non conta fra gli scritti')
    }
    return { code: scelto.pack.code, scelta: scelto.scelta,
             revisione: scelto.revisione,
             blocchi: primi.length + (rifiutato ? 1 : 0),
             bloccanti: nonScritto
               ? [{ rule: 'bozza-rifiutata', detail: esito.errore_scrittura || '' }, ...residui]
               : residui,
             esito }
  },
)

// `ultimo` accende `--ultimo-tentativo`, e si accende **solo** sulla seconda
// chiamata. Dentro il giro di riparazione la bozza bocciata deve andare su
// disco, perche' il passo 2 la rilegge da li' per riportare i rilievi a chi
// riscrive; quando il giro e' finito no, perche' li' sovrascriverebbe per
// sempre un articolo che il cancello aveva passato. Vedi `officina/pubblica.py`.
function pubblica(scelto, suffisso = '', ultimo = false) {
  return conTipo(
      `Pubblica l'articolo ${scelto.pack.code}. Due comandi, in quest'ordine.

1. Scrivi la bozza. Copia questo blocco intero, dalla prima riga all'ultima:

\`\`\`
${INTERPRETE} -m officina.pubblica ${scelto.pack.code}${ultimo ? ' --ultimo-tentativo' : ''} <<'BOZZA'
${JSON.stringify(bozzaDaScrivere(scelto.bozza))}
BOZZA
\`\`\`

   Se stampa un percorso, l'articolo e' scritto: rispondi \`scritto: true\`.
   Se esce 2, **non e' scritto**: rispondi \`scritto: false\` e copia in
   \`errore_scrittura\` il messaggio esatto. E' sempre un difetto della bozza
   (un ruolo doppio, una sezione senza corpo, un livello che l'indicatore non
   ha, oppure il cancello che blocca all'ultimo tentativo), mai un file da
   andare a cercare, e mai una cosa da aggiustare tu.

2. Esegui \`${INTERPRETE} -m officina.lint ${scelto.pack.code} --json\` e
   **riporta ogni rilievo**, sia \`blocca\` sia \`segnala\`, copiando \`rule\`,
   \`severity\` e \`detail\`. Uscita 2 vuol dire che il codice non ha risolto.

Non ripari niente, nemmeno un \`blocca\`: riparare vorrebbe dire riscrivere la
prosa, e la prosa non e' compito tuo. Un \`blocca\` torna a chi scrive, e il
workflow lo rimanda indietro da solo. I \`segnala\` non fermano niente e non si
nascondono: servono ad aggregare, non a giudicare questo articolo.

Il testo e' gia' deciso e gia' rivisto: non riscriverlo, non riordinarlo, non
migliorarlo. Il tuo unico giudizio e' il lint.`,
      { label: `pubblica:${scelto.pack.code}${suffisso}`, phase: 'Lint', schema: PUBBLICATO },
      'pubblicatore',
  )
}

const fatti = esiti.filter(Boolean)
// Tre numeri e non uno, perche' erano tre cose diverse contate come una.
// `fatti` sono gli indicatori arrivati in fondo alla catena; `bloccati` quelli
// che ci sono arrivati con il cancello ancora rosso; `scritti` sono soltanto
// quelli pubblicabili. Prima `scritti` valeva `fatti.length`, quindi una run
// con il lint rosso su ogni articolo si chiudeva dicendo che aveva scritto
// tutto. E `richiesti - fatti` sono gli indicatori persi per strada (pacchetto
// mancante, bozze non valide, revisione muta): anche quelli non erano visibili.
const bloccati = fatti.filter((f) => (f.bloccanti || []).length)
const scritti = fatti.filter((f) => !(f.bloccanti || []).length)
const persi = codes.filter((code) => !fatti.some((f) => f.code === code))
log(`${scritti.length} scritti su ${codes.length} richiesti`
    + (bloccati.length ? `, ${bloccati.length} bloccati dal lint` : '')
    + (persi.length ? `, ${persi.length} persi per strada: ${persi.join(', ')}` : ''))
return {
  scritti: scritti.length,
  richiesti: codes.length,
  // Gli articoli che stanno su disco con un rilievo bloccante: esistono, e non
  // sono pubblicabili. Vanno rimessi in coda, non dimenticati.
  bloccati: bloccati.map((f) => ({ code: f.code,
    regole: f.bloccanti.map((r) => r.rule) })),
  persi,
  // La traccia per misurare l'accordo fra il giudice e la misura, dopo dieci
  // articoli. Senza registrarlo si finisce per assumerlo.
  scelte: fatti.map((f) => ({ code: f.code, ...f.scelta })),
  // Che cosa e' stato fatto della diagnosi dei giudici, articolo per articolo.
  // Se dopo dieci articoli e' quasi sempre `non_applicabile`, i giudici stanno
  // diagnosticando testi che nessuno cambia, e uno dei due stadi va tolto.
  feedback: fatti.map((f) => ({ code: f.code, blocchi: f.blocchi, ...(f.revisione || {}) })),
  // I rilievi residui, aggregati. Vedi `PUBBLICATO`: il `segnala` si registra,
  // non si ripara e non si perde.
  rilievi: fatti.flatMap((f) => ((f.esito && f.esito.rilievi) || [])
    .map((r) => ({ code: f.code, ...r }))),
}
