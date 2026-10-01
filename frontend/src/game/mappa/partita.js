// La logica pura di "Dov'e' la provincia?": testi, tono, esiti da condividere, la partita in
// corso e la sua memoria locale. Niente React, niente DOM: `node --test` la importa cosi'
// com'e' (`partita.test.mjs`), e i giochi vicini fanno lo stesso (`compare-logica.js`).
//
// Il server decide tutto cio' che conta (punti, esito, distanza): qui si scrive soltanto
// come lo si dice. Un testo non usa mai `;`, i due trattini lunghi e i tre puntini, ne' dice
// il nome della provincia prima della rivelazione.

import { trovaTerritorioMio } from "../puri.js";

export const GIOCO = "mappa";

// Le tre partite del giorno. Il server le conosce come `level` e `mode`: tre esercizi diversi
// (la mappa a tutta Italia, la mappa con la regione detta, la sola regione senza mappa), e il
// terzo non e' equivalente ai primi due. `aiuto` lo dice.
export const OPZIONI = [
  {
    id: "italia-map",
    livello: "italia",
    modalita: "map",
    titolo: "Tutta Italia",
    aiuto: "Parti dall'Italia intera: tocca la regione, poi la provincia. Massimo 20 punti.",
  },
  {
    id: "regione-map",
    livello: "regione",
    modalita: "map",
    titolo: "Con la regione detta",
    aiuto: "Il livello facile: ti diciamo la regione e la mappa parte già stretta su di essa. Massimo 20 punti.",
  },
  {
    id: "italia-list",
    livello: "italia",
    modalita: "list",
    titolo: "Senza mappa: conta la regione",
    aiuto: "Un altro esercizio, per chi non usa la mappa: stesse province, ma dici solo in quale regione si trovano. Vale 1 punto, massimo 10.",
  },
];

export function opzione(livello, modalita) {
  return OPZIONI.find((o) => o.livello === livello && o.modalita === modalita) || OPZIONI[0];
}

export const DIREZIONI = {
  N: "nord",
  NE: "nord-est",
  E: "est",
  SE: "sud-est",
  S: "sud",
  SO: "sud-ovest",
  O: "ovest",
  NO: "nord-ovest",
};

export function frasePunti(n) {
  return `${n} ${n === 1 ? "punto" : "punti"}`;
}

// La domanda come la scrive il server (`question.label`: "Dov'è Lecce?"). Se il server
// mandasse solo il nome, si compone qui.
export function testoDomanda(domanda) {
  if (!domanda) return "";
  if (typeof domanda.label === "string" && domanda.label) return domanda.label;
  return domanda.name ? `Dov'è ${domanda.name}?` : "";
}

// "a circa 120 km a nord-est, stima": la distanza e la direzione dalla scelta alla giusta sono
// fra i centri delle sagome, quindi si dichiarano una stima. Senza distanza (esatta, o senza
// mappa) niente. Con una distanza ma senza direzione (centri coincidenti) solo i chilometri.
export function fraseDistanza(km, direzione) {
  if (!Number.isFinite(km) || km <= 0) return "";
  const dove = DIREZIONI[direzione];
  return dove ? `a circa ${km} km a ${dove}, stima` : `a circa ${km} km, stima`;
}

// La riga che dice che cosa fare adesso, sotto la domanda. Cambia con la vista e la selezione.
// Senza mappa e' un'altra istruzione. Mai il nome di una provincia.
export function testoIstruzione({ modalita, vista, selezionata }) {
  if (modalita === "list") return "Scegli la regione e conferma.";
  if (selezionata) return "Provincia scelta. Conferma, oppure tocca un'altra.";
  if (vista === "italia") return "Tocca la regione dove pensi che sia.";
  return "Tocca la provincia.";
}

// Come si dice un esito. `segno` e' il nome della forma (mai il solo colore) e `verdetto` la
// riga breve in cima, `dettaglio` quella sotto. `risposta` e' il 200 del server.
export function testoEsito(risposta, modalita) {
  const { esito, points: punti, chosen, right } = risposta;
  const luogo = `${right.name}, in ${right.region}`;
  if (modalita === "list") {
    if (esito === "exact") {
      return { segno: "esatto", verdetto: `Regione giusta, ${frasePunti(punti)}.`, dettaglio: `${luogo}.` };
    }
    return {
      segno: "errore",
      verdetto: `Regione sbagliata, ${frasePunti(punti)}.`,
      dettaglio: `Hai scelto ${chosen.name}. La risposta era ${luogo}.`,
    };
  }
  if (esito === "exact") {
    return { segno: "esatto", verdetto: `Esatto, ${frasePunti(punti)}.`, dettaglio: `${luogo}.` };
  }
  const distanza = fraseDistanza(risposta.distance_km, risposta.direction);
  const scia = distanza ? ` Dalla tua scelta è ${distanza}.` : "";
  const dettaglio = `Hai scelto ${chosen.name}. La risposta era ${luogo}.${scia}`;
  if (esito === "region") {
    return { segno: "vicino", verdetto: `Stessa regione, ${frasePunti(punti)}.`, dettaglio };
  }
  return { segno: "errore", verdetto: `Sbagliata, ${frasePunti(punti)}.`, dettaglio };
}

// Il tono dell'esito di una partita: "giusto" se almeno 80% dei punti, "sbagliato" solo a zero
// punti, "parziale" negli altri casi (un parziale non e' una croce).
export function tonoPartita(punti, massimo) {
  if (!(massimo > 0) || !(punti > 0)) return "sbagliato";
  return punti / massimo >= 0.8 ? "giusto" : "parziale";
}

// `FinePartita` chiama i toni in un altro modo (`pieno`, `parziale`, `nullo`).
export function tonoFine(tono) {
  return { giusto: "pieno", parziale: "parziale", sbagliato: "nullo" }[tono] || "nullo";
}

// Gli esiti da condividere sono `exact`, `region` e `miss` (le forme ●, ◐, ○). Senza mappa la
// risposta giusta e' la regione: la forma e' quella della "regione giusta", mai "esatta", perche'
// non si finge che le due partite siano la stessa.
export function esitiPerCondivisione(esiti, modalita) {
  const lista = Array.isArray(esiti) ? esiti : [];
  return lista.map((e) => {
    if (modalita === "list") return e === "exact" ? "region" : "miss";
    return e === "exact" || e === "region" ? e : "miss";
  });
}

function conta(esiti, valore) {
  return (Array.isArray(esiti) ? esiti : []).filter((e) => e === valore).length;
}

// La riga sotto il titolo di fine partita, senza spoiler.
export function riassunto(esiti, modalita) {
  if (modalita === "list") {
    const giuste = conta(esiti, "exact");
    return `${giuste} ${giuste === 1 ? "regione giusta" : "regioni giuste"}`;
  }
  const esatte = conta(esiti, "exact");
  const vicine = conta(esiti, "region");
  const prima = `${esatte} ${esatte === 1 ? "provincia esatta" : "province esatte"}`;
  return `${prima}, ${vicine} nella regione giusta`;
}

// La riga che l'hub mostra per la partita di oggi.
export function testoHub(punti, massimo, modalita) {
  const base = `${punti} su ${massimo}`;
  return modalita === "list" ? `${base}, senza mappa` : base;
}

export function titoloFine(punti, massimo) {
  return `${punti} su ${massimo}`;
}

export function chiavePartita(livello, modalita, iso) {
  return `di-mappa-partita:${livello}:${modalita}:${iso}`;
}

// Errori del server con un nome, e che cosa dire. Quelli di un doppio invio non si dicono: il
// primo invio e' gia' arrivato.
export const ERRORI = {
  puzzle_changed: "La sfida del giorno è cambiata mentre giocavi. Riapri la partita.",
  session_expired: "La partita è scaduta. Riaprila per giocare la sfida di oggi.",
  token_invalid: "",
  round_already_answered: "",
  rate_limited: "Troppe richieste in poco tempo. Riprova fra un minuto.",
  seed_unavailable: "La sfida del giorno non è disponibile in questo momento. Riprova più tardi.",
  bad_request: "Risposta non valida. Riprova.",
};

export const ERRORI_DA_RIAPRIRE = new Set(["puzzle_changed", "session_expired", "token_invalid"]);

export function messaggioErrore(codice) {
  return Object.prototype.hasOwnProperty.call(ERRORI, codice) ? ERRORI[codice] : "Qualcosa non ha funzionato. Riprova.";
}

// -- La partita in corso -----------------------------------------------------------------

export function nuovaPartita(sessione) {
  return {
    puzzle_id: sessione.puzzle_id,
    number: sessione.number,
    date: sessione.date,
    next_puzzle_at: sessione.next_puzzle_at,
    level: sessione.level,
    level_label: sessione.level_label,
    mode: sessione.mode,
    total: sessione.total,
    points_max: sessione.points_max,
    regions: Array.isArray(sessione.regions) ? sessione.regions : null,
    token: sessione.token,
    question: sessione.question,
    risposte: [],
    punti: 0,
    fine: null,
  };
}

function compatta(t) {
  if (!t) return null;
  const voce = { key: t.key, name: t.name, region: t.region, path: t.path };
  if (t.region_key) voce.region_key = t.region_key;
  return voce;
}

// La partita dopo una risposta del server. Non muta l'argomento. Si tiene solo cio' che serve a
// ripartire e a scrivere la fine: il token (che porta il resto), la domanda dopo e, per ogni
// domanda, l'esito con la provincia giusta.
export function applicaRisposta(partita, risposta) {
  return {
    ...partita,
    token: risposta.token,
    question: risposta.next_question || null,
    risposte: [
      ...partita.risposte,
      {
        index: risposta.index,
        esito: risposta.esito,
        points: risposta.points,
        chosen: compatta(risposta.chosen),
        right: compatta(risposta.right),
      },
    ],
    punti: risposta.score ? risposta.score.points : partita.punti + (risposta.points || 0),
    fine: risposta.summary || null,
  };
}

export function serializzaPartita(partita) {
  return JSON.stringify(partita);
}

// La partita letta dalla memoria locale, o `null`: JSON rotto, un'altra sfida (giorno, livello
// o modalita' diversi), forme che non tornano. E' una comodita': il token porta il resto, e se
// il server lo rifiuta si riapre.
export function leggiPartita(grezzo, { livello, modalita, iso }) {
  if (typeof grezzo !== "string" || grezzo.length > 60000) return null;
  let p;
  try {
    p = JSON.parse(grezzo);
  } catch {
    return null;
  }
  if (!p || typeof p !== "object") return null;
  if (p.puzzle_id !== `daily:${iso}` || p.level !== livello || p.mode !== modalita) return null;
  if (typeof p.token !== "string" || !p.token) return null;
  if (!Number.isInteger(p.total) || p.total <= 0 || !Number.isInteger(p.points_max)) return null;
  if (!Array.isArray(p.risposte) || p.risposte.length > p.total) return null;
  if (!Number.isInteger(p.punti) || p.punti < 0 || p.punti > p.points_max) return null;
  if (p.fine) {
    if (typeof p.fine !== "object" || !Array.isArray(p.fine.esiti) || p.risposte.length !== p.total) return null;
  } else if (!p.question || typeof p.question !== "object" || !Number.isInteger(p.question.index)
    || p.question.index !== p.risposte.length) {
    return null;
  }
  return p;
}

// Le dieci province della partita per i link a fine partita, nell'ordine delle domande.
export function territoriFinali(risposte) {
  const visti = new Set();
  const lista = [];
  for (const r of Array.isArray(risposte) ? risposte : []) {
    if (!r || !r.right || visti.has(r.right.path)) continue;
    visti.add(r.right.path);
    lista.push({ name: r.right.name, path: r.right.path });
  }
  return lista;
}

// Il nome del territorio del giocatore se e' una delle province della partita o la sua regione.
export function territorioMioFra(mio, risposte) {
  if (!mio) return null;
  const candidati = [];
  for (const r of Array.isArray(risposte) ? risposte : []) {
    if (!r || !r.right) continue;
    candidati.push({ key: r.right.key, level: "provincia", name: r.right.name });
    if (r.right.region_key) candidati.push({ key: r.right.region_key, level: "regione", name: r.right.region });
  }
  const trovato = trovaTerritorioMio(mio, candidati);
  return trovato ? trovato.name : null;
}

// I parametri dell'evento GA4 di una risposta: solo etichette e conti, mai un nome.
export function parametriRisposta(partita, risposta, extra = {}) {
  return {
    game: GIOCO,
    mode: "daily",
    level: partita.level,
    answer_mode: partita.mode,
    index: risposta.index,
    esito: risposta.esito,
    ...extra,
  };
}
