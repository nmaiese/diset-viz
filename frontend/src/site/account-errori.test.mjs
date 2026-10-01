import test from "node:test";
import assert from "node:assert/strict";
import {
  ELIMINA_FALLITO,
  ESPORTA_FALLITO,
  SESSIONE_SCADUTA,
  messaggioErrore,
} from "./account-errori.js";

test("senza risposta o con 401 la causa e' l'accesso", () => {
  assert.equal(messaggioErrore(null, ESPORTA_FALLITO), SESSIONE_SCADUTA);
  assert.equal(messaggioErrore({ status: 401 }, ELIMINA_FALLITO), SESSIONE_SCADUTA);
});

test("la rete caduta non e' colpa dell'accesso", () => {
  assert.equal(messaggioErrore({ ok: false, status: 0 }, ESPORTA_FALLITO), ESPORTA_FALLITO);
});

test("un errore del servizio porta il messaggio dell'azione", () => {
  assert.equal(messaggioErrore({ status: 500 }, ESPORTA_FALLITO), ESPORTA_FALLITO);
  assert.equal(messaggioErrore({ status: 503 }, ELIMINA_FALLITO), ELIMINA_FALLITO);
});

test("i messaggi sono in italiano e dicono che fare, senza i segni vietati dallo stile", () => {
  for (const m of [ESPORTA_FALLITO, ELIMINA_FALLITO, SESSIONE_SCADUTA]) {
    assert.match(m, /Riprova|accedi di nuovo/);
    assert.doesNotMatch(m, /[—–;…]/);
  }
});
