// Console di monitoraggio della catena, in tempo reale.
//
// Sostituisce il ?token= e il full-reload ogni 60s: login Google ristretto (la
// vera guardia e' la RLS su Postgres, questo controllo lato client e' solo per
// il messaggio), poi lettura iniziale e sottoscrizione Realtime alle tabelle
// pipeline_activity e pipeline_tokens. Un tick appare senza refresh.
//
// Vanilla, nessun React: la console e' una tabella viva, non un'app.

import { createClient } from "@supabase/supabase-js";

const cfg = window.__supabase || null;
const adminEmail = (window.__monitorAdminEmail || "").toLowerCase();
const root = document.getElementById("monitor-root");

function h(html) {
  root.innerHTML = html;
}

if (!cfg || !cfg.url || !cfg.anonKey) {
  h('<p class="mon-msg">Console non configurata: mancano le identita' + " Supabase.</p>");
} else {
  boot(createClient(cfg.url, cfg.anonKey, { auth: { persistSession: true, detectSessionInUrl: true } }));
}

async function boot(supabase) {
  const { data: sessionData } = await supabase.auth.getSession();
  let user = sessionData?.session?.user || null;

  supabase.auth.onAuthStateChange((_e, session) => {
    const next = session?.user || null;
    const was = user?.id || null;
    user = next;
    if ((next?.id || null) !== was) render(supabase, user);
  });

  render(supabase, user);
}

function loginView(supabase) {
  h(
    '<div class="mon-gate">' +
      "<h1>Console catena</h1>" +
      "<p>Accesso riservato.</p>" +
      '<button id="mon-login" class="mon-btn">Accedi con Google</button>' +
      "</div>"
  );
  document.getElementById("mon-login").onclick = () =>
    supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: window.location.href } });
}

function deniedView(supabase, email) {
  h(
    '<div class="mon-gate">' +
      "<h1>Console catena</h1>" +
      "<p>L'account <strong>" + escapeHtml(email) + "</strong> non e' autorizzato.</p>" +
      '<button id="mon-logout" class="mon-btn">Esci</button>' +
      "</div>"
  );
  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();
}

async function render(supabase, currentUser) {
  // Ogni render riparte da zero: rimuovi eventuali canali gia' aperti, cosi' un
  // TOKEN_REFRESHED (che rida' lo stesso utente) non accumula sottoscrizioni ne'
  // duplica le refresh().
  supabase.removeAllChannels();

  if (!currentUser) return loginView(supabase);
  const email = (currentUser.email || "").toLowerCase();
  if (adminEmail && email !== adminEmail) return deniedView(supabase, email);

  h(
    '<div class="mon-live">' +
      '<div class="mon-head"><h1>Console catena</h1>' +
      '<span class="mon-dot" title="in ascolto"></span>' +
      '<button id="mon-logout" class="mon-btn mon-btn--ghost">Esci</button></div>' +
      '<section><h2>Battiti e PR</h2><div id="mon-activity" class="mon-table">Carico...</div></section>' +
      '<section><h2>Token per run</h2><div id="mon-tokens" class="mon-table">Carico...</div></section>' +
      "</div>"
  );
  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();

  await refresh(supabase);
  // Realtime: a ogni cambiamento sulle due tabelle, rileggi (le tabelle sono
  // piccole, una rilettura completa e' piu' semplice del merge incrementale).
  supabase
    .channel("pipeline")
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_activity" }, () => refresh(supabase))
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_tokens" }, () => refresh(supabase))
    .subscribe();
}

async function refresh(supabase) {
  const [{ data: activity }, { data: tokens }] = await Promise.all([
    supabase.from("pipeline_activity").select("*").order("updated_at", { ascending: false }),
    supabase.from("pipeline_tokens").select("*").order("updated_at", { ascending: false }),
  ]);
  renderActivity(activity || []);
  renderTokens(tokens || []);
}

function renderActivity(rows) {
  const el = document.getElementById("mon-activity");
  if (!el) return;
  if (!rows.length) return (el.innerHTML = '<p class="mon-empty">Nessun lavoro in volo.</p>');
  el.innerHTML =
    '<table><thead><tr><th>Tipo</th><th>Ruolo</th><th>Indicatore</th><th>PR</th><th>CI</th><th>Aggiornato</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          "<tr><td>" + escapeHtml(r.kind) + "</td><td>" + escapeHtml(r.role) + "</td><td>" +
          escapeHtml(r.indicator) + "</td><td>" + (r.pr ? "#" + r.pr : "") + "</td><td>" +
          escapeHtml(r.ci || "") + "</td><td>" + escapeHtml(r.updated_at) + "</td></tr>"
      )
      .join("") +
    "</tbody></table>";
}

function renderTokens(rows) {
  const el = document.getElementById("mon-tokens");
  if (!el) return;
  if (!rows.length) return (el.innerHTML = '<p class="mon-empty">Nessun consumo registrato.</p>');
  el.innerHTML =
    '<table><thead><tr><th>Run</th><th>Indicatore</th><th>Ruolo</th><th>Token</th><th>Aggiornato</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          "<tr><td>" + escapeHtml(r.run_id) + "</td><td>" + escapeHtml(r.indicator) + "</td><td>" +
          escapeHtml(r.role) + "</td><td>" + Number(r.tokens || 0).toLocaleString("it-IT") +
          "</td><td>" + escapeHtml(r.updated_at) + "</td></tr>"
      )
      .join("") +
    "</tbody></table>";
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
