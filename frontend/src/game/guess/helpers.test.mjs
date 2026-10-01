import assert from "node:assert/strict";
import test from "node:test";
import { riassuntoRegione, titoloEsito, titoloIndizi, titoloTentativi } from "./helpers.js";

test("il testo condiviso di Indovina la Regione porta i tentativi", () => {
  assert.equal(riassuntoRegione({ won: true, tentativi: 3, totale: 6 }), "3 su 6");
  assert.equal(riassuntoRegione({ won: true, tentativi: 1, totale: 6 }), "1 su 6");
  assert.equal(riassuntoRegione({ won: false, tentativi: 6, totale: 6 }), "X su 6");
});

test("il titolo dell'esito dice 'in N tentativi' e non rivela niente se non e' andata", () => {
  assert.equal(titoloEsito("regione", true, 1), "Indovinata al primo tentativo");
  assert.equal(titoloEsito("regione", true, 4), "Indovinata in 4 tentativi");
  assert.equal(titoloEsito("regione", false, 6), "Regione non indovinata");
  assert.equal(titoloEsito("provincia", true, 2), "Indovinata in 2 tentativi");
  assert.equal(titoloEsito("provincia", false, 6), "Provincia non indovinata");
});

test("i titoli dei riquadri chiusi hanno il conteggio", () => {
  assert.equal(titoloIndizi(6), "Gli indizi, tutti e sei");
  assert.equal(titoloIndizi(5), "Gli indizi, tutti e cinque");
  assert.equal(titoloIndizi(11), "Gli indizi (11)");
  assert.equal(titoloTentativi(3), "I tuoi tentativi (3)");
  assert.equal(titoloTentativi(1), "I tuoi tentativi (1)");
});
