import test from "node:test";
import assert from "node:assert/strict";
import {
  metaUnita,
  nomeTerritorio,
  numeroIt,
  percorsoTerritorio,
  righeEsito,
  segnoPosizione,
  tastoPerLaRiga,
  tonoDaPunteggio,
  valoreConUnita,
} from "./order.puri.js";

// -- numeroIt e valoreConUnita ----------------------------------------------------

test("numeroIt scrive i numeri all'italiana, coi decimali giusti", () => {
  assert.equal(numeroIt(12.34), "12,3");
  assert.equal(numeroIt(1234.56), "1.235");
  assert.equal(numeroIt(0.4), "0,40");
  // Decimali fissi, come in `app/static/js/v1.js`: lo zero non ne ha.
  assert.equal(numeroIt(74), "74,0");
  assert.equal(numeroIt(0), "0");
  assert.equal(numeroIt(7), "7,0");
});

test("valoreConUnita mette il numero e l'unita' nello stesso modo del resto del sito", () => {
  assert.equal(valoreConUnita(12.34, "percentuale"), "12,3%");
  assert.equal(valoreConUnita(12.34, "Valori percentuali"), "12,3%");
  assert.equal(valoreConUnita(1234.56, "euro"), "1.235 euro");
  assert.equal(valoreConUnita(74, "percentuale"), "74,0%");
});

test("valoreConUnita scrive l'unita' come `phrase_unit` in numfmt.py", () => {
  // I punti percentuali non sono una percentuale: "1,2 punti percentuali".
  assert.equal(valoreConUnita(1.23, "punti percentuali"), "1,2 punti percentuali");
  // Un'etichetta che dice che cosa si conta non si scrive accanto alla cifra.
  assert.equal(valoreConUnita(29.04, "numero"), "29,0");
  assert.equal(valoreConUnita(7.2, "Valore medio"), "7,2");
  // Il tasso va detto, altrimenti "228 centomila anziani" sembrano ventidue milioni.
  assert.equal(valoreConUnita(228, "centomila anziani"), "228 ogni centomila anziani");
  assert.equal(valoreConUnita(228, "per centomila abitanti"), "228 per centomila abitanti");
});

// Il difetto che ha fatto fallire la prova: `formatValue` (la funzione degli altri giochi)
// con un valore assente restituisce "n.d.", e nell'esito finiva "Saldo migratorio: n.d.".
test("valoreConUnita non stampa mai n.d. quando il valore non c'e'", () => {
  for (const assente of [null, undefined, Number.NaN, Number.POSITIVE_INFINITY, "12,3", "", {}, []]) {
    assert.equal(valoreConUnita(assente, "percentuale"), "", `per ${JSON.stringify(assente)}`);
  }
  assert.ok(!/n\.d\./i.test(valoreConUnita(null, "percentuale")));
  assert.ok(!/n\.d\./i.test(valoreConUnita(12.3, "percentuale")));
});

test("valoreConUnita senza unita' stampa il numero e basta", () => {
  assert.equal(valoreConUnita(12.34, undefined), "12,3");
  assert.equal(valoreConUnita(12.34, "   "), "12,3");
});

// -- nomeTerritorio e percorsoTerritorio ------------------------------------------

test("nomeTerritorio legge il nome dove il payload lo mette", () => {
  assert.equal(nomeTerritorio({ name: "Torino", region: "Piemonte" }), "Torino");
  assert.equal(nomeTerritorio({ region: "Lombardia" }), "Lombardia");
  assert.equal(nomeTerritorio({}), "");
  assert.equal(nomeTerritorio(null), "");
});

// Il difetto che ha fatto fallire la prova: il percorso era costruito dal nome, e
// "Valle d'Aosta" dava `/regione/valle-d'aosta`, che non e' una pagina.
test("percorsoTerritorio esce dalla chiave del payload, mai dal nome", () => {
  assert.equal(percorsoTerritorio({ key: "valle-d-aosta", name: "Valle d'Aosta", region: "Valle d'Aosta" }), "/regione/valle-d-aosta");
  assert.equal(percorsoTerritorio({ region: "Lombardia", region_key: "lombardia" }), "/regione/lombardia");
});

test("percorsoTerritorio distingue la provincia dalla regione", () => {
  assert.equal(percorsoTerritorio({ key: "torino", name: "Torino", region: "Piemonte" }), "/provincia/torino");
});

test("percorsoTerritorio senza chiave non inventa un link", () => {
  assert.equal(percorsoTerritorio({ name: "Valle d'Aosta", region: "Valle d'Aosta" }), null);
  assert.equal(percorsoTerritorio({ key: "", name: "Lombardia" }), null);
  assert.equal(percorsoTerritorio(null), null);
  assert.ok(!/[']/.test(percorsoTerritorio({ region: "Valle d'Aosta" }) || ""));
});

// -- righeEsito -------------------------------------------------------------------

const POSITIONS = [
  { region: "Piemonte", region_key: "piemonte", value: 74.3, guessed_position: 1, correct: false, correct_position: 4 },
  { region: "Lombardia", region_key: "lombardia", value: 75.1, guessed_position: 2, correct: true, correct_position: 2 },
  { region: "Valle d'Aosta", region_key: "valle-d-aosta", value: 77.8, guessed_position: 3, correct: false, correct_position: 1 },
  { region: "Liguria", region_key: "liguria", value: 73.8, guessed_position: 4, correct: false, correct_position: 5 },
  { region: "Friuli-Venezia Giulia", region_key: "friuli-venezia-giulia", value: 74.7, guessed_position: 5, correct: false, correct_position: 3 },
];

const CORRECT = [
  { region: "Valle d'Aosta", region_key: "valle-d-aosta", value: 77.8 },
  { region: "Lombardia", region_key: "lombardia", value: 75.1 },
  { region: "Friuli-Venezia Giulia", region_key: "friuli-venezia-giulia", value: 74.7 },
  { region: "Piemonte", region_key: "piemonte", value: 74.3 },
  { region: "Liguria", region_key: "liguria", value: 73.8 },
];

test("righeEsito mette una riga per territorio, nell'ordine vero", () => {
  const righe = righeEsito(POSITIONS, CORRECT, "percentuale");
  assert.deepEqual(righe.map((r) => r.nome), [
    "Valle d'Aosta", "Lombardia", "Friuli-Venezia Giulia", "Piemonte", "Liguria",
  ]);
  assert.deepEqual(righe.map((r) => r.posizione), [1, 2, 3, 4, 5]);
});

test("righeEsito porta il valore e l'unita' accanto al nome di ogni riga", () => {
  const righe = righeEsito(POSITIONS, CORRECT, "percentuale");
  for (const riga of righe) {
    assert.equal(typeof riga.valore, "number", `il valore manca su ${riga.nome}`);
    assert.ok(riga.unita, `l'unita' manca su ${riga.nome}`);
    assert.match(valoreConUnita(riga.valore, riga.unita), /\d/, `la riga di ${riga.nome} non mostra il numero`);
    assert.ok(!/n\.d\./i.test(valoreConUnita(riga.valore, riga.unita)), `n.d. su ${riga.nome}`);
  }
  assert.equal(valoreConUnita(righe[0].valore, righe[0].unita), "77,8%");
});

test("righeEsito preferisce l'unita' della riga e cade su quella dell'indicatore", () => {
  const conUnita = righeEsito(POSITIONS, CORRECT.map((r) => ({ ...r, unit: "Valori percentuali" })), "percentuale");
  assert.equal(conUnita[0].unita, "Valori percentuali");
  const senza = righeEsito(POSITIONS, CORRECT, "percentuale");
  assert.equal(senza[0].unita, "percentuale");
});

test("righeEsito unisce le due liste per chiave e segna la posizione esatta", () => {
  const righe = righeEsito(POSITIONS, CORRECT, "percentuale");
  const lombardia = righe.find((r) => r.chiave === "lombardia");
  assert.equal(lombardia.esatta, true);
  assert.equal(lombardia.tua, 2);
  const piemonte = righe.find((r) => r.chiave === "piemonte");
  assert.equal(piemonte.esatta, false);
  assert.equal(piemonte.tua, 1);
  assert.equal(piemonte.posizione, 4);
});

test("righeEsito senza correct_order non butta via quello che c'e'", () => {
  const righe = righeEsito(POSITIONS, undefined, "percentuale");
  assert.equal(righe.length, 5);
  assert.deepEqual(righe.map((r) => r.nome), [
    "Piemonte", "Lombardia", "Valle d'Aosta", "Liguria", "Friuli-Venezia Giulia",
  ]);
  assert.equal(righe[0].unita, "percentuale");
});

test("righeEsito con payload vuoti non inventano righe", () => {
  assert.deepEqual(righeEsito(null, null, "percentuale"), []);
  assert.deepEqual(righeEsito([], [], "percentuale"), []);
});

// -- segnoPosizione ---------------------------------------------------------------

test("segnoPosizione sulla riga giusta e' il segno di spunta con la frase", () => {
  const segno = segnoPosizione({ esatta: true, tua: 2, posizione: 2 });
  assert.equal(segno.glifo, "✓");
  assert.equal(segno.esatta, true);
  assert.match(segno.testo, /posizione giusta/);
});

test("segnoPosizione sulla riga sbagliata dice dove l'avevi messa", () => {
  const segno = segnoPosizione({ esatta: false, tua: 3, posizione: 1 });
  assert.equal(segno.glifo, "✗");
  assert.equal(segno.esatta, false);
  assert.equal(segno.testo, "eri alla 3, era la 1");
});

test("segnoPosizione senza posizioni note non promette un numero", () => {
  const segno = segnoPosizione({ esatta: false, tua: null, posizione: null });
  assert.ok(!/\d/.test(segno.testo));
});

// -- tonoDaPunteggio --------------------------------------------------------------

test("tonoDaPunteggio distingue il pieno, il parziale e il nullo", () => {
  assert.equal(tonoDaPunteggio(5, 5), "pieno");
  assert.equal(tonoDaPunteggio(3, 5), "parziale");
  assert.equal(tonoDaPunteggio(0, 5), "nullo");
  assert.equal(tonoDaPunteggio(4, 3), "pieno");
  assert.equal(tonoDaPunteggio(NaN, 5), "nullo");
});

// -- metaUnita --------------------------------------------------------------------

test("metaUnita tiene la riga dei metadati su una riga e senza spaziatori vuoti", () => {
  assert.equal(metaUnita(["Nord", "", "percentuale", "   "]), "Nord · percentuale");
  assert.equal(metaUnita([undefined, "anni"]), "anni");
  assert.equal(metaUnita([]), "");
  assert.equal(metaUnita(null), "");
});

test("tastoPerLaRiga: Invio e Spazio sulla riga la attivano", () => {
  const riga = {};
  assert.equal(tastoPerLaRiga("Enter", riga, riga), true);
  assert.equal(tastoPerLaRiga(" ", riga, riga), true);
  assert.equal(tastoPerLaRiga("ArrowDown", riga, riga), false);
});

test("tastoPerLaRiga: sui bottoni freccia della riga Invio e Spazio restano del bottone", () => {
  const riga = {};
  const bottone = {};
  assert.equal(tastoPerLaRiga("Enter", bottone, riga), false);
  assert.equal(tastoPerLaRiga(" ", bottone, riga), false);
});
