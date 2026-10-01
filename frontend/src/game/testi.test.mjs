import test from "node:test";
import assert from "node:assert/strict";
import {
  ERRORE_GENERICO,
  ERRORE_LIMITE,
  ERRORE_RETE,
  erroreDiRete,
  messaggioTentativo,
  NUOVO_TENTATIVO,
  PARTITA_INTERROTTA,
  SFIDA_CAMBIATA,
} from "./testi.js";

test("erroreDiRete: la rete assente e ogni 5xx, 503 compreso, sono 'il server non risponde'", () => {
  for (const status of [undefined, 0, 500, 502, 503, 504]) assert.equal(erroreDiRete(status), true, String(status));
  for (const status of [400, 404, 409, 410, 429]) assert.equal(erroreDiRete(status), false, String(status));
});

test("messaggioTentativo: rete e 503 dicono la stessa cosa, il 429 il limite, il resto il generico", () => {
  assert.equal(messaggioTentativo(0), `${ERRORE_RETE} Riprova.`);
  assert.equal(messaggioTentativo(503), messaggioTentativo(undefined));
  assert.equal(messaggioTentativo(429), ERRORE_LIMITE);
  assert.equal(messaggioTentativo(400), ERRORE_GENERICO);
});

test("la voce: mai la prima persona singolare, mai 'scaduta' per la partita, mai 'non valida'", () => {
  for (const testo of [ERRORE_RETE, ERRORE_GENERICO, ERRORE_LIMITE, PARTITA_INTERROTTA, SFIDA_CAMBIATA, NUOVO_TENTATIVO]) {
    assert.ok(!/\bnon riesco\b|\bnon sono riuscit|\briprovo\b|scadut|non valid/i.test(testo), testo);
    assert.ok(!/[—–;…]/.test(testo), testo);
  }
});
