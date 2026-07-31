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

function _readJson(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) || "null") || {};
  } catch {
    return {};
  }
}

// Fonde le statistiche locali del gioco (localStorage) nell'account, UNA sola
// volta per account (flag one-time). I 'best' si fondono con max, i contatori con
// somma: l'idempotenza la garantisce il flag qui, cosi' un secondo login non
// raddoppia i contatori. Ritorna gli achievement eventualmente sbloccati.
export async function mergeLocalStatsOnce(userId) {
  if (!userId) return [];
  const flag = `di-merged-into:${userId}`;
  try {
    if (window.localStorage.getItem(flag)) return [];
  } catch {
    return [];
  }
  const cmp = _readJson("di-compare-stats");
  const ord = _readJson("di-order-stats");
  const day = _readJson("di-game-stats");
  const stats = {
    compare: { best_streak: cmp.bestStreak || 0, rounds_played: cmp.totalRounds || 0, correct: cmp.totalCorrect || 0 },
    order: { best_streak: Math.max(ord.bestScore3 || 0, ord.bestScore5 || 0), rounds_played: ord.totalRounds || 0 },
    daily: { games_played: day.played || 0, wins: day.wins || 0, max_daily_streak: day.maxStreak || 0 },
  };
  const token = await getAccessToken();
  if (!token) return [];
  try {
    const r = await fetch("/api/player/merge", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ stats }),
    });
    try {
      window.localStorage.setItem(flag, "1"); // una volta sola, comunque vada
    } catch {
      /* noop */
    }
    return r.ok ? (await r.json()).achievements || [] : [];
  } catch {
    return [];
  }
}
