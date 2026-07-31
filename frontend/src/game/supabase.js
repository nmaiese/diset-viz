// Client Supabase per il gioco: login Google e token di sessione.
//
// Tutto e' opzionale. La configurazione arriva dal server via window.__supabase
// (URL + anon key pubbliche, iniettate nel template). Se manca, il client e'
// null e il gioco resta esattamente anonimo com'era: nessun bottone di login
// compare, nessun header Authorization viene aggiunto. Cosi' il bundle si puo'
// spedire prima che Supabase sia configurato.

import { createClient } from "@supabase/supabase-js";

let _client = null;
let _initialized = false;

function client() {
  if (_initialized) return _client;
  _initialized = true;
  const cfg = typeof window !== "undefined" ? window.__supabase : null;
  if (cfg && cfg.url && cfg.anonKey) {
    _client = createClient(cfg.url, cfg.anonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
  }
  return _client;
}

export function isAuthConfigured() {
  return client() !== null;
}

// Il token di accesso corrente, o null. Da allegare come Bearer alle fetch che
// vogliono attribuire l'azione a un account.
export async function getAccessToken() {
  const c = client();
  if (!c) return null;
  const { data } = await c.auth.getSession();
  return data?.session?.access_token || null;
}

export async function getUser() {
  const c = client();
  if (!c) return null;
  const { data } = await c.auth.getUser();
  return data?.user || null;
}

export function onAuthChange(callback) {
  const c = client();
  if (!c) return () => {};
  const { data } = c.auth.onAuthStateChange((_event, session) => {
    callback(session?.user || null);
  });
  return () => data?.subscription?.unsubscribe();
}

export async function signInWithGoogle() {
  const c = client();
  if (!c) return;
  await c.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.href },
  });
}

export async function signOut() {
  const c = client();
  if (!c) return;
  await c.auth.signOut();
}
