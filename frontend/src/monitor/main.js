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
        '<div id="cat-legend"></div>' +
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
    // Un battito cambia gli in_flight: la board li fonde lato server, quindi
    // rifetchala oltre alle tabelle vive, o un indicatore appena avviato resterebbe
    // "in coda" nel catalogo fino a un Aggiorna manuale. La board e' memoizzata 30s
    // lato server, quindi rifetchare a ogni evento e' a buon mercato.
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_activity" }, () => {
      refresh(supabase);
      loadBoard(supabase);
    })
    // I token cambiano i totali della board (tokens_total) e la colonna token
    // della cronologia: rifetcha entrambe oltre alla tabella viva.
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_tokens" }, () => {
      refresh(supabase);
      loadBoard(supabase);
      loadRuns(supabase);
    })
    .subscribe();

  document.getElementById("cat-refresh").onclick = () => loadBoard(supabase);
  document.getElementById("run-refresh").onclick = () => loadRuns(supabase);
  ["cat-q", "cat-status", "cat-phase", "cat-owner"].forEach((id) => {
    document.getElementById(id).oninput = renderCatalogReset;
    document.getElementById(id).onchange = renderCatalogReset;
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

// Paginazione del catalogo: 383 indicatori in una tabella sola sono troppi.
// Pagina lato client, la pagina attiva in stato di modulo. Un cambio di filtro
// riparte da pagina 1 (renderCatalogReset); i bottoni pagina non azzerano.
let catPage = 0;
const CAT_PAGE_SIZE = 50;

function renderCatalogReset() {
  catPage = 0;
  renderCatalog();
}

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
  "da correggere",
  "bloccata",
  "in quarantena",
  "in lavorazione",
  "in coda",
  "proposta",
  "in attesa di monte",
  "da pubblicare",
  "pubblicata",
  "chiusa",
];

// La lavorazione parte dallo `state` autorevole del modello, che gia' antepone
// invalidazione e blocchi al pubblicato (una pagina pubblicata ma con una
// smentita aperta o dati scaduti e' `invalidata`, non `pubblicata`, e va corretta):
// leggere `published` per primo la nasconderebbe. L'unico affinamento e' spezzare
// l'`in-lavorazione` grezzo, che marca anche le centinaia mai toccate, in cio' che
// la pipeline lavora davvero (una run o un ruolo in volo) e cio' che e' solo in coda.
function workStatus(r) {
  switch (r.state) {
    case "pubblicata": return "pubblicata";
    case "fusa": return "da pubblicare";
    case "invalidata": return "da correggere";
    case "bloccata": return "bloccata";
    case "in-quarantena": return "in quarantena";
    case "chiusa": return "chiusa";
    case "proposta": return "proposta";
    case "in-attesa-di-monte": return "in attesa di monte";
    default: // in-lavorazione e ogni stato non previsto
      return (r.in_flight && r.in_flight.length) || (r.runs && r.runs.length) ? "in lavorazione" : "in coda";
  }
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

// Cosa vuol dire ogni lavorazione, in chiaro: finisce nel title del badge, cosi'
// "in attesa di monte" e simili non restano gergo. Testi da docs/EDITORIAL_PRACTICE.
const STATUS_HELP = {
  "in lavorazione": "La pipeline ci sta lavorando: una run in corso o gia' fatta.",
  "in coda": "Nel catalogo ma mai lavorato dalla pipeline (nessuna run).",
  "in attesa di monte": "Fermo perche' manca il passo a monte: l'artefatto atteso dallo stadio precedente (es. la curatela) non esiste ancora.",
  "da pubblicare": "Articolo fuso, in attesa della prova di pubblicazione sul sito.",
  "pubblicata": "Pubblicato sul sito, con prova registrata.",
  "da correggere": "Un input e' cambiato (dati aggiornati, definizione, o una smentita aperta): il lavoro a valle non vale piu' e va rifatto.",
  "bloccata": "Fermo in attesa di un cambio esterno (es. un chiarimento dalla fonte).",
  "in quarantena": "Bloccato in modo terminale, tolto dalla coda.",
  "proposta": "Candidato approvato, in attesa di essere promosso nel catalogo dal prossimo giro di ammissione (manca ancora curatela e articolo).",
  "chiusa": "Candidatura chiusa, nessuna azione.",
};

function renderCatalog() {
  const el = document.getElementById("mon-catalog");
  if (!el) return;
  if (!boardData) return (el.innerHTML = '<p class="mon-empty">Catalogo non disponibile (login o rete).</p>');
  const q = (document.getElementById("cat-q").value || "").trim().toLowerCase();
  const phase = document.getElementById("cat-phase").value;
  const status = document.getElementById("cat-status").value;
  const owner = document.getElementById("cat-owner").value;
  const allRows = boardData.rows || [];
  const rows = allRows.filter((r) => {
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

  // Contatori COMPLETI, sul catalogo intero, non sul solo filtro: restano stabili
  // mentre si filtra, cosi' "quanti pubblicati, quanti rimangono" si legge sempre.
  // Ogni pastiglia e' un filtro con un clic (toggle) sulla lavorazione; "pubblicata"
  // e' la scorciatoia per vedere solo i pubblicati. Il conteggio mostrato riflette
  // il filtro attuale, separato dai totali globali.
  const byStatusAll = {};
  allRows.forEach((r) => {
    const s = workStatus(r);
    byStatusAll[s] = (byStatusAll[s] || 0) + 1;
  });
  const published = byStatusAll["pubblicata"] || 0;
  const closed = byStatusAll["chiusa"] || 0;
  const remaining = allRows.length - published - closed;
  const summary =
    '<span class="mon-chip mon-chip--strong">Totale ' + allRows.length + "</span>" +
    '<span class="mon-chip mon-chip--strong">Pubblicati ' + published + "</span>" +
    '<span class="mon-chip mon-chip--strong">Rimanenti ' + remaining + "</span>" +
    (rows.length !== allRows.length ? '<span class="mon-chip">Mostrati ' + rows.length + "</span>" : "");
  const chips = STATUS_ORDER.filter((s) => byStatusAll[s])
    .map(
      (s) =>
        '<button type="button" class="mon-chip mon-chip--click' + (status === s ? " mon-chip--active" : "") +
        '" data-status="' + escapeHtml(s) + '">' + escapeHtml(s) + ": " + byStatusAll[s] + "</button>"
    )
    .join("");
  const totalsEl = document.getElementById("cat-totals");
  totalsEl.innerHTML =
    '<div class="mon-totals-row">' + summary + "</div>" +
    '<div class="mon-totals-row">' +
      '<button type="button" class="mon-chip mon-chip--click' + (!status ? " mon-chip--active" : "") + '" data-status="">tutti</button>' +
      chips +
    "</div>";
  // Clic su una pastiglia = imposta (o azzera) il filtro lavorazione, poi ridisegna
  // da pagina 1 (il filtro cambia, la pagina corrente non ha piu' senso).
  totalsEl.querySelectorAll(".mon-chip--click").forEach((btn) => {
    btn.onclick = () => {
      const sel = document.getElementById("cat-status");
      const target = btn.getAttribute("data-status");
      sel.value = sel.value === target ? "" : target; // ri-clic sull'attivo = azzera
      renderCatalogReset();
    };
  });

  // Legenda visibile degli stati presenti: il title del badge non arriva a chi usa
  // touch o tastiera (ne', sul layout a schede mobile, a nessuno). Un <details>
  // nativo e' focusabile, toccabile e leggibile dallo screen reader, e serve la
  // stessa domanda ("che vuol dire in attesa di monte?") a chiunque, sempre.
  const legendEl = document.getElementById("cat-legend");
  if (legendEl) {
    const items = STATUS_ORDER.filter((s) => byStatusAll[s])
      .map(
        (s) =>
          '<div class="mon-legend-row"><span class="mon-status mon-status--' + s.replace(/ /g, "-") + '">' +
          escapeHtml(s) + "</span><span>" + escapeHtml(STATUS_HELP[s] || "") + "</span></div>"
      )
      .join("");
    legendEl.innerHTML =
      '<details class="mon-legend"><summary>Cosa vuol dire ogni stato</summary>' + items + "</details>";
  }

  if (!rows.length) return (el.innerHTML = '<p class="mon-empty">Nessun indicatore col filtro attuale.</p>');

  // Pagina: clampa la pagina corrente all'intervallo valido (un filtro puo' averla
  // resa fuori range) e affetta le righe da mostrare.
  const totalPages = Math.max(1, Math.ceil(rows.length / CAT_PAGE_SIZE));
  if (catPage > totalPages - 1) catPage = totalPages - 1;
  if (catPage < 0) catPage = 0;
  const pageRows = rows.slice(catPage * CAT_PAGE_SIZE, catPage * CAT_PAGE_SIZE + CAT_PAGE_SIZE);
  const first = rows.length ? catPage * CAT_PAGE_SIZE + 1 : 0;
  const last = catPage * CAT_PAGE_SIZE + pageRows.length;
  const pager =
    '<div class="mon-pager">' +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" id="cat-prev"' + (catPage === 0 ? " disabled" : "") + ">Precedente</button>" +
      '<span class="mon-pager-info">' + first + "-" + last + " di " + rows.length + " · pagina " + (catPage + 1) + "/" + totalPages + "</span>" +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" id="cat-next"' + (catPage >= totalPages - 1 ? " disabled" : "") + ">Successiva</button>" +
    "</div>";

  el.innerHTML =
    pager +
    '<table class="mon-cards"><thead><tr><th>Indicatore</th><th>Famiglia</th><th>Lavorazione</th><th>Fase</th><th>Ciclo</th><th>Prossimo passo</th><th>Token</th><th>Articolo</th></tr></thead><tbody>' +
    pageRows
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
          '<tr><td data-label="Indicatore">' + name + "<br><small>" + escapeHtml(r.id) + "</small></td>" +
          '<td data-label="Famiglia">' + escapeHtml(r.family) + "</td>" +
          '<td data-label="Lavorazione"><span class="mon-status mon-status--' + st.replace(/ /g, "-") + '" title="' + escapeHtml(STATUS_HELP[st] || "") + '">' + escapeHtml(st) + "</span></td>" +
          '<td data-label="Fase">' + escapeHtml(r.phase) + "</td>" +
          '<td data-label="Ciclo" class="mon-mini">' + mini + "</td>" +
          '<td data-label="Prossimo passo">' + escapeHtml(ns.owner || "") + "<br><small>" + escapeHtml(ns.label || "") + "</small></td>" +
          '<td data-label="Token">' + (r.tokens_total != null ? Number(r.tokens_total).toLocaleString("it-IT") : "") + "</td>" +
          '<td data-label="Articolo">' + link + "</td></tr>"
        );
      })
      .join("") +
    "</tbody></table>" +
    pager; // pager anche in fondo: con 50 righe lo scroll e' lungo

  // Prev/Next compaiono due volte (sopra e sotto): querySelectorAll li prende
  // entrambi. Cambiano solo la pagina e ridisegnano, senza azzerarla.
  el.querySelectorAll("#cat-prev").forEach((b) => (b.onclick = () => { catPage -= 1; renderCatalog(); }));
  el.querySelectorAll("#cat-next").forEach((b) => (b.onclick = () => { catPage += 1; renderCatalog(); }));
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
    '<table class="mon-cards"><thead><tr><th>Quando</th><th>Stadio</th><th>Indicatore</th><th>Esito</th><th>Durata</th><th>Token</th><th>PR</th><th>Commit</th></tr></thead><tbody>' +
    runs
      .map((r) => {
        const inds = (r.indicators || []);
        const indCell = inds.length === 1 ? escapeHtml(inds[0]) : inds.length ? escapeHtml(inds.join(", ")) : "";
        return (
          '<tr><td data-label="Quando">' + escapeHtml((r.at || "").replace("T", " ").slice(0, 16)) + "</td>" +
          '<td data-label="Stadio">' + escapeHtml(r.stage) + "</td>" +
          '<td data-label="Indicatore" title="' + escapeHtml(r.summary || "") + '">' + indCell + "</td>" +
          '<td data-label="Esito">' + escapeHtml(r.outcome) + "</td>" +
          '<td data-label="Durata">' + escapeHtml(fmtDuration(r.duration_seconds)) + "</td>" +
          '<td data-label="Token">' + (r.tokens != null ? Number(r.tokens).toLocaleString("it-IT") : "") + "</td>" +
          '<td data-label="PR">' + (r.pr ? "#" + escapeHtml(String(r.pr)) : "") + "</td>" +
          '<td data-label="Commit">' + escapeHtml(r.commit || "") + "</td></tr>"
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
    '<table class="mon-cards"><thead><tr><th>Tipo</th><th>Ruolo</th><th>Indicatore</th><th>PR</th><th>CI</th><th>Aggiornato</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          '<tr><td data-label="Tipo">' + escapeHtml(r.kind) + '</td><td data-label="Ruolo">' + escapeHtml(r.role) + '</td><td data-label="Indicatore">' +
          escapeHtml(r.indicator) + '</td><td data-label="PR">' + (r.pr ? "#" + r.pr : "") + '</td><td data-label="CI">' +
          escapeHtml(r.ci || "") + '</td><td data-label="Aggiornato">' + escapeHtml(r.updated_at) + "</td></tr>"
      )
      .join("") +
    "</tbody></table>";
}

function renderTokens(rows) {
  const el = document.getElementById("mon-tokens");
  if (!el) return;
  if (!rows.length) return (el.innerHTML = '<p class="mon-empty">Nessun consumo registrato.</p>');
  el.innerHTML =
    '<table class="mon-cards"><thead><tr><th>Run</th><th>Indicatore</th><th>Ruolo</th><th>Token</th><th>Aggiornato</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          '<tr><td data-label="Run">' + escapeHtml(r.run_id) + '</td><td data-label="Indicatore">' + escapeHtml(r.indicator) + '</td><td data-label="Ruolo">' +
          escapeHtml(r.role) + '</td><td data-label="Token">' + Number(r.tokens || 0).toLocaleString("it-IT") +
          '</td><td data-label="Aggiornato">' + escapeHtml(r.updated_at) + "</td></tr>"
      )
      .join("") +
    "</tbody></table>";
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
