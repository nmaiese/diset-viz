import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { playStreak, serieDaGiorni } from "./oggi.js";

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
