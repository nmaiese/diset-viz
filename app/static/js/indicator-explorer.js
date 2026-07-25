/*
 * Indicator page in-page explorer (progressive enhancement).
 *
 * The server renders the editorial, the last-year ranking (with bars), the
 * choropleth (+ legend) and the region insights as plain, crawlable HTML. This
 * script reads the full year x region matrix embedded in <script id="indicator-data">
 * and turns that same markup into the interactive dashboard the atlas used to own:
 * year slider + region focus driving, in place, the ranking, the map (clickable +
 * hover), the map legend, the region readout (value, rank, historic trend) and a
 * per-region time series chart, with Map/Ranking/Serie storica tabs on mobile.
 *
 * One canonical URL per indicator: exploration states only touch the query string
 * via history.replaceState (served noindex). With JavaScript disabled the
 * server-rendered dashboard stays as the fallback and nothing here runs.
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
  var yearMin = years[0];
  var yearMax = years[years.length - 1];

  var nameByKey = {};
  regions.forEach(function (r) { nameByKey[r.key] = r.name; });

  var numberFmt = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var compactFmt = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 });
  function fmtValue(v) {
    if (v === null || v === undefined || isNaN(v)) return "n.d.";
    var s = numberFmt.format(v);
    if (!unit) return s;
    return unit === "%" ? s + "%" : s + " " + unit;
  }
  function fmtAxis(v) {
    var s = compactFmt.format(v);
    return unit === "%" ? s + "%" : s;
  }

  function valuesForYear(year) { return matrix[String(year)] || {}; }
  function ranked(year) {
    var byRegion = valuesForYear(year);
    var rows = Object.keys(byRegion).map(function (key) {
      return { key: key, name: nameByKey[key] || key, value: byRegion[key] };
    });
    rows.sort(function (a, b) { return higherBetter ? b.value - a.value : a.value - b.value; });
    rows.forEach(function (row, i) { row.rank = i + 1; });
    return rows;
  }
  function regionSeries(key) {
    return years.map(function (y) {
      var byRegion = matrix[String(y)] || {};
      return { year: y, value: key in byRegion ? byRegion[key] : null };
    });
  }
  function averageSeries() {
    return years.map(function (y) {
      var byRegion = matrix[String(y)] || {};
      var keys = Object.keys(byRegion);
      if (!keys.length) return { year: y, value: null };
      var s = 0; keys.forEach(function (k) { s += byRegion[k]; });
      return { year: y, value: s / keys.length };
    });
  }
  function regionTrend(key) {
    var rows = regionSeries(key).filter(function (p) { return p.value !== null; });
    if (!rows.length) return { label: "n.d.", text: "Serie non disponibile", dir: "flat" };
    var first = rows[0], last = rows[rows.length - 1];
    var delta = last.value - first.value;
    return {
      label: delta > 0 ? "In crescita" : delta < 0 ? "In calo" : "Stabile",
      text: fmtValue(first.value) + " → " + fmtValue(last.value) + " (" + first.year + "-" + last.year + ")",
      dir: delta > 0 ? "up" : delta < 0 ? "down" : "flat",
    };
  }

  function rampColor(t) {
    var c = [0, 0, 0];
    for (var i = 0; i < 3; i++) c[i] = Math.round(ramp.from[i] + (ramp.to[i] - ramp.from[i]) * t);
    return "#" + c.map(function (n) { var h = n.toString(16); return h.length === 1 ? "0" + h : h; }).join("");
  }

  // ---- Elements -----------------------------------------------------------
  var yearInput = root.querySelector('[data-explore="year"]');
  var yearLabel = root.querySelector('[data-explore="year-label"]');
  var regionSelect = root.querySelector('[data-explore="region"]');
  var focusName = root.querySelector('[data-explore="focus-name"]');
  var focusValue = root.querySelector('[data-explore="focus-value"]');
  var focusRank = root.querySelector('[data-explore="focus-rank"]');
  var focusTrendEl = root.querySelector('[data-explore="focus-trend"]');
  var focusLink = root.querySelector('[data-explore="focus-link"]');

  var trendFig = document.querySelector('[data-explore="trend"]');
  var trendSvg = document.querySelector('[data-explore="trend-svg"]');
  var trendTitle = document.querySelector('[data-explore="trend-title"]');
  var trendTip = document.querySelector('[data-explore="trend-tip"]');
  var trendRegionEl = document.querySelector('[data-explore="trend-region"]');

  var rankingEl = document.querySelector('[data-explore="ranking"]');
  var mapEl = document.querySelector('[data-explore="map"]');
  var mapTip = document.querySelector('[data-explore="map-tip"]');
  var legendMin = document.querySelector('[data-explore="legend-min"]');
  var legendMid = document.querySelector('[data-explore="legend-mid"]');
  var legendMax = document.querySelector('[data-explore="legend-max"]');
  var tabsEl = document.querySelector('[data-explore="tabs"]');
  var vizGrid = document.querySelector('[data-explore="viz-grid"]');
  var yearTitles = document.querySelectorAll('[data-explore="year-title"]');
  var mapYearEls = document.querySelectorAll('[data-explore="map-year"]');
  var yearLabelEls = document.querySelectorAll('[data-explore="year-label"]');
  var bestNameEl = document.querySelector('[data-explore="best-name"]');
  var bestValueEl = document.querySelector('[data-explore="best-value"]');
  var worstNameEl = document.querySelector('[data-explore="worst-name"]');
  var worstValueEl = document.querySelector('[data-explore="worst-value"]');
  var avgValueEl = document.querySelector('[data-explore="avg-value"]');
  var avgCountEl = document.querySelector('[data-explore="avg-count"]');

  var SVGNS = "http://www.w3.org/2000/svg";

  // ---- Region select ------------------------------------------------------
  regions.forEach(function (r) {
    var opt = document.createElement("option");
    opt.value = r.key; opt.textContent = r.name;
    regionSelect.appendChild(opt);
  });

  // ---- Initial state ------------------------------------------------------
  var params = new URLSearchParams(location.search);
  var startYear = data.defaultYear || yearMax;
  var paramYear = parseInt(params.get("anno"), 10);
  if (!isNaN(paramYear) && years.indexOf(paramYear) !== -1) startYear = paramYear;
  var startRegion = regions.length ? regions[0].key : null;
  var paramRegion = params.get("regione");
  if (paramRegion && nameByKey[paramRegion]) startRegion = paramRegion;
  var state = { yearIndex: Math.max(0, years.indexOf(startYear)), regionKey: startRegion };

  yearInput.min = 0;
  yearInput.max = years.length - 1;
  yearInput.value = state.yearIndex;
  if (years.length < 2) { yearInput.disabled = true; yearInput.setAttribute("aria-hidden", "true"); }
  regionSelect.value = state.regionKey || "";

  function currentYear() { return years[state.yearIndex]; }
  function setText(nodes, value) { for (var i = 0; i < nodes.length; i++) nodes[i].textContent = value; }

  // ---- Trend chart --------------------------------------------------------
  var TREND_W = 640, TREND_H = 200;
  var PAD = { l: 46, r: 14, t: 14, b: 26 };
  var trendGeom = null;

  function buildTrend() {
    if (!trendSvg) return;
    while (trendSvg.firstChild) trendSvg.removeChild(trendSvg.firstChild);
    var focus = regionSeries(state.regionKey);
    var avg = averageSeries();
    var all = [];
    focus.forEach(function (p) { if (p.value !== null) all.push(p.value); });
    avg.forEach(function (p) { if (p.value !== null) all.push(p.value); });
    if (!all.length) { if (trendFig) trendFig.hidden = true; return; }
    if (trendFig) trendFig.hidden = false;

    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    if (lo === hi) { lo -= 1; hi += 1; }
    var padY = (hi - lo) * 0.08; lo -= padY; hi += padY;
    var span = (yearMax - yearMin) || 1;
    function sx(year) { return PAD.l + ((year - yearMin) / span) * (TREND_W - PAD.l - PAD.r); }
    function sy(value) { return PAD.t + (1 - (value - lo) / (hi - lo)) * (TREND_H - PAD.t - PAD.b); }
    trendGeom = { sx: sx, sy: sy };

    function el(name, attrs) { var n = document.createElementNS(SVGNS, name); for (var k in attrs) n.setAttribute(k, attrs[k]); return n; }
    function pathFor(series, cls) {
      var d = "", started = false;
      series.forEach(function (p) {
        if (p.value === null) { started = false; return; }
        d += (started ? "L" : "M") + sx(p.year).toFixed(1) + " " + sy(p.value).toFixed(1) + " ";
        started = true;
      });
      if (!d) return null;
      return el("path", { d: d.trim(), class: cls, fill: "none", "vector-effect": "non-scaling-stroke" });
    }
    [lo + padY, (lo + hi) / 2, hi - padY].forEach(function (v) {
      var y = sy(v);
      trendSvg.appendChild(el("line", { x1: PAD.l, x2: TREND_W - PAD.r, y1: y, y2: y, class: "trend-grid" }));
      var t = el("text", { x: PAD.l - 6, y: y + 3, class: "trend-axis", "text-anchor": "end" });
      t.textContent = fmtAxis(v); trendSvg.appendChild(t);
    });
    [yearMin, yearMax].forEach(function (yr, i) {
      var t = el("text", { x: sx(yr), y: TREND_H - 8, class: "trend-axis", "text-anchor": i === 0 ? "start" : "end" });
      t.textContent = yr; trendSvg.appendChild(t);
    });
    var avgPath = pathFor(avg, "trend-line trend-line--avg"); if (avgPath) trendSvg.appendChild(avgPath);
    var focusPath = pathFor(focus, "trend-line trend-line--focus"); if (focusPath) trendSvg.appendChild(focusPath);
    focus.forEach(function (p) { if (p.value !== null) trendSvg.appendChild(el("circle", { cx: sx(p.year), cy: sy(p.value), r: 2.6, class: "trend-dot" })); });
    var yr = currentYear();
    trendSvg.appendChild(el("line", { x1: sx(yr), x2: sx(yr), y1: PAD.t, y2: TREND_H - PAD.b, class: "trend-marker" }));
    var cur = focus[state.yearIndex];
    if (cur && cur.value !== null) trendSvg.appendChild(el("circle", { cx: sx(yr), cy: sy(cur.value), r: 4.5, class: "trend-dot trend-dot--current" }));
    if (trendTitle) trendTitle.textContent = (nameByKey[state.regionKey] || "") + " (arancio) vs media delle regioni (tratteggio)";
    if (trendRegionEl) trendRegionEl.textContent = nameByKey[state.regionKey] || "";
  }

  function trendYearFromEvent(evt) {
    if (!trendGeom) return null;
    var rect = trendSvg.getBoundingClientRect();
    var xPix = ((evt.clientX - rect.left) / rect.width) * TREND_W;
    var span = (yearMax - yearMin) || 1;
    var yr = yearMin + ((xPix - PAD.l) / (TREND_W - PAD.l - PAD.r)) * span;
    var best = years[0], bestD = Infinity;
    years.forEach(function (y) { var d = Math.abs(y - yr); if (d < bestD) { bestD = d; best = y; } });
    return best;
  }

  // ---- Map ----------------------------------------------------------------
  var mapNodes = mapEl ? mapEl.querySelectorAll("[data-key]") : [];
  function paintMap(rows) {
    if (!mapEl) return;
    var values = rows.map(function (r) { return r.value; });
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    var span = hi - lo;
    var present = {};
    rows.forEach(function (row) {
      var node = mapEl.querySelector('[data-key="' + row.key + '"]');
      if (node) node.style.fill = rampColor(span ? (row.value - lo) / span : 1);
      present[row.key] = true;
    });
    for (var n = 0; n < mapNodes.length; n++) {
      var key = mapNodes[n].getAttribute("data-key");
      if (!present[key]) mapNodes[n].style.fill = "";
      mapNodes[n].classList.toggle("is-selected", key === state.regionKey);
    }
    if (legendMin) legendMin.textContent = fmtAxis(lo);
    if (legendMid) legendMid.textContent = fmtAxis(lo + (hi - lo) / 2);
    if (legendMax) legendMax.textContent = fmtAxis(hi);
  }
  function wireMap() {
    if (!mapEl) return;
    for (var i = 0; i < mapNodes.length; i++) {
      (function (node) {
        var key = node.getAttribute("data-key");
        if (!nameByKey[key]) return;
        node.style.cursor = "pointer";
        node.addEventListener("click", function () { state.regionKey = key; regionSelect.value = key; sync(); });
        node.addEventListener("mousemove", function (evt) {
          if (!mapTip) return;
          var byRegion = valuesForYear(currentYear());
          var v = key in byRegion ? byRegion[key] : null;
          mapTip.hidden = false;
          mapTip.innerHTML = "<b>" + (nameByKey[key] || key) + "</b> " + (v === null ? "n.d." : fmtValue(v));
          var wrap = mapEl.getBoundingClientRect();
          mapTip.style.left = (evt.clientX - wrap.left) + "px";
          mapTip.style.top = (evt.clientY - wrap.top) + "px";
        });
        node.addEventListener("mouseleave", function () { if (mapTip) mapTip.hidden = true; });
      })(mapNodes[i]);
    }
  }

  // ---- Tabs (mobile) ------------------------------------------------------
  function wireTabs() {
    if (!tabsEl || !vizGrid) return;
    tabsEl.hidden = false;
    var btns = tabsEl.querySelectorAll("button[data-tab]");
    btns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = btn.getAttribute("data-tab");
        vizGrid.className = "viz-grid active-" + tab;
        btns.forEach(function (b) { b.classList.toggle("is-active", b === btn); });
      });
    });
  }

  // ---- Render -------------------------------------------------------------
  function render() {
    var year = currentYear();
    var rows = ranked(year);
    var count = rows.length;
    var focus = null;
    for (var i = 0; i < rows.length; i++) { if (rows[i].key === state.regionKey) { focus = rows[i]; break; } }
    var focusNameStr = nameByKey[state.regionKey] || "-";

    if (yearLabel) yearLabel.textContent = year;
    setText(yearTitles, year);
    setText(mapYearEls, year);
    setText(yearLabelEls, year);

    // Focus region readout.
    if (focusName) focusName.textContent = focusNameStr + " · " + year;
    if (focusValue) focusValue.textContent = focus ? fmtValue(focus.value) : "n.d.";
    if (focusRank) focusRank.textContent = focus ? focus.rank + "ª su " + count + " regioni" : "dato non disponibile per il " + year;
    if (focusTrendEl) {
      var tr = regionTrend(state.regionKey);
      focusTrendEl.textContent = tr.label + " · " + tr.text;
      focusTrendEl.className = "insight__trend is-" + tr.dir;
    }
    if (focusLink && state.regionKey) {
      focusLink.setAttribute("href", "/regione/" + state.regionKey);
      focusLink.textContent = "Come è messa " + focusNameStr + " →";
    }

    // Ranking with bars.
    if (rankingEl) {
      var barMax = Math.max.apply(null, rows.map(function (r) { return r.value; }).concat([0]));
      var html = "";
      rows.forEach(function (row) {
        var w = barMax ? (row.value / barMax) * 100 : 0;
        var active = row.key === state.regionKey ? " is-active" : "";
        html +=
          '<div class="ranking-row' + active + '" data-region-key="' + row.key + '">' +
          '<span class="rank">' + row.rank + "</span>" +
          '<a class="region" href="/regione/' + row.key + '">' + row.name + "</a>" +
          '<span class="bar"><i style="width:' + Math.max(w, 2).toFixed(1) + '%"></i></span>' +
          '<strong class="num">' + numberFmt.format(row.value) + "</strong></div>";
      });
      rankingEl.innerHTML = html;
    }

    paintMap(rows);

    // Insight tiles.
    if (rows.length) {
      var sum = 0; rows.forEach(function (r) { sum += r.value; });
      if (avgValueEl) avgValueEl.textContent = numberFmt.format(sum / rows.length);
      if (avgCountEl) avgCountEl.textContent = count;
      if (scoreable) {
        var best = rows[0], worst = rows[rows.length - 1];
        if (bestNameEl) { bestNameEl.textContent = best.name; bestNameEl.setAttribute("href", "/regione/" + best.key); }
        if (bestValueEl) bestValueEl.textContent = numberFmt.format(best.value);
        if (worstNameEl) { worstNameEl.textContent = worst.name; worstNameEl.setAttribute("href", "/regione/" + worst.key); }
        if (worstValueEl) worstValueEl.textContent = numberFmt.format(worst.value);
      }
    }

    buildTrend();
  }

  function sync() {
    var qs = "?anno=" + currentYear() + "&regione=" + encodeURIComponent(state.regionKey || "");
    try { history.replaceState(null, "", basePath + qs); } catch (err) { /* ignore */ }
    render();
  }

  yearInput.addEventListener("input", function () { state.yearIndex = Number(yearInput.value); sync(); });
  regionSelect.addEventListener("change", function () { state.regionKey = regionSelect.value; sync(); });

  if (rankingEl) {
    rankingEl.addEventListener("click", function (evt) {
      var row = evt.target.closest(".ranking-row");
      if (!row || evt.target.closest("a")) return;
      var key = row.getAttribute("data-region-key");
      if (!key || !nameByKey[key]) return;
      state.regionKey = key; regionSelect.value = key; sync();
    });
  }

  if (trendSvg) {
    trendSvg.addEventListener("click", function (evt) {
      var yr = trendYearFromEvent(evt);
      if (yr == null) return;
      state.yearIndex = years.indexOf(yr); yearInput.value = state.yearIndex; sync();
    });
    trendSvg.addEventListener("mousemove", function (evt) {
      if (!trendTip || !trendGeom) return;
      var yr = trendYearFromEvent(evt);
      var byRegion = matrix[String(yr)] || {};
      var v = state.regionKey in byRegion ? byRegion[state.regionKey] : null;
      trendTip.hidden = false;
      trendTip.innerHTML = "<b>" + yr + "</b> " + (v === null ? "n.d." : fmtValue(v));
      var rect = trendSvg.getBoundingClientRect();
      trendTip.style.left = (evt.clientX - rect.left) + "px";
      trendTip.style.top = (evt.clientY - rect.top) + "px";
    });
    trendSvg.addEventListener("mouseleave", function () { if (trendTip) trendTip.hidden = true; });
  }

  wireMap();
  wireTabs();

  root.hidden = false;
  // Signal that the interactive trend chart is live, so the static sparkline
  // fallback lower on the page can hide itself (CSS: .has-explorer ...).
  document.documentElement.classList.add("has-explorer");
  if (params.has("anno") || params.has("regione")) sync();
  else render();
})();
