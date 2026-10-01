// La serie di Indovina, a giorni. Funzioni pure, senza React e senza
// localStorage: le prova `serie.test.mjs` (node --test).
//
// Regola, la stessa del server (`player_stats._daily_streaks`): la serie conta i
// GIORNI DI FILA in cui hai VINTO la sfida del giorno. Un giorno perso non
// spezza la serie da solo: si spezza quando passa un giorno senza vittoria, cioe'
// quando la differenza fra oggi e l'ultima vittoria supera un giorno. Il giorno
// e' quello di Roma.

const ROMA = "Europe/Rome";

export function oggiRoma(now = new Date()) {
  // "en-CA" scrive la data come YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", { timeZone: ROMA, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

function giornoUtc(iso) {
  const [y, m, d] = String(iso).split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

// Giorni interi da `daIso` a `aIso` (negativi se `aIso` e' prima).
export function giorniTra(daIso, aIso) {
  return Math.round((giornoUtc(aIso) - giornoUtc(daIso)) / 86400000);
}

// La data di un puzzle_id "daily:YYYY-MM-DD", o null.
export function dataDaPuzzleId(puzzleId) {
  const m = /^daily:(\d{4}-\d{2}-\d{2})$/.exec(puzzleId || "");
  return m ? m[1] : null;
}

// Le statistiche salvate prima della serie a giorni contavano vittorie di fila e
// portavano solo `lastWonPuzzleId`: la data si ricava da li'.
export function conData(stats) {
  if (stats.lastWonDate) return stats;
  return { ...stats, lastWonDate: dataDaPuzzleId(stats.lastWonPuzzleId) };
}

// La serie da mostrare oggi: zero se l'ultima vittoria e' di due giorni fa o piu'.
export function serieAttuale(stats, oggiIso) {
  const { lastWonDate, streak } = conData(stats);
  if (!lastWonDate) return 0;
  return giorniTra(lastWonDate, oggiIso) > 1 ? 0 : streak || 0;
}

// Le statistiche dopo una sfida del giorno finita. `giorno` e' la data ISO della
// sfida, `won` l'esito.
export function aggiornaSerie(stats, { won, giorno }) {
  const prev = conData(stats);
  if (!won) return { ...prev };
  let streak = 1;
  if (prev.lastWonDate) {
    const diff = giorniTra(prev.lastWonDate, giorno);
    if (diff === 0) streak = prev.streak || 1;
    else if (diff === 1) streak = (prev.streak || 0) + 1;
  }
  return {
    ...prev,
    streak,
    maxStreak: Math.max(prev.maxStreak || 0, streak),
    lastWonDate: giorno,
  };
}
