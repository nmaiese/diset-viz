import test from "node:test";
import assert from "node:assert/strict";
import {
  LATO_MINIMO,
  VIEWBOX_ITALIA,
  centro,
  leggiViewBox,
  puntoInVista,
  riquadroRivelazione,
  testoViewBox,
  unitaPerPixel,
  versoDelTasto,
  vicinaInDirezione,
} from "./geometria.js";

// I centri veri di sei regioni sul viewBox 560x660 (il centro del riquadro di ogni tracciato).
const REGIONI = [
  { id: "campania", x: 370, y: 373 },
  { id: "puglia", x: 449, y: 361.5 },
  { id: "basilicata", x: 424, y: 385.5 },
  { id: "calabria", x: 437, y: 464.5 },
  { id: "sicilia", x: 330, y: 561 },
  { id: "lazio", x: 286.5, y: 315.5 },
  { id: "sardegna", x: 133.5, y: 408.5 },
  { id: "toscana", x: 217, y: 229.5 },
  { id: "liguria", x: 125.5, y: 181.5 },
];
const per = (id) => REGIONI.find((r) => r.id === id);

test("leggiViewBox legge quattro numeri e scarta il resto", () => {
  assert.deepEqual(leggiViewBox("358.5 284 181 155"), [358.5, 284, 181, 155]);
  assert.deepEqual(leggiViewBox("0,0,560,660"), VIEWBOX_ITALIA);
  assert.equal(leggiViewBox("0 0 560"), null);
  assert.equal(leggiViewBox("0 0 0 660"), null);
  assert.equal(leggiViewBox("a b c d"), null);
  assert.equal(leggiViewBox(null), null);
});

test("testoViewBox arrotonda a un decimale e fa il giro", () => {
  assert.equal(testoViewBox([358.54, 284, 181.04, 155]), "358.5 284 181 155");
  assert.deepEqual(leggiViewBox(testoViewBox(VIEWBOX_ITALIA)), VIEWBOX_ITALIA);
});

test("centro e puntoInVista", () => {
  assert.deepEqual(centro({ x: 10, y: 20, width: 30, height: 40 }), { x: 25, y: 40 });
  assert.equal(puntoInVista({ x: 5, y: 5 }, [0, 0, 10, 10]), true);
  assert.equal(puntoInVista({ x: 11, y: 5 }, [0, 0, 10, 10]), false);
});

test("unitaPerPixel usa la scala piu' piccola (meet)", () => {
  // 358x422 px su 560x660: scala 0,6393 (larghezza) contro 0,6394 (altezza)
  const u = unitaPerPixel(358, 422, VIEWBOX_ITALIA);
  assert.ok(Math.abs(u - 560 / 358) < 1e-9);
  // un riquadro largo e basso e' limitato dalla larghezza
  assert.ok(Math.abs(unitaPerPixel(358, 422, [0, 0, 180, 100]) - 180 / 358) < 1e-9);
  // misure assenti: 1
  assert.equal(unitaPerPixel(0, 0, VIEWBOX_ITALIA), 1);
});

test("versoDelTasto", () => {
  assert.equal(versoDelTasto("ArrowUp"), "su");
  assert.equal(versoDelTasto("ArrowLeft"), "sinistra");
  assert.equal(versoDelTasto("Enter"), null);
});

test("sull'Italia: le frecce vanno alla regione piu' vicina in quella direzione", () => {
  assert.equal(vicinaInDirezione(per("calabria"), REGIONI, "giu"), "sicilia");
  assert.equal(vicinaInDirezione(per("sicilia"), REGIONI, "destra"), "calabria");
  // in linea batte vicina ma di lato: dalla Sicilia, su, c'e' la Campania prima della Calabria
  assert.equal(vicinaInDirezione(per("sicilia"), REGIONI, "su"), "campania");
  assert.equal(vicinaInDirezione(per("campania"), REGIONI, "destra"), "basilicata");
  assert.equal(vicinaInDirezione(per("puglia"), REGIONI, "sinistra"), "basilicata");
  assert.equal(vicinaInDirezione(per("lazio"), REGIONI, "su"), "toscana");
  assert.equal(vicinaInDirezione(per("lazio"), REGIONI, "sinistra"), "sardegna");
  assert.equal(vicinaInDirezione(per("liguria"), REGIONI, "su"), null);
});

test("nel riquadro: fra province vicine vince quella in linea", () => {
  const province = [
    { id: "lecce", x: 480, y: 410 },
    { id: "brindisi", x: 465, y: 392 },
    { id: "taranto", x: 440, y: 395 },
    { id: "bari", x: 450, y: 363 },
  ];
  assert.equal(vicinaInDirezione(province[0], province, "su"), "brindisi");
  assert.equal(vicinaInDirezione(province[1], province, "sinistra"), "taranto");
  assert.equal(vicinaInDirezione(province[2], province, "su"), "bari");
  assert.equal(vicinaInDirezione(province[3], province, "giu"), "taranto");
});

test("ai bordi: senza niente di la' si resta fermi", () => {
  assert.equal(vicinaInDirezione(per("sicilia"), REGIONI, "giu"), null);
  assert.equal(vicinaInDirezione(per("liguria"), REGIONI, "su"), null);
  assert.equal(vicinaInDirezione(per("liguria"), REGIONI, "sinistra"), null);
  assert.equal(vicinaInDirezione(per("puglia"), REGIONI, "destra"), null);
});

test("col cono vuoto si ripiega su qualcosa che stia di la'", () => {
  const corrente = { id: "a", x: 0, y: 0 };
  // solo un candidato quasi di lato: fuori dal cono di 90 gradi, ma a destra
  const candidati = [corrente, { id: "b", x: 10, y: 50 }];
  assert.equal(vicinaInDirezione(corrente, candidati, "destra"), "b");
  assert.equal(vicinaInDirezione(corrente, candidati, "sinistra"), null);
});

test("con un solo elemento, o con i dati guasti, e' null", () => {
  const solo = { id: "unica", x: 10, y: 10 };
  for (const verso of ["su", "giu", "sinistra", "destra"]) {
    assert.equal(vicinaInDirezione(solo, [solo], verso), null);
  }
  assert.equal(vicinaInDirezione(solo, [], "su"), null);
  assert.equal(vicinaInDirezione(null, [solo], "su"), null);
  assert.equal(vicinaInDirezione(solo, [solo, null, { id: "x", x: 20, y: 10 }], "destra"), "x");
  assert.equal(vicinaInDirezione(solo, [{ id: "x", x: 20, y: 10 }], "diagonale"), null);
});

test("a parita' di distanza vince l'id piu' piccolo", () => {
  const corrente = { id: "m", x: 0, y: 0 };
  const candidati = [{ id: "z", x: 10, y: -5 }, { id: "b", x: 10, y: 5 }];
  assert.equal(vicinaInDirezione(corrente, candidati, "destra"), "b");
});

test("riquadroRivelazione non muove la vista se tutto e' dentro", () => {
  const vista = [358.5, 284, 181, 155];
  const giusta = { x: 440, y: 380, width: 30, height: 30 };
  const scelta = { x: 400, y: 360, width: 30, height: 30 };
  assert.equal(riquadroRivelazione(vista, giusta, scelta), vista);
  assert.equal(riquadroRivelazione(vista, giusta, undefined), vista);
});

test("riquadroRivelazione prende una vista che contiene la giusta e la scelta", () => {
  const vista = [358.5, 284, 181, 155];
  const giusta = { x: 440, y: 380, width: 30, height: 30 };
  const lontana = { x: 100, y: 100, width: 40, height: 40 };
  const nuova = riquadroRivelazione(vista, giusta, lontana);
  for (const s of [giusta, lontana]) {
    assert.ok(nuova[0] <= s.x && nuova[1] <= s.y, "il riquadro parte prima della sagoma");
    assert.ok(nuova[0] + nuova[2] >= s.x + s.width && nuova[1] + nuova[3] >= s.y + s.height);
  }
});

test("riquadroRivelazione non scende sotto il lato minimo", () => {
  const vista = [0, 0, 20, 20];
  const nuova = riquadroRivelazione(vista, { x: 300, y: 300, width: 5, height: 5 });
  assert.ok(nuova[2] >= LATO_MINIMO && nuova[3] >= LATO_MINIMO);
});
