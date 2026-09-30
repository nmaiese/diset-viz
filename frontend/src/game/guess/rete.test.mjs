import assert from "node:assert/strict";
import test from "node:test";
import { inviaJson } from "./rete.js";

function fetchFinto(dati, { ok = true, status = 200, json } = {}) {
  const chiamate = [];
  const impl = async (url, init) => {
    chiamate.push({ url, init });
    return { ok, status, json: json || (async () => dati) };
  };
  impl.chiamate = chiamate;
  return impl;
}

test("manda il corpo come JSON e il Bearer se c'e' una sessione", async () => {
  const fetchImpl = fetchFinto({ ok: 1 });
  const dati = await inviaJson("/api/x", { a: 1 }, { getToken: async () => "jwt", fetchImpl });
  assert.deepEqual(dati, { ok: 1 });
  const { init } = fetchImpl.chiamate[0];
  assert.equal(init.headers["Content-Type"], "application/json");
  assert.equal(init.headers.Authorization, "Bearer jwt");
  assert.equal(init.body, '{"a":1}');
});

test("senza sessione (anche se il recupero del token fallisce) niente Authorization", async () => {
  for (const getToken of [undefined, async () => "", async () => { throw new Error("no"); }]) {
    const fetchImpl = fetchFinto({});
    await inviaJson("/api/x", {}, { getToken, fetchImpl });
    assert.equal("Authorization" in fetchImpl.chiamate[0].init.headers, false);
  }
});

test("un errore porta il codice del server e lo stato HTTP", async () => {
  const fetchImpl = fetchFinto({ error: "puzzle_changed" }, { ok: false, status: 410 });
  await assert.rejects(
    inviaJson("/api/game/guess", {}, { fetchImpl }),
    (errore) => errore.code === "puzzle_changed" && errore.status === 410,
  );
});

test("un errore senza corpo JSON e' comunque un errore con lo stato", async () => {
  const fetchImpl = fetchFinto(null, {
    ok: false,
    status: 502,
    json: async () => { throw new SyntaxError("non e' JSON"); },
  });
  await assert.rejects(inviaJson("/api/x", {}, { fetchImpl }), (errore) => errore.status === 502 && errore.code === undefined);
});
