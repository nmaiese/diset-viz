import assert from "node:assert/strict";
import test from "node:test";
import {
  analizza,
  distribuzioneValida,
  extraProvincia,
  interoNonNegativo,
  progressoValido,
  statsCompare,
  statsOrder,
  statsProvincia,
  statsRegione,
} from "./salvati.js";
import { loadProgress, loadStats } from "./guess/storage.js";
import { caricaProgresso, caricaStatistiche } from "./guess/provincia.js";

// Un localStorage finto, con quello che vogliamo trovarci.
function conDeposito(contenuto, prova) {
  const deposito = new Map(Object.entries(contenuto));
  globalThis.window = {
    localStorage: { getItem: (k) => deposito.get(k) ?? null, setItem: (k, v) => deposito.set(k, v) },
  };
  try {
    return prova();
  } finally {
    delete globalThis.window;
  }
}

test("interoNonNegativo: solo interi da zero in su", () => {
  for (const ok of [0, 1, 99]) assert.equal(interoNonNegativo(ok), true);
  for (const no of [-1, 1.5, NaN, Infinity, "3", null, undefined, {}, [], true]) assert.equal(interoNonNegativo(no), false);
});

test("le statistiche di Chi e' maggiore e Ordina ripiegano campo per campo sul valore di partenza", () => {
  assert.deepEqual(statsCompare({ bestStreak: 7, totalRounds: "ciao", totalCorrect: -3, extra: 1 }), {
    bestStreak: 7,
    totalRounds: 0,
    totalCorrect: 0,
  });
  assert.deepEqual(statsOrder({ bestScore3: 3, bestScore5: 4.5, totalRounds: NaN, totalPositionsCorrect: 12 }), {
    bestScore3: 3,
    bestScore5: 0,
    totalRounds: 0,
    totalPositionsCorrect: 12,
  });
  for (const rotto of [null, undefined, "x", 3, [], [1, 2]]) {
    assert.deepEqual(statsCompare(rotto), { bestStreak: 0, totalRounds: 0, totalCorrect: 0 });
  }
});

test("le statistiche non condividono l'oggetto di partenza", () => {
  const a = statsCompare(null);
  a.bestStreak = 9;
  assert.equal(statsCompare(null).bestStreak, 0);
});

test("la distribuzione tiene solo i secchi permessi con un conteggio intero", () => {
  assert.deepEqual(distribuzioneValida({ 1: 2, 3: -1, 4: "x", fail: 5, 9: 4 }, ["1", "2", "3", "4", "fail"]), { 1: 2, fail: 5 });
  assert.deepEqual(distribuzioneValida([1, 2], ["1"]), {});
  assert.deepEqual(distribuzioneValida(null, ["1"]), {});
});

test("le statistiche di Provincia e Regione ripuliscono anche la distribuzione e le date", () => {
  assert.deepEqual(statsProvincia({ played: 4, wins: "due", distribution: { 2: 1, fail: -1 } }), {
    played: 4,
    wins: 0,
    distribution: { 2: 1 },
  });
  const regione = statsRegione({
    played: 10,
    wins: 6,
    streak: 2,
    maxStreak: 1.5,
    lastWonPuzzleId: "daily:2026-09-30",
    lastWonDate: "ieri",
    distribution: { 3: 2, 7: 1 },
  });
  assert.deepEqual(regione, {
    played: 10,
    wins: 6,
    streak: 2,
    maxStreak: 0,
    lastWonPuzzleId: "daily:2026-09-30",
    distribution: { 3: 2 },
  });
  assert.equal(statsRegione({ lastWonDate: "2026-09-30" }).lastWonDate, "2026-09-30");
  assert.equal(statsRegione({ lastWonPuzzleId: 12 }).lastWonPuzzleId, null);
});

const PROGRESSO = {
  status: "playing",
  clues: [{ id: 1 }],
  guesses: [{ province_key: "x" }],
  solution: null,
  recap: null,
  fatto: null,
  statsRecorded: false,
};

test("progressoValido: la forma giusta passa, qualunque altra e' scartata", () => {
  assert.equal(progressoValido(PROGRESSO), PROGRESSO);
  const finita = { ...PROGRESSO, status: "won", solution: { province: "Lecce" }, recap: [], fatto: "un fatto" };
  assert.equal(progressoValido(finita), finita);
  const rotti = [
    null,
    "x",
    [],
    { ...PROGRESSO, status: "boh" },
    { ...PROGRESSO, clues: {} },
    { ...PROGRESSO, clues: [1] },
    { ...PROGRESSO, guesses: "no" },
    { ...PROGRESSO, guesses: [null] },
    { ...PROGRESSO, solution: "Lecce" },
    { ...PROGRESSO, recap: {} },
    { ...PROGRESSO, fatto: 3 },
    { ...PROGRESSO, status: "lost", solution: null },
  ];
  for (const r of rotti) assert.equal(progressoValido(r), null, JSON.stringify(r));
});

test("progressoValido: il controllo in piu' della Provincia vuole token e livello", () => {
  const extra = extraProvincia(["stessa_regione", "province"]);
  const buono = { ...PROGRESSO, token: "t", level: "province" };
  assert.equal(progressoValido(buono, { extra }), buono);
  assert.equal(progressoValido({ ...buono, token: "" }, { extra }), null);
  assert.equal(progressoValido({ ...buono, level: "mondo" }, { extra }), null);
  assert.equal(progressoValido(PROGRESSO, { extra }), null);
});

test("analizza: un JSON rotto o assente e' undefined, mai un'eccezione", () => {
  assert.equal(analizza("{rotto"), undefined);
  assert.equal(analizza(""), undefined);
  assert.equal(analizza(null), undefined);
  assert.deepEqual(analizza('{"a":1}'), { a: 1 });
});

test("Indovina la Regione: loadStats e loadProgress ripiegano sul default", () => {
  conDeposito({ "di-game-stats": '{"played":"molte","wins":3,"streak":-2,"distribution":[1]}' }, () => {
    const s = loadStats();
    assert.equal(s.played, 0);
    assert.equal(s.wins, 3);
    assert.equal(s.streak, 0);
    assert.deepEqual(s.distribution, {});
  });
  conDeposito({ "di-game-stats": "{rotto" }, () => assert.equal(loadStats().played, 0));
  conDeposito({}, () => assert.equal(loadStats().played, 0));
  conDeposito({ "di-game-progress:daily:2026-10-01": '{"status":"playing","clues":"no","guesses":[]}' }, () => {
    assert.equal(loadProgress("daily:2026-10-01"), null);
  });
  conDeposito({ "di-game-progress:daily:2026-10-01": JSON.stringify(PROGRESSO) }, () => {
    assert.deepEqual(loadProgress("daily:2026-10-01"), PROGRESSO);
  });
});

test("Indovina la Provincia: caricaStatistiche e caricaProgresso ripiegano sul default", () => {
  conDeposito({ "di-provincia-stats": '{"played":2,"wins":1.5,"distribution":{"2":1,"x":5}}' }, () => {
    assert.deepEqual(caricaStatistiche(), { played: 2, wins: 0, distribution: { 2: 1 } });
  });
  conDeposito({}, () => assert.deepEqual(caricaStatistiche(), { played: 0, wins: 0, distribution: {} }));
  conDeposito({ "di-provincia-progress:daily:2026-10-01": JSON.stringify({ ...PROGRESSO, token: "t", level: "boh" }) }, () => {
    assert.equal(caricaProgresso("daily:2026-10-01"), null);
  });
  const buono = { ...PROGRESSO, token: "t", level: "province" };
  conDeposito({ "di-provincia-progress:daily:2026-10-01": JSON.stringify(buono) }, () => {
    assert.deepEqual(caricaProgresso("daily:2026-10-01"), buono);
  });
});
