// Costanti, testi e salvataggi di Indovina la Provincia. Il risultato sta solo
// in localStorage: nella serie e in classifica lo porta l'ondata 3, e non entra
// mai nella serie regionale del server. Niente qui importa React o `shared.jsx`:
// la logica pura si prova con `node --test` (provincia.test.mjs).

import { normalize } from "./helpers.js";
import { inviaJson } from "./rete.js";
import { PARTITA_INTERROTTA } from "../testi.js";
import { analizza, extraProvincia, progressoValido, statsProvincia } from "../salvati.js";

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

// "Circa 120 km verso nord-est, stima". I km sono stimati fra i centri delle province, e lo dice la parola.
export function testoDistanza(guess) {
  if (guess.correct) return "";
  const punto = direzione(guess.direction);
  const km = Number(guess.distance_km).toLocaleString("it-IT");
  return punto ? `Circa ${km} km verso ${punto.parola}, stima` : `Circa ${km} km, stima`;
}

// "della regione", "di tutta Italia": si abbassa solo la prima lettera, "Italia" resta maiuscola.
export function nomeLivello(key) {
  const { label } = LIVELLI.find((l) => l.key === key) || LIVELLI[0];
  return label.charAt(0).toLowerCase() + label.slice(1);
}

// La riga di sintesi del testo condiviso: i tentativi ("3 su 6") e il livello, mai il nome.
export function riassuntoProvincia({ won, tentativi, totale, level }) {
  return `${won ? tentativi : "X"} su ${totale}, livello ${nomeLivello(level)}`;
}

// "a circa 120 km verso nord-est": la riga compatta di un tentativo sbagliato. Vuota per quello giusto.
export function testoDistanzaCompatta(guess) {
  const testo = testoDistanza(guess);
  return testo ? testo.replace(/^Circa/, "a circa") : "";
}

// -- Il nome di una regione in una frase ---------------------------------------------
// "della Puglia", "nel Lazio", "nelle Marche", "dell'Umbria": l'articolo non si deduce dal nome.
// Le venti regioni del gioco (i nomi di `game_daily.province_pool`) sono qui, e un nome che non
// c'e' non si indovina: "di X" e "in X", senza articolo.
const ARTICOLI_REGIONE = {
  "Abruzzo": ["dell'", "in "],
  "Basilicata": ["della ", "in "],
  "Calabria": ["della ", "in "],
  "Campania": ["della ", "in "],
  "Emilia-Romagna": ["dell'", "in "],
  "Friuli-Venezia Giulia": ["del ", "in "],
  "Lazio": ["del ", "nel "],
  "Liguria": ["della ", "in "],
  "Lombardia": ["della ", "in "],
  "Marche": ["delle ", "nelle "],
  "Molise": ["del ", "in "],
  "Piemonte": ["del ", "in "],
  "Puglia": ["della ", "in "],
  "Sardegna": ["della ", "in "],
  "Sicilia": ["della ", "in "],
  "Toscana": ["della ", "in "],
  "Trentino Alto Adige": ["del ", "in "],
  "Umbria": ["dell'", "in "],
  "Valle d'Aosta": ["della ", "in "],
  "Veneto": ["del ", "in "],
};

export function regioneConArticolo(nome) {
  const voce = ARTICOLI_REGIONE[nome];
  if (!voce) return { di: `di ${nome}`, in: `in ${nome}` };
  return { di: `${voce[0]}${nome}`, in: `${voce[1]}${nome}` };
}

// Che cosa dire sotto il campo quando il testo non porta a nessun suggerimento, al livello
// "della regione". `null` se non c'e' niente da dire (testo vuoto o suggerimenti in vista).
//   regione  { name }: la regione della provincia misteriosa, o null al livello di tutta Italia
//   opzioni  [{ key, name }]: le province della regione, fra cui si sceglie
//   altre    [{ name, region }]: le province delle altre regioni (`other_provinces` del payload)
//   tentate  [key]: le province gia' provate
// Tre casi: una provincia di un'altra regione ("Milano non e' in Puglia"), una della regione
// gia' provata, nessuna. Si confronta senza maiuscole, accenti e punteggiatura.
export function messaggioFuoriElenco(testo, { regione, opzioni = [], altre = [], tentate = [] }) {
  const q = chiave(testo);
  if (!q) return null;
  const dentro = opzioni.filter((p) => chiave(p.name).includes(q));
  if (dentro.length > 0) {
    if (dentro.some((p) => !tentate.includes(p.key))) return null;
    return `Hai già provato ${dentro[0].name}. Scegline un'altra dall'elenco.`;
  }
  // Senza regione (il livello di tutta Italia) si sceglie fra tutte: non c'e' un "altrove".
  if (!regione) return "Nessuna provincia si chiama così. Scegli dall'elenco.";
  const articolo = regioneConArticolo(regione.name);
  const fuori = trovaFuori(altre, q);
  if (fuori) {
    return `${fuori.name} non è ${articolo.in}. Qui cerchi fra le province ${articolo.di}.`;
  }
  return `Nessuna provincia ${articolo.di} si chiama così. Scegli dall'elenco.`;
}

// A fine partita, se il territorio scelto dal giocatore (`useTerritorioMio`, `di:mio`) c'entra con la
// provincia di oggi: una riga sola, o `null`. `soluzione` e' quella del payload di fine partita.
// `province` ([{ key, region }], quelle del payload) serve quando il territorio salvato e' una provincia
// senza la sua regione (`region` e' facoltativa in `di:mio`): la regione si ricava dal nome.
export function rigaTerritorio(mio, soluzione, province = []) {
  if (!mio || !soluzione) return null;
  if (mio.level === "provincia" && mio.key === soluzione.province_key) return "La provincia di oggi è la tua.";
  if (mio.level === "provincia" && !mio.region) {
    const sua = province.find((p) => p.key === mio.key);
    return sua && sua.region === soluzione.region ? "La provincia di oggi è della tua regione." : null;
  }
  const sua = mio.level === "provincia" ? mio.region : mio.key;
  return sua && sua === soluzione.region_key ? "La provincia di oggi è della tua regione." : null;
}

// Il testo come si confronta: senza maiuscole, accenti e punteggiatura ("Forlì-Cesena" e "forli cesena").
function chiave(testo) {
  return normalize(testo).replace(/[^a-z0-9]+/g, " ").trim();
}

// Fra le province delle altre regioni: prima il nome uguale al testo, poi uno che comincia cosi',
// poi uno che lo contiene. A parita' vince l'ordine dell'elenco (alfabetico).
function trovaFuori(altre, q) {
  const nomi = altre.map((p) => [p, chiave(p.name)]);
  const trovata = nomi.find(([, n]) => n === q) || nomi.find(([, n]) => n.startsWith(q)) || nomi.find(([, n]) => n.includes(q));
  return trovata ? trovata[0] : null;
}

// Il tentativo che il server ha registrato ma di cui il client non ha avuto la risposta (la rete e'
// caduta) lascia il token salvato superato: ogni nuovo tentativo darebbe `token_superato` (409), e
// ricaricare la pagina rimetterebbe lo stesso token. Si dimentica il progresso e si riparte, una
// volta, dicendolo.
export const AVVISO_RIPRESA = `${PARTITA_INTERROTTA} La riapriamo da capo.`;

// Che cosa fare di un tentativo rifiutato (funzione pura). Ritorna
//   "riprendi"  si dimentica il progresso salvato e si ricarica la sfida da soli, una volta sola;
//   "ricarica"  messaggio e "Ricarica la pagina" (la sfida e' cambiata, o la ripresa non e' bastata);
//   "messaggio" un errore che passa: si resta sul campo e si puo' riprovare.
// `giaRipresa` e' vero se la partita e' gia' ripartita da sola e non ha avuto un tentativo buono:
// un secondo `token_superato` non la rilancia (sarebbe un ciclo).
export function decisioneErroreTentativo({ status, code } = {}, { giaRipresa = false } = {}) {
  if (status === 409 || code === "token_superato") return giaRipresa ? "ricarica" : "riprendi";
  if (code === "sfida_scaduta") return "ricarica";
  return "messaggio";
}

// Un tentativo: manda il Bearer (il server attribuisce punteggio e traguardi all'account) e, a fine
// partita, passa i traguardi sbloccati a `notify` (il toast di `shared.jsx`).
export async function inviaTentativo(token, provinceKey, { getToken, fetchImpl, notify } = {}) {
  const risultato = await inviaJson(API_PROVINCIA.guess, { token, province_key: provinceKey }, { getToken, fetchImpl });
  if (notify && risultato && risultato.finished) notify(risultato.achievements, "provincia");
  return risultato;
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

// Il progresso salvato di una partita, o `null` se manca o non ha la forma giusta (si riparte da zero).
export function caricaProgresso(puzzleId) {
  return progressoValido(analizza(leggi(STORAGE_PROGRESS + puzzleId)), { extra: extraProvincia(LIVELLI.map((l) => l.key)) });
}

// Dimentica il progresso di una partita: dopo un tentativo perso in rete il token salvato e'
// superato, e rileggerlo darebbe lo stesso errore a ogni tentativo.
export function rimuoviProgresso(puzzleId) {
  try {
    window.localStorage.removeItem(STORAGE_PROGRESS + puzzleId);
  } catch {
    // niente da fare
  }
}

export function salvaProgresso(puzzleId, progresso) {
  scrivi(STORAGE_PROGRESS + puzzleId, JSON.stringify(progresso));
}

export function caricaStatistiche() {
  return statsProvincia(analizza(leggi(STORAGE_STATS)));
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
