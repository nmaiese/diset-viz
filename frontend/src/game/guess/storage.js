import { STORAGE_PROGRESS_PREFIX, STORAGE_STATS_KEY } from "./api.js";

export function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    if (!raw) throw new Error("empty");
    const parsed = JSON.parse(raw);
    return { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonPuzzleId: null, distribution: {}, ...parsed };
  } catch {
    return { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonPuzzleId: null, distribution: {} };
  }
}

export function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile: le statistiche restano solo in memoria per la sessione.
  }
}

export function loadProgress(puzzleId) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PROGRESS_PREFIX + puzzleId);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveProgress(puzzleId, progress) {
  try {
    window.localStorage.setItem(STORAGE_PROGRESS_PREFIX + puzzleId, JSON.stringify(progress));
  } catch {
    // Idem: modalità privata o quota piena, il gioco resta giocabile senza persistenza.
  }
}
