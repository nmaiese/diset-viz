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

// Il "fatto" lo scrive il server (`app/game_facts.py`, un worker dedicato) e questo client non
// lo calcola. Il contratto del payload non e' ancora deciso (la spec dice `fatto`, le regole
// `fact`; ne' dicono se sta nel `summary` o in cima alla risposta): si legge in UN punto solo,
// qui, cosi' quando si decide si cambia una riga.
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
