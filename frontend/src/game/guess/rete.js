// Le chiamate POST dei due giochi a indovinare, con il Bearer di chi ha fatto l'accesso.
//
// Sta qui e non in `shared.jsx` per due motivi: `postGame` butta via il codice e lo stato della
// risposta (qui servono, `puzzle_changed` e `sfida_scaduta` hanno un messaggio loro) e questo
// modulo e' puro, quindi lo prova `node --test` con un `fetch` finto. Il token di accesso e
// `fetch` si iniettano: il componente passa `getAccessToken` di `shared/supabase.js`.

// Header Authorization, o niente: per un anonimo il gioco non cambia, l'account e' un extra.
async function intestazioneAccesso(getToken) {
  if (!getToken) return {};
  try {
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

// POST di `body` come JSON. Ritorna il JSON della risposta. Se il server risponde con un errore
// lancia un `Error` con `.code` (il campo `error` del corpo, se c'e') e `.status` (HTTP).
export async function inviaJson(url, body, { getToken, fetchImpl } = {}) {
  const richiesta = fetchImpl || globalThis.fetch;
  const risposta = await richiesta(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await intestazioneAccesso(getToken)) },
    body: JSON.stringify(body),
  });
  let dati = null;
  try {
    dati = await risposta.json();
  } catch {
    dati = null;
  }
  if (!risposta.ok) {
    const errore = new Error((dati && dati.error) || `Request failed: ${url}`);
    errore.code = dati ? dati.error : undefined;
    errore.status = risposta.status;
    throw errore;
  }
  return dati;
}
