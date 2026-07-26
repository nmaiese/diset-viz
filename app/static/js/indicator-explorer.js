/*
 * Indicator cockpit (progressive enhancement).
 *
 * The server renders the facts, the KPI row, the ranking and the choropleth for
 * one territorial level as plain, crawlable HTML. This script reads the full
 * year x territory matrix for every level from <script id="indicator-data"> and
 * makes that same markup interactive: a year slider and a focus selector drive
 * the KPI row, the ranking, the map and a time-series chart in place, plus
 * Map/Ranking/Series tabs on mobile.
 *
 * Two things it must get right, both learned from the previous version:
 *
 * 1. Levels. A BES indicator has regions AND provinces, with different years and
 *    different territories, and provinces have no profile page and no map. The
 *    old script hardcoded "region" in six places, including the /regione/ link.
 *    Everything territorial is read off the active level here.
 * 2. Failing loudly is better than failing silently. The old script dereferenced
 *    two elements without a null check, so a markup rename left the whole
 *    cockpit hidden with no error anyone would notice. Nothing is required now,
 *    and the server-rendered state stays visible whatever happens.
 *
 * One canonical URL per indicator: exploration states only touch the query
 * string via history.replaceState and are served noindex.
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
  if (!data || !Array.isArray(data.levels) || !data.levels.length) return;

  var levelsByKey = {};
  data.levels.forEach(function (level) {
    level.nameByKey = {};
    (level.territories || []).forEach(function (t) { level.nameByKey[t.key] = t.name; });
    levelsByKey[level.key] = level;
  });

  var higherBetter = data.higherBetter !== false;
  var unit = data.unit || "";
  var changeUnit = data.changeUnit || "";
  var ramp = data.ramp || { from: [0xe7, 0xec, 0xf3], to: [0x15, 0x23, 0x3b] };
  var basePath = location.pathname;
  var SVGNS = "http://www.w3.org/2000/svg";

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
  function fmtSigned(v) {
    return (v > 0 ? "+" : "") + numberFmt.format(v);
  }

  // ---- State --------------------------------------------------------------
  var params = new URLSearchParams(location.search);
  var state = { levelKey: null, yearIndex: 0, territoryKey: null };

  function level() { return levelsByKey[state.levelKey]; }
  function years() { return level().years; }
  function currentYear() { return years()[state.yearIndex]; }
  function valuesForYear(year) { return (level().matrix || {})[String(year)] || {}; }

  function ranked(year) {
    var byKey = valuesForYear(year);
    var rows = Object.keys(byKey).map(function (key) {
      return { key: key, name: level().nameByKey[key] || key, value: byKey[key] };
    });
    // Same rule the server applies, ties included, so the client-side ranking
    // never disagrees with the one that was rendered into the HTML.
    rows.sort(function (a, b) {
      if (a.value !== b.value) return higherBetter ? b.value - a.value : a.value - b.value;
      return a.name.localeCompare(b.name, "it");
    });
    rows.forEach(function (row, i) { row.rank = i + 1; });
    return rows;
  }

  function territorySeries(key) {
    return years().map(function (y) {
      var byKey = (level().matrix || {})[String(y)] || {};
      return { year: y, value: key in byKey ? byKey[key] : null };
    });
  }

  function averageSeries() {
    return years().map(function (y) {
      var byKey = (level().matrix || {})[String(y)] || {};
      var keys = Object.keys(byKey);
      if (!keys.length) return { year: y, value: null };
      var sum = 0;
      keys.forEach(function (k) { sum += byKey[k]; });
      return { year: y, value: sum / keys.length };
    });
  }

  /* Mean change against the previous year that actually has data, over the
     territories present in both. Same rule as the server's year-over-year
     comparison, so the KPI does not contradict the article. */
  function changeAgainstPreviousYear(year) {
    var all = years();
    var index = all.indexOf(year);
    if (index < 1) return null;
    var current = valuesForYear(year);
    var previous = valuesForYear(all[index - 1]);
    var common = Object.keys(current).filter(function (key) { return key in previous; });
    if (!common.length) return null;
    var currentSum = 0, previousSum = 0;
    common.forEach(function (key) { currentSum += current[key]; previousSum += previous[key]; });
    return { from: all[index - 1], delta: currentSum / common.length - previousSum / common.length };
  }

  function rampColor(t) {
    var c = [0, 0, 0];
    for (var i = 0; i < 3; i++) c[i] = Math.round(ramp.from[i] + (ramp.to[i] - ramp.from[i]) * t);
    return "#" + c.map(function (n) { var h = n.toString(16); return h.length === 1 ? "0" + h : h; }).join("");
  }

  // ---- Elements (all optional) --------------------------------------------
  function one(selector, scope) { return (scope || document).querySelector(selector); }
  function all(selector, scope) { return Array.prototype.slice.call((scope || document).querySelectorAll(selector)); }
  function kpi(name) { return one('[data-kpi="' + name + '"]'); }

  var yearInput = one('[data-explore="year"]', root);
  var territorySelect = one('[data-explore="territory"]', root);
  var levelSwitch = one('[data-explore="levels"]', root);
  var yearLabels = all('[data-explore="year-label"]');

  var rankingEl = one('[data-explore="ranking"]');
  var mapCard = one('[data-tabpanel="map"]');
  var mapEl = one('[data-explore="map"]');
  var mapTip = one('[data-explore="map-tip"]');
  var legendMin = one('[data-explore="legend-min"]');
  var legendMid = one('[data-explore="legend-mid"]');
  var legendMax = one('[data-explore="legend-max"]');
  var tabsEl = one('[data-explore="tabs"]');
  var vizGrid = one('[data-explore="viz-grid"]');

  var trendFig = one('[data-explore="trend"]');
  var trendSvg = one('[data-explore="trend-svg"]');
  var trendTitle = one('[data-explore="trend-title"]');
  var trendTip = one('[data-explore="trend-tip"]');
  var trendRegionEl = one('[data-explore="trend-region"]');

  function setText(node, value) { if (node) node.textContent = value; }

  // ---- Level ---------------------------------------------------------------
  // Runs once, at boot, on the level the server rendered: switching level is a
  // navigation, not an in-place swap.
  function applyLevel(key) {
    if (!levelsByKey[key]) return;
    state.levelKey = key;
    var lv = level();

    state.yearIndex = lv.years.length - 1;

    if (territorySelect) {
      territorySelect.innerHTML = "";
      (lv.territories || []).forEach(function (t) {
        var opt = document.createElement("option");
        opt.value = t.key;
        opt.textContent = t.name;
        territorySelect.appendChild(opt);
      });
      if (!lv.nameByKey[state.territoryKey]) {
        // The level's own default, which is what the server rendered. Falling
        // back to territories[0] picked the alphabetically first territory and
        // made the focus tile jump on load.
        state.territoryKey = lv.defaultTerritory
          || (lv.territories.length ? lv.territories[0].key : null);
      }
      territorySelect.value = state.territoryKey || "";
      var label = territorySelect.closest(".cockpit-control");
      var span = label ? label.querySelector("span") : null;
      if (span) span.textContent = lv.singular.charAt(0).toUpperCase() + lv.singular.slice(1) + " a fuoco";
    }

    if (yearInput) {
      yearInput.min = 0;
      yearInput.max = lv.years.length - 1;
      yearInput.value = state.yearIndex;
      yearInput.disabled = lv.years.length < 2;
    }

    // Provinces have no map. Hide the card and its tab rather than leaving an
    // empty panel behind, and fall back to the ranking if the map tab was open.
    if (mapCard) mapCard.hidden = !lv.hasMap;
    var mapTab = tabsEl ? one('button[data-tab="map"]', tabsEl) : null;
    if (mapTab) {
      mapTab.hidden = !lv.hasMap;
      if (!lv.hasMap && mapTab.classList.contains("is-active")) selectTab("ranking");
    }
    if (vizGrid) vizGrid.classList.toggle("has-no-map", !lv.hasMap);

    if (levelSwitch) {
      all("[data-level]", levelSwitch).forEach(function (node) {
        var active = node.getAttribute("data-level") === key;
        node.classList.toggle("is-active", active);
        if (active) node.setAttribute("aria-current", "true");
        else node.removeAttribute("aria-current");
      });
    }
  }

  // ---- Trend chart --------------------------------------------------------
  var TREND_W = 640, TREND_H = 200;
  var PAD = { l: 46, r: 14, t: 14, b: 26 };
  var trendGeom = null;

  function buildTrend() {
    if (!trendSvg) return;
    while (trendSvg.firstChild) trendSvg.removeChild(trendSvg.firstChild);
    var focus = territorySeries(state.territoryKey);
    var avg = averageSeries();
    var values = [];
    focus.forEach(function (p) { if (p.value !== null) values.push(p.value); });
    avg.forEach(function (p) { if (p.value !== null) values.push(p.value); });
    if (!values.length) { if (trendFig) trendFig.hidden = true; return; }
    if (trendFig) trendFig.hidden = false;

    var yearList = years();
    var yearMin = yearList[0], yearMax = yearList[yearList.length - 1];
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    if (lo === hi) { lo -= 1; hi += 1; }
    var padY = (hi - lo) * 0.08;
    lo -= padY; hi += padY;
    var span = (yearMax - yearMin) || 1;
    function sx(year) { return PAD.l + ((year - yearMin) / span) * (TREND_W - PAD.l - PAD.r); }
    function sy(value) { return PAD.t + (1 - (value - lo) / (hi - lo)) * (TREND_H - PAD.t - PAD.b); }
    trendGeom = { sx: sx, sy: sy, yearMin: yearMin, yearMax: yearMax };

    function el(name, attrs) {
      var node = document.createElementNS(SVGNS, name);
      for (var k in attrs) node.setAttribute(k, attrs[k]);
      return node;
    }
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
      t.textContent = fmtAxis(v);
      trendSvg.appendChild(t);
    });
    [yearMin, yearMax].forEach(function (yr, i) {
      var t = el("text", { x: sx(yr), y: TREND_H - 8, class: "trend-axis", "text-anchor": i === 0 ? "start" : "end" });
      t.textContent = yr;
      trendSvg.appendChild(t);
    });

    var avgPath = pathFor(avg, "trend-line trend-line--avg");
    if (avgPath) trendSvg.appendChild(avgPath);
    var focusPath = pathFor(focus, "trend-line trend-line--focus");
    if (focusPath) trendSvg.appendChild(focusPath);
    focus.forEach(function (p) {
      if (p.value !== null) trendSvg.appendChild(el("circle", { cx: sx(p.year), cy: sy(p.value), r: 2.6, class: "trend-dot" }));
    });

    var yr = currentYear();
    trendSvg.appendChild(el("line", { x1: sx(yr), x2: sx(yr), y1: PAD.t, y2: TREND_H - PAD.b, class: "trend-marker" }));
    var cur = focus[state.yearIndex];
    if (cur && cur.value !== null) {
      trendSvg.appendChild(el("circle", { cx: sx(yr), cy: sy(cur.value), r: 4.5, class: "trend-dot trend-dot--current" }));
    }
    var focusName = level().nameByKey[state.territoryKey] || "";
    setText(trendTitle, focusName + " (arancio) vs media delle " + level().plural + " (tratteggio)");
    setText(trendRegionEl, focusName);
  }

  function trendYearFromEvent(evt) {
    if (!trendGeom || !trendSvg) return null;
    var rect = trendSvg.getBoundingClientRect();
    var xPix = ((evt.clientX - rect.left) / rect.width) * TREND_W;
    var span = (trendGeom.yearMax - trendGeom.yearMin) || 1;
    var approx = trendGeom.yearMin + ((xPix - PAD.l) / (TREND_W - PAD.l - PAD.r)) * span;
    var best = null, bestDistance = Infinity;
    years().forEach(function (y) {
      var d = Math.abs(y - approx);
      if (d < bestDistance) { bestDistance = d; best = y; }
    });
    return best;
  }

  // ---- Map ----------------------------------------------------------------
  function paintMap(rows) {
    if (!mapEl || !level().hasMap) return;
    var nodes = all("[data-key]", mapEl);
    var values = rows.map(function (r) { return r.value; });
    if (!values.length) return;
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    var span = hi - lo;
    var present = {};
    rows.forEach(function (row) {
      var node = one('[data-key="' + row.key + '"]', mapEl);
      if (node) node.style.fill = rampColor(span ? (row.value - lo) / span : 1);
      present[row.key] = true;
    });
    nodes.forEach(function (node) {
      var key = node.getAttribute("data-key");
      if (!present[key]) node.style.fill = "";
      node.classList.toggle("is-selected", key === state.territoryKey);
    });
    setText(legendMin, fmtAxis(lo));
    setText(legendMid, fmtAxis(lo + (hi - lo) / 2));
    setText(legendMax, fmtAxis(hi));
  }

  function wireMap() {
    if (!mapEl) return;
    all("[data-key]", mapEl).forEach(function (node) {
      var key = node.getAttribute("data-key");
      node.style.cursor = "pointer";
      node.addEventListener("click", function () {
        if (!level().nameByKey[key]) return;
        state.territoryKey = key;
        if (territorySelect) territorySelect.value = key;
        sync();
      });
      node.addEventListener("mousemove", function (evt) {
        if (!mapTip || !level().hasMap) return;
        var byKey = valuesForYear(currentYear());
        var value = key in byKey ? byKey[key] : null;
        mapTip.hidden = false;
        mapTip.innerHTML = "<b>" + (level().nameByKey[key] || key) + "</b> " + (value === null ? "n.d." : fmtValue(value));
        var wrap = mapEl.getBoundingClientRect();
        mapTip.style.left = (evt.clientX - wrap.left) + "px";
        mapTip.style.top = (evt.clientY - wrap.top) + "px";
      });
      node.addEventListener("mouseleave", function () { if (mapTip) mapTip.hidden = true; });
    });
  }

  // ---- Tabs (mobile) ------------------------------------------------------
  function selectTab(tab) {
    if (!vizGrid || !tabsEl) return;
    // classList, not className: the grid also carries state classes now, and
    // rewriting className wholesale used to wipe them.
    ["map", "ranking", "trend"].forEach(function (name) {
      vizGrid.classList.toggle("active-" + name, name === tab);
    });
    all("button[data-tab]", tabsEl).forEach(function (btn) {
      btn.classList.toggle("is-active", btn.getAttribute("data-tab") === tab);
    });
  }

  function wireTabs() {
    if (!tabsEl || !vizGrid) return;
    tabsEl.hidden = false;
    all("button[data-tab]", tabsEl).forEach(function (btn) {
      btn.addEventListener("click", function () { selectTab(btn.getAttribute("data-tab")); });
    });
  }

  // ---- Render -------------------------------------------------------------
  function render() {
    var lv = level();
    var year = currentYear();
    var rows = ranked(year);
    var count = rows.length;
    var focus = null;
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].key === state.territoryKey) { focus = rows[i]; break; }
    }
    var focusName = lv.nameByKey[state.territoryKey] || "-";

    yearLabels.forEach(function (node) { node.textContent = year; });

    setText(kpi("focus-name"), focusName);
    // Bare number, like every other KPI and like the server-rendered value:
    // the unit is declared once in the facts strip, and formatting this one
    // differently made the tile visibly change on hydration.
    setText(kpi("focus-value"), focus ? numberFmt.format(focus.value) : "n.d.");
    setText(
      kpi("focus-rank"),
      focus ? focus.rank + "ª su " + count + " " + lv.plural : "dato non disponibile nel " + year
    );
    var focusLink = kpi("focus-link");
    if (focusLink) {
      if (lv.profilePath && state.territoryKey) {
        focusLink.hidden = false;
        focusLink.setAttribute("href", lv.profilePath + state.territoryKey);
      } else {
        focusLink.hidden = true;
      }
    }

    if (rows.length) {
      var top = rows[0], bottom = rows[rows.length - 1];
      setText(kpi("top-value"), numberFmt.format(top.value));
      setText(kpi("top-name"), top.name);
      setText(kpi("bottom-value"), numberFmt.format(bottom.value));
      setText(kpi("bottom-name"), bottom.name);

      var sum = 0;
      rows.forEach(function (r) { sum += r.value; });
      setText(kpi("mean-value"), numberFmt.format(sum / rows.length));
      setText(kpi("mean-count"), count);

      var high = Math.max(top.value, bottom.value), low = Math.min(top.value, bottom.value);
      setText(kpi("gap-value"), numberFmt.format(high - low));
      var gapRatio = kpi("gap-ratio");
      if (gapRatio) {
        // Below 1,2 a ratio rounds to "1,0 volte" and reads as broken next to a
        // non-zero gap, so the unit is shown instead. Same threshold as the server.
        gapRatio.textContent = low > 0 && high / low >= 1.2
          ? compactFmt.format(high / low) + "× il più basso"
          : changeUnit;
      }
    }

    var change = changeAgainstPreviousYear(year);
    var changeValue = kpi("change-value");
    if (changeValue) {
      changeValue.textContent = change ? fmtSigned(change.delta) : "n.d.";
      setText(kpi("change-from"), change ? change.from : "-");
      var changeCard = changeValue.closest(".kpi");
      if (changeCard) changeCard.hidden = !change;
    }

    if (rankingEl) {
      var barMax = Math.max.apply(null, rows.map(function (r) { return r.value; }).concat([0]));
      var html = "";
      rows.forEach(function (row) {
        var width = barMax ? (row.value / barMax) * 100 : 0;
        var active = row.key === state.territoryKey ? " is-active" : "";
        var label = lv.profilePath
          ? '<a class="region" href="' + lv.profilePath + row.key + '">' + row.name + "</a>"
          : '<span class="region">' + row.name + "</span>";
        html +=
          '<div class="ranking-row' + active + '" data-region-key="' + row.key + '">' +
          '<span class="rank">' + row.rank + "</span>" + label +
          '<span class="bar"><i style="width:' + Math.max(width, 2).toFixed(1) + '%"></i></span>' +
          '<strong class="num">' + numberFmt.format(row.value) + "</strong></div>";
      });
      rankingEl.innerHTML = html;
    }

    paintMap(rows);
    buildTrend();
  }

  function sync() {
    var qs = "?anno=" + currentYear() + "&livello=" + encodeURIComponent(state.levelKey) +
      "&regione=" + encodeURIComponent(state.territoryKey || "");
    try { history.replaceState(null, "", basePath + qs); } catch (err) { /* ignore */ }
    render();
  }

  // ---- Wiring -------------------------------------------------------------
  if (yearInput) {
    yearInput.addEventListener("input", function () {
      state.yearIndex = Number(yearInput.value);
      sync();
    });
  }
  if (territorySelect) {
    territorySelect.addEventListener("change", function () {
      state.territoryKey = territorySelect.value;
      sync();
    });
  }
  // The level switch is left to the browser on purpose. Swapping it in place
  // updated only what this script owns, the controls, the KPIs, the ranking and
  // the trend, while the facts strip, the four-section article, the sources and
  // the citation kept the level the server had rendered: a provincial cockpit
  // under regional prose. Starting from ?livello=provincia there is no map in
  // the DOM either, so switching back could not have restored it. A full
  // navigation costs one server render and every block agrees.
  if (rankingEl) {
    rankingEl.addEventListener("click", function (evt) {
      var row = evt.target.closest(".ranking-row");
      if (!row || evt.target.closest("a")) return;
      var key = row.getAttribute("data-region-key");
      if (!key || !level().nameByKey[key]) return;
      state.territoryKey = key;
      if (territorySelect) territorySelect.value = key;
      sync();
    });
  }
  if (trendSvg) {
    trendSvg.addEventListener("click", function (evt) {
      var yr = trendYearFromEvent(evt);
      if (yr === null) return;
      state.yearIndex = years().indexOf(yr);
      if (yearInput) yearInput.value = state.yearIndex;
      sync();
    });
    trendSvg.addEventListener("mousemove", function (evt) {
      if (!trendTip || !trendGeom) return;
      var yr = trendYearFromEvent(evt);
      var byKey = (level().matrix || {})[String(yr)] || {};
      var value = state.territoryKey in byKey ? byKey[state.territoryKey] : null;
      trendTip.hidden = false;
      trendTip.innerHTML = "<b>" + yr + "</b> " + (value === null ? "n.d." : fmtValue(value));
      var rect = trendSvg.getBoundingClientRect();
      trendTip.style.left = (evt.clientX - rect.left) + "px";
      trendTip.style.top = (evt.clientY - rect.top) + "px";
    });
    trendSvg.addEventListener("mouseleave", function () { if (trendTip) trendTip.hidden = true; });
  }

  // ---- Boot ---------------------------------------------------------------
  var startLevel = params.get("livello");
  if (!levelsByKey[startLevel]) startLevel = data.defaultLevel || data.levels[0].key;
  state.territoryKey = params.get("regione") || null;
  applyLevel(startLevel);

  var paramYear = parseInt(params.get("anno"), 10);
  if (!isNaN(paramYear) && years().indexOf(paramYear) !== -1) {
    state.yearIndex = years().indexOf(paramYear);
    if (yearInput) yearInput.value = state.yearIndex;
  }

  wireMap();
  wireTabs();
  // The server deliberately ships no active-* class, so the no-JS mobile layout
  // shows every card. Now that the tabs work, pick one.
  selectTab(level().hasMap ? "map" : "ranking");

  // Signal that the interactive chart is live, for any CSS fallback.
  document.documentElement.classList.add("has-explorer");
  render();
})();
