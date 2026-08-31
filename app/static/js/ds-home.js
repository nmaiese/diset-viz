// Comportamenti della homepage (design system 2026).
//
// Ogni modulo qui dentro e progressive enhancement: la pagina server-rendered
// e gia completa e leggibile senza JavaScript. Questo file aggiunge la lettura
// della mappa, i due richiami sulle regioni estreme, il ridisegno del grafico
// di confronto e il cambio profilo della qualita della vita.
(function () {
  "use strict";

  var reduced =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function parseJSON(element, attribute) {
    if (!element) return null;
    try {
      return JSON.parse(element.getAttribute(attribute));
    } catch (e) {
      return null;
    }
  }

  // =======================================================================
  // MAPPA HERO
  // Stessa logica di home-map.js (hover, focus e doppio tap su touch), piu i
  // due richiami posizionati sui baricentri delle regioni estreme.
  // =======================================================================
  (function heroMap() {
    var card = document.querySelector("[data-ds-heromap]");
    if (!card) return;
    var svg = card.querySelector(".regions-map");
    var readout = card.querySelector("[data-ds-readout]");
    var byKey = parseJSON(card, "data-readout");
    if (!svg || !readout || !byKey) return;

    var hintText = readout.textContent;
    var hovered = null;
    var focused = null;
    var touchedKey = null;

    function paint() {
      var info = focused || hovered;
      readout.textContent = info
        ? info.name + " · " + info.value + (info.unit ? " " + info.unit : "") +
          " · " + info.rank + " su " + info.total + " per valore"
        : hintText;
    }

    function go(key) {
      window.location.href = "/regione/" + key;
    }

    var high = card.getAttribute("data-high");
    var low = card.getAttribute("data-low");

    Array.prototype.forEach.call(svg.querySelectorAll(".rmap-region"), function (region) {
      var key = region.getAttribute("data-key");
      var info = byKey[key];
      if (!info) return;

      if (key === high) region.classList.add("is-high");
      if (key === low) region.classList.add("is-low");

      // Il partial marca l'SVG come role="img", che rende presentazionali le
      // venti path. Con JavaScript le rendiamo davvero raggiungibili, quindi
      // l'SVG diventa un gruppo e ogni regione un link.
      region.setAttribute("tabindex", "0");
      region.setAttribute("role", "link");
      region.setAttribute(
        "aria-label",
        info.name + ": " + info.value + (info.unit ? " " + info.unit : "") +
          ", posizione " + info.rank + " su " + info.total
      );

      region.addEventListener("mouseenter", function () { hovered = info; paint(); });
      region.addEventListener("mouseleave", function () { hovered = null; paint(); });
      region.addEventListener("focus", function () { focused = info; paint(); });
      region.addEventListener("blur", function () { focused = null; paint(); });
      region.addEventListener("click", function () { go(key); });
      region.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          go(key);
        }
      });

      // Touch: il primo tocco mostra il valore, il secondo sulla stessa regione
      // apre il profilo. Senza questo, su mobile la lettura non si vede mai.
      region.addEventListener("touchend", function (event) {
        event.preventDefault();
        if (touchedKey === key) {
          go(key);
          return;
        }
        touchedKey = key;
        focused = null;
        hovered = info;
        paint();
      }, { passive: false });
    });

    svg.setAttribute("role", "group");
    svg.addEventListener("touchend", function (event) {
      if (event.target.closest && event.target.closest(".rmap-region")) return;
      touchedKey = null;
      hovered = null;
      paint();
    }, { passive: true });

    // --- richiami sulle due regioni estreme --------------------------------
    // La posizione viene dal baricentro reale della path, non da una stima:
    // getBBox e l'unica fonte affidabile e va letta dopo il layout.
    var canvas = card.querySelector(".heromap__canvas");
    var home = document.querySelector(".home");

    var svgNS = "http://www.w3.org/2000/svg";
    var leaders = null;

    function hideCallouts() {
      home.classList.remove("has-callouts");
      Array.prototype.forEach.call(card.querySelectorAll("[data-ds-callout]"), function (el) {
        el.hidden = true;
      });
      if (leaders) leaders.textContent = "";
    }

    function placeCallouts() {
      if (!canvas || !home) return;
      var box = svg.getBoundingClientRect();
      var viewBox = svg.viewBox.baseVal;
      if (!box.width || !box.height || !viewBox || !viewBox.width) return;

      var pairs = [["high", high], ["low", low]];
      var boxes = pairs.map(function (pair) {
        return card.querySelector('[data-ds-callout="' + pair[0] + '"]');
      });
      if (boxes.some(function (el) { return !el; })) return;

      // I richiami vanno misurati da visibili, quindi si scoprono prima di
      // leggerne il rettangolo. Sotto i 960px la container query li tiene
      // comunque nascosti: lì comandano le due schede .extreme, e si esce.
      boxes.forEach(function (el) { el.hidden = false; });
      home.classList.add("has-callouts");
      if (boxes[0].offsetParent === null) {
        hideCallouts();
        return;
      }

      // Un solo gruppo di guide, riscritto a ogni resize.
      if (!leaders) {
        leaders = document.createElementNS(svgNS, "g");
        leaders.setAttribute("aria-hidden", "true");
        svg.appendChild(leaders);
      }
      leaders.textContent = "";

      var placed = 0;
      var sides = {};
      pairs.forEach(function (pair) {
        var callout = card.querySelector('[data-ds-callout="' + pair[0] + '"]');
        var region = svg.querySelector('.rmap-region[data-key="' + pair[1] + '"]');
        if (!callout || !region) return;

        var bbox;
        try {
          bbox = region.getBBox();
        } catch (e) {
          return;
        }

        var cx = bbox.x + bbox.width / 2;
        var cy = bbox.y + bbox.height / 2;
        var side = cx / viewBox.width < 0.5 ? "left" : "right";
        // se le due regioni cadono dallo stesso lato, la seconda passa dall'altro
        if (sides[side]) side = side === "left" ? "right" : "left";
        sides[side] = true;

        callout.style.top = Math.min(92, Math.max(8, (cy / viewBox.height) * 100)) + "%";
        callout.style.transform = "translateY(-50%)";
        callout.style.left = side === "left" ? "0" : "auto";
        callout.style.right = side === "right" ? "0" : "auto";
        placed += 1;

        // Guida dal baricentro della regione al bordo interno del richiamo,
        // convertita nelle coordinate del viewBox: senza, i due riquadri
        // fluttuano senza dire a quale regione si riferiscono.
        var calloutBox = callout.getBoundingClientRect();
        var anchorPx = side === "left" ? calloutBox.right : calloutBox.left;
        var anchorX = ((anchorPx - box.left) / box.width) * viewBox.width;
        var anchorY = ((calloutBox.top + calloutBox.height / 2 - box.top) / box.height) * viewBox.height;

        var line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", cx.toFixed(1));
        line.setAttribute("y1", cy.toFixed(1));
        line.setAttribute("x2", anchorX.toFixed(1));
        line.setAttribute("y2", anchorY.toFixed(1));
        line.setAttribute("stroke", "var(--text-strong)");
        line.setAttribute("stroke-width", "1.4");
        line.setAttribute("vector-effect", "non-scaling-stroke");
        if (pair[0] === "low") line.setAttribute("stroke-dasharray", "5 4");
        leaders.appendChild(line);

        // Il punto di ancoraggio: pieno per il valore più alto, vuoto per il
        // più basso, come i bordi dei due riquadri.
        var dot = document.createElementNS(svgNS, "circle");
        dot.setAttribute("cx", cx.toFixed(1));
        dot.setAttribute("cy", cy.toFixed(1));
        dot.setAttribute("r", "6");
        dot.setAttribute("stroke", "var(--text-strong)");
        dot.setAttribute("stroke-width", "2");
        dot.setAttribute("fill", pair[0] === "high" ? "var(--text-strong)" : "var(--surface-card)");
        leaders.appendChild(dot);
      });

      if (placed !== 2) hideCallouts();
    }

    // il layout dell'SVG puo non essere ancora definitivo al DOMContentLoaded
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(placeCallouts);
    } else {
      placeCallouts();
    }
    window.addEventListener("resize", placeCallouts);
  })();

  // =======================================================================
  // CONFRONTO — serie storiche
  // =======================================================================
  (function compare() {
    var section = document.querySelector("[data-ds-compare]");
    if (!section) return;
    var data = parseJSON(section, "data-series");
    if (!data || !data.regions || !data.years) return;

    var chart = section.querySelector("[data-ds-chart]");
    var legend = section.querySelector("[data-ds-legend]");
    var rows = section.querySelector("[data-ds-rows]");
    var table = section.querySelector("[data-ds-chart-table]");
    var buttons = Array.prototype.slice.call(section.querySelectorAll("[data-ds-region]"));
    if (!chart || !legend || !rows) return;

    var byKey = {};
    data.regions.forEach(function (region) { byKey[region.key] = region; });
    var selected = data.default_keys.slice();

    // Geometria del grafico, identica a quella con cui il server lo disegna
    // (vedi _CHART_* in views.py). Le due versioni devono sovrapporsi esatte.
    var W = 260, H = 60, padL = 4, padR = 30, padT = 4, padB = 6;

    function bounds() {
      var values = [];
      selected.forEach(function (key) {
        if (byKey[key]) values = values.concat(byKey[key].series);
      });
      values = values.concat(data.reference.series);
      var low = Math.min.apply(null, values);
      var high = Math.max.apply(null, values);
      return { low: low, span: (high - low) || 1 };
    }

    function points(series, scale) {
      var last = data.years.length - 1;
      return series
        .map(function (value, index) {
          var x = padL + (index / last) * (W - padL - padR);
          var y = padT + (1 - (value - scale.low) / scale.span) * (H - padT - padB);
          return x.toFixed(1) + "," + y.toFixed(1);
        })
        .join(" ");
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, function (character) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
      });
    }

    function render() {
      var scale = bounds();
      var svgNS = "http://www.w3.org/2000/svg";
      chart.textContent = "";

      var baseline = document.createElementNS(svgNS, "line");
      baseline.setAttribute("x1", padL);
      baseline.setAttribute("y1", H - padB);
      baseline.setAttribute("x2", W - padR);
      baseline.setAttribute("y2", H - padB);
      baseline.setAttribute("stroke", "var(--chart-axis)");
      baseline.setAttribute("stroke-width", "0.4");
      baseline.setAttribute("vector-effect", "non-scaling-stroke");
      chart.appendChild(baseline);

      // La media delle regioni e una linea tratteggiata neutra: e un
      // riferimento, non una serie in gara con le altre.
      var reference = document.createElementNS(svgNS, "polyline");
      reference.setAttribute("points", points(data.reference.series, scale));
      reference.setAttribute("fill", "none");
      reference.setAttribute("stroke", "var(--data-reference)");
      reference.setAttribute("stroke-width", "1");
      reference.setAttribute("stroke-dasharray", "3 2");
      reference.setAttribute("vector-effect", "non-scaling-stroke");
      chart.appendChild(reference);

      selected.forEach(function (key, index) {
        var region = byKey[key];
        if (!region) return;
        var line = document.createElementNS(svgNS, "polyline");
        line.setAttribute("points", points(region.series, scale));
        line.setAttribute("fill", "none");
        line.setAttribute("stroke", region.color);
        line.setAttribute("stroke-width", "1.8");
        line.setAttribute("stroke-linejoin", "round");
        line.setAttribute("stroke-linecap", "round");
        line.setAttribute("vector-effect", "non-scaling-stroke");
        if (!reduced) {
          line.setAttribute("class", "cmp-line");
          line.style.animationDelay = index * 140 + "ms";
        }
        chart.appendChild(line);

        var last = region.series.length - 1;
        var dot = document.createElementNS(svgNS, "circle");
        var x = padL + (last / (data.years.length - 1)) * (W - padL - padR);
        var y = padT + (1 - (region.series[last] - scale.low) / scale.span) * (H - padT - padB);
        dot.setAttribute("cx", x.toFixed(1));
        dot.setAttribute("cy", y.toFixed(1));
        dot.setAttribute("r", "1.7");
        dot.setAttribute("fill", region.color);
        dot.setAttribute("vector-effect", "non-scaling-stroke");
        if (!reduced) {
          dot.setAttribute("class", "cmp-dot");
          dot.style.animationDelay = index * 140 + 760 + "ms";
        }
        chart.appendChild(dot);
      });

      chart.setAttribute(
        "aria-label",
        "Serie storica di " + data.indicator_name + " dal " + data.years[0] +
          " al " + data.years[data.years.length - 1] + " per " +
          selected.map(function (key) { return byKey[key] ? byKey[key].name : key; }).join(", ") +
          ", confrontate con la media delle regioni."
      );

      var legendHtml =
        '<span class="meta"><span class="cmplegend__rule"></span>' +
        escapeHtml(data.reference.short_label) + "</span>";
      selected.forEach(function (key) {
        var region = byKey[key];
        if (!region) return;
        legendHtml +=
          '<span class="meta"><span class="cmplegend__sw" style="background: ' +
          region.color + '"></span>' + escapeHtml(region.name) + "</span>";
      });
      legend.innerHTML = legendHtml;

      var rowsHtml = "";
      selected.forEach(function (key) {
        var region = byKey[key];
        if (!region) return;
        rowsHtml +=
          '<div class="cmprow cmprow--anim">' +
          '<span class="cmprow__sw" style="background: ' + region.color + '"></span>' +
          '<span class="cmprow__name">' + escapeHtml(region.name) + "</span>" +
          '<span class="cmprow__rank">' + region.rank + " su " + region.total + "</span>" +
          '<span class="cmprow__val">' + escapeHtml(region.value) + "</span>" +
          "</div>";
      });
      rowsHtml +=
        '<div class="cmprow">' +
        '<span class="cmprow__sw" style="background: var(--data-reference)"></span>' +
        '<span class="cmprow__name cmprow__name--ref">' + escapeHtml(data.reference.short_label) + "</span>" +
        '<span class="cmprow__rank"></span>' +
        '<span class="cmprow__val">' + escapeHtml(data.reference.value) + "</span>" +
        "</div>";
      rows.innerHTML = rowsHtml;

      if (table) {
        var head = "<tr><th scope=\"col\">Anno</th>";
        selected.forEach(function (key) {
          if (byKey[key]) head += "<th scope=\"col\">" + escapeHtml(byKey[key].name) + "</th>";
        });
        head += "<th scope=\"col\">" + escapeHtml(data.reference.short_label) + "</th></tr>";
        var body = "";
        data.years.forEach(function (year, index) {
          body += "<tr><th scope=\"row\">" + year + "</th>";
          selected.forEach(function (key) {
            if (byKey[key]) body += "<td>" + byKey[key].series[index].toFixed(1) + "</td>";
          });
          body += "<td>" + data.reference.series[index].toFixed(1) + "</td></tr>";
        });
        table.innerHTML =
          "<table><caption>" + escapeHtml(data.indicator_name) + ", " +
          escapeHtml(data.unit) + ", per anno.</caption><thead>" + head +
          "</thead><tbody>" + body + "</tbody></table>";
      }

      buttons.forEach(function (button) {
        var key = button.getAttribute("data-ds-region");
        var on = selected.indexOf(key) !== -1;
        button.setAttribute("aria-pressed", on ? "true" : "false");
        var dot = button.querySelector(".chip__dot");
        if (dot) dot.style.background = on && byKey[key] ? byKey[key].color : "var(--line-strong)";
      });
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var key = button.getAttribute("data-ds-region");
        var index = selected.indexOf(key);
        if (index !== -1) {
          // sotto un territorio il grafico non direbbe piu niente
          if (selected.length > 1) selected.splice(index, 1);
        } else {
          selected.push(key);
          if (selected.length > 3) selected.shift();
        }
        render();
      });
    });

    render();
  })();

  // =======================================================================
  // QUALITA DELLA VITA — cambio profilo di pesi
  // =======================================================================
  (function qualityOfLife() {
    var section = document.querySelector("[data-ds-qol]");
    if (!section) return;
    var data = parseJSON(section, "data-profiles");
    if (!data || !data.profiles) return;

    var buttons = Array.prototype.slice.call(section.querySelectorAll("[data-ds-profile]"));
    var top = section.querySelector("[data-ds-qol-top]");
    var bottom = section.querySelector("[data-ds-qol-bottom]");
    var topLabel = section.querySelector("[data-ds-qol-toplabel]");
    var bottomLabel = section.querySelector("[data-ds-qol-bottomlabel]");
    var description = section.querySelector("[data-ds-qol-desc]");
    var gap = section.querySelector("[data-ds-qol-gap]");
    if (!top || !bottom) return;

    var byslug = {};
    data.profiles.forEach(function (profile) { byslug[profile.slug] = profile; });

    function pad(value) {
      return value < 10 ? "0" + value : String(value);
    }

    function rowsHtml(rows) {
      return rows
        .map(function (row) {
          return (
            '<div class="qolrow qolrow--anim">' +
            '<span class="qolrow__rank">' + pad(row.rank) + "</span>" +
            '<span class="qolrow__name">' + row.name + "</span>" +
            '<span class="qolrow__bar"><span class="qolrow__fill" style="width: ' + row.score + '%"></span></span>' +
            '<span class="qolrow__score">' + row.score + "</span>" +
            "</div>"
          );
        })
        .join("");
    }

    function select(slug) {
      var profile = byslug[slug];
      if (!profile) return;
      top.innerHTML = rowsHtml(profile.top);
      bottom.innerHTML = rowsHtml(profile.bottom);
      if (topLabel) topLabel.textContent = "Punteggi più alti · profilo " + profile.name;
      if (bottomLabel) bottomLabel.textContent = "Punteggi più bassi · profilo " + profile.name;
      if (description) description.textContent = profile.description;
      if (gap) gap.textContent = profile.gap + " punti";
      buttons.forEach(function (button) {
        button.setAttribute(
          "aria-pressed",
          button.getAttribute("data-ds-profile") === slug ? "true" : "false"
        );
      });
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        select(button.getAttribute("data-ds-profile"));
      });
    });
  })();

  // =======================================================================
  // RIVELAZIONE DELLE BARRE quando il blocco entra in vista
  // =======================================================================
  (function reveal() {
    var targets = Array.prototype.slice.call(document.querySelectorAll("[data-ds-reveal]"));
    if (!targets.length) return;
    if (reduced || !("IntersectionObserver" in window)) {
      targets.forEach(function (target) { target.classList.add("in"); });
      return;
    }
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.3 }
    );
    targets.forEach(function (target) { observer.observe(target); });
  })();
})();
