/*
 * Indicator page in-page explorer (progressive enhancement).
 *
 * The server renders the last-year ranking, the choropleth and the definition
 * as plain, crawlable HTML. This script reads the full year x region matrix that
 * the server embeds in <script id="indicator-data"> and turns that same markup
 * into an interactive explorer: a year slider and a region selector that update
 * the ranking table, the map and the readout in place.
 *
 * There is one canonical URL per indicator. Exploration states only touch the
 * query string via history.replaceState, so the browser never navigates and the
 * canonical stays the base URL (the page is served noindex when parameters are
 * present). With JavaScript disabled, the server-rendered ranking remains the
 * fallback and nothing here runs.
 */
(function () {
  "use strict";

  var dataEl = document.getElementById("indicator-data");
  var root = document.querySelector("[data-explore-root]");
  if (!dataEl || !root) return;

  var data;
  try {
    data = JSON.parse(dataEl.textContent);
  } catch (err) {
    return;
  }
  if (!data || !Array.isArray(data.years) || !data.years.length || !data.matrix) return;

  var years = data.years.slice();
  var regions = data.regions || [];
  var matrix = data.matrix;
  var higherBetter = data.higherBetter !== false;
  var scoreable = !!data.scoreable;
  var unit = data.unit || "";
  var basePath = location.pathname;
  var ramp = data.ramp || { from: [0xe7, 0xec, 0xf3], to: [0x15, 0x23, 0x3b] };

  var nameByKey = {};
  regions.forEach(function (r) { nameByKey[r.key] = r.name; });

  var numberFmt = new Intl.NumberFormat("it-IT", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  function fmtValue(v) {
    if (v === null || v === undefined || isNaN(v)) return "n.d.";
    var s = numberFmt.format(v);
    if (!unit) return s;
    return unit === "%" ? s + "%" : s + " " + unit;
  }

  // Per-year ranking, ordered like the server: best first. "Best" depends on the
  // indicator direction; contextual indicators keep the raw value-descending
  // order and simply do not claim a winner.
  function ranked(year) {
    var byRegion = matrix[String(year)] || {};
    var rows = Object.keys(byRegion).map(function (key) {
      return { key: key, name: nameByKey[key] || key, value: byRegion[key] };
    });
    rows.sort(function (a, b) {
      return higherBetter ? b.value - a.value : a.value - b.value;
    });
    rows.forEach(function (row, i) { row.rank = i + 1; });
    return rows;
  }

  function rampColor(t) {
    var c = [0, 0, 0];
    for (var i = 0; i < 3; i++) {
      c[i] = Math.round(ramp.from[i] + (ramp.to[i] - ramp.from[i]) * t);
    }
    return "#" + c.map(function (n) {
      var h = n.toString(16);
      return h.length === 1 ? "0" + h : h;
    }).join("");
  }

  // ---- Elements -----------------------------------------------------------
  var yearInput = root.querySelector('[data-explore="year"]');
  var yearLabel = root.querySelector('[data-explore="year-label"]');
  var regionSelect = root.querySelector('[data-explore="region"]');
  var focusName = root.querySelector('[data-explore="focus-name"]');
  var focusValue = root.querySelector('[data-explore="focus-value"]');
  var focusRank = root.querySelector('[data-explore="focus-rank"]');

  var rankingBody = document.querySelector('[data-explore="ranking"]');
  var mapEl = document.querySelector('[data-explore="map"]');
  var yearTitles = document.querySelectorAll('[data-explore="year-title"]');
  var mapYearEls = document.querySelectorAll('[data-explore="map-year"]');
  var insightYearLabels = document.querySelectorAll('[data-explore="year-label"]');
  var bestNameEl = document.querySelector('[data-explore="best-name"]');
  var bestValueEl = document.querySelector('[data-explore="best-value"]');
  var worstNameEl = document.querySelector('[data-explore="worst-name"]');
  var worstValueEl = document.querySelector('[data-explore="worst-value"]');
  var avgValueEl = document.querySelector('[data-explore="avg-value"]');
  var avgCountEl = document.querySelector('[data-explore="avg-count"]');

  // ---- Region select ------------------------------------------------------
  regions.forEach(function (r) {
    var opt = document.createElement("option");
    opt.value = r.key;
    opt.textContent = r.name;
    regionSelect.appendChild(opt);
  });

  // ---- Initial state (URL params fall back to the canonical defaults) ------
  var params = new URLSearchParams(location.search);
  var startYear = data.defaultYear || years[years.length - 1];
  var paramYear = parseInt(params.get("anno"), 10);
  if (!isNaN(paramYear) && years.indexOf(paramYear) !== -1) startYear = paramYear;

  var startRegion = regions.length ? regions[0].key : null;
  var paramRegion = params.get("regione");
  if (paramRegion && nameByKey[paramRegion]) startRegion = paramRegion;

  var state = {
    yearIndex: Math.max(0, years.indexOf(startYear)),
    regionKey: startRegion,
  };

  // ---- Slider bounds ------------------------------------------------------
  yearInput.min = 0;
  yearInput.max = years.length - 1;
  yearInput.value = state.yearIndex;
  if (years.length < 2) {
    yearInput.disabled = true;
    yearInput.setAttribute("aria-hidden", "true");
  }
  regionSelect.value = state.regionKey || "";

  function currentYear() { return years[state.yearIndex]; }

  function setText(nodes, value) {
    for (var i = 0; i < nodes.length; i++) nodes[i].textContent = value;
  }

  function render() {
    var year = currentYear();
    var rows = ranked(year);
    var count = rows.length;
    var focus = null;
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].key === state.regionKey) { focus = rows[i]; break; }
    }

    // Year labels across the page.
    if (yearLabel) yearLabel.textContent = year;
    setText(yearTitles, year);
    setText(mapYearEls, year);
    setText(insightYearLabels, year);

    // Readout for the focused region.
    if (focusName) {
      focusName.textContent = (nameByKey[state.regionKey] || "-") + " · " + year;
    }
    if (focusValue) focusValue.textContent = focus ? fmtValue(focus.value) : "n.d.";
    if (focusRank) {
      focusRank.textContent = focus
        ? focus.rank + "ª su " + count + " regioni"
        : "dato non disponibile per il " + year;
    }

    // Ranking table, rebuilt for the selected year.
    if (rankingBody) {
      var html = "";
      rows.forEach(function (row) {
        var active = row.key === state.regionKey ? ' class="is-focus"' : "";
        html +=
          "<tr data-region-key=\"" + row.key + "\"" + active + ">" +
          '<td class="rank">' + row.rank + "</td>" +
          '<td><a href="/regione/' + row.key + '">' + row.name + "</a></td>" +
          '<td class="num">' + numberFmt.format(row.value) + "</td>" +
          "</tr>";
      });
      rankingBody.innerHTML = html;
    }

    // Choropleth recolor for the selected year.
    if (mapEl) {
      var values = rows.map(function (r) { return r.value; });
      var lo = Math.min.apply(null, values);
      var hi = Math.max.apply(null, values);
      var span = hi - lo;
      var present = {};
      rows.forEach(function (row) {
        var t = span ? (row.value - lo) / span : 1;
        var node = mapEl.querySelector('[data-key="' + row.key + '"]');
        if (node) node.style.fill = rampColor(t);
        present[row.key] = true;
      });
      // Regions without a value this year fall back to the default map fill.
      var allNodes = mapEl.querySelectorAll("[data-key]");
      for (var n = 0; n < allNodes.length; n++) {
        if (!present[allNodes[n].getAttribute("data-key")]) allNodes[n].style.fill = "";
      }
    }

    // Insight tiles (best / average / worst).
    if (rows.length) {
      var sum = values_sum(rows);
      if (avgValueEl) avgValueEl.textContent = numberFmt.format(sum / rows.length);
      if (avgCountEl) avgCountEl.textContent = count;
      if (scoreable) {
        var best = rows[0];
        var worst = rows[rows.length - 1];
        if (bestNameEl) { bestNameEl.textContent = best.name; bestNameEl.setAttribute("href", "/regione/" + best.key); }
        if (bestValueEl) bestValueEl.textContent = numberFmt.format(best.value);
        if (worstNameEl) { worstNameEl.textContent = worst.name; worstNameEl.setAttribute("href", "/regione/" + worst.key); }
        if (worstValueEl) worstValueEl.textContent = numberFmt.format(worst.value);
      }
    }
  }

  function values_sum(rows) {
    var s = 0;
    for (var i = 0; i < rows.length; i++) s += rows[i].value;
    return s;
  }

  // Same page, same canonical: only the query string changes.
  function sync() {
    var qs = "?anno=" + currentYear() + "&regione=" + encodeURIComponent(state.regionKey || "");
    try {
      history.replaceState(null, "", basePath + qs);
    } catch (err) { /* ignore, e.g. file:// */ }
    render();
  }

  yearInput.addEventListener("input", function () {
    state.yearIndex = Number(yearInput.value);
    sync();
  });
  regionSelect.addEventListener("change", function () {
    state.regionKey = regionSelect.value;
    sync();
  });

  // Clicking a ranking row focuses that region.
  if (rankingBody) {
    rankingBody.addEventListener("click", function (evt) {
      var tr = evt.target.closest("tr[data-region-key]");
      if (!tr) return;
      // Let the /regione link work normally.
      if (evt.target.closest("a")) return;
      var key = tr.getAttribute("data-region-key");
      if (!key || !nameByKey[key]) return;
      state.regionKey = key;
      regionSelect.value = key;
      sync();
    });
  }

  // Reveal the controls now that they are wired, and paint the initial state.
  root.hidden = false;
  // If the URL already carries an exploration state, replay it; otherwise just
  // render the canonical default without touching the URL.
  if (params.has("anno") || params.has("regione")) {
    sync();
  } else {
    render();
  }
})();
