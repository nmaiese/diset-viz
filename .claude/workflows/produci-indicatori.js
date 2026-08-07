export const meta = {
  name: 'produci-indicatori',
  description: 'Scrive gli articoli indicatore: pacchetti su disco, due bozze da due angoli, giudizio cieco, selezione deterministica, lint',
  whenToUse: 'Per smaltire l\'arretrato degli indicatori senza articolo, o per riscrivere quelli scaduti sui dati. Prende la lista dei codici in args.',
  phases: [
    { title: 'Pacchetti', detail: 'un agente per tutta la run: scrive i pacchetti su disco' },
    { title: 'Scrittura', detail: 'due bozze per indicatore, dai due angoli piu\' forti' },
    { title: 'Giudizio', detail: 'due giudici ciechi, ordine invertito fra loro' },
    { title: 'Lint', detail: 'cancello deterministico e riparazione mirata' },
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
    'pubblicatore',
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

  // Il lint e' l'unico cancello, ed e' deterministico. L'agente qui non
  // giudica: scrive il file, esegue il lint, e ripara solo cio' che il lint
  // nomina come `blocca`.
  //
  // Niente `isolation: 'worktree'`, ed e' una decisione con due ragioni. Due
  // agenti che scrivono due file diversi non collidono, e qui non si fa
  // nessuna operazione git, che e' quella che nella catena vecchia faceva
  // collidere gli agenti paralleli. E la cache di prompt e' legata alla
  // directory: un worktree in piu' e' un cache miss pieno per agente.
  async (scelto) => {
    if (!scelto) return null
    return conTipo(
      `Pubblica l'articolo ${scelto.pack.code}.

1. Scrivi la bozza in \`content/indicators/\` con
   \`${INTERPRETE} -m scripts.indicator_store\` (leggi il modulo per la forma
   esatta del file, e usa \`${INTERPRETE}\`, mai \`python3\`).
2. Esegui \`${INTERPRETE} -m officina.lint ${scelto.pack.code}\`.
   Uscita 2 vuol dire che il codice non ha risolto: correggi il codice, non
   il testo.
3. Ripara **solo** cio' che il lint nomina come \`blocca\`. Al massimo due giri.
4. Riesegui \`${INTERPRETE} -m officina.lint ${scelto.pack.code} --json\` e
   **riporta ogni rilievo residuo**, sia \`blocca\` sia \`segnala\`, copiando
   \`rule\`, \`severity\` e \`detail\`. I \`segnala\` non vanno riparati e non
   vanno nascosti: servono ad aggregare, non a giudicare questo articolo.

Un giudice ha indicato come piu' freddo: ${JSON.stringify(scelto.freddo)}.
Se quel paragrafo e' nel testo, riscrivilo perche' dica perche' importa,
appoggiandoti al corpus del pacchetto (${scelto.pack.path}). Se non hai un
identificatore per farlo, lascialo com'e' e non inventare una fonte.

La bozza:
${JSON.stringify(scelto.bozza, null, 1)}`,
      { label: `pubblica:${scelto.pack.code}`, phase: 'Lint', schema: PUBBLICATO },
      'pubblicatore',
    ).then((esito) => ({ code: scelto.pack.code, scelta: scelto.scelta, esito }))
  },
)

const fatti = esiti.filter(Boolean)
log(`${fatti.length} indicatori su ${codes.length}`)
return {
  scritti: fatti.length,
  richiesti: codes.length,
  // La traccia per misurare l'accordo fra il giudice e la misura, dopo dieci
  // articoli. Senza registrarlo si finisce per assumerlo.
  scelte: fatti.map((f) => ({ code: f.code, ...f.scelta })),
  // I rilievi residui, aggregati. Vedi `PUBBLICATO`: il `segnala` si registra,
  // non si ripara e non si perde.
  rilievi: fatti.flatMap((f) => ((f.esito && f.esito.rilievi) || [])
    .map((r) => ({ code: f.code, ...r }))),
}
