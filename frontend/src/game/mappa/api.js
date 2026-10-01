// La rete di "Dov'e' la provincia?": apertura e risposta della sfida del giorno, e la
// memoria locale della partita in corso. Il contratto del JSON sta in testa a `app/game_mappa.py`.

import { getAccessToken } from "../../shared/supabase.js";
import { chiavePartita, leggiPartita, serializzaPartita } from "./partita.js";

export const API = {
  sessione: (livello, modalita) =>
    `/api/game/map/daily/session?level=${encodeURIComponent(livello)}&mode=${encodeURIComponent(modalita)}`,
  risposta: "/api/game/map/daily/answer",
};

async function leggi(res) {
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

// Apre una sessione nuova (il server la apre sempre nuova). Non lancia: `{ok, status, data}`, con
// il nome dell'errore in `data.error`.
export async function apriSessione(livello, modalita) {
  try {
    return await leggi(await fetch(API.sessione(livello, modalita)));
  } catch {
    return { ok: false, status: 0, data: {} };
  }
}

// POST che non butta via il corpo degli errori: la sfida ha nomi di errore che il client deve
// distinguere (`puzzle_changed` da `round_already_answered`). Con un account il server attribuisce
// punteggio e traguardi (header Authorization), senza resta anonimo.
export async function rispondi(corpo) {
  let auth = {};
  try {
    const token = await getAccessToken();
    if (token) auth = { Authorization: `Bearer ${token}` };
  } catch {
    // Nessuna sessione: gioco anonimo, nessun header.
  }
  try {
    return await leggi(await fetch(API.risposta, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify(corpo),
    }));
  } catch {
    return { ok: false, status: 0, data: {} };
  }
}

// -- La partita in corso nel localStorage ----------------------------------------------------
// Una comodita': il token porta round e punteggio, e se il server lo rifiuta si riapre. Tutto in
// try/catch: senza localStorage la partita si gioca lo stesso.

export function leggiSalvata(livello, modalita, iso) {
  try {
    return leggiPartita(window.localStorage.getItem(chiavePartita(livello, modalita, iso)), { livello, modalita, iso });
  } catch {
    return null;
  }
}

export function salvaPartita(partita) {
  try {
    window.localStorage.setItem(chiavePartita(partita.level, partita.mode, partita.date), serializzaPartita(partita));
  } catch {
    // Il prossimo caricamento riparte da una sessione nuova, nessun danno.
  }
}

export function dimenticaPartita(livello, modalita, iso) {
  try {
    window.localStorage.removeItem(chiavePartita(livello, modalita, iso));
  } catch {
    // niente da fare
  }
}
