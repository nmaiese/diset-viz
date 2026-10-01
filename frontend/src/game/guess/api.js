// Indirizzi e chiavi di localStorage di Indovina la Regione.

export const API = {
  regions: "/api/game/regions",
  daily: "/api/game/daily",
  dailyForDate: (iso) => `/api/game/daily/${iso}`,
  archive: "/api/game/archive",
  practice: "/api/game/practice",
  guess: "/api/game/guess",
  playerMe: "/api/player/me",
};

export const STORAGE_PROGRESS_PREFIX = "di-game-progress:";
export const STORAGE_STATS_KEY = "di-game-stats";
export const STORAGE_ONBOARDED_KEY = "di-game-onboarded";
export const MAP_FRAME_ID = "game-map-frame";
export const DIST_BUCKETS = ["1", "2", "3", "4", "5", "6", "fail"];
