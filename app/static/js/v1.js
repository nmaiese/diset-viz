/* Divario Italia 1.0: il poco JavaScript che serve alle pagine rifatte.
   La pagina a riposo e' completa senza: mappa colorata, classifica, serie e
   tabelle vengono dal server. Qui c'e' solo l'interazione: il valore sulla
   mappa, l'anno e il territorio del modulo dato, la citazione da copiare,
   l'indice di pagina. Il tema lo tiene ds-chrome.js, come su ogni pagina.
   Nato coi prototipi (design/v1/src/js/proto.js). */
(function () {
  "use strict";

  /* ---------- numeri all'italiana, stessa regola di seo_titles._decimals ---------- */
  function decimals(v) {
    var m = Math.abs(v);
    if (m >= 100) return 0;
    if (m >= 10) return 1;
    return m < 1 ? 2 : 1;
  }
  // Come numfmt.text: il trattino davanti ai negativi, lo zero arrotondato senza segno.
  function fmt(v, d) {
    if (v === null || v === undefined || isNaN(v)) return "n.d.";
    if (d === undefined || d === null) d = decimals(v);
    var s = new Intl.NumberFormat("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }).format(Math.abs(v));
    var zero = Number(s.replace(/\./g, "").replace(",", ".")) === 0;
    return (v < 0 && !zero ? "-" : "") + s;
  }
  function withUnit(v, unit) {
    if (v === null || v === undefined) return "n.d.";
    if (unit === "%") return fmt(v) + "%";
    return unit ? fmt(v) + " " + unit : fmt(v);
  }

  /* ---------- copia la citazione ---------- */
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-copy]");
    if (!b) return;
    var box = b.closest(".cite");
    var text = box.querySelector("[data-cite-text]").textContent.trim();
    var status = box.querySelector("[data-copy-status]");
    function done(ok) {
      b.querySelector("span").textContent = ok ? "Citazione copiata" : "Seleziona il testo e copialo";
      if (status) status.textContent = ok ? "Citazione copiata" : "";
      if (!ok) {
        var r = document.createRange();
        r.selectNodeContents(box.querySelector("[data-cite-text]"));
        var s = getSelection(); s.removeAllRanges(); s.addRange(r);
      }
    }
    try { navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); }); }
    catch (e) { done(false); }
  });

  /* ---------- mappa: il valore al passaggio del mouse ---------- */
  document.querySelectorAll("[data-map]").forEach(function (box) {
    var tip = box.querySelector("[data-map-tip]");
    box.addEventListener("mousemove", function (ev) {
      var p = ev.target.closest("path[data-key]");
      if (!p) { tip.hidden = true; return; }
      var r = box.getBoundingClientRect();
      tip.innerHTML = "";
      var name = document.createElement("span");
      name.textContent = p.dataset.name + " ";
      var val = document.createElement("b");
      val.textContent = p.dataset.value || "n.d.";
      tip.append(name, val);
      tip.hidden = false;
      var x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14;
      if (x + tip.offsetWidth > r.width) x = ev.clientX - r.left - tip.offsetWidth - 10;
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    });
    box.addEventListener("mouseleave", function () { tip.hidden = true; });
  });

  /* ---------- il modulo dato della scheda ---------- */
  document.querySelectorAll("[data-explore]").forEach(function (mod) {
    var page = mod.closest("[data-page-root]") || document;
    var dataEl = page.querySelector("[data-explore-data]");
    if (!dataEl) return;
    var data = JSON.parse(dataEl.textContent);
    var slider = mod.querySelector("[data-year]");
    var select = mod.querySelector("[data-territory]");
    var body = mod.querySelector("[data-rank-body]");
    var claim = mod.querySelector("[data-claim]");
    var live = mod.querySelector("[data-live]");
    var series = page.querySelector("[data-series]");
    var lowerBetter = data.direction === "lower_better" || data.direction === "higher_worse";
    var current = data.years[data.years.length - 1];

    function rows(year) {
      var m = data.matrix[String(year)] || {};
      var list = Object.keys(m).filter(function (k) { return m[k] !== null; }).map(function (k) { return { key: k, name: data.names[k] || k, value: m[k] }; });
      list.sort(function (a, b) { return lowerBetter ? a.value - b.value : b.value - a.value; });
      return list;
    }

    function paint(year) {
      var list = rows(year);
      if (!list.length) return;
      var vals = list.map(function (r) { return r.value; });
      var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), span = (hi - lo) || 1;
      var avg = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
      var max = Math.max(hi, 0) || 1;
      var byKey = {};
      list.forEach(function (r) { byKey[r.key] = r; });

      mod.querySelectorAll("path[data-key]").forEach(function (p) {
        var r = byKey[p.dataset.key];
        p.classList.remove("q1", "q2", "q3", "q4", "q5", "q6");
        if (r) {
          p.classList.add("q" + Math.min(6, Math.floor((r.value - lo) / span * 6) + 1));
          p.style.fill = "";
          p.dataset.value = withUnit(r.value, data.unit);
        } else {
          p.dataset.value = "n.d.";
        }
      });
      var lg = { min: lo, mid: lo + span / 2, max: hi };
      mod.querySelectorAll("[data-legend]").forEach(function (el) { el.textContent = fmt(lg[el.dataset.legend]); });

      var sel = select ? select.value : "";
      var html = [], refDone = false;
      list.forEach(function (r, i) {
        var crosses = lowerBetter ? r.value > avg : r.value < avg;
        if (!refDone && crosses) {
          html.push('<tr class="ref"><td></td><th scope="row">Media semplice delle ' + list.length + " " + data.plural + '</th><td class="barcell" aria-hidden="true"></td><td class="val"><data class="n n--cell" value="' + avg + '">' + fmt(avg, data.decimals) + "</data></td></tr>");
          refDone = true;
        }
        var dot = data.areas && data.areas[r.key] ? '<span class="area-dot area-dot--' + data.areas[r.key] + '" aria-hidden="true"></span>' : "";
        var name = dot + (data.profile ? '<a href="' + profileHref(r.key) + '">' + esc(r.name) + "</a>" : esc(r.name));
        html.push('<tr data-key="' + r.key + '"' + (r.key === sel ? ' class="is-on" aria-current="true"' : "") + '><td class="rank"><span class="n n--rank"><data value="' + (i + 1) + '">' + (i + 1) + '</data><span class="n__o">ª</span></span></td><th scope="row">' + name +
          '</th><td class="barcell" aria-hidden="true"><span class="bar"><i style="width:' + (Math.max(r.value, 0) / max * 100).toFixed(1) + '%"></i></span></td><td class="val"><data class="n n--cell" value="' + r.value + '">' + fmt(r.value, data.decimals) + "</data></td></tr>");
      });
      body.innerHTML = html.join("");

      if (claim && data.south && data.south.length) {
        var south = list.filter(function (r) { return data.south.indexOf(r.key) >= 0; });
        var below = south.filter(function (r) { return r.value < avg; });
        var words = ["zero", "una", "due", "tre", "quattro", "cinque", "sei", "sette", "otto"];
        var w = function (n) { return words[n] || String(n); };
        if (below.length === south.length) claim.textContent = "Nel " + year + " tutte le " + w(south.length) + " regioni del Mezzogiorno stanno sotto la media semplice";
        else if (!below.length) claim.textContent = "Nel " + year + " tutte le " + w(south.length) + " regioni del Mezzogiorno stanno sopra la media semplice";
        else claim.textContent = "Nel " + year + " " + w(below.length) + " regioni del Mezzogiorno su " + w(south.length) + " stanno sotto la media semplice";
      }
      page.querySelectorAll("[data-year-label]").forEach(function (el) { el.textContent = year; });
      var out = mod.querySelector("[data-year-out]");
      if (out) out.textContent = year;
      if (slider) slider.setAttribute("aria-valuetext", String(year));
      if (live) live.textContent = "Classifica del " + year + ": in testa " + list[0].name + ", " + withUnit(list[0].value, data.unit) + ".";
    }

    function profileHref(key) { return data.profile + key; }
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

    function highlight(key) {
      mod.querySelectorAll("path[data-key]").forEach(function (p) { p.classList.toggle("is-on", p.dataset.key === key); });
      // Piu' di un corpo quando la home affianca le prime e le ultime dieci province.
      mod.querySelectorAll("[data-rank-body] tr[data-key]").forEach(function (tr) {
        var on = tr.dataset.key === key;
        tr.classList.toggle("is-on", on);
        if (on) tr.setAttribute("aria-current", "true"); else tr.removeAttribute("aria-current");
      });
      page.querySelectorAll("[data-series] svg").forEach(function (svg) {
        var hl = svg.querySelector("[data-hl]"), dot = svg.querySelector("[data-hl-dot]"), lab = svg.querySelector("[data-hl-lab]");
        if (!hl || !dot || !lab) return;
        var src = key ? svg.querySelector('polyline.ctx[data-key="' + key + '"], polyline.band__src[data-key="' + key + '"]') : null;
        if (src) {
          var pts = src.getAttribute("points").trim().split(" ");
          var last = pts[pts.length - 1].split(",");
          hl.setAttribute("points", src.getAttribute("points"));
          dot.setAttribute("cx", last[0]); dot.setAttribute("cy", last[1]); dot.setAttribute("r", 4);
          lab.setAttribute("y", Number(last[1]) + 4); lab.textContent = data.names[key] || key;
        } else {
          hl.setAttribute("points", ""); dot.setAttribute("r", 0); lab.textContent = "";
        }
      });
      page.querySelectorAll(".strip__dot").forEach(function (c) { c.classList.toggle("is-on", c.dataset.key === key); });
      if (live && key) {
        var r = rows(current).filter(function (x) { return x.key === key; })[0];
        if (r) live.textContent = r.name + ": " + withUnit(r.value, data.unit) + " nel " + current + ".";
        else live.textContent = (data.names[key] || key) + ": dato non disponibile nel " + current + ".";
      }
    }

    if (slider) slider.addEventListener("input", function () {
      current = data.years[Number(slider.value)];
      paint(current);
      highlight(select ? select.value : "");
    });
    if (select) select.addEventListener("change", function () { highlight(select.value); });
    page.querySelectorAll(".strip").forEach(function (svg) {
      svg.addEventListener("click", function (ev) {
        var c = ev.target.closest(".strip__dot");
        if (!c || !select) return;
        select.value = select.value === c.dataset.key ? "" : c.dataset.key;
        highlight(select.value);
      });
    });
    mod.addEventListener("click", function (ev) {
      var p = ev.target.closest("path[data-key]");
      if (!p || !select) return;
      select.value = select.value === p.dataset.key ? "" : p.dataset.key;
      highlight(select.value);
    });
  });

  /* ---------- tabelle lunghe: chiuse sul telefono, sempre nel DOM ---------- */
  if (matchMedia("(max-width: 599px)").matches) {
    document.querySelectorAll("details[data-collapse-mobile]").forEach(function (d) { d.open = false; });
  }

  /* ---------- indice di pagina: la voce della sezione che si sta leggendo ---------- */
  document.querySelectorAll(".toc").forEach(function (toc) {
    var links = Array.prototype.slice.call(toc.querySelectorAll("a[href^='#']"));
    var targets = links.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
    var ticking = false;
    function update() {
      ticking = false;
      var cur = -1;
      targets.forEach(function (t, i) { if (t && t.getBoundingClientRect().top < innerHeight * 0.3) cur = i; });
      links.forEach(function (a, j) {
        if (j === cur) {
          if (a.getAttribute("aria-current") !== "location") {
            a.setAttribute("aria-current", "location");
            var ol = a.closest("ol");
            if (ol && ol.scrollWidth > ol.clientWidth) ol.scrollLeft = Math.max(0, a.offsetLeft - 16);
          }
        } else a.removeAttribute("aria-current");
      });
    }
    addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
  });
})();
