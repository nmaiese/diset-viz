/* L'atlante della 1.0: filtri, ricerca e ordine sulle righe gia' in pagina.

   Il server rende tutte le serie del catalogo, tema per tema. Qui si legge lo
   stato dall'URL, con gli stessi parametri dell'atlante React di prima (theme,
   area, source, yfrom, yto, q, sort, fav, partial) piu' complete, e si
   nascondono le righe che non passano. `partial=1` e' ancora accettato ma non
   cambia niente: all'apertura le parziali ci sono gia'. Lo stato torna
   nell'URL con replaceState, cosi' un link condiviso riapre la stessa vista.

   Gli eventi hanno i nomi della SPA (docs/tracking_spec.md): filter_theme,
   filter_macro_area, filter_data_source, filter_year_range, sort_indicators,
   toggle_partial_data, select_indicator. Il page_view lo manda il server, con
   page_type "atlas" (`PAGE_TYPE` in _third_party_head.html).

   "Solo preferiti" compare solo a chi ha fatto l'accesso: il token lo da'
   window.diAuth (frontend/src/site/auth.js), che senza una sessione salvata
   risponde null senza caricare la libreria di accesso. */
(function () {
  "use strict";
  var root = document.getElementById("indicatori");
  var form = root && root.querySelector("[data-atlas-controls]");
  if (!form) return;

  var $ = function (sel) { return root.querySelector(sel); };
  var all = function (sel, el) { return Array.prototype.slice.call((el || root).querySelectorAll(sel)); };
  var q = $("#atl-q"), theme = $("#atl-theme"), source = $("#atl-source");
  var yfrom = $("#atl-yfrom"), yto = $("#atl-yto"), sort = $("#atl-sort");
  var complete = $("#atl-complete"), fav = $("#atl-fav"), favBox = $("[data-atlas-fav]");
  var live = $("[data-atlas-live]"), empty = $("[data-atlas-empty]");
  var areaButtons = all("[data-atlas-area]");
  var areas = all(".atlante-area");
  var groups = all(".atlante-group");
  var themeOptions = all("option[data-area]", theme);
  var rows = all("tr[data-id]");
  var favorites = null; // Set degli id, solo dopo l'accesso

  function norm(s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  // Il testo su cui si cerca: nome, tema, fonte e tema della fonte, come la SPA.
  var sourceLabel = {};
  all("option", source).forEach(function (o) { if (o.value) sourceLabel[o.value] = o.textContent; });
  rows.forEach(function (tr) {
    var a = tr.querySelector("th a");
    var group = tr.closest(".atlante-group");
    tr._name = a.textContent;
    tr._text = norm([a.textContent, group.getAttribute("data-theme"), tr.getAttribute("data-q"),
      sourceLabel[tr.getAttribute("data-s")]].join(" "));
  });

  /* ---------- stato ---------- */
  var state = { area: "", theme: "", source: "", yfrom: "", yto: "", q: "", sort: "complete", fav: false, complete: false, partial: "" };
  var params = new URLSearchParams(location.search);
  function has(select, value) { return all("option", select).some(function (o) { return o.value === value; }); }
  state.area = areaButtons.some(function (b) { return b.getAttribute("data-atlas-area") === params.get("area"); }) ? params.get("area") : "";
  state.theme = has(theme, params.get("theme") || "") ? params.get("theme") || "" : "";
  state.source = has(source, params.get("source") || "") ? params.get("source") || "" : "";
  state.yfrom = has(yfrom, params.get("yfrom") || "") ? params.get("yfrom") || "" : "";
  state.yto = has(yto, params.get("yto") || "") ? params.get("yto") || "" : "";
  state.sort = has(sort, params.get("sort") || "") ? params.get("sort") : "complete";
  state.q = params.get("q") || "";
  state.fav = params.get("fav") === "1";
  state.complete = params.get("complete") === "1";
  state.partial = params.get("partial") === "1" ? "1" : "";
  // Un tema fuori dall'area scelta non si puo' tenere: vince l'area.
  if (state.theme && state.area) {
    var opt = themeOptions.filter(function (o) { return o.value === state.theme; })[0];
    if (opt && opt.getAttribute("data-area") !== state.area) state.theme = "";
  }

  function writeUrl() {
    var url = new URL(location.href);
    ["area", "theme", "source", "yfrom", "yto", "q", "sort", "fav", "complete", "partial"].forEach(function (k) { url.searchParams.delete(k); });
    if (state.theme) url.searchParams.set("theme", state.theme);
    if (state.q) url.searchParams.set("q", state.q);
    if (state.sort !== "complete") url.searchParams.set("sort", state.sort);
    if (state.partial) url.searchParams.set("partial", "1");
    if (state.area) url.searchParams.set("area", state.area);
    if (state.source) url.searchParams.set("source", state.source);
    if (state.yfrom) url.searchParams.set("yfrom", state.yfrom);
    if (state.yto) url.searchParams.set("yto", state.yto);
    if (state.fav) url.searchParams.set("fav", "1");
    if (state.complete) url.searchParams.set("complete", "1");
    history.replaceState(history.state, "", url.pathname + url.search + url.hash);
  }

  /* ---------- eventi, come trackEvent di main.jsx ---------- */
  function track(name, extra) {
    var params = {
      page_type: "atlas",
      page_path: location.pathname + location.search,
      page_title: document.title
    };
    for (var k in extra) params[k] = extra[k];
    window.dataLayer = window.dataLayer || [];
    var push = { event: name };
    for (var p in params) push[p] = params[p];
    window.dataLayer.push(push);
    try {
      fetch("/api/events", {
        method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true, credentials: "omit",
        body: JSON.stringify({ name: name, params: params, path: location.pathname + location.search, title: document.title })
      }).catch(function () {});
    } catch (e) { /* niente */ }
  }

  /* ---------- ordine, dentro ogni tema ---------- */
  var num = function (tr, k) { return Number(tr.getAttribute(k)) || 0; };
  var byName = function (a, b) { return a._name.localeCompare(b._name, "it"); };
  var SORTERS = {
    complete: function (a, b) { return num(b, "data-c") - num(a, "data-c") || num(b, "data-y1") - num(a, "data-y1") || byName(a, b); },
    recent: function (a, b) { return num(b, "data-y1") - num(a, "data-y1") || num(b, "data-c") - num(a, "data-c") || byName(a, b); },
    az: byName,
    // Le righe stanno gia' in una tabella per tema: dentro il tema, per nome.
    theme: byName
  };
  var sorted = "complete"; // l'ordine del server
  function applySort() {
    if (state.sort === sorted) return;
    sorted = state.sort;
    all("tbody").forEach(function (tb) {
      var list = all("tr[data-id]", tb).sort(SORTERS[state.sort] || SORTERS.complete);
      list.forEach(function (tr) { tb.appendChild(tr); });
    });
  }

  /* ---------- filtri ---------- */
  function rowPasses(tr, needle) {
    if (state.source && tr.getAttribute("data-s") !== state.source) return false;
    if (state.yfrom && num(tr, "data-y0") > Number(state.yfrom)) return false;
    if (state.yto && num(tr, "data-y1") < Number(state.yto)) return false;
    if (state.complete && tr.hasAttribute("data-p")) return false;
    if (state.fav && favorites && !favorites.has(tr.getAttribute("data-id"))) return false;
    if (needle && tr._text.indexOf(needle) < 0) return false;
    return true;
  }
  function apply() {
    var needle = norm(state.q.trim());
    var counts = {}; // per tema, senza il filtro del tema e della ricerca, come la SPA
    var shown = 0;
    groups.forEach(function (g) {
      var name = g.getAttribute("data-theme");
      var area = g.parentNode.getAttribute("data-area");
      var inArea = !state.area || area === state.area;
      var inTheme = !state.theme || name === state.theme;
      var n = 0, pool = 0;
      all("tr[data-id]", g).forEach(function (tr) {
        var base = inArea && rowPasses(tr, "");
        if (base) pool += 1;
        var ok = base && inTheme && (!needle || tr._text.indexOf(needle) >= 0);
        tr.hidden = !ok;
        if (ok) n += 1;
      });
      counts[name] = pool;
      g.hidden = n === 0;
      g.querySelector("[data-atlas-n]").textContent = n;
      shown += n;
    });
    areas.forEach(function (a) { a.hidden = !a.querySelector(".atlante-group:not([hidden])"); });
    themeOptions.forEach(function (o) {
      var inArea = !state.area || o.getAttribute("data-area") === state.area;
      o.hidden = !inArea;
      o.disabled = !inArea || !counts[o.value];
      o.textContent = o.value + " (" + (counts[o.value] || 0) + ")";
    });
    areaButtons.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-atlas-area") === state.area ? "true" : "false"); });
    live.textContent = shown === 0 ? "Nessun indicatore con questi filtri" : shown + (shown === 1 ? " indicatore" : " indicatori");
    empty.hidden = shown !== 0;
    applySort();
    writeUrl();
  }

  function sync() {
    q.value = state.q; theme.value = state.theme; source.value = state.source;
    yfrom.value = state.yfrom; yto.value = state.yto; sort.value = state.sort;
    complete.checked = state.complete; fav.checked = state.fav;
  }

  /* ---------- i controlli ---------- */
  form.addEventListener("submit", function (ev) { ev.preventDefault(); });
  // "Sulla mappa" di una riga: la pagina si ricarica con `mappa` e con i
  // filtri gia' scelti, che il modulo da solo perderebbe.
  var mapForm = document.getElementById("atl-map");
  if (mapForm) mapForm.addEventListener("submit", function (ev) {
    if (!ev.submitter || !ev.submitter.value) return;
    ev.preventDefault();
    var url = new URL(location.href);
    url.searchParams.set("mappa", ev.submitter.value);
    location.assign(url.pathname + url.search + "#mappa");
  });
  areaButtons.forEach(function (b) {
    b.addEventListener("click", function () {
      state.area = b.getAttribute("data-atlas-area");
      state.theme = ""; // come la SPA: cambiare area azzera il tema
      theme.value = "";
      apply();
      track("filter_macro_area", { macro_area: state.area || "Tutte" });
    });
  });
  theme.addEventListener("change", function () {
    state.theme = theme.value;
    apply();
    track("filter_theme", { theme: state.theme || "Tutti" });
  });
  source.addEventListener("change", function () {
    state.source = source.value;
    state.theme = ""; theme.value = "";
    apply();
    track("filter_data_source", { source_family: state.source || "all" });
  });
  function years(which) {
    return function () {
      var from = yfrom.value, to = yto.value;
      // Le due soglie non si incrociano: si porta dietro l'altra, come la SPA.
      if (from && to && Number(from) > Number(to)) {
        if (which === "from") { to = from; yto.value = to; } else { from = to; yfrom.value = from; }
      }
      state.yfrom = from; state.yto = to;
      apply();
      track("filter_year_range", { year_from: from ? Number(from) : null, year_to: to ? Number(to) : null });
    };
  }
  yfrom.addEventListener("change", years("from"));
  yto.addEventListener("change", years("to"));
  sort.addEventListener("change", function () {
    state.sort = sort.value;
    apply();
    track("sort_indicators", { sort: state.sort });
  });
  complete.addEventListener("change", function () {
    state.complete = complete.checked;
    apply();
    track("toggle_partial_data", { enabled: !state.complete });
  });
  fav.addEventListener("change", function () {
    state.fav = fav.checked;
    apply();
  });
  var typing;
  q.addEventListener("input", function () {
    clearTimeout(typing);
    typing = setTimeout(function () { state.q = q.value; apply(); }, 120);
  });
  root.addEventListener("click", function (ev) {
    var a = ev.target.closest("tr[data-id] th a");
    if (!a) return;
    var tr = a.closest("tr");
    track("select_indicator", {
      indicator_id: tr.getAttribute("data-id"), indicator_name: tr._name,
      indicator_theme: tr.closest(".atlante-group").getAttribute("data-theme"), from: "atlas"
    });
  });

  /* ---------- i preferiti, solo dopo l'accesso ---------- */
  function wantFavourites() {
    var auth = window.diAuth;
    if (!auth || typeof auth.token !== "function") return false;
    auth.token().then(function (token) {
      if (!token) return;
      return fetch("/api/favorites", { headers: { Authorization: "Bearer " + token } })
        .then(function (r) { return r.ok ? r.json() : { favorites: [] }; })
        .then(function (d) {
          favorites = new Set((d.favorites || []).map(String));
          favBox.hidden = false;
          apply();
        });
    }).catch(function () {});
    return true;
  }
  // site.js e' un modulo e puo' arrivare dopo questo script: si aspetta il suo segnale.
  if (!wantFavourites()) document.addEventListener("di:auth", wantFavourites, { once: true });

  // Senza accesso un `?fav=1` condiviso mostra l'elenco intero, non un elenco
  // vuoto: il filtro vale solo quando i preferiti ci sono (`rowPasses`).
  sync();
  form.hidden = false;
  apply();
})();
