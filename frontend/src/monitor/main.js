// La console della catena: l'atlante e la macchina che lo scrive.
//
// Tre bande, in ordine di urgenza:
//
//   ADESSO      che sta girando ora, in push da Supabase Realtime. Compare solo
//               quando c'e' qualcosa da vedere.
//   L'ATLANTE   tutti e 634 gli indicatori con una pagina e che cosa e' scritto
//               di ognuno. E' la vista principale: la domanda che ci si fa piu'
//               spesso non e' "che ha fatto la run", e' "a che punto siamo".
//   LE RUN      una riga per workflow, apribile sui suoi agenti.
//
// La firma della pagina e' **l'anatomia**: un articolo indicatore e' un lead
// piu' esattamente quattro ruoli, e ogni riga porta quel glifo di cinque parti.
// Ripetuto 634 volte diventa la trama della pagina, e alla scala dell'atlante e'
// la banda del recap, dove ogni indicatore e' un filo. Non e' decorazione: e' il
// contratto editoriale disegnato, e la banda e' anche il filtro, cosi' un solo
// oggetto fa il riepilogo e la navigazione.
//
// Vanilla, nessun React: e' una tabella viva, non un'app.

import { createClient } from "@supabase/supabase-js";

const cfg = window.__supabase || null;
const adminEmail = (window.__monitorAdminEmail || "").toLowerCase();
const root = document.getElementById("monitor-root");

// Le cinque fasi della catena, nell'ordine in cui girano. Serve alla spina
// dorsale di ADESSO, che deve mostrare anche le fasi non ancora arrivate: senza
// quelle si vedrebbe il passato e non a che punto e' la run.
const FASI = ["Dossier", "Contesto", "Scrittura", "Verifica", "Pubblicazione"];

// I quattro ruoli di un articolo, nell'ordine in cui la pagina li rende.
const RUOLI = ["definizione", "quadro", "dinamica", "limiti"];

// I gruppi della banda, dal piu' fatto al meno: **quanto manca**, che e' quello
// che il glifo dice a livello di riga, cosi' banda e glifo sono la stessa idea a
// due scale.
//
// I gruppi vuoti non si stampano nella legenda, e oggi ne restano tre pieni: 55
// completi, 321 a cui mancano esattamente due sezioni (le stesse due, la
// definizione e la dinamica) e 257 senza testo. L'atlante e' cosi', a scalini, e
// una legenda con quattro voci a zero direbbe che la distribuzione ha una coda
// che non ha. `da rivedere` resta anche a zero: quello zero e' la notizia, ed e'
// il solo stato che si vuole vuoto.
const GRUPPI = [
  { chiave: "completo", nome: "completi" },
  { chiave: "senza-lead", nome: "senza attacco" },
  { chiave: "manca-1", nome: "manca 1 sezione" },
  { chiave: "manca-2", nome: "mancano 2 sezioni" },
  { chiave: "manca-3", nome: "mancano 3 o piu" },
  { chiave: "senza-testo", nome: "senza testo" },
  { chiave: "arretrato", nome: "da rivedere" },
];

const ORDINI = [
  { chiave: "coda", nome: "da scrivere" },
  { chiave: "nome", nome: "nome" },
  { chiave: "dato", nome: "anno del dato" },
  { chiave: "famiglia", nome: "famiglia" },
  { chiave: "parole", nome: "parole scritte" },
];

// Stato di modulo: i dati fetchati e i filtri, cosi' un cambio di filtro
// ridisegna senza rifetchare.
let runsData = null;
let indicatoriData = null;
let catalogoData = null;
let vista = "atlante";
let pagina = 0;
const PAGINA = 25;
const aperte = new Set();

function h(html) {
  root.innerHTML = html;
}

if (!cfg || !cfg.url || !cfg.anonKey) {
  h('<p class="mon-msg">Console non configurata: mancano le identità Supabase.</p>');
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
      "<p>L'account <strong>" + escapeHtml(email) + "</strong> non è autorizzato.</p>" +
      '<button id="mon-logout" class="mon-btn">Esci</button>' +
      "</div>"
  );
  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();
}

async function render(supabase, currentUser) {
  // Ogni render riparte da zero: rimuovi i canali gia' aperti, cosi' un
  // TOKEN_REFRESHED (che rida' lo stesso utente) non accumula sottoscrizioni.
  supabase.removeAllChannels();

  if (!currentUser) return loginView(supabase);
  const email = (currentUser.email || "").toLowerCase();
  if (adminEmail && email !== adminEmail) return deniedView(supabase, email);

  leggiHash();

  h(
    '<div class="mon-head"><h1>Console catena</h1>' +
      '<span class="mon-dot" title="in ascolto"></span>' +
      // I due bottoni stanno in un contenitore loro: sciolti nella testa vanno a
      // capo uno per volta, e su schermo stretto "Esci" finiva da solo a sinistra.
      '<div class="mon-azioni">' +
        '<button id="mon-aggiorna" class="mon-btn mon-btn--ghost mon-btn--sm">Aggiorna</button>' +
        '<button id="mon-logout" class="mon-btn mon-btn--ghost mon-btn--sm">Esci</button>' +
      "</div></div>" +

      '<section id="mon-adesso" class="mon-banda"></section>' +

      '<div class="mon-tabs" role="tablist">' +
        '<button class="mon-tab" id="tab-atl" role="tab">L\'atlante</button>' +
        '<button class="mon-tab" id="tab-run" role="tab">Le run</button>' +
      "</div>" +
      '<section id="mon-recap"></section>' +
      '<div id="mon-filtri" class="mon-filters"></div>' +
      '<div id="mon-lista" class="mon-table"><p class="mon-empty">Carico...</p></div>'
  );

  document.getElementById("mon-logout").onclick = () => supabase.auth.signOut();
  document.getElementById("mon-aggiorna").onclick = () => carica(supabase);
  document.getElementById("tab-atl").onclick = () => cambiaVista("atlante");
  document.getElementById("tab-run").onclick = () => cambiaVista("run");
  window.addEventListener("hashchange", () => { leggiHash(); disegna(); });

  await carica(supabase);

  // Realtime: a ogni cambiamento sulle due tabelle si rilegge tutto. Le tabelle
  // sono piccole e la rilettura completa e' piu' semplice (e meno fragile) di un
  // merge incrementale, che dovrebbe conoscere quale delle due sorgenti ha
  // scritto quale colonna.
  supabase
    .channel("cruscotto")
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_run" }, () => caricaFraPoco(supabase))
    .on("postgres_changes", { event: "*", schema: "public", table: "pipeline_agente" }, () => caricaFraPoco(supabase))
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
  const [runs, indicatori, catalogo] = await Promise.all([
    authedJson(supabase, "/_pipeline/api/runs"),
    authedJson(supabase, "/_pipeline/api/indicatori"),
    authedJson(supabase, "/_pipeline/api/catalogo"),
  ]);
  runsData = runs;
  indicatoriData = indicatori;
  catalogoData = catalogo;
  disegna();
}

// Realtime spara un evento per riga cambiata, e durante una run le righe
// cambiano a ogni giro del lettore: senza freno la console rifetcherebbe le API
// decine di volte al minuto per mostrare lo stesso stato.
let attesa = null;
function caricaFraPoco(supabase) {
  if (attesa) return;
  attesa = setTimeout(() => { attesa = null; carica(supabase); }, 1200);
}

// --- navigazione -----------------------------------------------------------

function leggiHash() {
  const hash = (window.location.hash || "").replace(/^#/, "");
  const [nome, chiave] = hash.split("/");
  if (nome === "run") vista = "run";
  else if (nome === "atlante") vista = "atlante";
  if (chiave) aperte.add(decodeURIComponent(chiave));
}

function cambiaVista(prossima) {
  vista = prossima;
  pagina = 0;
  window.location.hash = prossima;
  disegna();
}

// Un clic su un indicatore dalla vista Run porta alla sua riga nell'atlante, e
// viceversa: sono lo stesso fatto guardato da due lati, non due destinazioni.
function vaiA(prossima, chiave, filtro) {
  vista = prossima;
  pagina = 0;
  aperte.add(chiave);
  window.location.hash = prossima + "/" + encodeURIComponent(chiave);
  disegna();
  const q = document.getElementById("f-q");
  if (q && filtro != null) { q.value = filtro; disegna(); }
}

// --- disegno ---------------------------------------------------------------

function disegna() {
  disegnaAdesso();
  const tabAtl = document.getElementById("tab-atl");
  const tabRun = document.getElementById("tab-run");
  if (tabAtl) tabAtl.setAttribute("aria-selected", String(vista === "atlante"));
  if (tabRun) tabRun.setAttribute("aria-selected", String(vista === "run"));
  if (vista === "run") disegnaRun();
  else disegnaAtlante();
}

// --- banda 1: ADESSO -------------------------------------------------------

function disegnaAdesso() {
  const el = document.getElementById("mon-adesso");
  if (!el) return;
  // Rete caduta e catena ferma sono due cose diverse, e il posto dove
  // confonderle fa piu' danno e' proprio qui: "nessuna run" mentre una run gira
  // e' la bugia peggiore che questa pagina possa dire.
  if (!runsData) {
    el.innerHTML = '<p class="mon-empty">Non riesco a leggere le run (login o rete).</p>';
    return;
  }
  const runs = runsData.runs || [];
  if (!runs.length) {
    el.innerHTML = '<p class="mon-empty">Nessuna run registrata.</p>';
    return;
  }
  // Una run che non batte da un quarto d'ora non e' in volo: scende dal posto
  // d'onore e va nell'elenco. Cosi' `wf_precheck` non ci resta per sempre.
  const volo = runs.filter((r) => r.in_volo && !r.battito_fermo);
  if (!volo.length) {
    const ultima = runs[0];
    el.innerHTML =
      '<div class="mon-adesso mon-adesso--ferma">' +
        '<div class="mon-adesso-testa"><strong>Nessuna run in volo</strong>' +
        "<span>ultima " + escapeHtml(quando(ultima.avviata_il)) + " &middot; " +
        escapeHtml(ultima.workflow || ultima.run_id) + " &middot; " +
        badgeEsitoRun(ultima) + "</span></div></div>";
    return;
  }
  el.innerHTML = '<h2 class="mon-eyebrow">Adesso</h2>' + volo.map(cardVolo).join("");
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
            escapeHtml(a.agent_type) + (a.modello ? " &middot; " + escapeHtml(a.modello) : "") +
            " &middot; da " + escapeHtml(durataDa(a.avviato_il))).join(" &middot; ") + "</div>"
        : '<div class="mon-aperto">nessun agente aperto in questo momento</div>') +
    "</div>"
  );
}

// --- banda 2: L'ATLANTE ----------------------------------------------------

// Il gruppo di una riga: primo che calza, dal peggio al meglio. Un articolo
// arretrato e' il solo stato **sbagliato** e vince su tutto, perche' una cifra
// vecchia e' falsa mentre una sezione assente e' soltanto scarna.
function gruppoDi(r) {
  if (r.arretrato) return "arretrato";
  if (!r.scritte && !r.lead) return "senza-testo";
  const mancanti = (r.mancanti || []).length;
  if (!mancanti && r.lead) return "completo";
  if (!mancanti) return "senza-lead";
  if (mancanti === 1) return "manca-1";
  if (mancanti === 2) return "manca-2";
  return "manca-3";
}

function disegnaAtlante() {
  const filtri = document.getElementById("mon-filtri");
  const recap = document.getElementById("mon-recap");
  const el = document.getElementById("mon-lista");
  if (!el) return;
  if (!catalogoData) {
    recap.innerHTML = "";
    filtri.innerHTML = "";
    el.innerHTML = '<p class="mon-empty">Catalogo non disponibile (login o rete).</p>';
    return;
  }
  const tutte = (catalogoData.righe || []).filter((r) => r.predefinito);
  montaFiltriAtlante(filtri, tutte);
  disegnaRecap(recap, tutte);

  const righe = ordina(tutte.filter(passaFiltroAtlante));
  if (!righe.length) return (el.innerHTML = '<p class="mon-empty">Nessun indicatore col filtro attuale.</p>');

  // Niente impaginazione: 634 righe di tabella non pesano niente, e un elenco
  // esplorativo diviso in 26 pagine non si esplora. Cosi' funzionano anche lo
  // scorrimento e la ricerca del browser.
  el.innerHTML =
    '<p class="mon-conteggio">' + righe.length + " indicatori</p>" +
    // Niente colonna "famiglia": la porta gia' il codice (`ter-`, `bes-`,
    // `ims-`), e stamparla a parte vorrebbe dire stampare la chiave interna
    // (`territorial`, `multiscopo`), che e' proprio cio' che `app/sources.py`
    // vieta di mostrare a un lettore. Resta come filtro, dove serve.
    '<table class="mon-cards"><thead><tr>' +
      "<th>Indicatore</th><th>Anatomia</th>" +
      '<th class="mon-num">Parole</th><th class="mon-num">Dati</th>' +
      '<th>Stato</th><th class="mon-num">Ultima run</th>' +
    "</tr></thead><tbody>" +
    righe.map(rigaAtlante).join("") +
    "</tbody></table>";

  collega(el);
}

function disegnaRecap(el, righe) {
  if (!el) return;
  const totali = catalogoData.totali || {};
  const conta = {};
  GRUPPI.forEach((g) => { conta[g.chiave] = 0; });
  righe.forEach((r) => { conta[gruppoDi(r)] += 1; });

  // Ogni indicatore e' un filo. Ordinati per gruppo, i colori si raggruppano in
  // blocchi contigui, quindi la banda si legge in due modi insieme: come 634
  // fatti singoli e come una barra proporzionale.
  const fili = GRUPPI.flatMap((g) =>
    righe.filter((r) => gruppoDi(r) === g.chiave)
      .sort((a, b) => a.nome.localeCompare(b.nome, "it"))
      .map((r) => '<span class="mon-filo mon-filo--' + g.chiave + '" title="' +
        escapeHtml(r.nome + " (" + r.codice + "): " + g.nome) + '"></span>')
  ).join("");

  const scelto = valore("f-gruppo");
  const legenda = GRUPPI.filter((g) => conta[g.chiave] || g.chiave === "arretrato").map((g) =>
    '<button type="button" class="mon-legenda' + (scelto === g.chiave ? " mon-legenda--scelta" : "") +
      '" data-gruppo="' + g.chiave + '">' +
      '<span class="mon-quadro mon-filo--' + g.chiave + '"></span>' +
      "<strong>" + conta[g.chiave] + "</strong> " + escapeHtml(g.nome) + "</button>"
  ).join("");

  // Niente occhiello qui: la scheda sopra dice gia' "L'atlante", e ripeterlo a
  // due centimetri di distanza e' rumore.
  el.innerHTML =
    '<p class="mon-grande"><strong>' + (totali.indicatori || righe.length) + "</strong> indicatori con una pagina</p>" +
    '<div class="mon-banda-fili" role="img" aria-label="stato editoriale dei ' +
      (totali.indicatori || righe.length) + ' indicatori">' + fili + "</div>" +
    '<div class="mon-legende">' + legenda + "</div>" +
    '<p class="mon-sotto">' + (totali.con_articolo || 0) + " con testo &middot; " +
      (totali.indicizzabili || 0) + " in indice &middot; " +
      (totali.scritti_non_in_linea || 0) + " scritti e non ancora in linea &middot; " +
      (totali.rilievi || 0) + " rilievi di prosa</p>";

  el.querySelectorAll("[data-gruppo]").forEach((b) => {
    b.onclick = () => {
      const sel = document.getElementById("f-gruppo");
      const g = b.getAttribute("data-gruppo");
      if (sel) sel.value = sel.value === g ? "" : g;
      disegna();
    };
  });
}

function montaFiltriAtlante(el, righe) {
  if (!el || el.getAttribute("data-vista") === "atlante") return;
  el.setAttribute("data-vista", "atlante");
  el.innerHTML =
    '<input id="f-q" type="search" placeholder="Cerca nome, codice o tema">' +
    '<select id="f-famiglia"><option value="">Tutte le famiglie</option></select>' +
    '<select id="f-tema"><option value="">Tutti i temi</option></select>' +
    '<select id="f-gruppo"><option value="">Tutti gli stati</option>' +
      GRUPPI.map((g) => '<option value="' + g.chiave + '">' + escapeHtml(g.nome) + "</option>").join("") +
      '<option value="fuori-indice">fuori indice</option></select>' +
    '<label class="mon-ordina">ordina per <select id="f-ordina">' +
      ORDINI.map((o) => '<option value="' + o.chiave + '">' + escapeHtml(o.nome) + "</option>").join("") +
    "</select></label>";
  el.querySelectorAll("input, select").forEach((c) => {
    c.oninput = () => disegna();
    c.onchange = () => disegna();
  });
  opzioni("f-famiglia", uniq(righe.map((r) => r.famiglia_label)));
  opzioni("f-tema", uniq(righe.map((r) => r.tema)));
}

function passaFiltroAtlante(r) {
  const q = (valore("f-q") || "").trim().toLowerCase();
  const famiglia = valore("f-famiglia");
  const tema = valore("f-tema");
  const gruppo = valore("f-gruppo");
  const testo = [r.nome, r.codice, r.tema, r.famiglia_label].filter(Boolean).join(" ").toLowerCase();
  if (q && testo.indexOf(q) === -1) return false;
  if (famiglia && r.famiglia_label !== famiglia) return false;
  if (tema && r.tema !== tema) return false;
  if (gruppo === "fuori-indice") return !r.indicizzabile;
  if (gruppo && gruppoDi(r) !== gruppo) return false;
  return true;
}

function ordina(righe) {
  const come = valore("f-ordina") || "coda";
  const copia = righe.slice();
  if (come === "nome") copia.sort((a, b) => a.nome.localeCompare(b.nome, "it"));
  else if (come === "dato") copia.sort((a, b) => (b.anno_dato || 0) - (a.anno_dato || 0) || a.nome.localeCompare(b.nome, "it"));
  else if (come === "famiglia") copia.sort((a, b) => a.famiglia_label.localeCompare(b.famiglia_label, "it") || a.nome.localeCompare(b.nome, "it"));
  else if (come === "parole") copia.sort((a, b) => (b.parole || 0) - (a.parole || 0));
  // `coda` e' l'ordine che sceglie la catena: la prima riga qui e' la stessa che
  // sceglierebbe `lab.dossier --coda 1`. La console e la catena guardano una
  // classifica sola.
  else copia.sort((a, b) => (b.punteggio || 0) - (a.punteggio || 0) || a.nome.localeCompare(b.nome, "it"));
  return copia;
}

// Il glifo: un trattino per il lead, un quadro per ogni ruolo emesso, pieno se
// scritto da una persona e vuoto se composto dal template.
function anatomia(r) {
  const per = {};
  (r.ruoli || []).forEach((s) => { per[s.role] = s; });
  const pezzi = RUOLI.map((ruolo) => {
    const s = per[ruolo];
    if (!s) return '<span class="mon-anat-vuoto" title="' + ruolo + ': non resa"></span>';
    return '<span class="mon-anat-' + (s.authored ? "pieno" : "assente") + '" title="' +
      escapeHtml(ruolo + (s.authored ? ": " + (s.heading || "scritta") : ": composta dal template")) + '"></span>';
  }).join("");
  return '<span class="mon-anat">' +
    '<span class="mon-anat-lead' + (r.lead ? " mon-anat-lead--si" : "") +
      '" title="' + (r.lead ? "attacco scritto" : "attacco composto") + '"></span>' + pezzi + "</span>";
}

function rigaAtlante(r) {
  const apri = aperte.has(r.codice);
  const gruppo = gruppoDi(r);
  const nome = r.url
    ? '<a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener">' + escapeHtml(r.nome) + " &#8599;</a>"
    : escapeHtml(r.nome);
  const sotto = [r.codice, r.tema].filter(Boolean).join(" &middot; ") +
    (r.indicizzabile ? "" : ' &middot; <span class="mon-fuori">fuori indice: ' + escapeHtml(r.motivo || "non dichiarato") + "</span>");
  const riga =
    '<tr class="mon-riga' + (apri ? " mon-aperta" : "") + '" data-chiave="' + escapeHtml(r.codice) + '">' +
      '<td data-label="Indicatore">' + nome + "<small>" + sotto + "</small></td>" +
      '<td data-label="Anatomia">' + anatomia(r) + "</td>" +
      '<td data-label="Parole" class="mon-num">' + (r.parole || "") + "</td>" +
      '<td data-label="Dati" class="mon-num">' + (r.anno_dato || "") +
        (r.vintage != null && r.vintage !== r.anno_dato ? "<small>testo " + r.vintage + "</small>" : "") + "</td>" +
      '<td data-label="Stato">' + badgeGruppo(gruppo) +
        (r.stato === "scritto, non in linea" ? '<small class="mon-attesa-deploy">scritto, non ancora in linea</small>' : "") + "</td>" +
      '<td data-label="Ultima run" class="mon-num">' + (r.ultima_run
        ? '<button type="button" class="mon-link" data-vai-run="' + escapeHtml(r.ultima_run) + '">' +
          escapeHtml(quando(r.ultima_run_il)) + "</button>"
        : "") + "</td>" +
    "</tr>";
  return apri ? riga + '<tr><td class="mon-dettaglio" colspan="6">' + dettaglioAtlante(r) + "</td></tr>" : riga;
}

function dettaglioAtlante(r) {
  const pezzi = [];
  pezzi.push('<ul class="mon-elenco mon-ruoli">' + (r.ruoli || []).map((s) =>
    "<li><strong>" + escapeHtml(s.role) + "</strong> " +
    (s.authored ? escapeHtml(s.heading || "scritta") : '<span class="mon-fuori">composta dal template</span>') +
    "</li>").join("") + "</ul>");

  const fatti = [
    "attacco " + (r.lead ? "scritto" : "composto"),
    r.parole ? r.parole + " parole" : null,
    "dati " + (r.anno_dato || "?") + (r.vintage != null ? ", testo scritto sul " + r.vintage : ""),
    r.arretrato ? "il testo cita un anno più vecchio del dato" : null,
    r.indicizzabile ? "in indice" : "fuori indice: " + (r.motivo || "non dichiarato"),
    r.rilievi ? r.rilievi + " rilievi di prosa" : null,
    "punteggio di coda " + r.punteggio,
    r.certezza === "assente" ? "nessuna run registrata su questa pagina" : null,
  ].filter(Boolean);
  pezzi.push("<p>" + escapeHtml(fatti.join(" · ")) + "</p>");

  const storia = (indicatoriData?.indicatori || []).filter((v) => v.indicatore === r.codice);
  if (storia.length) {
    pezzi.push("<p><strong>Le run su questa pagina</strong></p><ul class=\"mon-elenco\">" +
      storia.map((v) =>
        "<li>" + escapeHtml(quando(v.at)) + " &middot; " + badgeEsito(v.esito) +
        (v.angolo ? " &middot; " + escapeHtml(taglia(v.angolo, 110)) : "") +
        (v.sovrascritto ? ' &middot; <span class="mon-sovra">ha sovrascritto' +
          (v.vintage_precedente != null ? ", copriva il " + escapeHtml(String(v.vintage_precedente)) : "") + "</span>" : "") +
        ' &middot; <button type="button" class="mon-link" data-vai-run="' + escapeHtml(v.run_id) + '">' +
        escapeHtml(v.run_id) + "</button></li>").join("") + "</ul>");
  } else {
    pezzi.push('<p class="mon-empty">Nessuna run ha ancora toccato questa pagina.</p>');
  }
  return pezzi.join("");
}

// --- banda 3: LE RUN -------------------------------------------------------

function montaFiltriRun(el, righe) {
  if (!el) return;
  if (el.getAttribute("data-vista") !== "run") {
    el.setAttribute("data-vista", "run");
    el.innerHTML =
      '<input id="f-q" type="search" placeholder="Cerca run, indicatore, agente">' +
      '<select id="f-esito"><option value="">Tutti gli esiti</option></select>' +
      '<label class="mon-date">da <input id="f-da" type="date"></label>' +
      '<label class="mon-date">a <input id="f-a" type="date"></label>';
    el.querySelectorAll("input, select").forEach((c) => {
      c.oninput = () => { pagina = 0; disegna(); };
      c.onchange = () => { pagina = 0; disegna(); };
    });
  }
  opzioni("f-esito", uniq(righe.map(etichettaEsitoRun)));
}

function disegnaRun() {
  const el = document.getElementById("mon-lista");
  const recap = document.getElementById("mon-recap");
  const filtri = document.getElementById("mon-filtri");
  if (!el) return;
  if (!runsData) {
    recap.innerHTML = "";
    return (el.innerHTML = '<p class="mon-empty">Run non disponibili (login o rete).</p>');
  }
  const tutte = runsData.runs || [];
  montaFiltriRun(filtri, tutte);
  const righe = tutte.filter((r) => passaFiltroRun(chiaveRun(r), r.avviata_il, etichettaEsitoRun(r)));

  recap.innerHTML =
    '<div class="mon-totals-row">' +
      '<span class="mon-chip mon-chip--strong">' + righe.length + " run</span>" +
      '<span class="mon-chip">' + somma(righe, "agenti_totali") + " agenti</span>" +
      '<span class="mon-chip">' + somma(righe, "turni") + " turni</span>" +
      '<span class="mon-chip">' + euro(righe.reduce((a, r) => a + (r.costo || 0), 0)) + " pavimento</span>" +
    "</div>" +
    '<details class="mon-nota"><summary>Perchè il costo è un pavimento</summary>' +
      "<p>Il costo si misura leggendo i trascritti, e un trascritto può essere " +
      "incompleto: in una run reale un agente ha registrato due token di output " +
      "sulla richiesta che restituiva una bozza intera. La misura è fedele a " +
      "quello che il trascritto dice, quindi ogni totale è un minimo e non una " +
      "cifra esatta.</p></details>";

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
      '<td data-label="Esito">' + badgeEsitoRun(run) +
        (run.battito_fermo ? '<small class="mon-muta">nessun battito da ' +
          escapeHtml(durataDa(run.ultimo_battito)) + ", la run può essere ancora viva</small>" : "") + "</td>" +
      '<td data-label="Durata" class="mon-num">' + escapeHtml(durata(run.durata_ms)) + "</td>" +
      // `agenti` e' la lista, `agenti_totali` il conteggio: erano la stessa
      // chiave, e la cella stampava `[object Object],[object Object],...`.
      '<td data-label="Agenti" class="mon-num">' + (run.agenti_totali != null ? run.agenti_totali : "") + "</td>" +
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
        return vaiA("atlante", codice, codice);
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
  el.querySelectorAll("[data-vai-run]").forEach((b) => {
    if (b.closest("tr.mon-riga")) return;
    b.onclick = (ev) => { ev.stopPropagation(); vaiA("run", b.getAttribute("data-vai-run"), b.getAttribute("data-vai-run")); };
  });
}

function impagina(righe) {
  const pagine = Math.max(1, Math.ceil(righe.length / PAGINA));
  if (pagina > pagine - 1) pagina = pagine - 1;
  if (pagina < 0) pagina = 0;
  const fetta = righe.slice(pagina * PAGINA, pagina * PAGINA + PAGINA);
  if (pagine === 1) return { fetta, pager: "" };
  const pager =
    '<div class="mon-pager">' +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" data-passo="-1"' + (pagina === 0 ? " disabled" : "") + ">Precedente</button>" +
      '<span class="mon-pager-info">pagina ' + (pagina + 1) + "/" + pagine + " &middot; " + righe.length + " righe</span>" +
      '<button type="button" class="mon-btn mon-btn--ghost mon-btn--sm" data-passo="1"' + (pagina >= pagine - 1 ? " disabled" : "") + ">Successiva</button>" +
    "</div>";
  return { fetta, pager };
}

function passaFiltroRun(chiave, quandoIso, esito) {
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

// I cinque esiti reali della catena, tenuti distinti perche' lo sono: un
// articolo fermato prima del disco e' la verifica che ha funzionato, e non va
// letto come un guasto.
function etichettaEsitoRun(run) {
  if (run.in_volo) return run.battito_fermo ? "battito fermo" : "in volo";
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
  "battito fermo": "muta",
};

function badgeEsitoRun(run) {
  return badgeEsito(etichettaEsitoRun(run));
}

function badgeEsito(etichetta) {
  const classe = CLASSE_ESITO[etichetta] || "";
  return '<span class="mon-esito' + (classe ? " mon-esito--" + classe : "") + '">' + escapeHtml(etichetta || "") + "</span>";
}

function badgeGruppo(chiave) {
  const g = GRUPPI.find((x) => x.chiave === chiave);
  return '<span class="mon-stato mon-stato--' + chiave + '">' +
    '<span class="mon-quadro mon-filo--' + chiave + '"></span>' + escapeHtml(g ? g.nome : chiave) + "</span>";
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
