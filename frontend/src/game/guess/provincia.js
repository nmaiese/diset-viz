// Costanti, testi e salvataggi di Indovina la Provincia. Il risultato sta solo
// in localStorage: nella serie e in classifica lo porta l'ondata 3, e non entra
// mai nella serie regionale del server.

export const API_PROVINCIA = {
  daily: (level) => `/api/game/provincia/daily?level=${encodeURIComponent(level)}`,
  guess: "/api/game/provincia/guess",
};

export const LIVELLI = [
  { key: "stessa_regione", label: "Della regione", aiuto: "ti diciamo la regione e scegli fra le sue province" },
  { key: "province", label: "Di tutta Italia", aiuto: "scegli fra tutte le province" },
];
export const LIVELLO_DEFAULT = "stessa_regione";

const STORAGE_PROGRESS = "di-provincia-progress:";
const STORAGE_STATS = "di-provincia-stats";
const STORAGE_ONBOARDED = "di-provincia-onboarded";
const STORAGE_LEVEL = "di-provincia-level";

const PUNTI = {
  N: { parola: "nord", freccia: "↑", gradi: 0 },
  NE: { parola: "nord-est", freccia: "↗", gradi: 45 },
  E: { parola: "est", freccia: "→", gradi: 90 },
  SE: { parola: "sud-est", freccia: "↘", gradi: 135 },
  S: { parola: "sud", freccia: "↓", gradi: 180 },
  SO: { parola: "sud-ovest", freccia: "↙", gradi: 225 },
  O: { parola: "ovest", freccia: "←", gradi: 270 },
  NO: { parola: "nord-ovest", freccia: "↖", gradi: 315 },
};

export function direzione(sigla) {
  return PUNTI[sigla] || null;
}

// "Circa 120 km verso nord-est". I km sono stimati fra i centri delle province.
export function testoDistanza(guess) {
  if (guess.correct) return "";
  const punto = direzione(guess.direction);
  const km = Number(guess.distance_km).toLocaleString("it-IT");
  return punto ? `Circa ${km} km verso ${punto.parola}` : `Circa ${km} km`;
}

export function nomeLivello(key) {
  return (LIVELLI.find((l) => l.key === key) || LIVELLI[0]).label.toLowerCase();
}

function leggi(chiave) {
  try {
    return window.localStorage.getItem(chiave);
  } catch {
    return null;
  }
}

function scrivi(chiave, valore) {
  try {
    window.localStorage.setItem(chiave, valore);
  } catch {
    // Modalita' privata o quota piena: il gioco resta giocabile senza salvataggio.
  }
}

export function caricaProgresso(puzzleId) {
  try {
    const raw = leggi(STORAGE_PROGRESS + puzzleId);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function salvaProgresso(puzzleId, progresso) {
  scrivi(STORAGE_PROGRESS + puzzleId, JSON.stringify(progresso));
}

const STATISTICHE_VUOTE = { played: 0, wins: 0, distribution: {} };

export function caricaStatistiche() {
  try {
    const raw = leggi(STORAGE_STATS);
    return raw ? { ...STATISTICHE_VUOTE, ...JSON.parse(raw) } : { ...STATISTICHE_VUOTE, distribution: {} };
  } catch {
    return { ...STATISTICHE_VUOTE, distribution: {} };
  }
}

// Registra una partita finita: una partita, una vittoria o no, in quale tentativo.
export function registraPartita(stats, { won, attempts }) {
  const distribution = { ...stats.distribution };
  const bucket = won ? String(attempts) : "fail";
  distribution[bucket] = (distribution[bucket] || 0) + 1;
  const next = { played: stats.played + 1, wins: stats.wins + (won ? 1 : 0), distribution };
  scrivi(STORAGE_STATS, JSON.stringify(next));
  return next;
}

export function livelloSalvato() {
  const k = leggi(STORAGE_LEVEL);
  return LIVELLI.some((l) => l.key === k) ? k : LIVELLO_DEFAULT;
}

export function salvaLivello(key) {
  scrivi(STORAGE_LEVEL, key);
}

export function onboardingFatto() {
  return Boolean(leggi(STORAGE_ONBOARDED));
}

export function segnaOnboarding() {
  scrivi(STORAGE_ONBOARDED, "1");
}
