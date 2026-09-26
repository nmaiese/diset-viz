/* Il confronto della 1.0: cambiare indicatore, territori e anno senza ricaricare.

   La pagina arriva completa dal server (app/design/pages/confronto.py): il
   form GET e' il modo di cambiare confronto senza JavaScript. Qui il form
   resta lo stesso, ma ogni campo applica la scelta subito: si legge
   /api/indicator/<id> (una volta per indicatore), si ridisegnano la frase in
   testa, la mappa, la tabella, la serie e la sua tabella, e lo stato torna
   nell'URL con replaceState e con i nomi del server (indicator, region fino a
   tre volte, year, livello), cosi' un link condiviso riapre la stessa vista.
   Se l'API non risponde si manda il form, come senza JavaScript.

   Lo stesso per le province (`cfg.level` "provincia"): i territori stanno in
   `provincia` fino a tre volte (`cfg.param`), i dati in
   /api/indicator/<id>?livello=provincia, nella stessa forma, e il selettore
   delle province e' diviso per regione (`cfg.groups`). Il livello si cambia
   con i link del selettore in testa, che ricaricano: qui si riscrive solo il
   loro indirizzo quando cambia l'indicatore (`switchHref`).

   Le cifre si scrivono con la regola di numfmt (decimali della grandezza,
   decimali di colonna sulla mediana), e la serie ha gli stessi due tagli e
   gli stessi numeri di `charts.compare_series`: la pagina servita e quella
   ridisegnata devono dire la stessa cosa.

   I confronti salvati (docs/ACCOUNT.md) compaiono solo a chi ha fatto
   l'accesso: il token lo da' window.diAuth (frontend/src/site/auth.js), che
   senza una sessione salvata risponde null senza caricare la libreria.

   Gli eventi hanno i nomi del resto del sito (docs/tracking_spec.md): la page
   view la manda il server con page_type "atlas", come la SPA di prima;
   compare_select_indicator (non select_indicator, che e' la conversione
   dell'atlante), change_region e change_year quando cambia il confronto, con
   il livello in `level`, open_region quando si apre il profilo di una regione
   dalla tabella, open_province quello di una provincia. */
(function () {
  "use strict";
  var root = document.querySelector('[data-v1="confronto"]');
  var dataEl = root && root.querySelector("[data-cmp-data]");
  if (!dataEl || !window.fetch || !window.URLSearchParams) return;
  var cfg = JSON.parse(dataEl.textContent);

  var $ = function (sel) { return root.querySelector(sel); };
  var all = function (sel, el) { return Array.prototype.slice.call((el || root).querySelectorAll(sel)); };
  var form = $("[data-cmp-form]");
  var indSel = $("[data-cmp-indicator]");
  var regionSels = all("[data-cmp-region]");
  var yearSel = $("[data-cmp-year]");
  var live = $("[data-cmp-live]");
  var THIN = " ";
  var DEFAULT_REGIONS = ["lombardia", "lazio", "campania"];
  var DEFAULT_PROVINCES = ["milano", "roma", "napoli"];
  var DEFAULTS = { regione: DEFAULT_REGIONS, provincia: DEFAULT_PROVINCES };
  // I nomi dei territori nell'URL per livello, come `LEVELS` di confronto.py.
  var PARAMS = { regione: "region", provincia: "provincia" };

  var state = { level: cfg.level, indicator: cfg.indicator, regions: cfg.regions.slice(), year: cfg.year };
  var models = {};   // id -> promessa del modello
  var model = null;  // il modello dell'indicatore in pagina
  var seq = 0;       // l'ultima richiesta: una risposta vecchia non ridisegna

  /* ---------- cifre, come numfmt ---------- */
  function decimals(v) {
    var m = Math.abs(v);
    if (m === 0 || m >= 100) return 0;
    if (m >= 1) return 1;
    if (m >= 0.01) return 2;
    return m >= 0.001 ? 3 : 4;
  }
  function columnDecimals(values) {
    var vals = values.filter(function (v) { return v !== null && v !== undefined; })
      .map(Math.abs).sort(function (a, b) { return a - b; });
    if (!vals.length) return 0;
    var median = vals[Math.floor(vals.length / 2)];
    return median ? decimals(median) : 2;
  }
  function fmt(v, d) {
    if (v === null || v === undefined || isNaN(v)) return "n.d.";
    if (d === undefined || d === null) d = decimals(v);
    var s = new Intl.NumberFormat("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }).format(Math.abs(v));
    var zero = Number(s.replace(/\./g, "").replace(",", ".")) === 0;
    return (v < 0 && !zero ? "-" : "") + s;
  }
  function withUnit(v, unit, d) {
    if (v === null || v === undefined) return "n.d.";
    if (unit === "%") return fmt(v, d) + "%";
    return unit ? fmt(v, d) + " " + unit : fmt(v, d);
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  // Il `<data>` di numfmt.num, ruolo "cell".
  function numHtml(v, unit, d) {
    if (v === null || v === undefined) return '<span class="n n--nd"><abbr title="dato non disponibile">n.d.</abbr></span>';
    var u = unit === "%" ? '<span class="n__u n__u--pct">%</span>' : unit ? '<span class="n__u">' + THIN + esc(unit) + "</span>" : "";
    return '<data class="n n--cell" value="' + Number(v.toPrecision(6)) + '">' + esc(fmt(v, d)) + u + "</data>";
  }
  function rankHtml(pos, total) {
    if (!pos) return '<span class="n n--nd">n.d.</span>';
    return '<span class="n n--rank"><data value="' + pos + '">' + pos + '</data><span class="n__o">ª</span>' +
      '<span class="n__u">' + THIN + "su " + total + "</span></span>";
  }

  /* ---------- il modello di un indicatore, da /api/indicator/<id> ---------- */
  function build(payload) {
    var names = {}, matrix = {};
    payload.series.forEach(function (r) {
      if (r.value === null || r.value === undefined) return;
      names[r.region_key] = r.region;
      (matrix[r.year] = matrix[r.year] || {})[r.region_key] = r.value;
    });
    var years = Object.keys(matrix).map(Number).sort(function (a, b) { return a - b; });
    var meta = payload.metadata;
    var dir = (meta.explain || {}).direction;
    var opt = indSel.querySelector('option[value="' + CSS.escape(String(meta.id)) + '"]');
    return {
      meta: meta, names: names, matrix: matrix, years: years,
      lowerBetter: dir === "lower_better" || dir === "higher_worse",
      unit: opt ? opt.getAttribute("data-u") || "" : ""
    };
  }
  function load(id) {
    var url = "/api/indicator/" + encodeURIComponent(id) + (cfg.level === "regione" ? "" : "?livello=" + cfg.level);
    if (!models[id]) {
      models[id] = fetch(url, { credentials: "omit" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(build);
      models[id].catch(function () { delete models[id]; });
    }
    return models[id];
  }

  /* ---------- lo stato: le stesse regole di resolve_state ---------- */
  function norm(s) {
    return String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
  }
  function normalize(m, wanted) {
    var byNorm = {};
    Object.keys(m.names).forEach(function (k) { byNorm[norm(k)] = k; byNorm[norm(m.names[k])] = k; });
    var regions = [];
    (wanted.regions || []).forEach(function (v) {
      var k = byNorm[norm(v)];
      if (k && regions.indexOf(k) < 0) regions.push(k);
    });
    regions = regions.slice(0, cfg.max);
    if (!regions.length) {
      regions = DEFAULTS[state.level].filter(function (k) { return m.names[k]; });
      if (!regions.length) regions = Object.keys(m.names).sort().slice(0, cfg.max);
    }
    var year = Number(wanted.year);
    if (m.years.indexOf(year) < 0) year = m.years[m.years.length - 1];
    return { level: state.level, indicator: String(m.meta.id), regions: regions, year: year };
  }
  function isDefault(s) {
    var d = cfg["default"];
    return s.indicator === d.indicator && s.year === d.year && s.level === d.level &&
      s.regions.join(",") === d.regions.join(",");
  }
  function writeUrl() {
    var url = new URL(location.href);
    ["indicator", "indicatore", "region", "regione", "provincia", "year", "anno", "livello", "view"].forEach(function (k) { url.searchParams.delete(k); });
    if (!isDefault(state)) {
      url.searchParams.set("indicator", state.indicator);
      state.regions.forEach(function (k) { url.searchParams.append(cfg.param, k); });
      if (state.year !== model.years[model.years.length - 1]) url.searchParams.set("year", String(state.year));
    }
    // La pagina nuda delle province e' `?livello=provincia`, non `/confronto`.
    if (state.level !== "regione") url.searchParams.set("livello", state.level);
    history.replaceState(history.state, "", url.pathname + url.search + url.hash);
  }

  /* ---------- eventi, come trackEvent di prima ---------- */
  function track(name, extra) {
    var params = { page_type: "atlas", page_path: location.pathname + location.search, page_title: document.title, level: state.level };
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

  /* ---------- la serie, come charts.compare_series ---------- */
  var CUTS = [["chart__l", 920, 320, 200, false], ["chart__s", 360, 260, 112, true]];
  // charts.SHORT_NAMES, regioni e province (una prova le confronta).
  var SHORT = { "Trentino Alto Adige": "Trentino A.A.", "Trentino-Alto Adige": "Trentino A.A.",
    "Friuli-Venezia Giulia": "Friuli V.G.", "Friuli Venezia Giulia": "Friuli V.G.",
    "Monza e della Brianza": "Monza Brianza", "Reggio Calabria": "Reggio Cal.",
    "Reggio nell'Emilia": "Reggio Emilia", "Barletta-Andria-Trani": "Barletta A.T.",
    "Verbano-Cusio-Ossola": "Verbano C.O.", "Pesaro e Urbino": "Pesaro Urbino",
    "Valle d'Aosta": "Valle d'Aosta", "Emilia-Romagna": "Emilia-Romagna" };
  function shortName(name, limit) {
    if (name.length <= limit) return name;
    if (SHORT[name]) return SHORT[name];
    var out = "";
    // Le parole tengono il loro separatore. Niente lookbehind: su Safari prima
    // della 16.4 e' un errore di sintassi e l'isola intera non partirebbe.
    var parts = name.split(/([ -])/), words = [];
    for (var j = 0; j < parts.length; j += 2) words.push(parts[j] + (parts[j + 1] || ""));
    for (var i = 0; i < words.length; i++) {
      if ((out + words[i]).length > limit) break;
      out += words[i];
    }
    return (out.replace(/[ -]+$/, "") || name.slice(0, limit)) + ".";
  }
  function nice(lo, hi, target) {
    var span = (hi - lo) || Math.abs(hi) || 1;
    var raw = span / target;
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var step = 10 * mag;
    [1, 2, 2.5, 5, 10].some(function (s) { if (s * mag >= raw) { step = s * mag; return true; } return false; });
    var t = Math.floor(lo / step) * step, ticks = [];
    while (!ticks.length || ticks[ticks.length - 1] < hi) {
      ticks.push(Math.round(t * 1e10) / 1e10);
      t += step;
    }
    return ticks;
  }
  // Come charts._compare_tick: un passo non intero tiene i suoi decimali.
  function tick(v, ticks) {
    var step = ticks.length > 1 ? Math.abs(ticks[1] - ticks[0]) : 1;
    if (step >= 1 && Number.isInteger(step)) return fmt(v, 0);
    var d = step >= 1 ? 1 : Math.min(2, Math.max(1, -Math.floor(Math.log10(step))));
    if (step < 1 && !Number.isInteger(Math.round(step * Math.pow(10, d) * 1e6) / 1e6)) d += 1;
    return fmt(v, d);
  }
  function marks(years, short) {
    var span = years[years.length - 1] - years[0];
    var step = span > 12 ? (short ? 10 : 5) : (span > 6 ? 2 : 1);
    var out = years.filter(function (y) { return (y - years[0]) % step === 0; });
    var last = years[years.length - 1];
    if (out.indexOf(last) < 0) {
      if (out.length && last - out[out.length - 1] < step / 2) out[out.length - 1] = last;
      else out.push(last);
    }
    return out;
  }
  function f1(v) { return (Math.round(v * 10) / 10).toFixed(1); }
  function drawCut(years, lines, avg, year, width, height, right, short) {
    var vals = [];
    lines.forEach(function (l) { l.points.forEach(function (p) { if (p[1] !== null) vals.push(p[1]); }); });
    avg.forEach(function (p) { if (p[1] !== null) vals.push(p[1]); });
    var ticks = nice(Math.min.apply(null, vals), Math.max.apply(null, vals), 4);
    var left = short ? 46 : 60, top = 16, bottom = 30;
    var pw = width - left - right, ph = height - top - bottom;
    var x = function (yr) { return left + (yr - years[0]) / ((years[years.length - 1] - years[0]) || 1) * pw; };
    var y = function (v) { return top + (1 - (v - ticks[0]) / ((ticks[ticks.length - 1] - ticks[0]) || 1)) * ph; };
    function path(points) {
      var out = "", pen = "M";
      points.forEach(function (p) {
        if (p[1] === null) { pen = "M"; return; }
        out += pen + f1(x(p[0])) + " " + f1(y(p[1]));
        pen = "L";
      });
      return out;
    }
    var parts = ['<svg viewBox="0 0 ' + width + " " + height + '" aria-hidden="true" focusable="false" class="cmpchart">'];
    ticks.forEach(function (t) {
      parts.push('<line class="band__grid" x1="' + left + '" x2="' + (left + pw) + '" y1="' + f1(y(t)) + '" y2="' + f1(y(t)) + '"/>');
      parts.push('<text class="band__tick" x="' + (left - 8) + '" y="' + f1(y(t) + 4) + '" text-anchor="end">' + esc(tick(t, ticks)) + "</text>");
    });
    marks(years, short).forEach(function (yr) {
      var anchor = yr === years[0] ? "start" : (yr === years[years.length - 1] ? "end" : "middle");
      parts.push('<text class="band__tick" x="' + f1(x(yr)) + '" y="' + (height - 8) + '" text-anchor="' + anchor + '">' + yr + "</text>");
    });
    parts.push('<line class="cmpchart__yr" x1="' + f1(x(year)) + '" x2="' + f1(x(year)) + '" y1="' + top + '" y2="' + (top + ph) + '"/>');
    var labels = [];
    var avgKnown = avg.filter(function (p) { return p[1] !== null; });
    if (avgKnown.length) {
      parts.push('<path class="band__avg" d="' + path(avg) + '"/>');
      var la = avgKnown[avgKnown.length - 1];
      labels.push([y(la[1]), (short ? "Media " : "Media semplice ") + fmt(la[1]), "band__lab band__lab--avg"]);
    }
    lines.forEach(function (l) {
      parts.push('<path class="cmpchart__line ' + l.cls + '" d="' + path(l.points) + '"/>');
      var known = l.points.filter(function (p) { return p[1] !== null; });
      var at = known.filter(function (p) { return p[0] === year; })[0];
      if (at) parts.push('<circle class="cmpchart__dot ' + l.cls + '" cx="' + f1(x(year)) + '" cy="' + f1(y(at[1])) + '" r="4.5"/>');
      if (known.length) {
        var last = known[known.length - 1];
        labels.push([y(last[1]), (short ? shortName(l.name, 13) : l.name) + " " + fmt(last[1]), "band__lab " + l.cls]);
      }
    });
    labels.sort(function (a, b) { return a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0); });
    var placed = [];
    labels.forEach(function (lab) {
      var ly = lab[0];
      if (placed.length && ly - placed[placed.length - 1] < 16) ly = placed[placed.length - 1] + 16;
      placed.push(ly);
      parts.push('<text class="' + lab[2] + '" x="' + (left + pw + 8) + '" y="' + f1(ly + 4) + '">' + esc(lab[1]) + "</text>");
    });
    parts.push("</svg>");
    return parts.join("");
  }
  function compareChart(years, lines, avg, year) {
    var any = lines.some(function (l) { return l.points.some(function (p) { return p[1] !== null; }); });
    if (years.length < 2 || !any) return "";
    return CUTS.map(function (c) {
      return '<div class="' + c[0] + '">' + drawCut(years, lines, avg, year, c[1], c[2], c[3], c[4]) + "</div>";
    }).join("");
  }

  /* ---------- la frase, come answer_text ---------- */
  function answerText(name, year, values, avg, avgN, unit, d) {
    var shown = values.filter(function (v) { return v[1] !== null && v[1] !== undefined; });
    if (!shown.length) return name;
    var parts = shown.map(function (v, i) {
      var last = i === shown.length - 1;
      return v[0] + " " + (unit === "%" || last ? withUnit(v[1], unit, d) : fmt(v[1], d));
    });
    var listed = parts.length === 1 ? parts[0] : parts.slice(0, -1).join(", ") + " e " + parts[parts.length - 1];
    var text = name + ", " + year + ": " + listed;
    if (avg !== null) text += ", contro una media semplice delle " + avgN + " " + cfg.plural + " di " + withUnit(avg, unit, d);
    return text + ".";
  }

  /* ---------- il disegno ---------- */
  function setText(sel, text) { all(sel).forEach(function (el) { el.textContent = text; }); }
  function optionHtml(items, chosen) {
    return items.map(function (it) {
      return '<option value="' + esc(it[0]) + '"' + (String(it[0]) === String(chosen) ? " selected" : "") + ">" + esc(it[1]) + "</option>";
    }).join("");
  }
  // `groups`, se c'e': [[etichetta, [chiavi]]], le province per regione.
  function options(select, items, chosen, empty, groups) {
    var html = empty ? '<option value="">' + esc(empty) + "</option>" : "";
    if (groups) {
      var byKey = {};
      items.forEach(function (it) { byKey[it[0]] = it; });
      groups.forEach(function (g) {
        var inside = g[1].filter(function (k) { return byKey[k]; }).map(function (k) { return byKey[k]; });
        if (inside.length) html += '<optgroup label="' + esc(g[0]) + '">' + optionHtml(inside, chosen) + "</optgroup>";
      });
    } else {
      html += optionHtml(items, chosen);
    }
    select.innerHTML = html;
  }
  // Il link del selettore del livello, come `switch_href` di confronto.py.
  function switchHref(level) {
    var other = cfg["switch"][level];
    var path = level === "regione" ? "/confronto" : "/confronto?livello=" + level;
    if (!other || other.shared.indexOf(state.indicator) < 0 || state.indicator === other["default"]) return path;
    return "/confronto?indicator=" + state.indicator + (level === "regione" ? "" : "&livello=" + level);
  }

  function render() {
    var m = model, meta = m.meta, year = state.year, unit = m.unit;
    var now = m.matrix[year] || {};
    var keys = Object.keys(now);
    var values = keys.map(function (k) { return now[k]; });
    var d = columnDecimals(values);
    var order = keys.slice().sort(function (a, b) {
      var diff = m.lowerBetter ? now[a] - now[b] : now[b] - now[a];
      var na = m.names[a], nb = m.names[b];
      return diff || (na < nb ? -1 : na > nb ? 1 : 0);
    });
    var avgN = values.length;
    var avgNow = avgN ? values.reduce(function (a, b) { return a + b; }, 0) / avgN : null;
    var sel = state.regions.map(function (k, i) {
      return { key: k, name: m.names[k], cls: cfg.classes[i], value: now[k] === undefined ? null : now[k], rank: order.indexOf(k) + 1 };
    });

    // testa
    $("[data-cmp-answer]").textContent = answerText(meta.name, year, sel.map(function (s) { return [s.name, s.value]; }), avgNow, avgN, unit, d);
    setText("[data-cmp-theme]", meta.theme || "");
    setText("[data-cmp-year-label]", String(year));
    setText("[data-cmp-name]", meta.name);

    // tabella
    var rows = sel.map(function (s) {
      return '<tr><th scope="row"><span class="swatch ' + s.cls + '" aria-hidden="true"></span><a href="' + esc(cfg.profile + s.key) + '">' +
        esc(s.name) + '</a></th><td class="val">' + numHtml(s.value, unit, d) + '</td><td class="val">' + rankHtml(s.value === null ? 0 : s.rank, keys.length) + "</td></tr>";
    });
    rows.push('<tr class="ref"><th scope="row">Media semplice delle ' + avgN + " " + esc(cfg.plural) + '</th><td class="val">' + numHtml(avgNow, unit, d) + "</td><td></td></tr>");
    $("[data-cmp-rows]").innerHTML = rows.join("");
    $("[data-cmp-rankrule]").textContent = "La posizione è fra le " + keys.length + " " + cfg.plural + " con il dato nel " + year + ", " +
      (m.lowerBetter ? "dal valore più basso, che qui è il migliore, al più alto." : "dal valore più alto al più basso.");

    // mappa, con i gradini di v1.js
    var box = $("[data-cmp-map]");
    if (values.length) {
      var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values), span = (hi - lo) || 1;
      var nd = box.querySelector(".map pattern[id]");
      all(".map [data-key]", box).forEach(function (p) {
        var k = p.getAttribute("data-key"), v = now[k];
        p.classList.remove("q1", "q2", "q3", "q4", "q5", "q6", "is-on", "is-nd");
        if (v !== undefined) {
          p.classList.add("q" + Math.min(6, Math.floor((v - lo) / span * 6) + 1));
          p.style.fill = "";
          p.setAttribute("data-value", withUnit(v, unit));
        } else {
          p.style.fill = nd ? "url(#" + nd.id + ")" : "";
          p.setAttribute("data-value", "");
        }
        if (state.regions.indexOf(k) >= 0) p.classList.add("is-on");
      });
      var lg = { min: lo, mid: lo + (hi - lo) / 2, max: hi };
      all("[data-legend]", box).forEach(function (el) { el.textContent = fmt(lg[el.getAttribute("data-legend")]); });
      // Come `legend_nd` della pagina: si contano i contorni, non i territori della serie.
      var shapes = all(".map [data-key]", box).length;
      all(".legend__nd", box).forEach(function (el) { el.hidden = keys.length >= shapes; });
      var svg = box.querySelector(".map svg");
      if (svg) svg.setAttribute("aria-label", "Mappa delle " + cfg.plural + " italiane per " + meta.name + ", " + year + ", con le " + cfg.plural + " a confronto in evidenza");
    }

    // la serie
    var averages = m.years.map(function (yr) {
      var vs = Object.keys(m.matrix[yr]).map(function (k) { return m.matrix[yr][k]; });
      return [yr, vs.length >= cfg.need ? vs.reduce(function (a, b) { return a + b; }, 0) / vs.length : null];
    });
    var lines = sel.map(function (s) {
      return { name: s.name, cls: s.cls, points: m.years.map(function (yr) { var v = m.matrix[yr][s.key]; return [yr, v === undefined ? null : v]; }) };
    });
    var chart = compareChart(m.years, lines, averages, year);
    var subline = $("[data-cmp-subline]");
    if (subline) subline.textContent = meta.name + (unit ? ", in " + unit : "") + ", dal " + m.years[0] + " al " + m.years[m.years.length - 1] + ".";
    $("[data-cmp-chart]").innerHTML = chart;
    $("[data-cmp-chartnote]").textContent = chart
      ? "La media semplice si disegna negli anni in cui almeno " + cfg.need + " " + cfg.plural + " hanno il dato. La linea tratteggiata verticale segna l'anno della tabella."
      : "Un anno solo: la serie non si disegna.";
    $("[data-cmp-key]").innerHTML = sel.map(function (s) {
      return '<li><span class="swatch ' + s.cls + '" aria-hidden="true"></span>' + esc(s.name) + "</li>";
    }).join("") + '<li><span class="swatch swatch--avg" aria-hidden="true"></span>Media semplice delle ' + esc(cfg.plural) + "</li>";
    var cells = [];
    m.years.forEach(function (yr) { sel.forEach(function (s) { var v = m.matrix[yr][s.key]; if (v !== undefined) cells.push(v); }); });
    var sd = columnDecimals(cells);
    $("[data-cmp-series-head]").innerHTML = '<tr><th scope="col">Anno</th>' + sel.map(function (s) {
      return '<th class="r" scope="col">' + esc(s.name) + "</th>";
    }).join("") + '<th class="r" scope="col">Media semplice</th></tr>';
    $("[data-cmp-series-rows]").innerHTML = m.years.slice().reverse().map(function (yr, i) {
      var avg = averages[averages.length - 1 - i][1];
      return '<tr><th scope="row">' + yr + "</th>" + sel.map(function (s) {
        var v = m.matrix[yr][s.key];
        return '<td class="val">' + numHtml(v === undefined ? null : v, unit, sd) + "</td>";
      }).join("") + '<td class="val">' + numHtml(avg, unit, sd) + "</td></tr>";
    }).join("");

    // fonte e scheda
    var src = $("[data-cmp-source]");
    if (src) { src.textContent = meta.source_label || meta.source || ""; if (meta.source_url) src.setAttribute("href", meta.source_url); }
    var scheda = $("[data-cmp-scheda]");
    if (scheda && meta.path) scheda.setAttribute("href", meta.path);

    // i campi
    indSel.value = state.indicator;
    options(yearSel, m.years.slice().reverse().map(function (y) { return [y, y]; }), year);
    var territories = Object.keys(m.names).map(function (k) { return [k, m.names[k]]; })
      .sort(function (a, b) { return a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0; });
    regionSels.forEach(function (s, i) { options(s, territories, state.regions[i] || "", i > 0 ? "Nessuna" : null, cfg.groups); });
    all("[data-cmp-switch]").forEach(function (a) {
      var level = a.getAttribute("data-cmp-switch");
      if (level !== state.level) a.setAttribute("href", switchHref(level));
    });

    live.textContent = $("[data-cmp-answer]").textContent;
  }

  /* ---------- i cambi ---------- */
  function submitForm() { form.submit(); }
  // `failed`, se c'e', prende il posto del ripiego sul form: un confronto
  // salvato con un indicatore che non esiste piu' lo dice, non ricarica.
  function apply(wanted, done, failed) {
    var mine = ++seq;
    root.setAttribute("aria-busy", "true");
    var offered = indSel.querySelector('option[value="' + String(wanted.indicator).replace(/["\\]/g, "") + '"]');
    if (!offered) {
      root.removeAttribute("aria-busy");
      if (failed) failed(); else submitForm();
      return;
    }
    load(wanted.indicator).then(function (m) {
      if (mine !== seq) return;
      model = m;
      state = normalize(m, wanted);
      render();
      writeUrl();
      root.removeAttribute("aria-busy");
      if (done) done();
    }).catch(function () {
      if (mine !== seq) return;
      root.removeAttribute("aria-busy");
      if (failed) failed(); else submitForm();
    });
  }
  function fromFields() {
    return {
      indicator: indSel.value,
      regions: regionSels.map(function (s) { return s.value; }).filter(Boolean),
      year: yearSel.value
    };
  }

  form.addEventListener("submit", function (ev) { ev.preventDefault(); apply(fromFields()); });
  indSel.addEventListener("change", function () {
    // L'anno torna all'ultimo dell'indicatore nuovo, come nella SPA.
    var wanted = fromFields();
    wanted.year = null;
    apply(wanted, function () {
      // Non `select_indicator`: quello e' la conversione GA4 "apertura di un
      // indicatore dall'atlante" (docs/tracking_spec.md), e il selettore del
      // confronto la gonfierebbe a ogni cambio.
      track("compare_select_indicator", {
        indicator_id: state.indicator, indicator_name: model.meta.name,
        indicator_theme: model.meta.theme
      });
    });
  });
  regionSels.forEach(function (s) {
    s.addEventListener("change", function () {
      apply(fromFields(), function () { track("change_region", { region: state.regions.join(","), indicator_id: state.indicator }); });
    });
  });
  yearSel.addEventListener("change", function () {
    apply(fromFields(), function () { track("change_year", { year: state.year, indicator_id: state.indicator }); });
  });

  // Un clic sulla mappa mette la regione nel confronto, o la toglie. Con tre
  // regioni gia' scelte prende il posto dell'ultima. La tastiera ha i campi.
  $("[data-cmp-map]").addEventListener("click", function (ev) {
    var p = ev.target.closest(".map [data-key]");
    if (!p) return;
    var k = p.getAttribute("data-key");
    // Un territorio senza nome nel payload (n.d. in tutta la serie) non entra:
    // prenderebbe il posto dell'ultimo e poi sparirebbe in silenzio.
    if (!model || !model.names[k]) return;
    var regions = state.regions.slice();
    var at = regions.indexOf(k);
    if (at >= 0) {
      if (regions.length === 1) return;
      regions.splice(at, 1);
    } else if (regions.length < cfg.max) {
      regions.push(k);
    } else {
      regions[regions.length - 1] = k;
    }
    apply({ indicator: state.indicator, regions: regions, year: state.year }, function () {
      track("change_region", { region: state.regions.join(","), indicator_id: state.indicator });
    });
  });
  root.addEventListener("click", function (ev) {
    var a = ev.target.closest("[data-cmp-rows] a[href^='" + cfg.profile + "']");
    if (!a) return;
    var key = a.getAttribute("href").slice(cfg.profile.length);
    if (state.level === "provincia") track("open_province", { province_key: key });
    else track("open_region", { region_key: key });
  });

  /* ---------- i confronti salvati, solo dopo l'accesso ---------- */
  var savedBox = $("[data-cmp-saved]");
  var list = $("[data-cmp-list]");
  var status = $("[data-cmp-saved-status]");
  var titleIn = $("[data-cmp-title]");
  function authed(url, options) {
    return window.diAuth.token().then(function (token) {
      if (!token) return null;
      options = options || {};
      options.headers = { Authorization: "Bearer " + token, "Content-Type": "application/json" };
      return fetch(url, options);
    });
  }
  function defaultTitle() {
    var names = model ? state.regions.map(function (k) { return model.names[k]; }) : [];
    var ind = indSel.options[indSel.selectedIndex];
    return (ind ? ind.textContent : "Confronto") + (names.length ? ": " + names.join(", ") : "");
  }
  function reloadSaved() {
    return authed("/api/comparisons").then(function (r) {
      if (!r || !r.ok) return;
      return r.json().then(function (d) {
        var items = d.comparisons || [];
        list.innerHTML = items.map(function (it) {
          return '<li><button type="button" data-cmp-load="' + esc(it.id) + '">' + esc(it.title) + "</button>" +
            '<button type="button" data-cmp-del="' + esc(it.id) + '" aria-label="Elimina ' + esc(it.title) + '">Elimina</button></li>';
        }).join("");
        list._items = items;
      });
    });
  }
  $("[data-cmp-save]").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var go = function () {
      var names = state.regions.map(function (k) { return model.names[k]; });
      // `indId` e `regionNames` sono i nomi della SPA: i confronti salvati
      // allora si ricaricano anche adesso. `regions` porta le chiavi.
      var config = { indId: state.indicator, regionNames: names, regions: state.regions, year: state.year, level: state.level };
      var title = titleIn.value.trim() || defaultTitle();
      authed("/api/comparisons", { method: "POST", body: JSON.stringify({ title: title, config: config }) })
        .then(function (r) {
          var ok = r && r.ok;
          status.textContent = ok ? "Confronto salvato" : "Il confronto non si è salvato";
          if (ok) titleIn.value = "";
          return reloadSaved();
        }).catch(function () { status.textContent = "Il confronto non si è salvato"; });
    };
    if (model) go(); else apply({ indicator: state.indicator, regions: state.regions, year: state.year }, go);
  });
  list.addEventListener("click", function (ev) {
    var load = ev.target.closest("[data-cmp-load]");
    var del = ev.target.closest("[data-cmp-del]");
    var items = list._items || [];
    if (load) {
      var it = items.filter(function (x) { return String(x.id) === load.getAttribute("data-cmp-load"); })[0];
      var c = (it && it.config) || {};
      // Un confronto salvato sull'altro livello si apre su quella pagina: i
      // suoi territori e i suoi indicatori sono quelli dell'altro livello.
      var level = c.level || "regione";
      if (level !== state.level && PARAMS[level]) {
        var q = new URLSearchParams();
        if (c.indId) q.set("indicator", String(c.indId));
        (c.regions || c.regionNames || []).forEach(function (k) { q.append(PARAMS[level], k); });
        if (level !== "regione") q.set("livello", level);
        location.assign("/confronto?" + q.toString());
        return;
      }
      // L'anno torna all'ultimo (docs/ACCOUNT.md): si ricaricano indicatore e territori.
      apply({ indicator: String(c.indId || state.indicator), regions: c.regions || c.regionNames || [], year: null }, function () {
        status.textContent = "Confronto caricato";
        $("[data-cmp-answer]").scrollIntoView({ block: "center" });
      }, function () {
        status.textContent = "Questo confronto non si apre: il suo indicatore non c'è più";
      });
    } else if (del) {
      authed("/api/comparisons/" + encodeURIComponent(del.getAttribute("data-cmp-del")), { method: "DELETE" })
        .then(function () { status.textContent = "Confronto eliminato"; return reloadSaved(); })
        .catch(function () {});
    }
  });
  function wantSaved() {
    var auth = window.diAuth;
    if (!auth || typeof auth.token !== "function") return false;
    auth.token().then(function (token) {
      if (!token) return;
      savedBox.hidden = false;
      reloadSaved();
    }).catch(function () {});
    return true;
  }
  // site.js e' un modulo e puo' arrivare dopo questo script: si aspetta il suo segnale.
  if (!wantSaved()) document.addEventListener("di:auth", wantSaved, { once: true });

  /* ---------- l'avvio ---------- */
  // Con il JavaScript ogni campo applica la scelta da solo: il bottone del
  // form serve solo senza.
  $("[data-cmp-submit]").hidden = true;
  // L'URL prende la forma normalizzata dello stato servito: un link vecchio
  // (?view=confronto, ?region=Lombardia) diventa quello che il server scrive.
  // Si aspetta la prima richiesta: l'URL la scrive `apply`.
  var params = new URLSearchParams(location.search);
  if (["view", "indicatore", "regione", "anno"].some(function (k) { return params.has(k); }) ||
      params.getAll("region").some(function (v) { return v !== v.toLowerCase(); })) {
    apply({ indicator: state.indicator, regions: state.regions, year: state.year });
  }
})();
