import test from "node:test";
import assert from "node:assert/strict";
import {
  MASSIMI_SFIDA,
  countUpValue,
  fattoPresentabile,
  fraseTerritorioMio,
  giorniDiFila,
  leggiSfida,
  linkConSfida,
  parametriEvento,
  parseTerritorioMio,
  testoConfrontoSfida,
  testoSfida,
  titoloContabile,
  tonoFinale,
  trovaTerritorioMio,
} from "./puri.js";

// -- countUpValue -----------------------------------------------------------------

test("countUpValue parte da 0 e arriva esattamente al valore in 450 ms", () => {
  assert.equal(countUpValue(7, 0), 0);
  assert.equal(countUpValue(7, 450), 7);
  assert.equal(countUpValue(7, 10_000), 7);
});

test("countUpValue sale senza mai scendere e senza superare il valore (ease-out)", () => {
  let prima = 0;
  for (let ms = 0; ms <= 450; ms += 15) {
    const v = countUpValue(10, ms);
    assert.ok(v >= prima, `scende a ${ms} ms`);
    assert.ok(v <= 10);
    prima = v;
  }
  // ease-out: a meta' del tempo si e' gia' oltre meta' del percorso.
  assert.ok(countUpValue(10, 225) > 5);
});

test("countUpValue con tempo negativo o mancante sta a 0, e con valore non numerico non inventa", () => {
  assert.equal(countUpValue(7, -20), 0);
  assert.equal(countUpValue(7, Number.NaN), 0);
  assert.ok(Number.isNaN(countUpValue(Number.NaN, 100)));
  assert.equal(countUpValue(undefined, 100), undefined);
});

test("countUpValue con durata zero mostra subito il finale", () => {
  assert.equal(countUpValue(7, 0, 0), 7);
});

test("titoloContabile trova il numero di 'N su M' e lascia il resto", () => {
  assert.deepEqual(titoloContabile("7 su 10"), { prima: "", valore: 7, dopo: " su 10" });
  assert.deepEqual(titoloContabile("Perfetto! 5 su 5 posizioni corrette."), {
    prima: "Perfetto! ", valore: 5, dopo: " su 5 posizioni corrette.",
  });
  assert.deepEqual(titoloContabile("Hai 12 punti: 7 su 10"), { prima: "Hai 12 punti: ", valore: 7, dopo: " su 10" });
});

test("titoloContabile non conta un titolo senza 'N su M'", () => {
  assert.equal(titoloContabile("Indovinata in 3 tentativi"), null);
  assert.equal(titoloContabile(""), null);
  assert.equal(titoloContabile(undefined), null);
});

// -- tono -------------------------------------------------------------------------

test("tonoFinale: il default viene da won, un tono valido vince", () => {
  assert.equal(tonoFinale(true), "pieno");
  assert.equal(tonoFinale(false), "nullo");
  assert.equal(tonoFinale(false, "parziale"), "parziale");
  assert.equal(tonoFinale(true, "nullo"), "nullo");
  assert.equal(tonoFinale(true, "strano"), "pieno");
});

// -- leggiSfida ---------------------------------------------------------------------

const opzioni = { massimo: 10, numeroOggi: 12 };

test("leggiSfida accetta un frammento valido", () => {
  assert.deepEqual(leggiSfida("#sfida=7-12", opzioni), { punteggio: 7, numero: 12 });
  assert.deepEqual(leggiSfida("#sfida=0-12", opzioni), { punteggio: 0, numero: 12 });
  assert.deepEqual(leggiSfida("#sfida=10-12", opzioni), { punteggio: 10, numero: 12 });
});

test("leggiSfida confronta il numero anche se il server lo manda come stringa di cifre", () => {
  assert.deepEqual(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: "12" }), { punteggio: 7, numero: 12 });
  assert.equal(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: "012" }), null);
  assert.equal(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: "dodici" }), null);
});

test("leggiSfida scarta un punteggio fuori scala", () => {
  assert.equal(leggiSfida("#sfida=11-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=999-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=-1-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=6-12", { massimo: 5, numeroOggi: 12 }), null);
});

test("leggiSfida scarta un numero diverso da quello di oggi", () => {
  assert.equal(leggiSfida("#sfida=7-11", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-13", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: undefined }), null);
  assert.equal(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: null }), null);
  assert.equal(leggiSfida("#sfida=7-12", { massimo: 10, numeroOggi: 12.5 }), null);
});

test("leggiSfida scarta un frammento doppio o con altro attorno", () => {
  assert.equal(leggiSfida("#sfida=7-12&sfida=8-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12#sfida=8-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12&x=1", opzioni), null);
  assert.equal(leggiSfida("#x=1&sfida=7-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12 ", opzioni), null);
  assert.equal(leggiSfida(" #sfida=7-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12\n", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12-3", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-12,8-12", opzioni), null);
});

test("leggiSfida scarta i caratteri che non sono cifre ASCII", () => {
  assert.equal(leggiSfida("#sfida=7a-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7.5-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=+7-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=0x7-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7e0-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=٧-12", opzioni), null); // cifra araba
  assert.equal(leggiSfida("#sfida=７-12", opzioni), null); // cifra a larghezza piena
  assert.equal(leggiSfida("#sfida=7-１２", opzioni), null);
  assert.equal(leggiSfida("#sfida=<b>-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-", opzioni), null);
  assert.equal(leggiSfida("#sfida=", opzioni), null);
});

test("leggiSfida scarta gli zeri davanti e i numeri lunghi", () => {
  assert.equal(leggiSfida("#sfida=07-12", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-012", opzioni), null);
  assert.equal(leggiSfida("#sfida=7-1234567", opzioni), null);
  assert.equal(leggiSfida("#sfida=1000-12", opzioni), null);
});

test("leggiSfida vuole il frammento con il suo nome, e non una query", () => {
  assert.equal(leggiSfida("?sfida=7-12", opzioni), null);
  assert.equal(leggiSfida("sfida=7-12", opzioni), null);
  assert.equal(leggiSfida("#Sfida=7-12", opzioni), null);
  assert.equal(leggiSfida("#a=7&n=12", opzioni), null);
  assert.equal(leggiSfida("", opzioni), null);
  assert.equal(leggiSfida(undefined, opzioni), null);
  assert.equal(leggiSfida(null, opzioni), null);
  assert.equal(leggiSfida(72, opzioni), null);
});

test("leggiSfida senza un massimo del gioco non da' mai una sfida", () => {
  assert.equal(leggiSfida("#sfida=7-12", { numeroOggi: 12 }), null);
  assert.equal(leggiSfida("#sfida=0-12", { massimo: 0, numeroOggi: 12 }), null);
  assert.equal(leggiSfida("#sfida=7-12", { massimo: null, numeroOggi: 12 }), null);
  assert.equal(leggiSfida("#sfida=7-12"), null);
});

test("i massimi per gioco sono quelli delle sfide del giorno", () => {
  assert.equal(MASSIMI_SFIDA.compare, 10);
  assert.equal(MASSIMI_SFIDA.order, 5);
  assert.equal(MASSIMI_SFIDA.mappa, 20);
  assert.deepEqual(leggiSfida("#sfida=14-12", { massimo: MASSIMI_SFIDA.mappa, numeroOggi: 12 }), { punteggio: 14, numero: 12 });
  assert.equal(leggiSfida("#sfida=21-12", { massimo: MASSIMI_SFIDA.mappa, numeroOggi: 12 }), null);
});

test("linkConSfida mette il frammento, non una query, e toglie quello di prima", () => {
  assert.equal(linkConSfida("https://divarioitalia.it/quiz/chi-e-maggiore", 8, 12), "https://divarioitalia.it/quiz/chi-e-maggiore#sfida=8-12");
  assert.equal(linkConSfida("https://divarioitalia.it/quiz/ordina#sfida=7-12", 5, 12), "https://divarioitalia.it/quiz/ordina#sfida=5-12");
  assert.ok(!linkConSfida("https://divarioitalia.it/quiz/ordina", 5, 12).includes("?"));
  assert.ok(!/nome|nick|user/i.test(linkConSfida("https://divarioitalia.it/quiz/ordina", 5, 12)));
});

test("linkConSfida con punteggio o numero che non sono cifre sensate da' il link pulito", () => {
  const base = "https://divarioitalia.it/quiz/ordina";
  assert.equal(linkConSfida(`${base}#sfida=7-12`, -1, 12), base);
  assert.equal(linkConSfida(base, 1.5, 12), base);
  assert.equal(linkConSfida(base, 5, 0), base);
  assert.equal(linkConSfida(base, 5, undefined), base);
  assert.equal(linkConSfida(base, "5", 12), base);
  assert.equal(linkConSfida(base, Number.NaN, 12), base);
});

test("un link condiviso si legge di nuovo con leggiSfida", () => {
  const link = linkConSfida("https://divarioitalia.it/quiz/chi-e-maggiore", 8, 12);
  const hash = link.slice(link.indexOf("#"));
  assert.deepEqual(leggiSfida(hash, opzioni), { punteggio: 8, numero: 12 });
});

test("il testo della sfida non attribuisce il punteggio a nessuno", () => {
  assert.equal(testoSfida(7, 10), "La sfida condivisa: 7 su 10. Riesci a superarla?");
  assert.ok(!/amic|ha fatto|giocatore|utente/i.test(testoSfida(7, 10)));
  assert.equal(testoConfrontoSfida(8, 7), "Tu 8, la sfida condivisa 7");
});

test("i testi visibili non usano i caratteri vietati dallo stile", () => {
  for (const t of [testoSfida(7, 10), testoConfrontoSfida(8, 7), fraseTerritorioMio("Puglia")]) {
    for (const vietato of ["—", "–", ";", "…"]) assert.ok(!t.includes(vietato), `${t} contiene ${vietato}`);
  }
});

// -- territorioMio ------------------------------------------------------------------

const regione = { level: "regione", key: "puglia", name: "Puglia" };
const provincia = { level: "provincia", key: "lecce", name: "Lecce", region: "puglia", regionName: "Puglia" };

test("parseTerritorioMio legge il formato di v1.js", () => {
  assert.deepEqual(parseTerritorioMio(JSON.stringify(regione)), regione);
  assert.deepEqual(parseTerritorioMio(JSON.stringify(provincia)), provincia);
  assert.deepEqual(parseTerritorioMio(JSON.stringify({ level: "regione", key: "valle-d-aosta", name: "Valle d'Aosta" })),
    { level: "regione", key: "valle-d-aosta", name: "Valle d'Aosta" });
});

test("parseTerritorioMio: JSON corrotto o non oggetto e' null", () => {
  for (const grezzo of ["", "{", "{\"level\":", "null", "true", "42", "\"regione\"", "[]", "[1,2]", "undefined", "{level:'regione'}"]) {
    assert.equal(parseTerritorioMio(grezzo), null, grezzo);
  }
  assert.equal(parseTerritorioMio(null), null);
  assert.equal(parseTerritorioMio(undefined), null);
  assert.equal(parseTerritorioMio({ level: "regione", key: "puglia", name: "Puglia" }), null);
  assert.equal(parseTerritorioMio("x".repeat(5000)), null);
});

test("parseTerritorioMio: un livello sconosciuto e' null", () => {
  for (const level of ["comune", "Regione", "REGIONE", "", null, 1, [], {}, undefined]) {
    assert.equal(parseTerritorioMio(JSON.stringify({ ...regione, level })), null, String(level));
  }
});

test("parseTerritorioMio: una chiave con caratteri strani e' null", () => {
  const strane = [
    "Puglia", "pu glia", "puglia/", "../puglia", "puglia?x=1", "puglia#x", "puglia%20", "<script>", "puglia\n",
    "puglia'", 'puglia"', "puglia;", "-puglia", "puglia-", "pu--glia", "pugliàa", "", "a".repeat(61), 12, null, ["puglia"], { a: 1 },
  ];
  for (const key of strane) {
    assert.equal(parseTerritorioMio(JSON.stringify({ ...regione, key })), null, JSON.stringify(key));
  }
  assert.equal(parseTerritorioMio(JSON.stringify({ level: "regione", name: "Puglia" })), null);
});

test("parseTerritorioMio: un nome con markup, controllo o fuori misura e' null", () => {
  const nomi = ["<b>Puglia</b>", "Pu<glia", "Puglia>", "P&amp;uglia", 'Pu"glia', "Pu`glia", "Pu\\glia", "Pu\nglia", "Pu\u0000glia",
    " Puglia", "Puglia ", "", "a".repeat(81), 7, null, ["Puglia"]];
  for (const name of nomi) {
    assert.equal(parseTerritorioMio(JSON.stringify({ ...regione, name })), null, JSON.stringify(name));
  }
  assert.equal(parseTerritorioMio(JSON.stringify({ level: "regione", key: "puglia" })), null);
});

test("parseTerritorioMio: per la provincia la regione, se c'e', deve essere valida", () => {
  assert.equal(parseTerritorioMio(JSON.stringify({ ...provincia, region: "Puglia!" })), null);
  assert.equal(parseTerritorioMio(JSON.stringify({ ...provincia, regionName: "<i>Puglia</i>" })), null);
  assert.equal(parseTerritorioMio(JSON.stringify({ ...provincia, regionName: undefined })), null);
  assert.deepEqual(parseTerritorioMio(JSON.stringify({ level: "provincia", key: "lecce", name: "Lecce" })),
    { level: "provincia", key: "lecce", name: "Lecce" });
});

test("parseTerritorioMio butta i campi che il formato non ha", () => {
  const mio = parseTerritorioMio(JSON.stringify({ ...regione, html: "<img onerror=x>", __proto__: { admin: true }, region: "x" }));
  assert.deepEqual(mio, regione);
  assert.ok(!("html" in mio) && !("admin" in mio) && !("region" in mio));
});

test("trovaTerritorioMio evidenzia il territorio del giocatore fra quelli della partita", () => {
  const regioni = [{ key: "lombardia" }, { key: "puglia" }, { key: "molise" }];
  assert.deepEqual(trovaTerritorioMio(regione, regioni), { key: "puglia" });
  assert.equal(trovaTerritorioMio({ ...regione, key: "toscana" }, regioni), null);
});

test("trovaTerritorioMio: una provincia scelta accende la sua regione, non il contrario", () => {
  const regioni = [{ key: "lombardia" }, { key: "puglia" }];
  assert.deepEqual(trovaTerritorioMio(provincia, regioni), { key: "puglia" });
  const province = [{ key: "lecce" }, { key: "bari" }];
  assert.deepEqual(trovaTerritorioMio(provincia, province), { key: "lecce" });
  assert.equal(trovaTerritorioMio(regione, province), null);
});

test("trovaTerritorioMio rispetta il livello quando il territorio lo dichiara", () => {
  assert.equal(trovaTerritorioMio(regione, [{ key: "puglia", level: "provincia" }]), null);
  assert.deepEqual(trovaTerritorioMio(regione, [{ key: "puglia", level: "regione" }]), { key: "puglia", level: "regione" });
});

test("trovaTerritorioMio senza scelta o con elenco guasto e' null", () => {
  assert.equal(trovaTerritorioMio(null, [{ key: "puglia" }]), null);
  assert.equal(trovaTerritorioMio(regione, null), null);
  assert.equal(trovaTerritorioMio(regione, [null, 3, "puglia", { nokey: 1 }]), null);
});

test("la frase del territorio", () => {
  assert.equal(fraseTerritorioMio("Puglia"), "C'era anche il tuo territorio: Puglia.");
});

// -- eventi -------------------------------------------------------------------------

test("parametriEvento tiene un game valido e lo segnala mancante o inventato", () => {
  for (const game of ["regione", "provincia", "compare", "order", "mappa"]) {
    assert.deepEqual(parametriEvento({ game, level: "x" }), { valido: true, params: { level: "x", game } });
  }
  assert.deepEqual(parametriEvento({ level: "x" }), { valido: false, params: { level: "x" } });
  assert.deepEqual(parametriEvento({ game: "tris", level: "x" }), { valido: false, params: { level: "x" } });
  assert.deepEqual(parametriEvento({ game: undefined }), { valido: false, params: {} });
  assert.deepEqual(parametriEvento(undefined), { valido: false, params: {} });
  assert.deepEqual(parametriEvento("compare"), { valido: false, params: {} });
});

// -- serie dell'hub -----------------------------------------------------------------

test("giorniDiFila: con il profilo vale il server, senza il conto locale", () => {
  assert.equal(giorniDiFila({ current: 3, max: 9 }, 1), 3);
  assert.equal(giorniDiFila({ current: 0, max: 9 }, 4), 0);
  assert.equal(giorniDiFila(undefined, 4), 4);
  assert.equal(giorniDiFila(null, 0), 0);
  assert.equal(giorniDiFila({ current: "3" }, 2), 2);
  assert.equal(giorniDiFila({}, undefined), 0);
});

// -- fatto da portarti via ------------------------------------------------------------

test("fattoPresentabile lascia passare una frase sana, tolta dagli spazi", () => {
  assert.equal(fattoPresentabile("  Hai messo Lazio sopra Puglia: Lazio ha 12,4 %, Puglia 15,1 % (2023). "),
    "Hai messo Lazio sopra Puglia: Lazio ha 12,4 %, Puglia 15,1 % (2023).");
});

test("fattoPresentabile non fa uscire una frase con un numero mancante", () => {
  for (const frase of ["Il valore e' n.d. nel 2023.", "Puglia ha n. d. punti", "Valore NaN nel 2023", "Valore undefined", "Valore null", "Infinity volte"]) {
    assert.equal(fattoPresentabile(frase), null, frase);
  }
});

test("fattoPresentabile non fa uscire una frase con i caratteri vietati dallo stile", () => {
  for (const vietato of ["—", "–", ";", "…"]) assert.equal(fattoPresentabile(`Prima ${vietato} dopo`), null, vietato);
});

test("fattoPresentabile scarta tutto cio' che non e' una frase", () => {
  for (const v of [undefined, null, "", "   ", 42, {}, [], "x".repeat(401)]) assert.equal(fattoPresentabile(v), null, String(v));
});
