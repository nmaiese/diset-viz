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
      // Il vivo (push da Supabase Realtime): battiti dei ruoli in volo, token per run.
      '<section><h2>Battiti e PR</h2><div id="mon-activity" class="mon-table">Carico...</div></section>' +
      '<section><h2>Token per run</h2><div id="mon-tokens" class="mon-table">Carico...</div></section>' +
      // La storia (fetch authed dai file git via /_pipeline/api): catalogo e cronologia.
      "<section>" +
        '<div class="mon-head2"><h2>Catalogo indicatori</h2><button id="cat-refresh" class="mon-btn mon-btn--ghost mon-btn--sm">Aggiorna</button></div>' +
        '<div class="mon-filters">' +
          '<input id="cat-q" type="search" placeholder="Cerca nome, codice, stato, bandiera">' +
          '<select id="cat-status"><option value="">Tutte le lavorazioni</option></select>' +
          '<select id="cat-phase"><option value="">Tutte le fasi</option></select>' +
          '<select id="cat-owner"><option value="">Tutti i prossimi ruoli</option></select>' +
        "</div>" +
        '<div id="cat-totals" class="mon-totals"></div>' +
        '<div id="mon-catalog" class="mon-table">Carico...</div>' +
      "</section>" +
      "<section>" +
        '<div class="mon-head2"><h2>Cronologia azioni</h2><button id="run-refresh" class="mon-btn mon-btn--ghost mon-btn--sm">Aggiorna</button></div>' +
        '<div class="mon-filters">' +
          '<input id="run-q" type="search" placeholder="Cerca indicatore, summary, run">' +
          '<select id="run-stage"><option value="">Tutti gli stadi</option></select>' +
          '<select id="run-outcome"><option value="">Tutti gli esiti</option></select>' +
          '<label class="mon-date">da <input id="run-from" type="date"></label>' +
          '<label class="mon-date">a <input id="run-to" type="date"></label>' +
        "</div>" +
        '<div id="run-totals" class="mon-totals"></div>' +
        '<div id="mon-runs" class="mon-table">Carico...</div>' +
      "</section>" +
      "</div>"
  );
  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();

  await refresh(supabase);
  await loadHistory(supabase);
  // Realtime: a ogni cambiamento sulle due tabelle, rileggi il vivo (le tabelle
  // sono piccole, una rilettura completa e' piu' semplice del merge
  // incrementale). Catalogo e cronologia sono storia dai file git, non push:
  // fetch al caricamento e sul bottone Aggiorna, non a ogni tick.
  supabase
    .channel("pipeline")
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_activity" }, () => refresh(supabase))
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_tokens" }, () => refresh(supabase))
    .subscribe();

  document.getElementById("cat-refresh").onclick = () => loadBoard(supabase);
  document.getElementById("run-refresh").onclick = () => loadRuns(supabase);
  ["cat-q", "cat-status", "cat-phase", "cat-owner"].forEach((id) => {
    document.getElementById(id).oninput = renderCatalog;
    document.getElementById(id).onchange = renderCatalog;
  });
  ["run-q", "run-stage", "run-outcome", "run-from", "run-to"].forEach((id) => {
    document.getElementById(id).oninput = renderRuns;
    document.getElementById(id).onchange = renderRuns;
  });
}

// La storia authed. Il Bearer del login Google e' lo stesso confine mail-admin
// del backend; senza, i due endpoint fanno 404 (endpoint interno, non conferma
// di esistere). I due dati si tengono in modulo cosi' i filtri ridisegnano
// senza rifetchare.
let boardData = null;
let runsData = null;

async function getToken(supabase) {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token || null;
}

async function authedJson(supabase, path) {
  const token = await getToken(supabase);
  if (!token) return null;
  try {
    const r = await fetch(path, { headers: { Authorization: "Bearer " + token } });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function loadHistory(supabase) {
  await Promise.all([loadBoard(supabase), loadRuns(supabase)]);
}

async function loadBoard(supabase) {
  const data = await authedJson(supabase, "/_pipeline/api/board");
  boardData = data;
  const rows = (data && data.rows) || [];
  // La lavorazione, non lo stato grezzo del modello: STATUS_ORDER da' l'ordine.
  fillOptions("cat-status", STATUS_ORDER.filter((s) => rows.some((r) => workStatus(r) === s)));
  fillOptions("cat-phase", uniq(rows.map((r) => r.phase)));
  fillOptions("cat-owner", uniq(rows.map((r) => r.next_step && r.next_step.owner)));
  renderCatalog();
}

// La lavorazione come la intende chi guarda: "in lavorazione" e' solo cio' che la
// pipeline ha davvero toccato (una run, o un ruolo in volo). Lo stato grezzo del
// modello (`state`) marca "in-lavorazione" ogni indicatore non ancora pubblicato,
// comprese le centinaia mai lavorate (prosa legacy, zero run): qui si separano.
// Derivato lato console, senza toccare il modello condiviso con /_pipeline.
const STATUS_ORDER = [
  "in lavorazione",
  "in coda",
  "in attesa di monte",
  "da pubblicare",
  "pubblicata",
  "chiusa",
];

function workStatus(r) {
  if (r.published === true) return "pubblicata";
  if (r.state === "chiusa") return "chiusa";
  if (r.state === "fusa") return "da pubblicare";
  if (r.state === "in-attesa-di-monte") return "in attesa di monte";
  if ((r.in_flight && r.in_flight.length) || (r.runs && r.runs.length)) return "in lavorazione";
  return "in coda";
}

async function loadRuns(supabase) {
  const data = await authedJson(supabase, "/_pipeline/api/runs");
  runsData = data;
  const runs = (data && data.runs) || [];
  fillOptions("run-stage", uniq(runs.map((r) => r.stage)));
  fillOptions("run-outcome", uniq(runs.map((r) => r.outcome)));
  renderRuns();
}

function uniq(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => String(a).localeCompare(String(b), "it"));
}

function fillOptions(id, values) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const keep = sel.value;
  const first = sel.options[0]; // "Tutte/Tutti ..."
  sel.innerHTML = "";
  sel.appendChild(first);
  values.forEach((v) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  });
  sel.value = keep;
}

const MINI_STATUS = { done: "●", current: "◐", issue: "◆", off: "○", waiting: "○" };

function renderCatalog() {
  const el = document.getElementById("mon-catalog");
  if (!el) return;
  if (!boardData) return (el.innerHTML = '<p class="mon-empty">Catalogo non disponibile (login o rete).</p>');
  const q = (document.getElementById("cat-q").value || "").trim().toLowerCase();
  const phase = document.getElementById("cat-phase").value;
  const status = document.getElementById("cat-status").value;
  const owner = document.getElementById("cat-owner").value;
  const rows = (boardData.rows || []).filter((r) => {
    const ns = r.next_step || {};
    const st = workStatus(r);
    const key = [r.id, r.name, r.family, r.state, st, r.phase, ns.owner, ns.label, (r.flags || []).join(" ")]
      .join(" ")
      .toLowerCase();
    return (
      (!q || key.indexOf(q) !== -1) &&
      (!phase || r.phase === phase) &&
      (!status || st === status) &&
      (!owner || (ns.owner || "") === owner)
    );
  });

  // Totali per lavorazione, nell'ordine di STATUS_ORDER: e' la riga che risponde
  // a "perche' sono tutti in lavorazione", separando la coda da cio' che si lavora.
  const byStatus = {};
  rows.forEach((r) => {
    const s = workStatus(r);
    byStatus[s] = (byStatus[s] || 0) + 1;
  });
  document.getElementById("cat-totals").innerHTML =
    '<span class="mon-chip">' + rows.length + " indicatori</span>" +
    STATUS_ORDER.filter((s) => byStatus[s])
      .map((s) => '<span class="mon-chip">' + escapeHtml(s) + ": " + byStatus[s] + "</span>")
      .join("");

  if (!rows.length) return (el.innerHTML = '<p class="mon-empty">Nessun indicatore col filtro attuale.</p>');
  el.innerHTML =
    "<table><thead><tr><th>Indicatore</th><th>Famiglia</th><th>Lavorazione</th><th>Fase</th><th>Ciclo</th><th>Prossimo passo</th><th>Token</th><th>Articolo</th></tr></thead><tbody>" +
    rows
      .map((r) => {
        const ns = r.next_step || {};
        const st = workStatus(r);
        const link = r.published_url
          ? '<a href="' + escapeHtml(r.published_url) + '" target="_blank" rel="noopener">apri ' + String.fromCharCode(8599) + "</a>"
          : "";
        const name = r.published_url
          ? '<a href="' + escapeHtml(r.published_url) + '" target="_blank" rel="noopener">' + escapeHtml(r.name) + "</a>"
          : escapeHtml(r.name);
        const mini = (r.lifecycle || [])
          .map((p) => '<span title="' + escapeHtml(p.label) + " (" + escapeHtml(p.status) + ')">' + (MINI_STATUS[p.status] || "○") + "</span>")
          .join(" ");
        return (
          "<tr><td>" + name + "<br><small>" + escapeHtml(r.id) + "</small></td>" +
          "<td>" + escapeHtml(r.family) + "</td>" +
          '<td><span class="mon-status mon-status--' + st.replace(/ /g, "-") + '">' + escapeHtml(st) + "</span></td>" +
          "<td>" + escapeHtml(r.phase) + "</td>" +
          '<td class="mon-mini">' + mini + "</td>" +
          "<td>" + escapeHtml(ns.owner || "") + "<br><small>" + escapeHtml(ns.label || "") + "</small></td>" +
          "<td>" + (r.tokens_total != null ? Number(r.tokens_total).toLocaleString("it-IT") : "") + "</td>" +
          "<td>" + link + "</td></tr>"
        );
      })
      .join("") +
    "</tbody></table>";
}

function fmtDuration(sec) {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m ? m + "m " + s + "s" : s + "s";
}

function renderRuns() {
  const el = document.getElementById("mon-runs");
  if (!el) return;
  if (!runsData) return (el.innerHTML = '<p class="mon-empty">Cronologia non disponibile (login o rete).</p>');
  const q = (document.getElementById("run-q").value || "").trim().toLowerCase();
  const stage = document.getElementById("run-stage").value;
  const outcome = document.getElementById("run-outcome").value;
  const from = document.getElementById("run-from").value; // YYYY-MM-DD o ""
  const to = document.getElementById("run-to").value;
  const runs = (runsData.runs || []).filter((r) => {
    const day = (r.at || "").slice(0, 10);
    const key = [(r.indicators || []).join(" "), r.summary, r.run_id, r.stage].join(" ").toLowerCase();
    return (
      (!q || key.indexOf(q) !== -1) &&
      (!stage || r.stage === stage) &&
      (!outcome || r.outcome === outcome) &&
      (!from || day >= from) &&
      (!to || day <= to)
    );
  });

  // Totali sul sottoinsieme filtrato: token totali, conteggio, per esito e per stadio.
  const tokTotal = runs.reduce((a, r) => a + (r.tokens || 0), 0);
  const byOutcome = {};
  const byStage = {};
  runs.forEach((r) => {
    byOutcome[r.outcome] = (byOutcome[r.outcome] || 0) + 1;
    byStage[r.stage] = (byStage[r.stage] || 0) + (r.tokens || 0);
  });
  document.getElementById("run-totals").innerHTML =
    '<span class="mon-chip">' + runs.length + " run</span>" +
    '<span class="mon-chip">' + tokTotal.toLocaleString("it-IT") + " token</span>" +
    Object.keys(byOutcome)
      .sort()
      .map((o) => '<span class="mon-chip">' + escapeHtml(o) + ": " + byOutcome[o] + "</span>")
      .join("") +
    Object.keys(byStage)
      .filter((s) => byStage[s] > 0)
      .sort()
      .map((s) => '<span class="mon-chip">' + escapeHtml(s) + ": " + byStage[s].toLocaleString("it-IT") + "</span>")
      .join("");

  if (!runs.length) return (el.innerHTML = '<p class="mon-empty">Nessuna run col filtro attuale.</p>');
  el.innerHTML =
    "<table><thead><tr><th>Quando</th><th>Stadio</th><th>Indicatore</th><th>Esito</th><th>Durata</th><th>Token</th><th>PR</th><th>Commit</th></tr></thead><tbody>" +
    runs
      .map((r) => {
        const inds = (r.indicators || []);
        const indCell = inds.length === 1 ? escapeHtml(inds[0]) : inds.length ? escapeHtml(inds.join(", ")) : "";
        return (
          "<tr><td>" + escapeHtml((r.at || "").replace("T", " ").slice(0, 16)) + "</td>" +
          "<td>" + escapeHtml(r.stage) + "</td>" +
          '<td title="' + escapeHtml(r.summary || "") + '">' + indCell + "</td>" +
          "<td>" + escapeHtml(r.outcome) + "</td>" +
          "<td>" + escapeHtml(fmtDuration(r.duration_seconds)) + "</td>" +
          "<td>" + (r.tokens != null ? Number(r.tokens).toLocaleString("it-IT") : "") + "</td>" +
          "<td>" + (r.pr ? "#" + escapeHtml(String(r.pr)) : "") + "</td>" +
          "<td>" + escapeHtml(r.commit || "") + "</td></tr>"
        );
      })
      .join("") +
    "</tbody></table>";
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
