// La logica pura di "Chi è maggiore?": niente React, niente DOM, niente rete vera. Sta qui, e
// non in `compare.jsx`, perche' `node --test` la importa cosi' com'e' (`compare-logica.test.mjs`)
// e il timer, la chiamata "Avanti" e il tono si provano senza un browser.

import { trovaTerritorioMio } from "./puri.js";

export const ROUND_MS = 10000;
export const TICK_MS = 100;
export const API_AVANTI = "/api/game/compare/daily/next";

// -- Il timer -------------------------------------------------------------------------

// Il conto alla rovescia di un round. La scadenza e' ASSOLUTA (`adesso() + ms`, calcolata una
// volta): un intervallo che il browser rallenta in una scheda in background non allunga il
// tempo, e il server (che misura da se') non risponde `late` per un conto che va piano.
//
// `onTick(rimasto)` riceve un numero gia' calcolato (mai una funzione da dare a `setState`: un
// updater deve essere puro, e React puo' invocarlo piu' volte). `onScadenza()` parte UNA volta
// sola. Ritorna `ferma()`. Orologio e pianificatore si possono iniettare: e' cosi' che il test
// usa un tempo finto.
export function avviaScadenza({
  ms,
  tick = TICK_MS,
  onTick,
  onScadenza,
  adesso = () => Date.now(),
  programma = (fn, ogni) => setInterval(fn, ogni),
  annulla = (id) => clearInterval(id),
}) {
  const scadenza = adesso() + ms;
  let finito = false;
  let id = null;
  const ferma = () => {
    finito = true;
    if (id !== null) annulla(id);
  };
  id = programma(() => {
    if (finito) return;
    const rimasto = Math.max(0, scadenza - adesso());
    if (onTick) onTick(rimasto);
    if (rimasto <= 0) {
      ferma();
      if (onScadenza) onScadenza();
    }
  }, tick);
  return ferma;
}

// -- L'invio di una risposta -----------------------------------------------------------------

export const MAX_TENTATIVI_INVIO = 3;
export const ATTESA_RITENTO_MS = 1500;

// Gli errori che il server da' senza aver consumato il round: si possono rimandare.
const ERRORI_SENZA_CONSUMO = new Set(["timeout_too_early", "rate_limited"]);

// Che cosa fare dell'esito di `POST /api/game/compare/daily/answer`, in un punto solo (funzione
// pura). `esito` e' `{ ok, status, data }`. `scelta` e' quello che si e' mandato ("region_a",
// "region_b", "timeout"), `tentativi` quanti rinvii di questo invio ci sono gia' stati e
// `rimastoMs` il tempo che il conto alla rovescia aveva ancora (`Infinity` senza timer).
// Ritorna `{ azione, ... }`:
//   rivelata   il server ha risposto 200: giusta, sbagliata o in ritardo (`data.late`, una risposta
//              sbagliata come le altre, non un errore);
//   riprova    si rimanda lo STESSO invio fra `attesaMs`, con `scelta` (puo' diventare "timeout");
//   domanda    si torna alla domanda, con `errore`: il server non ha consumato il round e c'e' tempo;
//   bloccata   la partita non puo' proseguire: `errore` dice perche', il bottone e' "Riapri".
// Un 409 o un `token_invalid` sono "bloccata": il primo invio e' gia' arrivato, ed ignorarli
// lascerebbe la partita senza messaggio e senza bottone. Mai "domanda" a tempo scaduto: il timer
// ripartirebbe da zero e scatterebbe a ogni tick, quindi la risposta e' un timeout.
export function decisioneInvio({ ok, status, data }, { scelta, tentativi = 0, rimastoMs = Infinity }) {
  if (ok) return { azione: "rivelata" };
  const errore = data && typeof data.error === "string" ? data.error : "";
  if (status === 409 || errore === "token_invalid") {
    return { azione: "bloccata", errore: errore || "round_already_answered" };
  }
  const rete = status === 0 || status >= 500;
  if (rete || ERRORI_SENZA_CONSUMO.has(errore)) {
    if (tentativi >= MAX_TENTATIVI_INVIO) return { azione: "bloccata", errore: rete ? "rete" : errore };
    if (rete || scelta === "timeout") return { azione: "riprova", scelta, attesaMs: ATTESA_RITENTO_MS };
    // Una scelta fatta con tempo ancora a disposizione: si torna alla domanda. A tempo finito no.
    if (rimastoMs <= 0) return { azione: "riprova", scelta: "timeout", attesaMs: ATTESA_RITENTO_MS };
    return { azione: "domanda", errore };
  }
  return { azione: "bloccata", errore };
}

// -- "Avanti" ----------------------------------------------------------------------------

// Lega al token la domanda dopo quella appena risposta (`POST /api/game/compare/daily/next`).
// `q` e' l'INDICE della domanda appena risposta: il server lega la `q + 1` e il tempo della
// prossima parte da li', non dal momento in cui si e' risposto alla precedente. `post` e'
// `(url, corpo) => Promise<{ ok, status, data }>`.
//
// Esito: `{ ok: true, token }`, oppure `{ ok: false, riprova, errore }`. `riprova` dice se ha
// senso premere di nuovo lo stesso bottone: la rete che non risponde (status 0), un errore del
// server o il limite di frequenza si. Un token superato (`round_already_bound`, `token_invalid`)
// o un giorno cambiato (`puzzle_changed`) no: il primo invio e' arrivato e il round legato e'
// perso, l'unica strada e' riaprire la sfida.
export async function chiediAvanti({ post, token, puzzleId, q }) {
  const { ok, status, data } = await post(API_AVANTI, { token, puzzle_id: puzzleId, q });
  if (ok && data && typeof data.token === "string" && data.token) return { ok: true, token: data.token };
  const errore = data && typeof data.error === "string" ? data.error : "";
  const riprova = !ok && (status === 0 || status === 429 || status >= 500);
  return { ok: false, riprova, errore };
}

// -- Il tono della fine partita --------------------------------------------------------------

// Un parziale non e' un fallimento: pieno solo se tutte giuste, nullo solo se nessuna.
// Un punteggio o un totale senza senso e' "parziale" (neutro), mai una croce.
export function tonoCompare(giuste, totale) {
  if (!Number.isInteger(giuste) || !Number.isInteger(totale) || totale <= 0) return "parziale";
  if (giuste < 0 || giuste > totale) return "parziale";
  if (giuste === totale) return "pieno";
  if (giuste === 0) return "nullo";
  return "parziale";
}

// -- Il fatto da portarti via ------------------------------------------------------------------

// Il "fatto" lo scrive il server (`app/game_facts.py`) e questo client non lo calcola. Il
// contratto: `summary.fact` in Chi e' maggiore? (con `summary.fact_path`), `fact` in cima al
// risultato in Ordina. Si legge in UN punto solo, qui.
export function campoFatto(risposta) {
  if (!risposta || typeof risposta !== "object") return undefined;
  const fonti = [risposta.summary, risposta];
  for (const fonte of fonti) {
    if (!fonte || typeof fonte !== "object") continue;
    for (const chiave of ["fatto", "fact"]) {
      if (typeof fonte[chiave] === "string") return fonte[chiave];
    }
  }
  return undefined;
}

// Il link alla scheda dell'indicatore del fatto: `summary.fact_path`, solo un percorso interno.
export function campoFattoPath(risposta) {
  const percorso = risposta && risposta.summary && risposta.summary.fact_path;
  return typeof percorso === "string" && /^\/indicatore\/[\w\-/]+$/.test(percorso) ? percorso : undefined;
}

// -- Il territorio del giocatore ---------------------------------------------------------------

// Il livello dei territori di una sfida: il livello "regioni" gioca fra regioni, gli altri due
// fra province. Serve a `trovaTerritorioMio`, perche' una chiave di regione puo' coincidere con
// una di provincia.
export function livelloTerritorio(livello) {
  return livello === "regioni" ? "regione" : "provincia";
}

// Il lato ("a" o "b") della coppia in cui c'e' il territorio del giocatore, o `null`. Una
// provincia scelta accende anche la sua regione nelle coppie fra regioni.
export function coppiaDelTerritorio(mio, domanda, livello) {
  if (!mio || !domanda || !domanda.a || !domanda.b) return null;
  const tipo = livelloTerritorio(livello);
  const territori = [
    { key: domanda.a.key, level: tipo, lato: "a" },
    { key: domanda.b.key, level: tipo, lato: "b" },
  ];
  const trovato = trovaTerritorioMio(mio, territori);
  return trovato ? trovato.lato : null;
}

// Il nome (come lo scrive il server) del primo territorio del giocatore fra le domande, o
// `null`. Le chiavi sono nelle domande prima di rispondere: non rivela niente.
export function primoTerritorioMio(mio, domande, livello) {
  if (!mio || !Array.isArray(domande)) return null;
  for (const domanda of domande) {
    const lato = coppiaDelTerritorio(mio, domanda, livello);
    if (lato) return domanda[lato].name || null;
  }
  return null;
}
