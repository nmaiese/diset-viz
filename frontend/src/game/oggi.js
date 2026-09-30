// Lo stato di oggi, in un punto solo: quali sfide del giorno ha giocato questo
// dispositivo e come sono andate. Lo scrivono i quattro giochi a fine partita
// (`segnaGiocata`), lo legge l'hub (`statoOggi`, `serieLocale`). Sta nel
// localStorage con la chiave `di-oggi:<gioco>:<ISO>`, il giorno e' quello di
// Roma. Niente React qui: le funzioni sono pure salvo la lettura e la scrittura
// del localStorage, e se questo manca (navigazione privata) tutto tace.

import { oggiRoma } from "./guess/serie.js";

export { oggiRoma };

export const GIOCHI = ["indovina", "provincia", "compare", "order"];

const PREFISSO = "di-oggi:";

function chiave(gioco, iso) {
  return `${PREFISSO}${gioco}:${iso}`;
}

// `esito` e' `{ ok: boolean, testo: string }`: `ok` decide l'icona (giusto o
// sbagliato), `testo` e' la riga che la accompagna ("Risolta in 3 tentativi").
export function segnaGiocata(gioco, iso, esito) {
  if (!GIOCHI.includes(gioco) || !/^\d{4}-\d{2}-\d{2}$/.test(iso || "")) return;
  try {
    window.localStorage.setItem(chiave(gioco, iso), JSON.stringify({ ok: Boolean(esito && esito.ok), testo: String((esito && esito.testo) || "") }));
  } catch {
    // Senza localStorage l'hub non sa che hai giocato: nessun danno per la partita.
  }
}

// L'esito di oggi di un gioco, o null se non e' stato giocato.
export function statoOggi(gioco, iso = oggiRoma()) {
  try {
    const grezzo = window.localStorage.getItem(chiave(gioco, iso));
    if (!grezzo) return null;
    const esito = JSON.parse(grezzo);
    return { ok: Boolean(esito.ok), testo: String(esito.testo || "") };
  } catch {
    return null;
  }
}

// Un giorno riposato non spezza la serie, ma si perdona al massimo una volta ogni tanti giorni.
export const RIPOSO_OGNI_GIORNI = 7;

const ISO = /^\d{4}-\d{2}-\d{2}$/;

// Il numero di giorno (dall'epoca Unix) di una data ISO, o null se non e' una data vera.
function numeroDiGiorno(iso) {
  if (typeof iso !== "string" || !ISO.test(iso)) return null;
  const [y, m, d] = iso.split("-").map(Number);
  const t = Date.UTC(y, m - 1, d);
  const data = new Date(t);
  if (data.getUTCFullYear() !== y || data.getUTCMonth() !== m - 1 || data.getUTCDate() !== d) return null;
  return Math.round(t / 86400000);
}

// `{ current, max }`: la serie dei giorni giocati di fila. E' la STESSA definizione di
// `player_stats.play_streak` sul server, e le due si provano sugli stessi vettori
// (`tests/fixtures/play_streak_cases.json`): un giorno conta se hai giocato almeno una
// delle quattro sfide del giorno. Un giorno di riposo e' automatico: la serie continua
// se fra due giorni giocati manca al massimo UN giorno, e quel perdono si usa al massimo
// una volta ogni 7 giorni. La serie conta i giorni GIOCATI, non quelli perdonati. Le date
// non ISO e quelle dopo `oggiIso` si ignorano, i doppioni contano una volta, l'ordine non
// conta. `current` vale solo se l'ultimo giorno giocato e' oggi o ieri. Funzione pura.
export function playStreak(giorni, oggiIso) {
  const oggi = numeroDiGiorno(oggiIso);
  if (oggi === null) return { current: 0, max: 0 };
  const insieme = new Set();
  for (const g of giorni instanceof Set ? giorni : Array.from(giorni || [])) {
    const n = numeroDiGiorno(g);
    if (n !== null && n <= oggi) insieme.add(n);
  }
  const ordinati = [...insieme].sort((a, b) => a - b);
  if (ordinati.length === 0) return { current: 0, max: 0 };
  let corrente = 1;
  let massimo = 1;
  let perdonato = null; // il giorno vuoto perdonato piu' di recente nella serie
  for (let i = 1; i < ordinati.length; i += 1) {
    const prima = ordinati[i - 1];
    const distanza = ordinati[i] - prima;
    const riposo = prima + 1;
    if (distanza === 1) {
      corrente += 1;
    } else if (distanza === 2 && (perdonato === null || riposo - perdonato >= RIPOSO_OGNI_GIORNI)) {
      corrente += 1;
      perdonato = riposo;
    } else {
      corrente = 1;
      perdonato = null;
    }
    massimo = Math.max(massimo, corrente);
  }
  const attuale = oggi - ordinati[ordinati.length - 1] <= 1 ? corrente : 0;
  return { current: attuale, max: massimo };
}

// I giorni di fila di oggi (il solo `current`), per chi non ha bisogno del massimo.
export function serieDaGiorni(giorni, oggiIso) {
  return playStreak(giorni, oggiIso).current;
}

// La serie di questo dispositivo, dalle chiavi `di-oggi:*`.
export function serieLocale(oggiIso = oggiRoma()) {
  const giorni = new Set();
  try {
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const k = window.localStorage.key(i);
      if (k && k.startsWith(PREFISSO)) giorni.add(k.slice(k.lastIndexOf(":") + 1));
    }
  } catch {
    return 0;
  }
  return serieDaGiorni(giorni, oggiIso);
}
