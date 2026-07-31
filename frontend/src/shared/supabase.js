// Client Supabase per il gioco: login Google e token di sessione.
//
// Tutto e' opzionale. La configurazione arriva dal server via window.__supabase
// (URL + anon key pubbliche, iniettate nel template). Se manca, il gioco resta
// esattamente anonimo com'era: nessun bottone di login, nessun header
// Authorization, e -- importante -- la libreria @supabase/supabase-js NON viene
// nemmeno scaricata (import dinamico dietro il flag di configurazione). Cosi' la
// pagina del gioco non paga il peso di supabase finche' l'account non e' attivo.

let _clientPromise = null;

function _config() {
  const cfg = typeof window !== "undefined" ? window.__supabase : null;
  return cfg && cfg.url && cfg.anonKey ? cfg : null;
}

export function isAuthConfigured() {
  return _config() !== null;
}

async function client() {
  const cfg = _config();
  if (!cfg) return null;
  if (!_clientPromise) {
    _clientPromise = import("@supabase/supabase-js").then(({ createClient }) =>
      createClient(cfg.url, cfg.anonKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
      })
    );
  }
  return _clientPromise;
}

// Il token di accesso corrente, o null. Da allegare come Bearer alle fetch che
// vogliono attribuire l'azione a un account.
export async function getAccessToken() {
  const c = await client();
  if (!c) return null;
  const { data } = await c.auth.getSession();
  return data?.session?.access_token || null;
}

export async function getUser() {
  const c = await client();
  if (!c) return null;
  const { data } = await c.auth.getUser();
  return data?.user || null;
}

export async function onAuthChange(callback) {
  const c = await client();
  if (!c) return () => {};
  const { data } = c.auth.onAuthStateChange((_event, session) => {
    callback(session?.user || null);
  });
  return () => data?.subscription?.unsubscribe();
}

export async function signInWithGoogle() {
  const c = await client();
  if (!c) return;
  await c.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.href },
  });
}

export async function signOut() {
  const c = await client();
  if (!c) return;
  await c.auth.signOut();
}

// Segnala al server la sessione: upsert del profilo + last_seen (best-effort).
// Da chiamare da OGNI punto in cui il frontend conferma un login, cosi' il
// profilo nasce ovunque ci si logghi (atlante compreso). Seed del nickname dal
// locale del gioco solo alla creazione. Ritorna il profilo o null.
export async function syncProfile() {
  const token = await getAccessToken();
  if (!token) return null;
  let nick = "";
  try {
    nick = window.localStorage.getItem("di-nickname") || "";
  } catch {
    /* localStorage negato */
  }
  const q = nick ? `?nick=${encodeURIComponent(nick)}` : "";
  try {
    const r = await fetch(`/api/auth/me${q}`, { headers: { Authorization: `Bearer ${token}` } });
    return r.ok ? (await r.json()).profile : null;
  } catch {
    return null;
  }
}
