import { STORAGE_PROGRESS_PREFIX, STORAGE_STATS_KEY } from "./api.js";
import { analizza, progressoValido, statsRegione } from "../salvati.js";

// Le statistiche salvate, con la forma controllata (`salvati.js`): un campo che non torna vale zero.
export function loadStats() {
  try {
    return statsRegione(analizza(window.localStorage.getItem(STORAGE_STATS_KEY)));
  } catch {
    return statsRegione(null);
  }
}

export function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile: le statistiche restano solo in memoria per la sessione.
  }
}

// Il progresso di una partita, o `null` se manca o non ha la forma giusta (si riparte da zero).
export function loadProgress(puzzleId) {
  try {
    return progressoValido(analizza(window.localStorage.getItem(STORAGE_PROGRESS_PREFIX + puzzleId)));
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
