import test from "node:test";
import assert from "node:assert/strict";
import {
  ATTESA_RITENTO_MS,
  MAX_TENTATIVI_INVIO,
  decisioneInvio,
  API_AVANTI,
  ROUND_MS,
  TICK_MS,
  avviaScadenza,
  campoFatto,
  chiediAvanti,
  coppiaDelTerritorio,
  livelloTerritorio,
  primoTerritorioMio,
  tonoCompare,
} from "./compare-logica.js";

// -- Il timer --------------------------------------------------------------------

// Un orologio e un pianificatore finti: niente attese vere, e il tempo avanza solo quando
// lo dice il test.
function orologioFinto() {
  let ora = 1000;
  const intervalli = new Map();
  let prossimo = 1;
  return {
    adesso: () => ora,
    programma: (fn, ogni) => {
      const id = prossimo++;
      intervalli.set(id, { fn, ogni });
      return id;
    },
    annulla: (id) => intervalli.delete(id),
    attivi: () => intervalli.size,
    avanza(ms) {
      const passi = Math.ceil(ms / TICK_MS);
      for (let i = 0; i < passi; i += 1) {
        ora += TICK_MS;
        for (const { fn } of [...intervalli.values()]) fn();
      }
    },
    salta(ms) {
      // Una scheda in background: il tempo passa ma gli intervalli non scattano.
      ora += ms;
    },
    scatta() {
      for (const { fn } of [...intervalli.values()]) fn();
    },
  };
}

test("la scadenza chiama la risposta di timeout UNA volta sola", () => {
  const o = orologioFinto();
  let chiamate = 0;
  avviaScadenza({ ms: ROUND_MS, onScadenza: () => { chiamate += 1; }, ...o });
  o.avanza(ROUND_MS + 2000);
  assert.equal(chiamate, 1);
  assert.equal(o.attivi(), 0, "l'intervallo si ferma alla scadenza");
});

test("un aggiornamento di stato chiamato due volte, come fa StrictMode, non spara due timeout", () => {
  // Lo schema vecchio chiamava la risposta DENTRO l'updater di `setTimeLeft`: React puo'
  // invocare un updater piu' volte, e ogni invocazione rifaceva la richiesta. Qui
  // `onTick` riceve un valore gia' calcolato e lo aggiornamento dello stato e' puro.
  const o = orologioFinto();
  let chiamate = 0;
  const visti = [];
  const setStatoFinto = (valore) => {
    // Come StrictMode: stessa funzione/valore applicato due volte.
    visti.push(valore);
    visti.push(valore);
  };
  avviaScadenza({
    ms: 500,
    onTick: setStatoFinto,
    onScadenza: () => { chiamate += 1; },
    ...o,
  });
  o.avanza(1000);
  assert.equal(chiamate, 1);
  assert.ok(visti.every((v) => typeof v === "number"), "onTick riceve un numero, non un updater");
  assert.equal(visti[visti.length - 1], 0);
});

test("il conto e' a scadenza assoluta: una scheda in background non rallenta il tempo", () => {
  const o = orologioFinto();
  const tick = [];
  let chiamate = 0;
  avviaScadenza({ ms: ROUND_MS, onTick: (r) => tick.push(r), onScadenza: () => { chiamate += 1; }, ...o });
  o.avanza(300);
  assert.equal(tick[tick.length - 1], ROUND_MS - 300);
  o.salta(ROUND_MS); // il browser ha congelato gli intervalli
  o.scatta();
  assert.equal(chiamate, 1, "al primo scatto utile il tempo e' scaduto");
  assert.equal(tick[tick.length - 1], 0);
});

test("fermare il timer prima della scadenza non chiama niente", () => {
  const o = orologioFinto();
  let chiamate = 0;
  const ferma = avviaScadenza({ ms: ROUND_MS, onScadenza: () => { chiamate += 1; }, ...o });
  o.avanza(1000);
  ferma();
  o.avanza(ROUND_MS * 2);
  assert.equal(chiamate, 0);
  assert.equal(o.attivi(), 0);
});

test("dopo la scadenza i tick in ritardo non richiamano la risposta", () => {
  const o = orologioFinto();
  let chiamate = 0;
  avviaScadenza({ ms: 200, onScadenza: () => { chiamate += 1; }, ...o });
  o.avanza(200);
  o.scatta();
  o.scatta();
  assert.equal(chiamate, 1);
});

// -- "Avanti" --------------------------------------------------------------------

test("Avanti chiama next con token, puzzle_id e l'indice appena risposto", async () => {
  const chiamate = [];
  const post = async (url, corpo) => {
    chiamate.push({ url, corpo });
    return { ok: true, status: 200, data: { token: "token-nuovo" } };
  };
  const esito = await chiediAvanti({ post, token: "token-vecchio", puzzleId: "daily:2026-10-01", q: 3 });
  assert.deepEqual(chiamate, [
    { url: "/api/game/compare/daily/next", corpo: { token: "token-vecchio", puzzle_id: "daily:2026-10-01", q: 3 } },
  ]);
  assert.equal(API_AVANTI, "/api/game/compare/daily/next");
  assert.deepEqual(esito, { ok: true, token: "token-nuovo" });
});

test("un errore di rete si puo' riprovare, un token superato no", async () => {
  const rete = await chiediAvanti({
    post: async () => ({ ok: false, status: 0, data: {} }), token: "t", puzzleId: "p", q: 0,
  });
  assert.deepEqual(rete, { ok: false, riprova: true, errore: "" });

  const server = await chiediAvanti({
    post: async () => ({ ok: false, status: 503, data: {} }), token: "t", puzzleId: "p", q: 0,
  });
  assert.equal(server.riprova, true);

  const limite = await chiediAvanti({
    post: async () => ({ ok: false, status: 429, data: { error: "rate_limited" } }), token: "t", puzzleId: "p", q: 0,
  });
  assert.equal(limite.riprova, true);

  const usato = await chiediAvanti({
    post: async () => ({ ok: false, status: 409, data: { error: "round_already_bound" } }),
    token: "t", puzzleId: "p", q: 0,
  });
  assert.deepEqual(usato, { ok: false, riprova: false, errore: "round_already_bound" });

  const cambiato = await chiediAvanti({
    post: async () => ({ ok: false, status: 400, data: { error: "puzzle_changed" } }), token: "t", puzzleId: "p", q: 0,
  });
  assert.equal(cambiato.riprova, false);
});

test("una risposta 200 senza un token valido non passa per buona", async () => {
  const esito = await chiediAvanti({
    post: async () => ({ ok: true, status: 200, data: {} }), token: "t", puzzleId: "p", q: 0,
  });
  assert.equal(esito.ok, false);
  assert.equal(esito.riprova, false);
});

// -- Il tono ----------------------------------------------------------------------

test("il tono: pieno solo 10 su 10, nullo solo 0, parziale tutto il resto", () => {
  assert.equal(tonoCompare(10, 10), "pieno");
  assert.equal(tonoCompare(0, 10), "nullo");
  for (const giuste of [1, 4, 5, 6, 9]) assert.equal(tonoCompare(giuste, 10), "parziale", `${giuste} su 10`);
});

test("un punteggio o un totale che non hanno senso non diventano mai un fallimento", () => {
  assert.equal(tonoCompare(undefined, 10), "parziale");
  assert.equal(tonoCompare(3, 0), "parziale");
  assert.equal(tonoCompare(-1, 10), "parziale");
  assert.equal(tonoCompare(11, 10), "parziale");
});

// -- Il fatto ----------------------------------------------------------------------

test("il fatto si legge in un punto solo e solo se e' una stringa", () => {
  assert.equal(campoFatto({ summary: { fatto: "Una frase." } }), "Una frase.");
  assert.equal(campoFatto({ summary: { fact: "Una frase." } }), "Una frase.");
  assert.equal(campoFatto({ fatto: "Una frase." }), "Una frase.");
  assert.equal(campoFatto({ summary: {} }), undefined);
  assert.equal(campoFatto({ summary: { fatto: 12 } }), undefined);
  assert.equal(campoFatto(null), undefined);
});

// -- Il territorio del giocatore -----------------------------------------------------

test("il livello dei territori: le regioni sono regioni, tutto il resto e' provincia", () => {
  assert.equal(livelloTerritorio("regioni"), "regione");
  assert.equal(livelloTerritorio("stessa_regione"), "provincia");
  assert.equal(livelloTerritorio("province"), "provincia");
});

const DOMANDE = [
  { a: { key: "lombardia", name: "Lombardia" }, b: { key: "puglia", name: "Puglia" } },
  { a: { key: "sicilia", name: "Sicilia" }, b: { key: "veneto", name: "Veneto" } },
];

test("il territorio scelto compare nella coppia, con il lato giusto", () => {
  const mio = { level: "regione", key: "puglia", name: "Puglia" };
  assert.equal(coppiaDelTerritorio(mio, DOMANDE[0], "regioni"), "b");
  assert.equal(coppiaDelTerritorio(mio, DOMANDE[1], "regioni"), null);
});

test("una chiave di regione non accende una provincia con la stessa chiave", () => {
  const mio = { level: "regione", key: "puglia", name: "Puglia" };
  assert.equal(coppiaDelTerritorio(mio, DOMANDE[0], "province"), null);
});

test("la provincia scelta accende la sua regione nelle coppie fra regioni", () => {
  const mio = { level: "provincia", key: "bari", name: "Bari", region: "puglia", regionName: "Puglia" };
  assert.equal(coppiaDelTerritorio(mio, DOMANDE[0], "regioni"), "b");
});

test("senza territorio o senza coppia non c'e' niente da evidenziare", () => {
  assert.equal(coppiaDelTerritorio(null, DOMANDE[0], "regioni"), null);
  assert.equal(coppiaDelTerritorio({ level: "regione", key: "x", name: "X" }, null, "regioni"), null);
});

test("fra le dieci coppie si trova il nome del territorio, quello del server", () => {
  const mio = { level: "regione", key: "veneto", name: "Veneto" };
  assert.equal(primoTerritorioMio(mio, DOMANDE, "regioni"), "Veneto");
  assert.equal(primoTerritorioMio({ level: "regione", key: "molise", name: "Molise" }, DOMANDE, "regioni"), null);
  assert.equal(primoTerritorioMio(null, DOMANDE, "regioni"), null);
  assert.equal(primoTerritorioMio(mio, [], "regioni"), null);
});

test("il link del fatto e' solo un percorso interno di scheda indicatore", async () => {
  const { campoFattoPath } = await import("./compare-logica.js");
  assert.equal(campoFattoPath({ summary: { fact_path: "/indicatore/tasso-di-occupazione/ter-105" } }), "/indicatore/tasso-di-occupazione/ter-105");
  assert.equal(campoFattoPath({ summary: { fact_path: "https://esempio.it/x" } }), undefined);
  assert.equal(campoFattoPath({ summary: { fact_path: "//esempio.it" } }), undefined);
  assert.equal(campoFattoPath({}), undefined);
  assert.equal(campoFattoPath(null), undefined);
});

// -- L'invio di una risposta ------------------------------------------------------------------

const RISPOSTA_200 = { ok: true, status: 200, data: { correct: false, late: true, token: "t" } };
const RETE = { ok: false, status: 0, data: {} };

test("decisioneInvio: un 200 e' una rivelazione, anche con late: true (una risposta sbagliata)", () => {
  assert.deepEqual(decisioneInvio(RISPOSTA_200, { scelta: "region_a" }), { azione: "rivelata" });
  assert.deepEqual(decisioneInvio({ ok: true, status: 200, data: { correct: true } }, { scelta: "region_b" }), { azione: "rivelata" });
});

test("decisioneInvio: un 409 o un token_invalid bloccano la partita, mai in silenzio", () => {
  const dopo409 = decisioneInvio({ ok: false, status: 409, data: { error: "round_already_answered" } }, { scelta: "region_a" });
  assert.deepEqual(dopo409, { azione: "bloccata", errore: "round_already_answered" });
  const senzaNome = decisioneInvio({ ok: false, status: 409, data: {} }, { scelta: "region_a" });
  assert.equal(senzaNome.azione, "bloccata");
  assert.notEqual(senzaNome.errore, "");
  const token = decisioneInvio({ ok: false, status: 400, data: { error: "token_invalid" } }, { scelta: "timeout", rimastoMs: 0 });
  assert.deepEqual(token, { azione: "bloccata", errore: "token_invalid" });
});

test("decisioneInvio: un errore di rete rimanda lo stesso invio, poi blocca", () => {
  for (const scelta of ["region_a", "timeout"]) {
    for (let tentativi = 0; tentativi < MAX_TENTATIVI_INVIO; tentativi += 1) {
      assert.deepEqual(
        decisioneInvio(RETE, { scelta, tentativi, rimastoMs: 4000 }),
        { azione: "riprova", scelta, attesaMs: ATTESA_RITENTO_MS },
      );
    }
    assert.deepEqual(decisioneInvio(RETE, { scelta, tentativi: MAX_TENTATIVI_INVIO }), { azione: "bloccata", errore: "rete" });
  }
  // Un errore del server e' come la rete.
  assert.equal(decisioneInvio({ ok: false, status: 503, data: {} }, { scelta: "region_b" }).azione, "riprova");
});

test("decisioneInvio: mai tornare alla domanda a tempo scaduto, la risposta e' un timeout", () => {
  const limite = { ok: false, status: 429, data: { error: "rate_limited" } };
  assert.deepEqual(decisioneInvio(limite, { scelta: "region_a", rimastoMs: 2500 }), { azione: "domanda", errore: "rate_limited" });
  assert.deepEqual(
    decisioneInvio(limite, { scelta: "region_a", rimastoMs: 0 }),
    { azione: "riprova", scelta: "timeout", attesaMs: ATTESA_RITENTO_MS },
  );
  // Senza timer il tempo non scade.
  assert.equal(decisioneInvio(limite, { scelta: "region_a" }).azione, "domanda");
  // Un timeout rimandato resta un timeout, e dopo i tentativi blocca (non gira all'infinito).
  const presto = { ok: false, status: 400, data: { error: "timeout_too_early" } };
  assert.equal(decisioneInvio(presto, { scelta: "timeout", tentativi: 0, rimastoMs: 0 }).azione, "riprova");
  assert.equal(decisioneInvio(presto, { scelta: "timeout", tentativi: MAX_TENTATIVI_INVIO, rimastoMs: 0 }).azione, "bloccata");
});

test("decisioneInvio: ogni altro errore del server blocca, con il suo nome", () => {
  assert.deepEqual(
    decisioneInvio({ ok: false, status: 400, data: { error: "puzzle_changed" } }, { scelta: "region_a" }),
    { azione: "bloccata", errore: "puzzle_changed" },
  );
  assert.equal(decisioneInvio({ ok: false, status: 400, data: null }, { scelta: "region_a" }).azione, "bloccata");
});
