import test from "node:test";
import assert from "node:assert/strict";
import {
  AVVISO_RIPRESA,
  DIREZIONI,
  ERRORI,
  OPZIONI,
  applicaRisposta,
  chiavePartita,
  decisioneErroreRisposta,
  esitiPerCondivisione,
  fraseDistanza,
  frasePunti,
  leggiPartita,
  messaggioErrore,
  messaggioRiapertura,
  nuovaPartita,
  opzione,
  parametriRisposta,
  riassunto,
  serializzaPartita,
  territoriFinali,
  territorioMioFra,
  testoDomanda,
  testoEsito,
  testoHub,
  testoIstruzione,
  tonoFine,
  tonoPartita,
} from "./partita.js";

const SESSIONE = {
  puzzle_id: "daily:2026-10-12",
  number: 90,
  date: "2026-10-12",
  next_puzzle_at: "2026-10-12T22:00:00+00:00",
  level: "italia",
  level_label: "Tutta Italia",
  mode: "map",
  total: 10,
  points_max: 20,
  token: "tok0",
  question: { index: 0, name: "Lecce", label: "Dov'è Lecce?" },
};

const RISPOSTA = {
  index: 0,
  esito: "region",
  points: 1,
  score: { points: 1, max: 20, answered: 1 },
  chosen: { key: "brindisi", name: "Brindisi", region: "Puglia", path: "/provincia/brindisi" },
  right: { key: "lecce", name: "Lecce", region: "Puglia", region_key: "puglia", path: "/provincia/lecce" },
  distance_km: 35,
  direction: "SE",
  finished: false,
  next_question: { index: 1, name: "Cuneo", label: "Dov'è Cuneo?" },
  token: "tok1",
};

// Tutto il testo che si legge: mai i caratteri che lo stile vieta.
const VIETATI = /[—–;…]/;

test("testoDomanda usa la frase del server, o la compone dal nome", () => {
  assert.equal(testoDomanda({ name: "Lecce", label: "Dov'è Lecce?" }), "Dov'è Lecce?");
  assert.equal(testoDomanda({ name: "Lecce" }), "Dov'è Lecce?");
  assert.equal(testoDomanda(null), "");
});

test("fraseDistanza dichiara la stima", () => {
  assert.equal(fraseDistanza(120, "NE"), "a circa 120 km a nord-est, stima");
  assert.equal(fraseDistanza(35, "S"), "a circa 35 km a sud, stima");
  assert.equal(fraseDistanza(35, null), "a circa 35 km, stima");
  assert.equal(fraseDistanza(null, null), "");
  assert.equal(fraseDistanza(0, null), "");
  for (const dir of Object.keys(DIREZIONI)) assert.match(fraseDistanza(10, dir), /stima$/);
});

test("frasePunti", () => {
  assert.equal(frasePunti(0), "0 punti");
  assert.equal(frasePunti(1), "1 punto");
  assert.equal(frasePunti(2), "2 punti");
});

test("testoEsito: esatta, stessa regione, sbagliata", () => {
  const esatta = testoEsito({ ...RISPOSTA, esito: "exact", points: 2, chosen: RISPOSTA.right, distance_km: null, direction: null }, "map");
  assert.equal(esatta.segno, "esatto");
  assert.equal(esatta.verdetto, "Esatto, 2 punti.");
  assert.equal(esatta.dettaglio, "Lecce, in Puglia.");

  const vicina = testoEsito(RISPOSTA, "map");
  assert.equal(vicina.segno, "vicino");
  assert.equal(vicina.verdetto, "Stessa regione, 1 punto.");
  assert.equal(vicina.dettaglio, "Hai scelto Brindisi. La risposta era Lecce, in Puglia. Dalla tua scelta è a circa 35 km a sud-est, stima.");

  const sbagliata = testoEsito({ ...RISPOSTA, esito: "miss", points: 0, chosen: { ...RISPOSTA.chosen, name: "Matera", region: "Basilicata" }, distance_km: 120, direction: "NE" }, "map");
  assert.equal(sbagliata.segno, "errore");
  assert.equal(sbagliata.verdetto, "Sbagliata, 0 punti.");
  assert.match(sbagliata.dettaglio, /Dalla tua scelta è a circa 120 km a nord-est, stima\.$/);
});

test("testoEsito senza mappa: la regione, mai la distanza", () => {
  const giusta = testoEsito({ ...RISPOSTA, esito: "exact", points: 1, chosen: { key: "puglia", name: "Puglia", region: "Puglia", path: "/regione/puglia" }, distance_km: null, direction: null }, "list");
  assert.equal(giusta.verdetto, "Regione giusta, 1 punto.");
  const sbagliata = testoEsito({ ...RISPOSTA, esito: "miss", points: 0, chosen: { key: "basilicata", name: "Basilicata", region: "Basilicata", path: "/regione/basilicata" }, distance_km: null, direction: null }, "list");
  assert.equal(sbagliata.segno, "errore");
  assert.equal(sbagliata.dettaglio, "Hai scelto Basilicata. La risposta era Lecce, in Puglia.");
  assert.doesNotMatch(sbagliata.dettaglio, /km/);
});

test("nessun testo contiene un carattere vietato", () => {
  const esiti = [
    testoEsito(RISPOSTA, "map"),
    testoEsito({ ...RISPOSTA, esito: "miss", points: 0 }, "map"),
    testoEsito({ ...RISPOSTA, esito: "exact", points: 2, distance_km: null, direction: null }, "map"),
    testoEsito({ ...RISPOSTA, esito: "exact", points: 1, distance_km: null, direction: null }, "list"),
    testoEsito({ ...RISPOSTA, esito: "miss", points: 0, distance_km: null, direction: null }, "list"),
  ];
  const testi = [
    ...esiti.flatMap((e) => [e.verdetto, e.dettaglio]),
    ...Object.values(ERRORI),
    ...Object.values(DIREZIONI),
    ...OPZIONI.flatMap((o) => [o.titolo, o.aiuto]),
    messaggioErrore("sconosciuto"),
    riassunto(["exact", "region", "miss"], "map"),
    riassunto(["exact"], "list"),
    testoHub(14, 20, "map"),
    testoHub(6, 10, "list"),
  ];
  for (const testo of testi) assert.doesNotMatch(testo, VIETATI, testo);
});

test("tonoPartita: giusto da 80%, sbagliato solo a zero, parziale in mezzo", () => {
  assert.equal(tonoPartita(16, 20), "giusto");
  assert.equal(tonoPartita(20, 20), "giusto");
  assert.equal(tonoPartita(15, 20), "parziale");
  assert.equal(tonoPartita(1, 20), "parziale");
  assert.equal(tonoPartita(0, 20), "sbagliato");
  assert.equal(tonoPartita(8, 10), "giusto");
  assert.equal(tonoPartita(7, 10), "parziale");
  assert.equal(tonoPartita(5, 0), "sbagliato");
});

test("tonoFine traduce nei toni di FinePartita", () => {
  assert.equal(tonoFine("giusto"), "pieno");
  assert.equal(tonoFine("parziale"), "parziale");
  assert.equal(tonoFine("sbagliato"), "nullo");
  assert.equal(tonoFine("boh"), "nullo");
});

test("esitiPerCondivisione: senza mappa la regione giusta e' una regione giusta, non una esatta", () => {
  assert.deepEqual(esitiPerCondivisione(["exact", "region", "miss"], "map"), ["exact", "region", "miss"]);
  assert.deepEqual(esitiPerCondivisione(["exact", "miss"], "list"), ["region", "miss"]);
  assert.deepEqual(esitiPerCondivisione(["strano"], "map"), ["miss"]);
  assert.deepEqual(esitiPerCondivisione(null, "map"), []);
});

test("riassunto e testoHub", () => {
  assert.equal(riassunto(["exact", "exact", "region", "miss"], "map"), "2 province esatte, 1 nella regione giusta");
  assert.equal(riassunto(["exact", "miss"], "map"), "1 provincia esatta, 0 nella regione giusta");
  assert.equal(riassunto(["exact", "exact", "miss"], "list"), "2 regioni giuste");
  assert.equal(riassunto(["exact"], "list"), "1 regione giusta");
  assert.equal(testoHub(14, 20, "map"), "14 su 20");
  assert.equal(testoHub(6, 10, "list"), "6 su 10, senza mappa");
});

test("chiavePartita e opzione", () => {
  assert.equal(chiavePartita("italia", "map", "2026-10-12"), "di-mappa-partita:italia:map:2026-10-12");
  assert.equal(opzione("italia", "list").id, "italia-list");
  assert.equal(opzione("boh", "boh").id, "italia-map");
});

test("messaggioErrore: nessun errore noto e' muto, gli sconosciuti hanno una frase", () => {
  for (const codice of Object.keys(ERRORI)) assert.notEqual(messaggioErrore(codice), "", codice);
  assert.equal(messaggioErrore("round_already_answered"), AVVISO_RIPRESA);
  assert.match(messaggioErrore("puzzle_changed"), /Riaprila/);
  assert.match(messaggioErrore("session_expired"), /interrotta/);
  assert.doesNotMatch(messaggioErrore("session_expired"), /scadut/);
  assert.match(messaggioErrore(undefined), /Riprova/);
  // Senza un nome decide lo stato: rete e 503 dicono che il server non risponde, il 429 il limite.
  assert.match(messaggioErrore(undefined, 503), /non risponde/);
  assert.equal(messaggioErrore(undefined, 0), messaggioErrore(undefined, 503));
  assert.match(messaggioErrore(undefined, 429), /Troppe richieste/);
});

test("decisioneErroreRisposta: 409 e token superato riprendono da soli, una volta", () => {
  assert.equal(decisioneErroreRisposta({ status: 409, error: "round_already_answered" }), "riprendi");
  assert.equal(decisioneErroreRisposta({ status: 409 }), "riprendi");
  assert.equal(decisioneErroreRisposta({ status: 400, error: "token_superato" }), "riprendi");
  // Gia' ripresa e senza una risposta buona: niente ciclo, il bottone.
  assert.equal(decisioneErroreRisposta({ status: 409, error: "round_already_answered" }, { giaRiaperta: true }), "riapri");
  assert.equal(decisioneErroreRisposta({ status: 400, error: "token_superato" }, { giaRiaperta: true }), "riapri");
});

test("decisioneErroreRisposta: token scaduto e sfida cambiata col bottone, il resto riprova", () => {
  for (const error of ["token_invalid", "puzzle_changed", "session_expired"]) {
    assert.equal(decisioneErroreRisposta({ status: 400, error }), "riapri", error);
  }
  for (const input of [{ status: 0, error: undefined }, { status: 429, error: "rate_limited" }, { status: 500 }, undefined]) {
    assert.equal(decisioneErroreRisposta(input), "messaggio");
  }
});

test("messaggioRiapertura: dice sempre qualcosa, e la partita non e' mai scaduta", () => {
  assert.match(messaggioRiapertura("token_invalid", { status: 400 }), /interrotta/);
  assert.match(messaggioRiapertura("round_already_answered", { status: 409 }), /interrotta/);
  assert.match(messaggioRiapertura("puzzle_changed", { status: 400 }), /cambiata/);
});

test("applicaRisposta non muta e tiene solo il necessario", () => {
  const prima = nuovaPartita(SESSIONE);
  const copia = JSON.stringify(prima);
  const dopo = applicaRisposta(prima, RISPOSTA);
  assert.equal(JSON.stringify(prima), copia);
  assert.equal(dopo.token, "tok1");
  assert.equal(dopo.punti, 1);
  assert.deepEqual(dopo.question, RISPOSTA.next_question);
  assert.equal(dopo.risposte.length, 1);
  assert.deepEqual(Object.keys(dopo.risposte[0]).sort(), ["chosen", "esito", "index", "points", "right"]);
  assert.equal(dopo.fine, null);
  const ultima = applicaRisposta(dopo, { ...RISPOSTA, index: 1, next_question: null, finished: true, score: { points: 3, max: 20, answered: 2 }, summary: { esiti: ["region", "exact"], score: { points: 3, max: 20 } } });
  assert.equal(ultima.question, null);
  assert.equal(ultima.punti, 3);
  assert.ok(ultima.fine);
});

test("leggiPartita ridà la partita giusta e scarta le altre", () => {
  const partita = applicaRisposta(nuovaPartita(SESSIONE), RISPOSTA);
  const grezzo = serializzaPartita(partita);
  const attesi = { livello: "italia", modalita: "map", iso: "2026-10-12" };
  assert.deepEqual(leggiPartita(grezzo, attesi), partita);
  // un altro giorno, un altro livello, un'altra modalita'
  assert.equal(leggiPartita(grezzo, { ...attesi, iso: "2026-10-13" }), null);
  assert.equal(leggiPartita(grezzo, { ...attesi, livello: "regione" }), null);
  assert.equal(leggiPartita(grezzo, { ...attesi, modalita: "list" }), null);
  // json rotto, forme che non tornano
  assert.equal(leggiPartita("{", attesi), null);
  assert.equal(leggiPartita(null, attesi), null);
  assert.equal(leggiPartita(JSON.stringify({ ...partita, token: "" }), attesi), null);
  assert.equal(leggiPartita(JSON.stringify({ ...partita, punti: 99 }), attesi), null);
  assert.equal(leggiPartita(JSON.stringify({ ...partita, question: { index: 5 } }), attesi), null);
  assert.equal(leggiPartita(JSON.stringify({ ...partita, risposte: new Array(11).fill({}) }), attesi), null);
});

test("leggiPartita: una partita finita deve avere tutte le risposte", () => {
  let p = nuovaPartita(SESSIONE);
  for (let i = 0; i < 10; i += 1) {
    const ultima = i === 9;
    p = applicaRisposta(p, {
      ...RISPOSTA,
      index: i,
      score: { points: i + 1, max: 20, answered: i + 1 },
      next_question: ultima ? null : { index: i + 1, name: "X", label: "Dov'è X?" },
      summary: ultima ? { esiti: new Array(10).fill("region"), score: { points: 10, max: 20 } } : undefined,
    });
  }
  const attesi = { livello: "italia", modalita: "map", iso: "2026-10-12" };
  assert.ok(leggiPartita(serializzaPartita(p), attesi));
  assert.equal(leggiPartita(serializzaPartita({ ...p, risposte: p.risposte.slice(0, 5) }), attesi), null);
});

test("territoriFinali: un link per provincia, nell'ordine, senza doppioni", () => {
  const risposte = [
    { right: { name: "Lecce", path: "/provincia/lecce" } },
    { right: { name: "Cuneo", path: "/provincia/cuneo" } },
    { right: { name: "Lecce", path: "/provincia/lecce" } },
    null,
  ];
  assert.deepEqual(territoriFinali(risposte), [
    { name: "Lecce", path: "/provincia/lecce" },
    { name: "Cuneo", path: "/provincia/cuneo" },
  ]);
  assert.deepEqual(territoriFinali(undefined), []);
});

test("territorioMioFra: una delle province della partita o la sua regione", () => {
  const risposte = [
    { right: { key: "lecce", name: "Lecce", region: "Puglia", region_key: "puglia" } },
    { right: { key: "cuneo", name: "Cuneo", region: "Piemonte", region_key: "piemonte" } },
  ];
  assert.equal(territorioMioFra({ level: "provincia", key: "cuneo", name: "Cuneo" }, risposte), "Cuneo");
  assert.equal(territorioMioFra({ level: "regione", key: "puglia", name: "Puglia" }, risposte), "Puglia");
  assert.equal(territorioMioFra({ level: "provincia", key: "bari", name: "Bari", region: "puglia", regionName: "Puglia" }, risposte), "Puglia");
  assert.equal(territorioMioFra({ level: "provincia", key: "roma", name: "Roma" }, risposte), null);
  assert.equal(territorioMioFra(null, risposte), null);
});

test("parametriRisposta porta etichette e conti, mai un nome", () => {
  const partita = nuovaPartita(SESSIONE);
  const p = parametriRisposta(partita, RISPOSTA, { reselects: 2 });
  assert.deepEqual(p, { game: "mappa", mode: "daily", level: "italia", answer_mode: "map", index: 0, esito: "region", reselects: 2 });
  assert.ok(!JSON.stringify(p).includes("Lecce"));
});

test("testoIstruzione segue la vista e la selezione", () => {
  assert.equal(testoIstruzione({ modalita: "map", vista: "italia", selezionata: null }), "Tocca la regione dove pensi che sia.");
  assert.equal(testoIstruzione({ modalita: "map", vista: "puglia", selezionata: null }), "Tocca la provincia.");
  assert.equal(testoIstruzione({ modalita: "map", vista: "puglia", selezionata: "lecce" }), "Provincia scelta. Conferma, oppure tocca un'altra.");
  assert.equal(testoIstruzione({ modalita: "list", vista: "italia", selezionata: null }), "Scegli la regione e conferma.");
  for (const stato of [{ vista: "italia" }, { vista: "x" }, { vista: "x", selezionata: "y" }, { modalita: "list" }]) {
    assert.doesNotMatch(testoIstruzione({ modalita: "map", ...stato }), VIETATI);
  }
});
