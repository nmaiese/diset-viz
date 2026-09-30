import assert from "node:assert/strict";
import test from "node:test";
import { aggiornaSerie, dataDaPuzzleId, giorniTra, oggiRoma, serieAttuale } from "./serie.js";

const vuote = { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonDate: null, distribution: {} };

test("giorniTra conta giorni interi, anche a cavallo di mese e di ora legale", () => {
  assert.equal(giorniTra("2026-09-29", "2026-09-30"), 1);
  assert.equal(giorniTra("2026-09-30", "2026-10-01"), 1);
  assert.equal(giorniTra("2026-10-24", "2026-10-26"), 2);
  assert.equal(giorniTra("2026-10-26", "2026-10-24"), -2);
});

test("oggiRoma segue la mezzanotte di Roma, non quella UTC", () => {
  assert.equal(oggiRoma(new Date("2026-09-30T21:30:00Z")), "2026-09-30");
  assert.equal(oggiRoma(new Date("2026-09-30T23:30:00Z")), "2026-10-01");
  assert.equal(oggiRoma(new Date("2026-12-31T23:30:00Z")), "2027-01-01");
});

test("vittorie in giorni consecutivi fanno salire la serie", () => {
  let s = aggiornaSerie(vuote, { won: true, giorno: "2026-09-28" });
  assert.equal(s.streak, 1);
  s = aggiornaSerie(s, { won: true, giorno: "2026-09-29" });
  s = aggiornaSerie(s, { won: true, giorno: "2026-09-30" });
  assert.equal(s.streak, 3);
  assert.equal(s.maxStreak, 3);
  assert.equal(s.lastWonDate, "2026-09-30");
});

test("un salto di giorni azzera la serie alla vittoria successiva e tiene il record", () => {
  let s = { ...vuote, streak: 4, maxStreak: 4, lastWonDate: "2026-09-20" };
  s = aggiornaSerie(s, { won: true, giorno: "2026-09-23" });
  assert.equal(s.streak, 1);
  assert.equal(s.maxStreak, 4);
});

test("la stessa sfida registrata due volte non allunga la serie", () => {
  let s = aggiornaSerie(vuote, { won: true, giorno: "2026-09-30" });
  s = aggiornaSerie(s, { won: true, giorno: "2026-09-30" });
  assert.equal(s.streak, 1);
});

test("una sconfitta non spezza da sola la serie, la spezza il giorno saltato", () => {
  let s = { ...vuote, streak: 3, maxStreak: 3, lastWonDate: "2026-09-29" };
  s = aggiornaSerie(s, { won: false, giorno: "2026-09-30" });
  assert.equal(s.streak, 3);
  assert.equal(serieAttuale(s, "2026-09-30"), 3);
  assert.equal(serieAttuale(s, "2026-10-01"), 0);
});

test("la serie mostrata e' zero se l'ultima vittoria e' di oltre un giorno fa", () => {
  const s = { ...vuote, streak: 5, maxStreak: 5, lastWonDate: "2026-09-27" };
  assert.equal(serieAttuale(s, "2026-09-28"), 5);
  assert.equal(serieAttuale(s, "2026-09-29"), 0);
});

test("le statistiche vecchie, senza data, si leggono da lastWonPuzzleId", () => {
  assert.equal(dataDaPuzzleId("daily:2026-09-29"), "2026-09-29");
  assert.equal(dataDaPuzzleId("practice:abc"), null);
  const vecchie = { played: 6, wins: 5, streak: 2, maxStreak: 3, lastWonPuzzleId: "daily:2026-09-29", distribution: {} };
  assert.equal(serieAttuale(vecchie, "2026-09-30"), 2);
  assert.equal(aggiornaSerie(vecchie, { won: true, giorno: "2026-09-30" }).streak, 3);
  assert.equal(serieAttuale({ ...vecchie, lastWonPuzzleId: null }, "2026-09-30"), 0);
});
