export const meta = {
  name: 'indicatore-lite',
  description: 'Pipeline lite: dossier, contesto verificato, una bozza, verifica delle cifre e delle fonti, scrittura in data/lab/',
  whenToUse: "Per scrivere articoli indicatore con la catena minima e confrontarla con produci-indicatori. Prende i codici in args, es. ['ter-30']. Senza args sceglie dalla coda editoriale l'indicatore più urgente con dati del 2025.",
  phases: [
    { title: 'Dossier', detail: 'un agente per run: bin/py -m lab.dossier, dai codici o dalla coda' },
    { title: 'Contesto', detail: 'tre scout in parallelo per indicatore: eventi, Europa, perche conta' },
    { title: 'Scrittura', detail: 'una bozza sola, tesi e forma scelte da chi scrive' },
    { title: 'Verifica', detail: 'cifre contro il dossier, fonti rifetchate, link risolti, al massimo due giri di correzione' },
    { title: 'Pubblicazione', detail: 'la bozza congelata diventa un file in data/lab/articoli/' },
  ],
}

// La catena minima: cinque stadi, un solo ramo (la correzione dopo una
// smentita). Niente cancello, niente canary, niente selezione fra due bozze.
// L'unica cosa che può fermare un articolo è una cifra o una fonte che non
// esiste, e la ferma il verificatore, non uno script.
//
// Il testo attraversa un prompt una volta sola, fra scrittore e verificatore.
// Da lì in poi viaggia come file: il verificatore lo congela con
// `lab.controlla --salva`, il pubblicatore riceve quel percorso. Così ciò che
// finisce su disco è per costruzione ciò che è stato verificato.

// `args` può arrivare come lista vera o come stringa (`'["ter-6"]'`, o
// `'ter-6 ter-92'`, o un codice solo): si normalizza qui, perché un codice
// letto male diventa un indicatore inesistente e la run finisce a vuoto.
function codiciDa(valore) {
  if (Array.isArray(valore)) return valore.flatMap(codiciDa)
  if (typeof valore !== 'string') return valore ? [String(valore)] : []
  const testo = valore.trim()
  if (testo.startsWith('[')) {
    try {
      return codiciDa(JSON.parse(testo))
    } catch (errore) {
      // cade sullo split qui sotto
    }
  }
  return testo.split(/[\s,]+/).map((c) => c.replace(/^["']|["']$/g, '')).filter(Boolean)
}

// Senza codici si lascia scegliere alla coda editoriale. `scripts/text_queue.py`
// ordina già il catalogo intero (cifre arretrate, poi sezioni mancanti, poi se
// la pagina è indicizzabile) e `lab.dossier --coda` ci aggiunge il filtro sul
// dato fresco. Nove agenti per articolo: uno per run, non due.
// Quanti passaggi del verificatore, cioè un giro di correzione in meno. Tre
// perché due non bastavano: il rilievo che ha fermato `ter-13` stava nella
// prima bozza e il primo passaggio non l'ha visto.
const VERIFICHE = 3

const CODICI = codiciDa(args)
const COMANDO_DOSSIER = CODICI.length
  ? `bin/py -m lab.dossier ${CODICI.join(' ')} --out data/lab/dossier`
  : `bin/py -m lab.dossier --coda 1 --freschi 2025 --out data/lab/dossier`

const PERCORSI = {
  type: 'object',
  required: ['dossier'],
  properties: {
    dossier: {
      type: 'array',
      items: {
        type: 'object',
        required: ['codice', 'percorso'],
        properties: {
          codice: { type: 'string' },
          percorso: { type: 'string' },
          anomalie: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    mancanti: { type: 'array', items: { type: 'string' } },
  },
}

const CLAIM = {
  type: 'object',
  required: ['claim'],
  properties: {
    claim: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'istituzione', 'url', 'citazione', 'relation_type'],
        properties: {
          claim: { type: 'string' },
          istituzione: { type: 'string' },
          url: { type: 'string' },
          data_pubblicazione: { type: ['string', 'null'] },
          territorio: { type: ['string', 'null'] },
          periodo: { type: ['string', 'null'] },
          unita: { type: ['string', 'null'] },
          citazione: { type: 'string' },
          relation_type: {
            type: 'string',
            enum: ['descriptive', 'association', 'possible_explanation', 'causal'],
          },
          // Un solo valore, e non duplica `relation_type`: marca i claim che
          // dicono dove sta l'Italia rispetto ad altri paesi, perché quelli si
          // giudicano su cose che gli altri non hanno (definizione,
          // denominatore, tipo di media, anno che quasi mai coincide).
          usage: { type: ['string', 'null'], enum: ['external_comparison', null] },
          confidenza: { type: ['string', 'null'] },
        },
      },
    },
    note: { type: ['string', 'null'] },
  },
}

const BOZZA = {
  type: 'object',
  required: ['angolo', 'lead', 'sections'],
  properties: {
    angolo: { type: 'string' },
    lead: { type: 'string' },
    // I ruoli sono quattro, le sezioni no: la pagina tiene una lista per ruolo
    // e deriva la sequenza degli H2 dalle sezioni scritte, **conservando ordine
    // e ripetizioni**. Due `quadro` con due `h` diversi rendono due sezioni, ed
    // è così che un confronto europeo o un "perché conta" trovano posto
    // senza toccare `app/`. Nessun `roles_covered`: dichiarare la forma una
    // seconda volta è il modo di farla divergere, e la dichiarazione vince,
    // quindi un ruolo elencato una volta sola butterebbe la sezione gemella.
    sections: {
      type: 'array',
      items: {
        type: 'object',
        required: ['role', 'h', 'body'],
        properties: {
          role: { type: 'string', enum: ['definizione', 'quadro', 'dinamica', 'limiti'] },
          h: { type: 'string' },
          body: { type: 'string' },
        },
      },
    },
    fonti: {
      type: 'array',
      items: {
        type: 'object',
        required: ['testo', 'url'],
        properties: { testo: { type: 'string' }, url: { type: 'string' } },
      },
    },
    correzioni: { type: ['array', 'null'], items: { type: 'string' } },
  },
}

const VERDETTO = {
  type: 'object',
  required: ['smentite', 'verificate'],
  properties: {
    smentite: {
      type: 'array',
      items: {
        type: 'object',
        required: ['tipo', 'dove', 'cosa_dice_il_testo', 'cosa_dicono_i_dati'],
        properties: {
          tipo: { type: 'string', enum: ['cifra', 'fonte', 'causale', 'definizione'] },
          dove: { type: 'string' },
          cosa_dice_il_testo: { type: 'string' },
          cosa_dicono_i_dati: { type: 'string' },
          gravita: { type: ['string', 'null'] },
        },
      },
    },
    verificate: { type: 'number' },
    bozza_salvata: { type: ['string', 'null'] },
    impronta: {
      type: ['object', 'null'],
      properties: {
        caratteri: { type: 'number' },
        parole: { type: 'number' },
        cifre: { type: 'number' },
        sezioni: { type: 'number' },
        fonti: { type: 'number' },
      },
    },
    note: { type: ['string', 'null'] },
  },
}

// L'impronta della bozza come la calcola `lab.controlla`, ricostruita qui sulla
// bozza che lo script ha in mano. È l'unico punto in cui il testo passa ancora
// dentro un prompt (fra chi scrive e chi verifica): se il verificatore lo
// ribatte male, i numeri non coincidono e l'articolo si ferma invece di finire
// su disco diverso da come è stato verificato.
function improntaDi(bozza) {
  const pezzi = [bozza.lead ?? '']
    .concat((bozza.sections ?? []).map((s) => (s.h ?? '') + (s.body ?? '')))
    .concat((bozza.fonti ?? []).map((f) => (f.testo ?? '') + (f.url ?? '')))
  const testo = pezzi.join('')
  return {
    caratteri: testo.replace(/\s+/g, '').length,
    parole: testo.split(/\s+/).filter(Boolean).length,
    // `\d` conta 0-9 e basta, come `isdecimal` in Python. Non `isdigit`, che
    // è vero anche per l'esponente di `km²`: due definizioni diverse di
    // "cifra" fermerebbero un articolo giusto.
    cifre: (testo.match(/\d/g) ?? []).length,
    sezioni: (bozza.sections ?? []).length,
    fonti: (bozza.fonti ?? []).length,
  }
}

function improntaDiversa(attesa, trovata) {
  if (!trovata) return null
  const campi = ['caratteri', 'parole', 'cifre', 'sezioni', 'fonti']
  const scarti = campi.filter((campo) => attesa[campo] !== trovata[campo])
  return scarti.length ? scarti.map((c) => `${c}: ${attesa[c]} != ${trovata[c]}`).join(', ') : null
}

const PUBBLICATO = {
  type: 'object',
  required: ['scritto'],
  properties: {
    scritto: { type: 'boolean' },
    sovrascritto: { type: ['boolean', 'null'] },
    percorso: { type: ['string', 'null'] },
    parole: { type: ['number', 'null'] },
    impaginazione: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          role: { type: 'string' },
          h2: { type: 'string' },
          scritta: { type: 'boolean' },
        },
      },
    },
    problemi: { type: 'array', items: { type: 'string' } },
    rilievi: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'string' },
          severity: { type: 'string' },
          detail: { type: 'string' },
        },
      },
    },
    uscita: { type: ['string', 'null'] },
  },
}

const json = (valore) => JSON.stringify(valore, null, 1)

// Un verificatore che finisce i turni senza restituire lo schema fa fallire lo
// stadio e l'articolo sparisce come `null`. È successo al primo giro reale:
// trentun turni spesi a decomprimere un PDF a mano, nessun verdetto. Qui
// l'errore diventa un esito con un motivo leggibile.
async function verifica(prompt, opzioni) {
  try {
    return await agent(prompt, opzioni)
  } catch (errore) {
    log(`verifica non conclusa (${opzioni.label}): ${errore.message}`)
    return null
  }
}

// Le tre lenti del ventaglio. Non esiste in Claude Code un subagente di deep
// research da chiamare: l'equivalente è questo, agenti stretti che cercano
// cose diverse e sono ciechi l'uno all'altro. Il budget sta nel prompt e non
// nel frontmatter, perché `maxTurns` dentro un workflow non viene rispettato
// (sedici dichiarati, trentuno fatti al primo giro reale).
const LENTI = [
  {
    chiave: 'eventi',
    agentType: 'lab-scout',
    mandato: 'Che cosa e successo. Cerca eventi datati e verificabili che si affiancano ai ' +
      'movimenti della serie: provvedimenti, chiusure, riforme, eventi naturali, cambi di ' +
      'rilevazione. Le anomalie gia misurate sono il posto piu probabile dove un evento ' +
      'esiste davvero, non una lista da spuntare.',
  },
  {
    chiave: 'europa',
    agentType: 'lab-scout-europa',
    mandato: 'Dove sta l Italia. Cerca il valore italiano in una fonte europea, la media UE e ' +
      'i paesi vicini per valore, e controlla la comparabilita prima del numero. Se le due ' +
      'misure non sono confrontabili, dillo in note e restituisci una lista vuota.',
  },
  {
    chiave: 'perche-conta',
    agentType: 'lab-scout',
    mandato: 'Perche conta. Cerca che cosa questo fenomeno produce nella vita di chi ci abita: ' +
      'conseguenze documentate, chi ne e toccato, che cosa ne dicono le istituzioni che se ne ' +
      'occupano. Non cercare eventi e non cercare confronti europei: li fanno gli altri due.',
  },
]

phase('Dossier')
const montati = await agent(
  `Esegui esattamente questo comando dalla radice del repository e restituisci quello che stampa:\n\n` +
  `    ${COMANDO_DOSSIER}\n\n` +
  `Stampa JSON con \`dossier\` (codice, percorso, byte, anomalie) e \`mancanti\`.`,
  { agentType: 'lab-dossierista', model: 'haiku', effort: 'low', schema: PERCORSI, label: 'dossier' },
)

if (!montati || !montati.dossier?.length) {
  return { errore: 'nessun dossier montato', mancanti: montati?.mancanti ?? CODICI }
}
if (montati.mancanti?.length) log(`indicatori sconosciuti, saltati: ${montati.mancanti.join(', ')}`)
log(`indicatori: ${montati.dossier.map((d) => d.codice).join(', ')}`)

const esiti = await pipeline(
  montati.dossier,

  // 1. Contesto: il ventaglio. `parallel()` e non tre await, così uno scout
  //    che solleva diventa `null` invece di portarsi via l'articolo.
  (d) => parallel(LENTI.map((lente) => () => agent(
    `Indicatore ${d.codice} di Divario Italia. Il dossier è qui, aprilo con Read prima di cercare:\n\n` +
    `    ${d.percorso}\n\n` +
    `**La tua lente**: ${lente.mandato}\n\n` +
    `Anomalie già misurate sulla serie, come materiale:\n` +
    `${(d.anomalie ?? []).map((a) => `- ${a}`).join('\n') || '- nessuna'}\n\n` +
    `Restituisci al massimo tre claim, ognuno con la citazione testuale cercata come ` +
    `stringa nella pagina fetchata. Lista vuota se non trovi niente che regga: è un buon ` +
    `esito, e va detto in \`note\`.\n\n` +
    `Budget: due ricerche, tre fetch, poi restituisci. Un documento che non si legge col ` +
    `fetch si scarta e se ne prende un altro, non si insegue con altri strumenti.`,
    {
      agentType: lente.agentType, model: 'sonnet', effort: 'medium',
      phase: 'Contesto', schema: CLAIM, label: `${lente.chiave}:${d.codice}`,
    },
  ).then((esito) => ({ lente: lente.chiave, ...esito })))),

  // 2. Scrittura: una bozza sola. Tesi e forma le sceglie chi scrive, e nessuno
  //    a monte gliele propone: gli scout portano materiale, non una scaletta.
  (raccolto, d) => {
    const lenti = (raccolto ?? []).filter(Boolean)
    const claim = lenti.flatMap((c) => (c.claim ?? []).map((v) => ({ lente: c.lente, ...v })))
    const vuote = LENTI.map((l) => l.chiave).filter((k) => !claim.some((c) => c.lente === k))
    if (vuote.length) log(`${d.codice}: nessun claim da ${vuote.join(', ')}`)
    return agent(
      `Scrivi l'articolo dell'indicatore ${d.codice} di Divario Italia.\n\n` +
      `Dossier da aprire con Read (leggilo tutto prima di scrivere: porta anche i gruppi in ` +
      `cui la classifica si spacca e gli indicatori imparentati con i loro valori):\n\n` +
      `    ${d.percorso}\n\n` +
      `Claim verificati da tre scout, ognuno con la lente da cui viene. Sono l'unica fonte ` +
      `esterna che puoi citare, e nessuno di loro ti propone un angolo:\n${json(claim)}\n\n` +
      `Compito: **scrivi**. Decidi tu la tesi, quali temi coprire, quante sezioni, in che ` +
      `ordine, con che titoli, e quali indicatori imparentati linkare. Dichiara la tesi in ` +
      `\`angolo\`, dicendo perché quella e non un'altra.`,
      // Opus a scrivere. Con sonnet la bozza costava 0,90 $ e reggeva, ma è
      // l'unico stadio in cui il prodotto **è** il testo: quello che manca a
      // un articolo debole non lo recupera nessun verificatore, che smentisce
      // il falso e non aggiunge il buono.
      { agentType: 'lab-scrittore', model: 'opus', effort: 'high', phase: 'Scrittura', schema: BOZZA, label: `scrivi:${d.codice}` },
    ).then((bozza) => ({ bozza, claim }))
  },

  // 3. Verifica, con al massimo due giri di correzione.
  //
  // Erano uno. Sul secondo giro reale (ter-13) è arrivato un rilievo che il
  // primo passaggio non aveva visto su un testo identico, quindi l'articolo si
  // è fermato non per un difetto grave ma per un difetto **scoperto tardi**.
  // Un verificatore non è esaustivo in un colpo solo, e la cura sta dalla
  // parte dei giri, non dalla parte del giudizio. Il tetto resta, perché una
  // catena che itera finché il critico tace non converge: converge il critico.
  async ({ bozza, claim }, d) => {
    if (!bozza) return { codice: d.codice, pubblicabile: false, motivo: 'nessuna bozza' }
    let corrente = bozza
    for (let giro = 0; giro < VERIFICHE; giro++) {
      // Il verificatore può anche non tornare (schema non chiamato, turni
      // finiti). Non deve portarsi via l'articolo in silenzio: si registra il
      // motivo e si finisce nella lista dei fermati, che è un esito leggibile.
      const verdetto = await verifica(
        `Prova a smentire questo articolo dell'indicatore ${d.codice} di Divario Italia, ` +
        `prima che venga scritto su disco.\n\n` +
        `Dossier: ${d.percorso}\n\n` +
        `Bozza da giudicare:\n${json(corrente)}\n\n` +
        `Claim raccolti dai tre scout, con la lente da cui vengono:\n${json(claim ?? [])}\n\n` +
        `Comando da eseguire, con la bozza qui sopra copiata nel heredoc senza cambiare un carattere:\n\n` +
        "    bin/py -m lab.controlla " + d.codice + " --salva <<'BOZZA'\n    ...\n    BOZZA\n\n" +
        `L'uscita porta anche un blocco \`link\`. Un percorso con stato "non esiste" è una ` +
        `smentita: manda il lettore su una pagina che non c'è. Uno "esiste, fuori dai ` +
        `parenti" è solo una nota.\n\n` +
        `Restituisci le smentite, quante cifre e fonti hai verificato, il percorso ` +
        `\`bozza_salvata\` e l'\`impronta\`, entrambi copiati dall'uscita del comando ` +
        `senza modificarli: l'impronta serve a dimostrare che il file congelato è ` +
        `questa bozza e non una versione ribattuta.\n\n` +
        `Budget: un comando \`lab.controlla\`, una lettura del dossier, un fetch per url. ` +
        `Un documento che non si legge col fetch è \`non verificabile\` e va in \`note\`: ` +
        `non si insegue con altri strumenti. Finiti i controlli, restituisci subito ` +
        `il risultato strutturato.`,
        { agentType: 'lab-verificatore', model: 'opus', effort: 'high', phase: 'Verifica', schema: VERDETTO, label: `verifica:${d.codice}${giro ? ` (${giro + 1})` : ''}` },
      )
      if (!verdetto) return { codice: d.codice, pubblicabile: false, motivo: 'verifica non conclusa', giri: giro }

      // Un rilievo ferma l'articolo se è `alta` **o se non porta gravità**:
      // una severità che nessuno ha dichiarato non è un permesso a pubblicare.
      const gravi = verdetto.smentite.filter((s) => s.gravita !== 'media' && s.gravita !== 'bassa')
      const ultimo = giro === VERIFICHE - 1

      // All'ultimo passaggio si consegna il giudizio invece di iterare. Misurato
      // su `ter-13`: tre passaggi dello stesso verificatore sullo stesso testo
      // hanno prodotto 3, poi 1, poi 2 rilievi, ogni volta **nuovi**, e ogni
      // volta su frasi che c'erano dalla prima bozza. Non è il testo che non
      // converge, è la lettura: un critico forte trova sempre qualcosa in più
      // se lo si richiama. Quindi il freno non è il silenzio del critico, è la
      // gravità che il critico stesso assegna, e i rilievi che restano
      // viaggiano col pezzo invece di sparire.
      if (!verdetto.smentite.length || (ultimo && !gravi.length)) {
        const scarto = improntaDiversa(improntaDi(corrente), verdetto.impronta)
        if (scarto) {
          log(`${d.codice}: la bozza congelata non coincide con quella scritta (${scarto})`)
          return { codice: d.codice, pubblicabile: false, giri: giro, verdetto,
                   motivo: `bozza congelata diversa da quella verificata: ${scarto}` }
        }
        if (verdetto.smentite.length) {
          log(`${d.codice}: scritto con ${verdetto.smentite.length} rilievi aperti, nessuno grave`)
        }
        return { codice: d.codice, bozza: corrente, verdetto, giri: giro,
                 bozza_salvata: verdetto.bozza_salvata, rilievi_aperti: verdetto.smentite }
      }
      if (ultimo) {
        // Un rilievo grave all'ultimo passaggio: l'articolo non si scrive. È
        // l'unico caso in cui la lite si ferma, e si ferma prima del disco.
        log(`${d.codice}: ${gravi.length} rilievi gravi dopo ${VERIFICHE} passaggi, non scritto`)
        return { codice: d.codice, pubblicabile: false, motivo: `smentito ${VERIFICHE} volte`, verdetto, giri: giro }
      }
      const corretta = await agent(
        `Correggi il tuo articolo dell'indicatore ${d.codice}. Compito: **correggi**.\n\n` +
        `Dossier: ${d.percorso}\n\n` +
        `Bozza attuale:\n${json(corrente)}\n\n` +
        // Una smentita nomina una frase, ma vale sul claim. Al secondo giro
        // reale (ter-13) il corpo della sezione `limiti` è stato corretto
        // bene e il titolo, che diceva il contrario, è rimasto: smentito una
        // seconda volta, con gravità alta. Stessa run: le tre occorrenze del
        // 63,04 ri-etichettate una per una e il 16,85 del lead, che ha lo
        // stesso difetto identico, lasciato dov'era.
        `Smentite del verificatore. Per ognuna cambia ciò che nomina, **e** ogni altro ` +
        `posto dove quello stesso claim compare (titolo della sezione, \`lead\`, ` +
        `\`angolo\`), **e** gli altri punti che hanno lo stesso difetto anche se la ` +
        `smentita non li nomina. Il resto del testo non si tocca. Dichiara in ` +
        `\`correzioni\` che cosa hai cambiato e dove l'hai propagato:\n${json(verdetto.smentite)}`,
        { agentType: 'lab-scrittore', model: 'opus', effort: 'high', phase: 'Scrittura', schema: BOZZA, label: `correggi:${d.codice}${giro ? ` (${giro + 1})` : ''}` },
      )
      if (!corretta) return { codice: d.codice, pubblicabile: false, motivo: 'correzione non conclusa', verdetto, giri: giro }
      corrente = corretta
    }
  },

  // 4. Pubblicazione: passa il percorso della bozza congelata, mai il testo.
  (esito, d) => {
    if (esito.pubblicabile === false) return esito
    if (!esito.bozza_salvata) {
      return { ...esito, pubblicabile: false, motivo: 'il verificatore non ha restituito la bozza congelata' }
    }
    return agent(
      `Scrivi su disco l'articolo già verificato dell'indicatore ${d.codice}. ` +
      `Esegui esattamente questo comando e restituisci quello che stampa:\n\n` +
      `    bin/py -m lab.pubblica ${d.codice} --bozza ${esito.bozza_salvata}\n\n` +
      `Riporta \`impaginazione\` (gli H2 che la pagina renderebbe), \`sovrascritto\` `+
      `(l'articolo scriveva su una pagina che esisteva gia') e tutti i rilievi, ` +
      `anche quelli di severità \`segnala\`. Non correggere niente: se il comando ` +
      `rifiuta, riporta i problemi così come li stampa.`,
      { agentType: 'lab-pubblicatore', model: 'haiku', effort: 'low', phase: 'Pubblicazione', schema: PUBBLICATO, label: `pubblica:${d.codice}` },
    ).then((pubblicato) => ({
      codice: d.codice,
      scritto: !!pubblicato?.scritto,
      sovrascritto: pubblicato?.sovrascritto ?? null,
      percorso: pubblicato?.percorso ?? null,
      parole: pubblicato?.parole ?? null,
      angolo: esito.bozza?.angolo ?? null,
      giri_di_correzione: esito.giri ?? 0,
      cifre_verificate: esito.verdetto?.verificate ?? null,
      // Gli H2 come li vedrebbe un lettore. Serve perché `data/lab/articoli/`
      // non è letto da nessuna pagina: senza questo, la forma variabile
      // sarebbe una promessa che nessuno può controllare.
      impaginazione: pubblicato?.impaginazione ?? [],
      sezioni: (esito.bozza?.sections ?? []).map((s) => `${s.role}: ${s.h}`),
      rilievi: pubblicato?.rilievi ?? [],
      // I rilievi non gravi con cui il pezzo è uscito. Non spariscono: un
      // articolo pubblicato con due note aperte è un'altra cosa da uno
      // pubblicato pulito, e chi legge l'esito deve poterlo distinguere.
      rilievi_aperti: (esito.rilievi_aperti ?? []).map(
        (s) => `${s.gravita ?? 'senza gravità'} | ${s.tipo} | ${s.dove}: ${s.cosa_dice_il_testo}`),
    }))
  },
)

const finiti = esiti.filter(Boolean)
return {
  richiesti: CODICI.length || montati.dossier.length,
  scritti: finiti.filter((e) => e.scritto).length,
  fermati: finiti.filter((e) => e.pubblicabile === false),
  articoli: finiti.filter((e) => e.scritto),
}
