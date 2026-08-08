// La console della catena: tre orizzonti, due punti di vista, una pagina.
//
// Una run adesso è **un workflow** con dentro N agenti, non un indicatore che
// attraversa stadi. La console lo mostra così:
//
//   ADESSO        che sta girando ora, in push da Supabase Realtime;
//   Run           una riga per workflow, apribile sui suoi agenti;
//   Indicatori    lo stesso fatto per indicatore: che cosa è stato scritto o
//                 riscritto, con quale tesi, e se ha coperto una pagina che
//                 esisteva.
//
// Le due viste sono due bottoni e non due rotte: sono lo stesso stato guardato
// da due lati, e un clic passa dall'uno all'altro portandosi dietro il filtro.
//
// Vanilla, nessun React: è una tabella viva, non un'app.

import { createClient } from "@supabase/supabase-js";

const cfg = window.__supabase || null;
const adminEmail = (window.__monitorAdminEmail || "").toLowerCase();
const root = document.getElementById("monitor-root");

// Le cinque fasi della catena, nell'ordine in cui girano. Serve alla spina
// dorsale di ADESSO, che deve mostrare anche le fasi non ancora arrivate: senza
// quelle si vedrebbe il passato e non a che punto è la run.
const FASI = ["Dossier", "Contesto", "Scrittura", "Verifica", "Pubblicazione"];

// Stato di modulo: i dati fetchati e i filtri, così un cambio di filtro
// ridisegna senza rifetchare.
let runsData = null;
let indicatoriData = null;
let vista = "run";
let pagina = 0;
const PAGINA = 25;
const aperte = new Set();

function h(html) {
  root.innerHTML = html;
}

if (!cfg || !cfg.url || !cfg.anonKey) {
  h('<p class="mon-msg">Console non configurata: mancano le identità Supabase.</p>');
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
      "<p>L'account <strong>" + escapeHtml(email) + "</strong> non è autorizzato.</p>" +
      '<button id="mon-logout" class="mon-btn">Esci</button>' +
      "</div>"
  );
  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();
}

async function render(supabase, currentUser) {
  // Ogni render riparte da zero: rimuovi i canali già aperti, così un
  // TOKEN_REFRESHED (che ridà lo stesso utente) non accumula sottoscrizioni.
  supabase.removeAllChannels();

  if (!currentUser) return loginView(supabase);
  const email = (currentUser.email || "").toLowerCase();
  if (adminEmail && email !== adminEmail) return deniedView(supabase, email);

  leggiHash();

  h(
    '<div class="mon-head"><h1>Console catena</h1>' +
      '<span class="mon-dot" title="in ascolto"></span>' +
      '<button id="mon-logout" class="mon-btn mon-btn--ghost mon-btn--sm">Esci</button></div>' +

      '<h2>Adesso</h2><div id="mon-adesso"><p class="mon-empty">Carico...</p></div>' +

      '<div class="mon-tabs" role="tablist">' +
        '<button class="mon-tab" id="tab-run" role="tab">Run</button>' +
        '<button class="mon-tab" id="tab-ind" role="tab">Indicatori</button>' +
      "</div>" +
      '<div class="mon-filters">' +
        '<input id="f-q" type="search" placeholder="Cerca indicatore, run, tesi, agente">' +
        '<select id="f-esito"><option value="">Tutti gli esiti</option></select>' +
        '<label class="mon-date">da <input id="f-da" type="date"></label>' +
        '<label class="mon-date">a <input id="f-a" type="date"></label>' +
        '<button id="f-aggiorna" class="mon-btn mon-btn--ghost mon-btn--sm">Aggiorna</button>' +
      "</div>" +
      '<div id="mon-totali" class="mon-totals-row"></div>' +
      '<details class="mon-nota"><summary>Perché il costo è un pavimento</summary>' +
        "<p>Il costo si misura leggendo i trascritti, e un trascritto può essere " +
        "incompleto: in una run reale un agente ha registrato due token di output " +
        "sulla richiesta che restituiva una bozza intera. La misura è fedele a " +
        "quello che il trascritto dice, quindi ogni totale è un minimo e non una " +
        "cifra esatta.</p></details>" +
      '<div id="mon-lista" class="mon-table"><p class="mon-empty">Carico...</p></div>'
  );

  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();
  document.getElementById("tab-run").onclick = () => cambiaVista("run");
  document.getElementById("tab-ind").onclick = () => cambiaVista("indicatori");
  document.getElementById("f-aggiorna").onclick = () => carica(supabase);
  ["f-q", "f-esito", "f-da", "f-a"].forEach((id) => {
    const el = document.getElementById(id);
    el.oninput = () => { pagina = 0; disegna(); };
    el.onchange = () => { pagina = 0; disegna(); };
  });
  window.addEventListener("hashchange", () => { leggiHash(); disegna(); });

  await carica(supabase);

  // Realtime: a ogni cambiamento sulle due tabelle si rilegge tutto. Le tabelle
  // sono piccole e la rilettura completa è più semplice (e meno fragile) di un
  // merge incrementale, che dovrebbe conoscere quale delle due sorgenti ha
  // scritto quale colonna.
  supabase
    .channel("cruscotto")
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_run" }, () => carica(supabase))
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_agente" }, () => carica(supabase))
    .subscribe();
}

// --- dati ------------------------------------------------------------------

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

async function carica(supabase) {
  const [runs, indicatori] = await Promise.all([
    authedJson(supabase, "/_pipeline/api/runs"),
    authedJson(supabase, "/_pipeline/api/indicatori"),
  ]);
  runsData = runs;
  indicatoriData = indicatori;
  disegna();
}

// --- navigazione -----------------------------------------------------------

function leggiHash() {
  const hash = (window.location.hash || "").replace(/^#/, "");
  // `chiave` e non `valore`: `valore()` e' la funzione che legge i filtri, e
  // ombreggiarla qui dentro sarebbe una trappola per chi tocca questa funzione.
  const [nome, chiave] = hash.split("/");
  if (nome === "indicatori") vista = "indicatori";
  else if (nome === "run") vista = "run";
  if (chiave) aperte.add(decodeURIComponent(chiave));
}

function cambiaVista(prossima) {
  vista = prossima;
  pagina = 0;
  window.location.hash = prossima;
  disegna();
}

// Un clic su un indicatore dalla vista Run porta alla sua storia, e viceversa:
// le due viste sono lo stesso fatto, non due destinazioni separate.
function vaiA(prossima, chiave, filtro) {
  vista = prossima;
  pagina = 0;
  aperte.add(chiave);
  const q = document.getElementById("f-q");
  if (q && filtro != null) q.value = filtro;
  window.location.hash = prossima + "/" + encodeURIComponent(chiave);
  disegna();
}

// --- disegno ---------------------------------------------------------------

function disegna() {
  disegnaAdesso();
  const tabRun = document.getElementById("tab-run");
  const tabInd = document.getElementById("tab-ind");
  if (tabRun) tabRun.setAttribute("aria-selected", String(vista === "run"));
  if (tabInd) tabInd.setAttribute("aria-selected", String(vista === "indicatori"));
  if (vista === "run") disegnaRun();
  else disegnaIndicatori();
}

function disegnaAdesso() {
  const el = document.getElementById("mon-adesso");
  if (!el) return;
  const runs = (runsData && runsData.runs) || [];
  if (!runs.length) {
    el.innerHTML = '<p class="mon-empty">Nessuna run registrata.</p>';
    return;
  }
  const volo = runs.filter((r) => r.in_volo);
  if (!volo.length) {
    const ultima = runs[0];
    el.innerHTML =
      '<div class="mon-adesso mon-adesso--ferma">' +
        '<div class="mon-adesso-testa"><strong>Nessuna run in volo</strong>' +
        "<span>ultima " + escapeHtml(quando(ultima.avviata_il)) + " · " +
        escapeHtml(ultima.workflow || ultima.run_id) + " · " +
        badgeEsitoRun(ultima) + "</span></div></div>";
    return;
  }
  el.innerHTML = volo.map(cardVolo).join("");
}

function cardVolo(run) {
  const agenti = run.agenti || [];
  const aperto = agenti.filter((a) => a.stato_vivo === "aperto");
  const spina = FASI.map((fase) => {
    const dentro = agenti.filter((a) => a.fase === fase);
    const pallini = dentro.length
      ? dentro.map((a) => '<span class="' + (a.stato_vivo === "aperto" ? "aperto" : "fatto") + '">' +
          (a.stato_vivo === "aperto" ? "◐" : "●") + "</span>").join("")
      : '<span class="attesa">○</span>';
    const corrente = dentro.some((a) => a.stato_vivo === "aperto");
    return '<div class="mon-fase' + (corrente ? " mon-fase--corrente" : "") + '">' +
      '<span class="mon-fase-nome">' + escapeHtml(fase) + "</span>" +
      '<span class="mon-pallini">' + pallini + "</span></div>";
  }).join("");
  const codici = uniq(agenti.map((a) => a.indicatore));
  return (
    '<div class="mon-adesso">' +
      '<div class="mon-adesso-testa">' +
        // Il nome del workflow arriva col consuntivo: mentre gira si mostra
        // quello che si sa davvero, cioe' la run e i suoi indicatori.
        "<strong>" + escapeHtml(run.workflow || "Run in corso") + "</strong>" +
        "<span>" + escapeHtml(codici.join(", ") || "indicatore non ancora noto") + "</span>" +
        "<span>da " + escapeHtml(durataDa(run.avviata_il)) + "</span>" +
        "<span>" + escapeHtml(run.run_id) + "</span>" +
      "</div>" +
      '<div class="mon-spina">' + spina + "</div>" +
      (aperto.length
        ? '<div class="mon-aperto">aperto ' + aperto.map((a) =>
            "<strong>" + escapeHtml(a.label || a.agent_type || a.agent_id) + "</strong> " +
            escapeHtml(a.agent_type) + (a.modello ? " · " + escapeHtml(a.modello) : "") +
            " · da " + escapeHtml(durataDa(a.avviato_il))).join(" &middot; ") + "</div>"
        : '<div class="mon-aperto">nessun agente aperto in questo momento</div>') +
    "</div>"
  );
}

// --- vista Run -------------------------------------------------------------

function disegnaRun() {
  const el = document.getElementById("mon-lista");
  if (!el) return;
  if (!runsData) return (el.innerHTML = '<p class="mon-empty">Run non disponibili (login o rete).</p>');
  const tutte = runsData.runs || [];
  opzioni("f-esito", uniq(tutte.map((r) => etichettaEsitoRun(r))));
  const righe = tutte.filter((r) => passaFiltro(chiaveRun(r), r.avviata_il, etichettaEsitoRun(r)));

  totali([
    ['<span class="mon-chip mon-chip--strong">' + righe.length + " run</span>"],
    ['<span class="mon-chip">' + somma(righe, "agenti") + " agenti</span>"],
    ['<span class="mon-chip">' + somma(righe, "turni") + " turni</span>"],
    ['<span class="mon-chip">' + euro(righe.reduce((a, r) => a + (r.costo || 0), 0)) + " pavimento</span>"],
  ]);

  if (!righe.length) return (el.innerHTML = '<p class="mon-empty">Nessuna run col filtro attuale.</p>');
  const { fetta, pager } = impagina(righe);

  el.innerHTML =
    pager +
    '<table class="mon-cards"><thead><tr>' +
      "<th>Quando</th><th>Workflow</th><th>Indicatore</th><th>Esito</th>" +
      '<th class="mon-num">Durata</th><th class="mon-num">Agenti</th>' +
      '<th class="mon-num">Turni</th><th class="mon-num">Costo</th>' +
    "</tr></thead><tbody>" +
    fetta.map(rigaRun).join("") +
    "</tbody></table>" +
    pager;

  collega(el);
}

function rigaRun(run) {
  const codici = uniq((run.agenti || []).map((a) => a.indicatore));
  const apri = aperte.has(run.run_id);
  const riga =
    '<tr class="mon-riga' + (apri ? " mon-aperta" : "") + '" data-chiave="' + escapeHtml(run.run_id) + '">' +
      '<td data-label="Quando">' + escapeHtml(quando(run.avviata_il)) + "<small>" + escapeHtml(run.run_id) + "</small></td>" +
      '<td data-label="Workflow">' + escapeHtml(run.workflow || "") + "</td>" +
      '<td data-label="Indicatore">' + (codici.length
        ? codici.map((c) => '<button type="button" class="mon-link" data-vai="' + escapeHtml(c) + '">' + escapeHtml(c) + "</button>").join(", ")
        : "") + "</td>" +
      '<td data-label="Esito">' + badgeEsitoRun(run) + "</td>" +
      '<td data-label="Durata" class="mon-num">' + escapeHtml(durata(run.durata_ms)) + "</td>" +
      '<td data-label="Agenti" class="mon-num">' + (run.agenti != null ? run.agenti : (run.agenti_visti || "")) + "</td>" +
      '<td data-label="Turni" class="mon-num">' + (run.turni != null ? run.turni : "") + "</td>" +
      '<td data-label="Costo" class="mon-num">' + (run.costo != null ? euro(run.costo) : "") + "</td>" +
    "</tr>";
  return apri ? riga + '<tr><td class="mon-dettaglio" colspan="8">' + dettaglioRun(run) + "</td></tr>" : riga;
}

function dettaglioRun(run) {
  const agenti = (run.agenti || []).slice().sort((a, b) => (a.avviato_il || "").localeCompare(b.avviato_il || ""));
  const tabella =
    '<table class="mon-agenti"><thead><tr>' +
      "<th>Agente</th><th>Fase</th><th>Tipo</th><th>Modello</th><th>Stato</th>" +
      '<th class="mon-num">Turni</th><th class="mon-num">Tool</th>' +
      '<th class="mon-num">Cache letta</th><th class="mon-num">Output</th><th class="mon-num">Costo</th>' +
    "</tr></thead><tbody>" +
    agenti.map((a) =>
      "<tr>" +
        '<td class="mon-label">' + escapeHtml(a.label || a.agent_id) +
          (a.indicatore ? "<small>" + escapeHtml(a.indicatore) + "</small>" : "") + "</td>" +
        "<td>" + escapeHtml(a.fase || "") +
          (a.fase_stimata && a.fase ? ' <span class="mon-stimata">stimata</span>' : "") + "</td>" +
        "<td>" + escapeHtml(a.agent_type || "") + "</td>" +
        "<td>" + escapeHtml(a.modello || "") + "</td>" +
        "<td>" + escapeHtml(a.stato || a.stato_vivo || "") + "</td>" +
        '<td class="mon-num">' + (a.turni != null ? a.turni : "") + "</td>" +
        '<td class="mon-num">' + (a.tool != null ? a.tool : "") + "</td>" +
        '<td class="mon-num">' + numero(a.token && a.token.cache_r) + "</td>" +
        '<td class="mon-num">' + numero(a.token && a.token.out) + "</td>" +
        '<td class="mon-num">' + (a.costo != null ? euro(a.costo) : "") + "</td>" +
      "</tr>" +
      (a.risultato != null
        ? '<tr><td colspan="10"><details class="mon-json"><summary>che cosa ha restituito ' +
          escapeHtml(a.label || a.agent_id) + "</summary><pre>" +
          escapeHtml(JSON.stringify(a.risultato, null, 1)) + "</pre></details></td></tr>"
        : "")
    ).join("") +
    "</tbody></table>";
  const logs = (run.logs || []).length
    ? '<details class="mon-json"><summary>' + run.logs.length + " righe di log del workflow</summary><ul class=\"mon-elenco\">" +
      run.logs.map((l) => "<li>" + escapeHtml(l) + "</li>").join("") + "</ul></details>"
    : "";
  const esito = run.esito != null
    ? '<details class="mon-json"><summary>esito della run</summary><pre>' +
      escapeHtml(JSON.stringify(run.esito, null, 1)) + "</pre></details>"
    : "";
  return tabella + logs + esito;
}

// --- vista Indicatori ------------------------------------------------------

function disegnaIndicatori() {
  const el = document.getElementById("mon-lista");
  if (!el) return;
  if (!indicatoriData) return (el.innerHTML = '<p class="mon-empty">Indicatori non disponibili (login o rete).</p>');
  const tutti = indicatoriData.indicatori || [];
  opzioni("f-esito", uniq(tutti.map((r) => r.esito)));
  const righe = tutti.filter((r) => passaFiltro(chiaveIndicatore(r), r.at, r.esito));

  const riscritti = righe.filter((r) => r.sovrascritto).length;
  totali([
    ['<span class="mon-chip mon-chip--strong">' + righe.length + " scritture</span>"],
    ['<span class="mon-chip">' + righe.filter((r) => r.scritto).length + " arrivate a pagina</span>"],
    ['<span class="mon-chip">' + riscritti + " hanno sovrascritto</span>"],
    ['<span class="mon-chip">' + righe.filter((r) => r.esito === "fermato").length + " fermate</span>"],
  ]);

  if (!righe.length) return (el.innerHTML = '<p class="mon-empty">Nessuna scrittura col filtro attuale.</p>');
  const { fetta, pager } = impagina(righe);

  el.innerHTML =
    pager +
    '<table class="mon-cards"><thead><tr>' +
      "<th>Indicatore</th><th>Quando</th><th>Esito</th><th>Tesi</th>" +
      '<th class="mon-num">Parole</th><th class="mon-num">Giri</th>' +
      '<th class="mon-num">Rilievi</th><th>Sovrascritto</th>' +
    "</tr></thead><tbody>" +
    fetta.map(rigaIndicatore).join("") +
    "</tbody></table>" +
    pager;

  collega(el);
}

function chiaveRiga(r) {
  return r.indicatore + "@" + r.run_id;
}

function rigaIndicatore(r) {
  const apri = aperte.has(chiaveRiga(r));
  const nome = r.published_url
    ? '<a href="' + escapeHtml(r.published_url) + '" target="_blank" rel="noopener">' + escapeHtml(r.indicatore) + " &#8599;</a>"
    : escapeHtml(r.indicatore);
  const riga =
    '<tr class="mon-riga' + (apri ? " mon-aperta" : "") + '" data-chiave="' + escapeHtml(chiaveRiga(r)) + '">' +
      '<td data-label="Indicatore">' + nome + "</td>" +
      '<td data-label="Quando">' + escapeHtml(quando(r.at)) +
        '<small><button type="button" class="mon-link" data-vai-run="' + escapeHtml(r.run_id) + '">' +
        escapeHtml(r.run_id) + "</button></small></td>" +
      '<td data-label="Esito">' + badgeEsito(r.esito) +
        (r.motivo ? "<small>" + escapeHtml(r.motivo) + "</small>" : "") + "</td>" +
      '<td data-label="Tesi">' + escapeHtml(taglia(r.angolo, 90)) + "</td>" +
      '<td data-label="Parole" class="mon-num">' + (r.parole != null ? r.parole : "") + "</td>" +
      '<td data-label="Giri" class="mon-num">' + (r.giri_di_correzione != null ? r.giri_di_correzione : "") + "</td>" +
      '<td data-label="Rilievi" class="mon-num">' + ((r.rilievi_aperti || []).length || "") + "</td>" +
      '<td data-label="Sovrascritto">' + (r.sovrascritto
        ? '<span class="mon-sovra">sì' + (r.vintage_precedente != null
            ? "<small>copriva il " + escapeHtml(String(r.vintage_precedente)) + "</small>" : "") + "</span>"
        : (r.sovrascritto === false ? "no" : "")) + "</td>" +
    "</tr>";
  return apri ? riga + '<tr><td class="mon-dettaglio" colspan="8">' + dettaglioIndicatore(r) + "</td></tr>" : riga;
}

function dettaglioIndicatore(r) {
  const pezzi = [];
  if (r.angolo) pezzi.push("<p><strong>Tesi</strong>: " + escapeHtml(r.angolo) + "</p>");
  if ((r.impaginazione || []).length) {
    pezzi.push("<p><strong>Come la vede un lettore</strong></p><ul class=\"mon-elenco\">" +
      r.impaginazione.map((s) => "<li>" + escapeHtml((s.role || "") + ": " + (s.h2 || "")) +
        (s.scritta === false ? " (persa)" : "") + "</li>").join("") + "</ul>");
  }
  if ((r.rilievi_aperti || []).length) {
    pezzi.push("<p><strong>Rilievi aperti, usciti col pezzo</strong></p><ul class=\"mon-elenco\">" +
      r.rilievi_aperti.map((s) => "<li>" + escapeHtml(
        typeof s === "string" ? s
          : [s.gravita || "senza gravità", s.tipo, s.dove, s.cosa_dice_il_testo].filter(Boolean).join(" | ")
      ) + "</li>").join("") + "</ul>");
  }
  if ((r.rilievi || []).length) {
    pezzi.push("<p><strong>Rilievi del lint</strong></p><ul class=\"mon-elenco\">" +
      r.rilievi.map((s) => "<li>" + escapeHtml([s.severity, s.rule, s.detail].filter(Boolean).join(" · ")) + "</li>").join("") +
      "</ul>");
  }
  const dettagli = [
    r.cifre_verificate != null ? r.cifre_verificate + " cifre verificate" : null,
    r.percorso ? "scritto in " + r.percorso : null,
    r.costo != null ? euro(r.costo) + " la run (pavimento)" : null,
  ].filter(Boolean);
  if (dettagli.length) pezzi.push("<p>" + escapeHtml(dettagli.join(" · ")) + "</p>");
  return pezzi.join("") || '<p class="mon-empty">Nessun dettaglio registrato.</p>';
}

// --- pezzi comuni ----------------------------------------------------------

function collega(el) {
  el.querySelectorAll("[data-passo]").forEach((b) => {
    b.onclick = () => { pagina += Number(b.getAttribute("data-passo")); disegna(); };
  });
  el.querySelectorAll("tr.mon-riga").forEach((tr) => {
    tr.onclick = (ev) => {
      const vai = ev.target.closest("[data-vai]");
      if (vai) {
        ev.stopPropagation();
        const codice = vai.getAttribute("data-vai");
        return vaiA("indicatori", codice, codice);
      }
      const vaiRun = ev.target.closest("[data-vai-run]");
      if (vaiRun) {
        ev.stopPropagation();
        const runId = vaiRun.getAttribute("data-vai-run");
        return vaiA("run", runId, runId);
      }
      if (ev.target.closest("a, details, summary")) return;
      const chiave = tr.getAttribute("data-chiave");
      if (aperte.has(chiave)) aperte.delete(chiave);
      else aperte.add(chiave);
      disegna();
    };
  });
}

function impagina(righe) {
  const pagine = Math.max(1, Math.ceil(righe.length / PAGINA));
  if (pagina > pagine - 1) pagina = pagine - 1;
  if (pagina < 0) pagina = 0;
  const fetta = righe.slice(pagina * PAGINA, pagina * PAGINA + PAGINA);
  if (pagine === 1) return { fetta, pager: "" };
  // I bottoni li aggancia `collega()`, dopo che l'HTML e' finito nel DOM: qui si
  // costruisce solo il markup.
  const pager =
    '<div class="mon-pager">' +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" data-passo="-1"' + (pagina === 0 ? " disabled" : "") + ">Precedente</button>" +
      '<span class="mon-pager-info">pagina ' + (pagina + 1) + "/" + pagine + " · " + righe.length + " righe</span>" +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" data-passo="1"' + (pagina >= pagine - 1 ? " disabled" : "") + ">Successiva</button>" +
    "</div>";
  return { fetta, pager };
}

function passaFiltro(chiave, quandoIso, esito) {
  const q = (valore("f-q") || "").trim().toLowerCase();
  const filtroEsito = valore("f-esito");
  const da = valore("f-da");
  const a = valore("f-a");
  const giorno = (quandoIso || "").slice(0, 10);
  return (
    (!q || chiave.toLowerCase().indexOf(q) !== -1) &&
    (!filtroEsito || esito === filtroEsito) &&
    (!da || giorno >= da) &&
    (!a || giorno <= a)
  );
}

function chiaveRun(r) {
  return [r.run_id, r.workflow, (r.agenti || []).map((a) => a.indicatore + " " + (a.label || "") + " " + a.agent_type).join(" ")].join(" ");
}

function chiaveIndicatore(r) {
  return [r.indicatore, r.run_id, r.angolo, r.motivo, r.esito].filter(Boolean).join(" ");
}

// I quattro esiti reali della catena, tenuti distinti perché lo sono: un
// articolo fermato prima del disco è la verifica che ha funzionato, e non va
// letto come un guasto.
function etichettaEsitoRun(run) {
  if (run.in_volo) return "in volo";
  if (run.stato && run.stato !== "completed") return "guasto";
  const esito = run.esito || {};
  if ((esito.fermati || []).length && !(esito.articoli || []).length) return "fermato";
  const rilievi = (esito.articoli || []).some((a) => (a.rilievi_aperti || []).length);
  if ((esito.articoli || []).length) return rilievi ? "scritto con rilievi" : "scritto";
  return run.stato === "completed" ? "senza articoli" : "guasto";
}

const CLASSE_ESITO = {
  "scritto": "scritto",
  "scritto con rilievi": "rilievi",
  "fermato": "fermato",
  "guasto": "guasto",
  "in volo": "volo",
};

function badgeEsitoRun(run) {
  return badgeEsito(etichettaEsitoRun(run));
}

function badgeEsito(etichetta) {
  const classe = CLASSE_ESITO[etichetta] || "";
  return '<span class="mon-esito' + (classe ? " mon-esito--" + classe : "") + '">' + escapeHtml(etichetta || "") + "</span>";
}

function totali(pezzi) {
  const el = document.getElementById("mon-totali");
  if (el) el.innerHTML = pezzi.flat().join("");
}

function opzioni(id, valori) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const tieni = sel.value;
  const primo = sel.options[0];
  sel.innerHTML = "";
  sel.appendChild(primo);
  valori.forEach((v) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  });
  sel.value = tieni;
}

function valore(id) {
  const el = document.getElementById(id);
  return el ? el.value : "";
}

function somma(righe, campo) {
  return righe.reduce((a, r) => a + (r[campo] || 0), 0).toLocaleString("it-IT");
}

function uniq(valori) {
  return Array.from(new Set((valori || []).filter(Boolean))).sort((a, b) =>
    String(a).localeCompare(String(b), "it"));
}

function numero(n) {
  return n == null ? "" : Number(n).toLocaleString("it-IT");
}

function euro(n) {
  return n == null ? "" : Number(n).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " $";
}

function quando(iso) {
  if (!iso) return "";
  return iso.replace("T", " ").slice(0, 16);
}

function durata(ms) {
  if (ms == null) return "";
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  return m ? m + "m " + (s % 60) + "s" : s + "s";
}

function durataDa(iso) {
  if (!iso) return "?";
  const da = Date.parse(iso);
  if (Number.isNaN(da)) return "?";
  return durata(Math.max(0, Date.now() - da));
}

function taglia(testo, n) {
  const s = String(testo == null ? "" : testo);
  return s.length > n ? s.slice(0, n - 3) + "..." : s;
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
