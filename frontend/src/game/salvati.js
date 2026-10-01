// La forma di cio' che i giochi rileggono dal localStorage, in un punto solo. Un valore salvato puo'
// essere stato scritto da una versione vecchia, da un'altra scheda o a mano: un numero che non e'
// un intero non negativo, una lista che e' un oggetto o uno stato che non esiste farebbero
// scrivere `NaN` in pagina o rompere un `.map`. Qui ogni campo che non torna ripiega sul valore di
// partenza, e un progresso con la forma sbagliata e' scartato intero (si riparte da una partita
// nuova). Niente React, niente DOM: `node --test` lo importa cosi' com'e' (`salvati.test.mjs`).

export function interoNonNegativo(v) {
  return Number.isInteger(v) && v >= 0;
}

function oggetto(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

// Le statistiche: parte da `difetto`, e per ogni chiave numerica del difetto tiene il valore salvato
// solo se e' un intero non negativo. Le chiavi che il difetto non conosce si buttano via. Ritorna
// sempre un oggetto nuovo, mai quello in ingresso.
export function statisticheValide(salvato, difetto) {
  const out = { ...difetto };
  if (!oggetto(salvato)) return out;
  for (const [chiave, valore] of Object.entries(difetto)) {
    if (typeof valore === "number" && interoNonNegativo(salvato[chiave])) out[chiave] = salvato[chiave];
  }
  return out;
}

// La distribuzione dei tentativi, `{ "1": n, ..., "fail": n }`: tiene solo i secchi permessi con un
// conteggio intero non negativo.
export function distribuzioneValida(salvata, secchi) {
  const out = {};
  if (!oggetto(salvata)) return out;
  for (const secchio of secchi) {
    if (interoNonNegativo(salvata[secchio])) out[secchio] = salvata[secchio];
  }
  return out;
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;

export const SECCHI_DISTRIBUZIONE = ["1", "2", "3", "4", "5", "6", "fail"];

export const STATS_COMPARE = { bestStreak: 0, totalRounds: 0, totalCorrect: 0 };
export const STATS_ORDER = { bestScore3: 0, bestScore5: 0, totalRounds: 0, totalPositionsCorrect: 0 };
export const STATS_PROVINCIA = { played: 0, wins: 0 };
export const STATS_REGIONE = { played: 0, wins: 0, streak: 0, maxStreak: 0 };

export function statsCompare(salvato) {
  return statisticheValide(salvato, STATS_COMPARE);
}

export function statsOrder(salvato) {
  return statisticheValide(salvato, STATS_ORDER);
}

export function statsProvincia(salvato) {
  return {
    ...statisticheValide(salvato, STATS_PROVINCIA),
    distribution: distribuzioneValida(oggetto(salvato) ? salvato.distribution : null, SECCHI_DISTRIBUZIONE),
  };
}

// Indovina la Regione tiene anche la data dell'ultima vittoria (`lastWonDate`, ISO) e il suo
// `puzzle_id` (`lastWonPuzzleId`, "daily:YYYY-MM-DD"), che la serie legge: se non sono stringhe
// fatte cosi' valgono `null`.
export function statsRegione(salvato) {
  const base = oggetto(salvato) ? salvato : {};
  const out = {
    ...statisticheValide(base, STATS_REGIONE),
    lastWonPuzzleId: typeof base.lastWonPuzzleId === "string" && /^daily:\d{4}-\d{2}-\d{2}$/.test(base.lastWonPuzzleId)
      ? base.lastWonPuzzleId
      : null,
    distribution: distribuzioneValida(base.distribution, SECCHI_DISTRIBUZIONE),
  };
  if (typeof base.lastWonDate === "string" && ISO.test(base.lastWonDate)) out.lastWonDate = base.lastWonDate;
  return out;
}

// Il progresso di una partita a indovinare (Regione e Provincia), o `null` se non ha la forma giusta.
// `extra(p)` e' un controllo in piu' del gioco (la Provincia vuole un token e un livello). Una
// partita finita (`won`, `lost`) deve avere la soluzione, perche' la schermata finale la legge.
export function progressoValido(salvato, { extra } = {}) {
  if (!oggetto(salvato)) return null;
  if (!["playing", "won", "lost"].includes(salvato.status)) return null;
  if (!Array.isArray(salvato.clues) || !salvato.clues.every(oggetto)) return null;
  if (!Array.isArray(salvato.guesses) || !salvato.guesses.every(oggetto)) return null;
  if (salvato.solution != null && !oggetto(salvato.solution)) return null;
  if (salvato.recap != null && !Array.isArray(salvato.recap)) return null;
  if (salvato.fatto != null && typeof salvato.fatto !== "string") return null;
  if (salvato.status !== "playing" && !oggetto(salvato.solution)) return null;
  if (extra && !extra(salvato)) return null;
  return salvato;
}

// Il controllo in piu' della Provincia: il token della sessione e il livello giocato.
export function extraProvincia(livelli) {
  return (p) => typeof p.token === "string" && p.token.length > 0 && livelli.includes(p.level);
}

// Legge e analizza un JSON salvato: `undefined` se manca o e' rotto (chi chiama ripiega).
export function analizza(grezzo) {
  if (typeof grezzo !== "string" || !grezzo) return undefined;
  try {
    return JSON.parse(grezzo);
  } catch {
    return undefined;
  }
}
