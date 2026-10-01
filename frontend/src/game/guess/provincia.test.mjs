import assert from "node:assert/strict";
import test from "node:test";
import {
  API_PROVINCIA,
  AVVISO_RIPRESA,
  decisioneErroreTentativo,
  rimuoviProgresso,
  caricaProgresso,
  salvaProgresso,
  inviaTentativo,
  messaggioFuoriElenco,
  nomeLivello,
  regioneConArticolo,
  rigaTerritorio,
  riassuntoProvincia,
  testoDistanzaCompatta,
} from "./provincia.js";

// Una risposta finta di `fetch`: `{ ok, status, json() }`.
function risposta(dati, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => dati };
}

function fetchFinto(dati, opzioni) {
  const chiamate = [];
  const impl = async (url, init) => {
    chiamate.push({ url, init });
    return risposta(dati, opzioni);
  };
  impl.chiamate = chiamate;
  return impl;
}

const PUGLIA = { name: "Puglia" };
const OPZIONI = [
  { key: "bari", name: "Bari" },
  { key: "barletta-andria-trani", name: "Barletta-Andria-Trani" },
  { key: "brindisi", name: "Brindisi" },
  { key: "foggia", name: "Foggia" },
  { key: "lecce", name: "Lecce" },
  { key: "taranto", name: "Taranto" },
];
const ALTRE = [
  { name: "Milano", region: "Lombardia" },
  { name: "Forlì-Cesena", region: "Emilia-Romagna" },
  { name: "Reggio Calabria", region: "Calabria" },
  { name: "Reggio Emilia", region: "Emilia-Romagna" },
];
const CONTESTO = { regione: PUGLIA, opzioni: OPZIONI, altre: ALTRE, tentate: [] };

test("una provincia di un'altra regione dice dove sta e dove si cerca", () => {
  assert.equal(
    messaggioFuoriElenco("Milano", CONTESTO),
    "Milano non è in Puglia. Qui cerchi fra le province della Puglia.",
  );
});

test("il confronto ignora maiuscole, accenti e trattini", () => {
  assert.match(messaggioFuoriElenco("forli cesena", CONTESTO), /^Forlì-Cesena non è in Puglia/);
  assert.match(messaggioFuoriElenco("MILANO", CONTESTO), /^Milano non è in Puglia/);
});

test("fra due province fuori regione vince quella scritta per intero", () => {
  assert.match(messaggioFuoriElenco("reggio emilia", CONTESTO), /^Reggio Emilia non è in Puglia/);
  assert.match(messaggioFuoriElenco("reggio cal", CONTESTO), /^Reggio Calabria non è in Puglia/);
});

test("un testo che non e' nessuna provincia dice che non c'e' e rimanda all'elenco", () => {
  assert.equal(
    messaggioFuoriElenco("Atlantide", CONTESTO),
    "Nessuna provincia della Puglia si chiama così. Scegli dall'elenco.",
  );
});

test("finche' il testo ha dei suggerimenti in regione non c'e' niente da dire", () => {
  assert.equal(messaggioFuoriElenco("ba", CONTESTO), null);
  assert.equal(messaggioFuoriElenco("Lecce", CONTESTO), null);
  assert.equal(messaggioFuoriElenco("   ", CONTESTO), null);
  assert.equal(messaggioFuoriElenco("", CONTESTO), null);
});

test("una provincia della regione gia' tentata non e' 'nessuna si chiama cosi'", () => {
  const dopo = { ...CONTESTO, tentate: ["lecce"] };
  assert.equal(messaggioFuoriElenco("Lecce", dopo), "Hai già provato Lecce. Scegline un'altra dall'elenco.");
  // Se altre province corrispondono ancora al testo ci sono suggerimenti: niente messaggio.
  assert.equal(messaggioFuoriElenco("ba", { ...CONTESTO, tentate: ["bari"] }), null);
});

test("gli articoli delle regioni: Puglia, Lazio, Marche e le vocali", () => {
  assert.deepEqual(regioneConArticolo("Puglia"), { di: "della Puglia", in: "in Puglia" });
  assert.deepEqual(regioneConArticolo("Lazio"), { di: "del Lazio", in: "nel Lazio" });
  assert.deepEqual(regioneConArticolo("Marche"), { di: "delle Marche", in: "nelle Marche" });
  assert.deepEqual(regioneConArticolo("Umbria"), { di: "dell'Umbria", in: "in Umbria" });
  assert.deepEqual(regioneConArticolo("Abruzzo"), { di: "dell'Abruzzo", in: "in Abruzzo" });
  assert.deepEqual(regioneConArticolo("Valle d'Aosta"), { di: "della Valle d'Aosta", in: "in Valle d'Aosta" });
  assert.deepEqual(regioneConArticolo("Friuli-Venezia Giulia"), {
    di: "del Friuli-Venezia Giulia",
    in: "in Friuli-Venezia Giulia",
  });
  // Un nome che non conosciamo non si inventa: forma senza articolo.
  assert.deepEqual(regioneConArticolo("Atlantide"), { di: "di Atlantide", in: "in Atlantide" });
});

test("il messaggio usa l'articolo giusto della regione", () => {
  const lazio = { ...CONTESTO, regione: { name: "Lazio" } };
  assert.equal(
    messaggioFuoriElenco("Milano", lazio),
    "Milano non è nel Lazio. Qui cerchi fra le province del Lazio.",
  );
  assert.equal(
    messaggioFuoriElenco("xyz", { ...lazio, opzioni: [{ key: "roma", name: "Roma" }] }),
    "Nessuna provincia del Lazio si chiama così. Scegli dall'elenco.",
  );
});

test("il nome del livello abbassa solo la prima lettera: Italia resta maiuscola", () => {
  assert.equal(nomeLivello("province"), "di tutta Italia");
  assert.equal(nomeLivello("stessa_regione"), "della regione");
  assert.equal(nomeLivello("sconosciuto"), "della regione");
});

test("il testo condiviso porta i tentativi e il livello, senza spoiler", () => {
  assert.equal(riassuntoProvincia({ won: true, tentativi: 3, totale: 6, level: "stessa_regione" }), "3 su 6, livello della regione");
  assert.equal(riassuntoProvincia({ won: true, tentativi: 4, totale: 6, level: "province" }), "4 su 6, livello di tutta Italia");
  assert.equal(riassuntoProvincia({ won: false, tentativi: 6, totale: 6, level: "province" }), "X su 6, livello di tutta Italia");
});

test("la riga compatta di un tentativo: a circa N km verso il punto cardinale", () => {
  assert.equal(testoDistanzaCompatta({ correct: false, distance_km: 120, direction: "NE" }), "a circa 120 km verso nord-est, stima");
  assert.equal(testoDistanzaCompatta({ correct: false, distance_km: 1200, direction: "S" }), "a circa 1200 km verso sud, stima");
  assert.equal(testoDistanzaCompatta({ correct: false, distance_km: 40 }), "a circa 40 km, stima");
  assert.equal(testoDistanzaCompatta({ correct: true, distance_km: 0, direction: "N" }), "");
});

test("il tentativo manda il Bearer di chi ha fatto l'accesso", async () => {
  const fetchImpl = fetchFinto({ correct: false, finished: false, token: "t2" });
  await inviaTentativo("t1", "bari", { getToken: async () => "jwt-di-prova", fetchImpl });
  assert.equal(fetchImpl.chiamate.length, 1);
  const { url, init } = fetchImpl.chiamate[0];
  assert.equal(url, API_PROVINCIA.guess);
  assert.equal(init.method, "POST");
  assert.equal(init.headers.Authorization, "Bearer jwt-di-prova");
  assert.deepEqual(JSON.parse(init.body), { token: "t1", province_key: "bari" });
});

test("da anonimo il tentativo parte senza Authorization", async () => {
  for (const getToken of [async () => null, async () => { throw new Error("niente sessione"); }, undefined]) {
    const fetchImpl = fetchFinto({ correct: false, finished: false, token: "t2" });
    await inviaTentativo("t1", "bari", { getToken, fetchImpl });
    assert.equal("Authorization" in fetchImpl.chiamate[0].init.headers, false);
  }
});

test("a fine partita i traguardi vanno al toast, col nome del gioco", async () => {
  const traguardi = [{ id: "geografo", title: "Geografo" }];
  const fetchImpl = fetchFinto({ correct: true, finished: true, achievements: traguardi, token: "t2" });
  const chiamate = [];
  const risultato = await inviaTentativo("t1", "bari", {
    getToken: async () => "jwt",
    fetchImpl,
    notify: (lista, gioco) => chiamate.push([lista, gioco]),
  });
  assert.deepEqual(chiamate, [[traguardi, "provincia"]]);
  assert.equal(risultato.correct, true);
});

test("un tentativo a meta' partita non notifica niente", async () => {
  const fetchImpl = fetchFinto({ correct: false, finished: false, token: "t2" });
  const chiamate = [];
  await inviaTentativo("t1", "bari", { fetchImpl, notify: (...args) => chiamate.push(args) });
  assert.deepEqual(chiamate, []);
});

test("l'errore del server arriva con codice e stato", async () => {
  const fetchImpl = fetchFinto({ error: "sfida_scaduta" }, { ok: false, status: 410 });
  await assert.rejects(
    inviaTentativo("t1", "bari", { fetchImpl }),
    (errore) => errore.code === "sfida_scaduta" && errore.status === 410,
  );
});

test("senza regione (livello di tutta Italia) il messaggio non nomina una regione", () => {
  const italia = { regione: null, opzioni: OPZIONI, altre: [], tentate: [] };
  assert.equal(messaggioFuoriElenco("Atlantide", italia), "Nessuna provincia si chiama così. Scegli dall'elenco.");
  assert.equal(messaggioFuoriElenco("ba", italia), null);
  assert.equal(messaggioFuoriElenco("Lecce", { ...italia, tentate: ["lecce"] }), "Hai già provato Lecce. Scegline un'altra dall'elenco.");
});

const SOLUZIONE = { province_key: "bari", region_key: "puglia" };

test("la riga del territorio: la provincia di oggi e' nella tua regione", () => {
  const mio = { level: "provincia", key: "lecce", name: "Lecce", region: "puglia", regionName: "Puglia" };
  assert.equal(rigaTerritorio(mio, SOLUZIONE), "La provincia di oggi è della tua regione.");
});

test("la riga del territorio: e' proprio la tua provincia, o la regione che hai scelto", () => {
  const tua = { level: "provincia", key: "bari", name: "Bari", region: "puglia", regionName: "Puglia" };
  assert.equal(rigaTerritorio(tua, SOLUZIONE), "La provincia di oggi è la tua.");
  assert.equal(rigaTerritorio({ level: "regione", key: "puglia", name: "Puglia" }, SOLUZIONE), "La provincia di oggi è della tua regione.");
});

test("la riga del territorio non esce se non c'entra o se manca il dato", () => {
  const altrove = { level: "provincia", key: "milano", name: "Milano", region: "lombardia", regionName: "Lombardia" };
  assert.equal(rigaTerritorio(altrove, SOLUZIONE), null);
  assert.equal(rigaTerritorio({ level: "regione", key: "lazio", name: "Lazio" }, SOLUZIONE), null);
  assert.equal(rigaTerritorio(null, SOLUZIONE), null);
  assert.equal(rigaTerritorio({ level: "provincia", key: "lecce", name: "Lecce" }, SOLUZIONE), null);
  assert.equal(rigaTerritorio({ level: "provincia", key: "lecce", name: "Lecce" }, SOLUZIONE, [{ key: "lecce", region: "Lombardia" }]), null);
  assert.equal(rigaTerritorio(altrove, null), null);
});

test("la provincia scelta senza la sua regione la trova fra le province del payload", () => {
  const soluzione = { province_key: "bari", region_key: "puglia", region: "Puglia" };
  const senzaRegione = { level: "provincia", key: "lecce", name: "Lecce" };
  assert.equal(
    rigaTerritorio(senzaRegione, soluzione, [{ key: "lecce", region: "Puglia" }]),
    "La provincia di oggi è della tua regione.",
  );
});

test("decisioneErroreTentativo: 409 e token superato riprendono da soli, una volta", () => {
  assert.equal(decisioneErroreTentativo({ status: 409, code: "token_superato" }), "riprendi");
  assert.equal(decisioneErroreTentativo({ status: 409 }), "riprendi");
  assert.equal(decisioneErroreTentativo({ code: "token_superato" }), "riprendi");
  assert.equal(decisioneErroreTentativo({ status: 409, code: "token_superato" }, { giaRipresa: true }), "ricarica");
});

test("decisioneErroreTentativo: la sfida cambiata si ricarica, il resto riprova", () => {
  assert.equal(decisioneErroreTentativo({ status: 410, code: "sfida_scaduta" }), "ricarica");
  assert.equal(decisioneErroreTentativo({ status: 410, code: "sfida_scaduta" }, { giaRipresa: true }), "ricarica");
  for (const input of [{ status: 429, code: "rate_limited" }, { status: 400, code: "provincia_gia_tentata" }, { status: 0 }, {}, undefined]) {
    assert.equal(decisioneErroreTentativo(input), "messaggio");
  }
});

test("l'avviso della ripresa non ha colpa, ne' punteggiatura vietata", () => {
  assert.match(AVVISO_RIPRESA, /non per colpa tua/);
  assert.doesNotMatch(AVVISO_RIPRESA, /[;—–…]/);
});

test("rimuoviProgresso dimentica il progresso salvato e solo quello", () => {
  const deposito = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (k) => deposito.get(k) ?? null,
      setItem: (k, v) => deposito.set(k, v),
      removeItem: (k) => deposito.delete(k),
    },
  };
  try {
    const progresso = { level: "province", token: "t", clues: [], guesses: [], status: "playing", solution: null, recap: null };
    salvaProgresso("daily:2026-10-01", progresso);
    salvaProgresso("daily:2026-09-30", progresso);
    assert.deepEqual(caricaProgresso("daily:2026-10-01"), progresso);
    rimuoviProgresso("daily:2026-10-01");
    assert.equal(caricaProgresso("daily:2026-10-01"), null);
    assert.deepEqual(caricaProgresso("daily:2026-09-30"), progresso);
  } finally {
    delete globalThis.window;
  }
});
