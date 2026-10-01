import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { GIOCHI, playStreak, serieDaGiorni, segnaGiocata, statoOggi } from "./oggi.js";

test("giorni di fila fino a oggi", () => {
  assert.equal(serieDaGiorni(["2026-09-28", "2026-09-29", "2026-09-30"], "2026-09-30"), 3);
});

test("se oggi non ha ancora giocato, la serie di ieri vale ancora", () => {
  assert.equal(serieDaGiorni(["2026-09-28", "2026-09-29"], "2026-09-30"), 2);
});

test("un giorno intero senza sfide spezza la serie", () => {
  assert.equal(serieDaGiorni(["2026-09-27", "2026-09-28"], "2026-09-30"), 0);
});

test("attraversa il cambio di mese", () => {
  assert.equal(serieDaGiorni(["2026-09-30", "2026-10-01"], "2026-10-01"), 2);
});

// Gli STESSI vettori del server: `player_stats.play_streak` li legge da
// tests/integration/test_player_stats.py. Se una delle due definizioni cambia, una
// delle due prove cade.
const vettori = JSON.parse(
  readFileSync(new URL("../../../tests/fixtures/play_streak_cases.json", import.meta.url), "utf8"),
);

test("i vettori condivisi col server ci sono", () => {
  assert.ok(vettori.cases.length >= 10);
});

for (const caso of vettori.cases) {
  test(`playStreak, vettore del server: ${caso.name}`, () => {
    assert.deepEqual(playStreak(caso.dates, caso.today), { current: caso.current, max: caso.max });
  });
}

test("playStreak accetta un Set e non muta l'ingresso", () => {
  const giorni = ["2026-10-09", "2026-10-10"];
  assert.deepEqual(playStreak(new Set(giorni), "2026-10-10"), { current: 2, max: 2 });
  assert.deepEqual(giorni, ["2026-10-09", "2026-10-10"]);
});

test("playStreak ignora date impossibili e un oggi illeggibile", () => {
  assert.deepEqual(playStreak(["2026-02-30", "2026-13-01", "0050-01-01"], "2026-10-10"), { current: 0, max: 0 });
  assert.deepEqual(playStreak(["2026-10-10"], "non-una-data"), { current: 0, max: 0 });
  assert.deepEqual(playStreak(null, "2026-10-10"), { current: 0, max: 0 });
});

test("un riposo perdonato tiene viva la serie locale come quella del server", () => {
  assert.equal(serieDaGiorni(["2026-10-05", "2026-10-06", "2026-10-08", "2026-10-09", "2026-10-10"], "2026-10-10"), 5);
});

test("un risultato a meta ha il tono neutro, non quello sbagliato", () => {
  const deposito = new Map();
  globalThis.window = {
    localStorage: { getItem: (k) => deposito.get(k) ?? null, setItem: (k, v) => deposito.set(k, v) },
  };
  try {
    segnaGiocata("compare", "2026-10-01", { ok: true, tono: "parziale", testo: "6 su 10" });
    assert.equal(statoOggi("compare", "2026-10-01").tono, "parziale");
    segnaGiocata("order", "2026-10-01", { ok: false, testo: "0 su 5" });
    assert.equal(statoOggi("order", "2026-10-01").tono, "sbagliato");
    segnaGiocata("indovina", "2026-10-01", { ok: true, tono: "inventato", testo: "" });
    assert.equal(statoOggi("indovina", "2026-10-01").tono, "giusto");
  } finally {
    delete globalThis.window;
  }
});

test("la mappa e' un gioco del giorno come gli altri e conta nella serie", () => {
  assert.ok(GIOCHI.includes("mappa"));
});

function conDeposito(prova) {
  const deposito = new Map();
  globalThis.window = {
    localStorage: { getItem: (k) => deposito.get(k) ?? null, setItem: (k, v) => deposito.set(k, v) },
  };
  try {
    prova(deposito);
  } finally {
    delete globalThis.window;
  }
}

test("segnaGiocata: la prima partita del giorno resta, un rigioco non la sovrascrive", () => {
  conDeposito(() => {
    assert.equal(segnaGiocata("compare", "2026-10-01", { ok: true, tono: "parziale", testo: "6 su 10" }), true);
    // "Rivedi le stesse coppie" finito con 10 su 10: l'hub tiene il 6 su 10.
    assert.equal(segnaGiocata("compare", "2026-10-01", { ok: true, tono: "giusto", testo: "10 su 10" }), false);
    const stato = statoOggi("compare", "2026-10-01");
    assert.equal(stato.tono, "parziale");
    assert.equal(stato.testo, "6 su 10");
  });
});

test("segnaGiocata: un altro esercizio della mappa non cambia l'esito gia' segnato", () => {
  conDeposito(() => {
    segnaGiocata("mappa", "2026-10-01", { ok: true, tono: "giusto", testo: "17 su 20" });
    segnaGiocata("mappa", "2026-10-01", { ok: true, tono: "sbagliato", testo: "0 su 10, senza mappa" });
    assert.equal(statoOggi("mappa", "2026-10-01").testo, "17 su 20");
  });
});

test("segnaGiocata: giorni e giochi diversi non si toccano, e una data che non e' ISO non scrive", () => {
  conDeposito((deposito) => {
    assert.equal(segnaGiocata("order", "2026-10-01", { ok: true, testo: "a" }), true);
    assert.equal(segnaGiocata("order", "2026-10-02", { ok: true, testo: "b" }), true);
    assert.equal(segnaGiocata("compare", "2026-10-01", { ok: true, testo: "c" }), true);
    assert.equal(segnaGiocata("order", undefined, { ok: true, testo: "d" }), false);
    assert.equal(segnaGiocata("order", "oggi", { ok: true, testo: "d" }), false);
    assert.equal(deposito.size, 3);
  });
});
