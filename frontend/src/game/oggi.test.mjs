import test from "node:test";
import assert from "node:assert/strict";
import { serieDaGiorni } from "./oggi.js";

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
