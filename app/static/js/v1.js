/* Divario Italia 1.0: il poco JavaScript che serve alle pagine rifatte.
   La pagina a riposo e' completa senza: mappa colorata, classifica, serie e
   tabelle vengono dal server. Qui c'e' solo l'interazione: il valore sulla
   mappa, l'anno e il territorio del modulo dato, la citazione da copiare,
   l'indice di pagina. Il tema lo tiene ds-chrome.js, come su ogni pagina.
   Nato coi prototipi (design/v1/src/js/proto.js).

   Gli agganci li fa DiV1.init(root): al caricamento su tutto il documento, e
   di nuovo su un pezzo di pagina arrivato dopo (un modulo dato che cambia
   indicatore senza ricaricare). Ogni elemento si aggancia una volta sola, per
   quante volte init lo incontri: un doppio aggancio non si vede finche' due
   clic sulla mappa non si annullano a vicenda. */
(function () {
  "use strict";
  if (window.DiV1) return;

  /* ---------- numeri all'italiana, stessa regola di seo_titles._decimals ----------
     Lo zero si scrive "0", e sotto un centesimo i decimali arrivano alla prima
     cifra significativa. tests/unit/test_decimals_parity.py legge il corpo di
     questa funzione e lo confronta con le due copie Python: una riga di forma
     diversa fa fallire la prova, apposta. */
  function decimals(v) {
    var m = Math.abs(v);
    if (m === 0) return 0;
    if (m >= 100) return 0;
    if (m >= 1) return 1;
    if (m >= 0.01) return 2;
    return m >= 0.001 ? 3 : 4;
  }
  // Come numfmt.text: il trattino davanti ai negativi, lo zero arrotondato senza segno.
  function fmt(v, d) {
    if (v === null || v === undefined || isNaN(v)) return "n.d.";
    if (d === undefined || d === null) d = decimals(v);
    var s = new Intl.NumberFormat("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }).format(Math.abs(v));
    var zero = Number(s.replace(/\./g, "").replace(",", ".")) === 0;
    return (v < 0 && !zero ? "-" : "") + s;
  }
  /* ---------- i gradini della mappa, stessa regola di choropleth_scale ----------
     Sei gradini uguali fra minimo e massimo; sei gruppi di pari numerosita'
     (quantili) quando un gradino solo prenderebbe almeno meta' dei territori.
     La regola vive in app/indicator_notes.py, e tests/unit/test_choropleth_parity.py
     esegue queste righe con node e le confronta con la copia Python. */
  /* choro:start */
  var QUANTILE_SHARE = 0.5, QUANTILE_MIN_N = 6;
  var LEGEND_MODE = {
    equal: "Sei gradini uguali fra minimo e massimo.",
    quantile: "Sei gruppi con lo stesso numero di territori, perché un valore fuori scala metterebbe quasi tutti gli altri nello stesso colore. Al centro la mediana."
  };
  function choroScale(values) {
    var v = values.slice().sort(function (a, b) { return a - b; });
    var n = v.length;
    if (!n) return null;
    var lo = v[0], hi = v[n - 1], span = (hi - lo) || 1;
    var counts = [0, 0, 0, 0, 0, 0];
    v.forEach(function (x) { counts[Math.min(5, Math.floor((x - lo) / span * 6))] += 1; });
    var mid = Math.floor(n / 2), median = n % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
    if (n >= QUANTILE_MIN_N && hi > lo && Math.max.apply(null, counts) >= QUANTILE_SHARE * n) {
      return { mode: "quantile", lo: lo, hi: hi, median: median, sorted: v };
    }
    return { mode: "equal", lo: lo, hi: hi, median: median, sorted: v };
  }
  function choroStep(x, sc) {
    if (sc.mode === "equal") return Math.min(6, Math.floor((x - sc.lo) / ((sc.hi - sc.lo) || 1) * 6) + 1);
    var i = 0;
    while (i < sc.sorted.length && sc.sorted[i] < x) i++;
    return Math.min(6, Math.floor(i * 6 / sc.sorted.length) + 1);
  }
  /* choro:end */
  // La legenda di una mappa ricolorata: soglie e frase sui gradini.
  function choroLegend(box, sc) {
    var lg = { min: sc.lo, mid: sc.mode === "quantile" ? sc.median : sc.lo + (sc.hi - sc.lo) / 2, max: sc.hi };
    box.querySelectorAll("[data-legend]").forEach(function (el) {
      var key = el.dataset.legend;
      el.textContent = key === "mode" ? LEGEND_MODE[sc.mode] : fmt(lg[key]);
    });
  }
  function withUnit(v, unit) {
    if (v === null || v === undefined) return "n.d.";
    if (unit === "%") return fmt(v) + "%";
    return unit ? fmt(v) + " " + unit : fmt(v);
  }

  /* ---------- una volta sola per elemento ----------
     Il segno sta in una WeakMap, non in un attributo: un elemento clonato si
     porta dietro gli attributi ma non gli ascoltatori, e un segno nel DOM lo
     farebbe credere gia' agganciato. */
  var bound = new WeakMap();
  function each(root, selector, fn) {
    var found = Array.prototype.slice.call(root.querySelectorAll(selector));
    // querySelectorAll non guarda root: un modulo passato da solo e' anche il suo root.
    if (root.matches && root.matches(selector)) found.unshift(root);
    found.forEach(function (el) {
      var seen = bound.get(el);
      if (!seen) { seen = {}; bound.set(el, seen); }
      if (seen[selector]) return;
      seen[selector] = true;
      fn(el);
    });
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

  /* ---------- il suggerimento delle mappe: solo col mouse ----------
     Al tocco un suggerimento che segue il dito non si legge (il dito lo
     copre), e su iOS un contenuto nuovo mostrato al mousemove di
     compatibilita' si mangiava il click: per questo `pointermove` e solo
     `pointerType === "mouse"`. Resta dentro la mappa e va a capo. */
  function placeTip(box, tip, ev) {
    var r = box.getBoundingClientRect();
    var x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14;
    if (x + tip.offsetWidth > r.width) x = ev.clientX - r.left - tip.offsetWidth - 10;
    tip.style.left = Math.max(0, Math.min(x, r.width - tip.offsetWidth)) + "px";
    tip.style.top = y + "px";
  }

  /* ---------- mappa: il valore al passaggio del mouse ---------- */
  function initMap(box) {
    var tip = box.querySelector("[data-map-tip]");
    box.addEventListener("pointermove", function (ev) {
      if (ev.pointerType !== "mouse") return;
      var p = ev.target.closest(".map [data-key]");
      if (!p) { tip.hidden = true; return; }
      tip.innerHTML = "";
      var name = document.createElement("span");
      name.textContent = p.dataset.name + " ";
      var val = document.createElement("b");
      val.textContent = p.dataset.value || "n.d.";
      tip.append(name, val);
      tip.hidden = false;
      placeTip(box, tip, ev);
    });
    box.addEventListener("pointerleave", function () { tip.hidden = true; });
  }

  function nearestDot(svg, ev, radius) {
    var best = null, bestD = radius * radius;
    svg.querySelectorAll(".strip__dot").forEach(function (d) {
      var r = d.getBoundingClientRect();
      var dx = r.left + r.width / 2 - ev.clientX, dy = r.top + r.height / 2 - ev.clientY;
      var dd = dx * dx + dy * dy;
      if (dd <= bestD) { bestD = dd; best = d; }
    });
    return best;
  }

  /* ---------- il modulo dato della scheda ----------
     Il confine e' il `data-page-root` piu' vicino (il modulo stesso, quando
     sta da solo), se no il documento: dentro stanno la striscia e la serie
     che il territorio scelto accende. Il JSON sta nel modulo (ui.explore) o,
     in home, accanto nel pannello. */
  // Il modulo agganciato per ultimo in ogni confine, per la striscia che sta fuori.
  var liveExplore = new WeakMap();
  // Il modulo di ogni classifica, per l'ancora #p-<key> che arriva dopo (hashchange).
  var exploreOf = new WeakMap();

  // "Dall'11ª alla 97ª", come classifica.from_to: l'articolo si elide davanti
  // a ottava, undicesima, ottantesima e simili.
  function fromTo(first, last) {
    function art(prep, n) {
      var vowel = n === 8 || n === 11 || (n >= 80 && n <= 89) || (n >= 800 && n <= 899);
      return prep + (vowel ? "ll'" : "lla ") + n + "ª";
    }
    var text = art("da", first) + " " + art("a", last);
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  // L'ancora di una riga della classifica (#p-<key>, da /provincia/<key>)
  // diventa la scelta del modulo: con il JavaScript la riga si accende come
  // una scelta, insieme alla mappa, alla striscia e alla serie, e resta
  // accesa quando il cambio d'anno ridisegna le righe. Un ascoltatore solo,
  // sul documento.
  function hashId() {
    try { return decodeURIComponent(location.hash.slice(1)); } catch (e) { return ""; }
  }
  function followHash() {
    var id = hashId();
    var row = id && document.getElementById(id);
    var mod = row && row.closest("[data-explore]");
    var ctl = mod && exploreOf.get(mod);
    if (ctl && row.dataset.key) ctl.choose(row.dataset.key);
  }
  addEventListener("hashchange", followHash);

  function initExplore(mod) {
    var page = mod.closest("[data-page-root]") || document;
    var dataEl = mod.querySelector("[data-explore-data]") || page.querySelector("[data-explore-data]");
    if (!dataEl) return;
    var data = JSON.parse(dataEl.textContent);
    var slider = mod.querySelector("[data-year]");
    var select = mod.querySelector("[data-territory]");
    var body = mod.querySelector("[data-rank-body]");
    // La classifica piegata (province): tre corpi, prime, di mezzo e ultime.
    var parts = {
      head: mod.querySelector('[data-rank-part="head"]'),
      middle: mod.querySelector('[data-rank-part="middle"]'),
      tail: mod.querySelector('[data-rank-part="tail"]')
    };
    var claim = mod.querySelector("[data-claim]");
    var live = mod.querySelector("[data-live]");
    // "Vai alla riga nella classifica", accanto al campo (solo le province).
    var jump = mod.querySelector("[data-rank-goto]");
    var series = page.querySelector("[data-series]");
    var lowerBetter = data.direction === "lower_better" || data.direction === "higher_worse";
    var current = data.years[data.years.length - 1];

    // A pari valore l'ordine e' per nome, come sul server (indicator_view
    // _build_level): il confronto semplice, non localeCompare, perche' Python
    // confronta le stringhe per codice. Senza, un pari merito cambiava
    // posizione fra la pagina servita e lo stesso anno ridisegnato.
    function rows(year) {
      var m = data.matrix[String(year)] || {};
      var list = Object.keys(m).filter(function (k) { return m[k] !== null; }).map(function (k) { return { key: k, name: data.names[k] || k, value: m[k] }; });
      list.sort(function (a, b) {
        var d = lowerBetter ? a.value - b.value : b.value - a.value;
        return d || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
      });
      return list;
    }

    function paint(year) {
      var list = rows(year);
      if (!list.length) return;
      var vals = list.map(function (r) { return r.value; });
      var sc = choroScale(vals);
      var lo = sc.lo, hi = sc.hi;
      var avg = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
      var max = Math.max(hi, 0) || 1;
      var byKey = {};
      list.forEach(function (r) { byKey[r.key] = r; });

      // Un territorio senza dato nell'anno scelto prende il tratteggio del
      // n.d., lo stesso pattern che il server mette sull'ultimo anno: le
      // province con un dato cambiano da un anno all'altro (95 o 106 su 107).
      var nd = mod.querySelector(".map pattern[id]");
      mod.querySelectorAll(".map [data-key]").forEach(function (p) {
        var r = byKey[p.dataset.key];
        p.classList.remove("q1", "q2", "q3", "q4", "q5", "q6");
        if (r) {
          p.classList.add("q" + choroStep(r.value, sc));
          p.style.fill = "";
          p.dataset.value = withUnit(r.value, data.unit);
        } else {
          p.style.fill = nd ? "url(#" + nd.id + ")" : "";
          p.dataset.value = "n.d.";
        }
      });
      choroLegend(mod, sc);

      var sel = select ? select.value : "";
      // Piegata come sul server (indicatore.fold): le prime e le ultime
      // `edge` righe in vista, le altre nel details, se le righe dell'anno
      // sono piu' di `over`. La riga della media va nel pezzo della riga che
      // la segue. Si riscrivono solo i corpi: il details resta aperto o chiuso.
      var folded = !!(data.fold && parts.head && parts.middle && parts.tail && list.length > data.fold.over);
      var edge = folded ? data.fold.edge : 0;
      var html = { head: [], middle: [], tail: [] }, refDone = false;
      list.forEach(function (r, i) {
        var part = !folded || i < edge ? "head" : i >= list.length - edge ? "tail" : "middle";
        var crosses = lowerBetter ? r.value > avg : r.value < avg;
        if (!refDone && crosses) {
          html[part].push('<tr class="ref"><td></td><th scope="row">Media semplice delle ' + list.length + " " + data.plural + '</th><td class="barcell" aria-hidden="true"></td><td class="val"><data class="n n--cell" value="' + avg + '">' + fmt(avg, data.decimals) + "</data></td></tr>");
          refDone = true;
        }
        var dot = data.areas && data.areas[r.key] ? '<span class="area-dot area-dot--' + data.areas[r.key] + '" aria-hidden="true"></span>' : "";
        var name = dot + (data.profile ? '<a href="' + profileHref(r.key) + '">' + esc(r.name) + "</a>" : esc(r.name));
        var id = data.row_id ? ' id="' + data.row_id + r.key + '"' : "";
        html[part].push('<tr data-key="' + r.key + '"' + id + (r.key === sel ? ' class="is-on" aria-current="true"' : "") + '><td class="rank"><span class="n n--rank"><data value="' + (i + 1) + '">' + (i + 1) + '</data><span class="n__o">ª</span></span></td><th scope="row">' + name +
          '</th><td class="barcell" aria-hidden="true"><span class="bar"><i style="width:' + (Math.max(r.value, 0) / max * 100).toFixed(1) + '%"></i></span></td><td class="val"><data class="n n--cell" value="' + r.value + '">' + fmt(r.value, data.decimals) + "</data></td></tr>");
      });
      if (parts.head && parts.middle && parts.tail) {
        parts.head.innerHTML = html.head.join("");
        parts.middle.innerHTML = html.middle.join("");
        parts.tail.innerHTML = html.tail.join("");
        // Un anno con meno righe della soglia non si piega: tutte in cima.
        var more = mod.querySelector("[data-rank-more]"), tail = mod.querySelector("[data-rank-tail]");
        if (more) more.hidden = !folded;
        if (tail) tail.hidden = !folded;
        var cap = mod.querySelector("[data-rank-caption]");
        if (cap) cap.textContent = folded ? "Le prime " + edge + " " + data.plural : "Le " + list.length + " " + data.plural;
        if (folded) {
          var label = fromTo(edge + 1, list.length - edge) + ": le altre " + (list.length - 2 * edge) + " " + data.plural;
          mod.querySelectorAll("[data-rank-summary]").forEach(function (el) { el.textContent = label; });
        }
      } else {
        body.innerHTML = html.head.join("");
      }

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

    // La riga della classifica di un territorio, o null se nell'anno non c'e'.
    function rowOf(key) {
      var row = null;
      if (key) mod.querySelectorAll("[data-rank-body] tr[data-key]").forEach(function (tr) { if (tr.dataset.key === key) row = tr; });
      return row;
    }

    function highlight(key) {
      mod.querySelectorAll(".map [data-key]").forEach(function (p) { p.classList.toggle("is-on", p.dataset.key === key); });
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
      page.querySelectorAll(".tile[data-key]").forEach(function (t) { t.classList.toggle("is-on", t.dataset.key === key); });
      page.querySelectorAll(".sm__item[data-key]").forEach(function (t) { t.classList.toggle("is-on", t.dataset.key === key); });
      // La barra della striscia che resta dice chi e' scelto, col valore
      // dell'anno della striscia (l'ultimo); e la scelta si ricorda fra le
      // schede della stessa famiglia (initFamily).
      var lastYear = data.years[data.years.length - 1];
      page.querySelectorAll("[data-stripbar-sel]").forEach(function (el) {
        var hit = key ? rows(lastYear).filter(function (x) { return x.key === key; })[0] : null;
        if (hit) el.innerHTML = "<b>" + esc(hit.name) + "</b> " + esc(withUnit(hit.value, data.unit));
        else el.textContent = key && data.names[key] ? data.names[key] + ": n.d." : el.dataset.empty;
      });
      try { if (key) sessionStorage.setItem("di:territorio", key); else sessionStorage.removeItem("di:territorio"); } catch (e) { /* senza storage non si ricorda */ }
      // "Pavia: 82,6 anni nel 2024, 86ª su 107 province dal valore più alto":
      // la posizione col suo denominatore (chi ha il dato quell'anno) e il
      // criterio, lo stesso ordine della classifica.
      if (live && key) {
        var list = rows(current), at = -1;
        list.forEach(function (x, i) { if (x.key === key) at = i; });
        if (at >= 0) {
          live.textContent = list[at].name + ": " + withUnit(list[at].value, data.unit) + " nel " + current + ", " + (at + 1) + "ª su " + list.length + " " + data.plural +
            (lowerBetter ? " dal valore più basso." : " dal valore più alto.");
        } else live.textContent = (data.names[key] || key) + ": dato non disponibile nel " + current + ".";
      }
      // Il link alla riga c'e' solo se la riga c'e': un anno senza il dato
      // della provincia scelta lo nasconde, il cambio d'anno lo rivaluta.
      if (jump) {
        var goRow = rowOf(key);
        jump.hidden = !(goRow && goRow.id);
        if (goRow && goRow.id) jump.setAttribute("href", "#" + goRow.id);
      }
    }

    // La linea sotto cui una riga si vede davvero: lo scroll-padding della
    // pagina (la testata) piu' lo scroll-margin della riga (sotto i 1200 la
    // barra delle sezioni, components.css). E' dove il browser porta
    // un'ancora: una riga sopra quella linea sta sotto una barra.
    function landing(row) {
      var pad = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
      return pad + (parseFloat(getComputedStyle(row).scrollMarginTop) || 0);
    }

    // La riga di un territorio a vista: il details che la tiene si apre, e
    // la pagina scorre solo se la riga non si vede gia' (dopo un'ancora il
    // browser di solito l'ha gia' portata li'). Un pixel di tolleranza: il
    // browser la lascia sulla linea, e senza la riga appena arrivata
    // sembrerebbe coperta e la pagina scorrerebbe una seconda volta.
    function reveal(key) {
      var row = rowOf(key);
      if (!row) return;
      var more = row.closest("details");
      if (more && !more.open) more.open = true;
      var box = row.getBoundingClientRect();
      if (box.top >= landing(row) - 1 && box.bottom <= innerHeight) return;
      var still = matchMedia("(prefers-reduced-motion: reduce)").matches;
      row.scrollIntoView({ block: "center", behavior: still ? "auto" : "smooth" });
    }

    // Scegliere un territorio dall'ancora della riga (#p-<key>): all'arrivo,
    // da un hashchange o dal link accanto al campo. Il campo sceglie da se'.
    function choose(key) {
      if (!select || !data.names[key]) return;
      select.value = key;
      highlight(key);
      reveal(key);
    }

    if (slider) slider.addEventListener("input", function () {
      current = data.years[Number(slider.value)];
      paint(current);
      highlight(select ? select.value : "");
    });
    // Il campo accende e basta, come la mappa e la striscia: con le frecce
    // (Chrome su Windows e Linux) ogni tasto e' un change, e far scorrere la
    // pagina a ogni tasto portava il campo fuori dalla vista. Alla riga porta
    // il link accanto al campo (#p-<key>), che passa da followHash e reveal.
    if (select) select.addEventListener("change", function () { highlight(select.value); });
    // Prima che il browser segua il link apre il details che tiene la riga:
    // alla stessa ancora di prima (#p-pavia due volte) non arriva nessun
    // hashchange, e il browser scorre solo verso una riga che si vede.
    if (jump) jump.addEventListener("click", function () {
      var row = rowOf(select ? select.value : "");
      var more = row && row.closest("details");
      if (more && !more.open) more.open = true;
    });
    // Con il JavaScript l'ancora della riga diventa una scelta (followHash),
    // e `:target` non accende piu' la riga da solo: una seconda riga accesa
    // accanto alla scelta sarebbe un'altra scelta.
    mod.classList.add("has-js");
    exploreOf.set(mod, { choose: choose });
    // Il campo ripristinato dal browser dopo un Indietro riaccende la sua evidenza.
    if (select && select.value) highlight(select.value);
    // Arrivati da una scheda della stessa famiglia, il territorio scelto la'
    // resta scelto qui (se qui c'e').
    else if (select && fromFamily()) {
      var kept = null;
      try { kept = sessionStorage.getItem("di:territorio"); } catch (e) { kept = null; }
      if (kept && data.names[kept]) { select.value = kept; highlight(kept); }
    }
    // Il tuo territorio, quando non c'e' gia' un'altra scelta: acceso in
    // striscia, mappa e classifica, e una riga sotto la figura d'apertura.
    else if (select && page.querySelector("[data-mine-note]")) {
      var mine = readMine();
      var mk = mine && (data.names[mine.key] ? mine.key : (mine.region && data.names[mine.region] ? mine.region : null));
      var note = page.querySelector("[data-mine-note]");
      if (mk) {
        select.value = mk;
        highlight(mk);
        if (note) {
          var yr = data.years[data.years.length - 1], list = rows(yr), at = -1;
          list.forEach(function (x, i) { if (x.key === mk) at = i; });
          var who = mk === mine.key ? "La tua " + (mine.level === "provincia" ? "provincia" : "regione") + ", " + mine.name
                                    : data.names[mk] + ", la regione di " + mine.name;
          note.textContent = at >= 0
            ? who + ": " + withUnit(list[at].value, data.unit) + " nel " + yr + ", " + (at + 1) + "ª su " + list.length + " " + data.plural + (lowerBetter ? " dal valore più basso." : " dal valore più alto.")
            : who + ": dato non disponibile nel " + yr + ".";
          note.hidden = false;
        }
      }
    }
    // Arrivati da /provincia/<key> con #p-<key>: la riga diventa la scelta, e
    // se il browser non ha aperto il details da se' lo apre reveal.
    var target = hashId();
    if (data.row_id && target.indexOf(data.row_id) === 0) {
      var targetRow = document.getElementById(target);
      if (targetRow && mod.contains(targetRow)) choose(targetRow.dataset.key);
    }
    // La striscia sta fuori dal modulo, nel confine: un modulo sostituito sul
    // posto la ritrova gia' agganciata. Il suo clic si aggancia una volta sola
    // e parla col modulo agganciato per ultimo, non con quello che l'ha vista
    // per primo e che forse non e' piu' nella pagina.
    liveExplore.set(page, { select: select, highlight: highlight });
    each(page, ".strip", function (svg) {
      svg.addEventListener("click", function (ev) {
        // Un punto e' piccolo: al tocco vale il piu' vicino entro 22 pixel.
        var c = ev.target.closest(".strip__dot") || nearestDot(svg, ev, 22);
        var cur = liveExplore.get(page);
        if (!c || !cur || !cur.select) return;
        cur.select.value = cur.select.value === c.dataset.key ? "" : c.dataset.key;
        cur.highlight(cur.select.value);
      });
    });
    mod.addEventListener("click", function (ev) {
      var p = ev.target.closest(".map [data-key]");
      if (!p || !select) return;
      // Un territorio senza dato non ha una voce nel campo: sceglierlo lo svuotava.
      if (!data.names[p.dataset.key]) return;
      select.value = select.value === p.dataset.key ? "" : p.dataset.key;
      highlight(select.value);
    });
  }

  /* ---------- mappe per scegliere un territorio ----------
     Col mouse il nome al passaggio e il clic apre il profilo. Al tocco il
     primo tocco mostra: contorna il territorio e scrive sotto la mappa il suo
     nome (con la posizione o il valore che la mappa porta in `data-name`) e
     il link al profilo, da 44 pixel. Il secondo tocco sullo stesso territorio,
     o il link, lo apre. Senza JavaScript ogni tracciato resta un link. Le
     mappe dentro un `[data-picker]` (la fascia dei territori della home)
     scelgono gia' da sole, e qui non si toccano. */
  function initNavmap(box) {
    var tip = box.querySelector("[data-navmap-tip]");
    if (!tip) return;
    box.addEventListener("pointermove", function (ev) {
      if (ev.pointerType !== "mouse") return;
      var a = ev.target.closest("a[data-key]");
      if (!a) { tip.hidden = true; return; }
      tip.textContent = a.dataset.name;
      tip.hidden = false;
      placeTip(box, tip, ev);
    });
    box.addEventListener("pointerleave", function () { tip.hidden = true; });
    if (box.closest("[data-picker]")) return;
    var touch = false, card = null, picked = null;
    box.addEventListener("pointerdown", function (ev) { touch = ev.pointerType !== "mouse"; });
    box.addEventListener("click", function (ev) {
      var a = ev.target.closest("a[data-key]");
      if (!a || !touch || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
      if (picked === a) return; // secondo tocco: il link apre il profilo
      ev.preventDefault();
      if (picked) picked.classList.remove("is-on");
      picked = a;
      a.classList.add("is-on");
      if (!card) {
        card = document.createElement("p");
        card.className = "navmap__card";
        card.setAttribute("role", "status");
        box.appendChild(card);
      }
      card.innerHTML = '<span class="navmap__card-t">' + esc(a.dataset.name) + '</span> <a class="linkarrow" href="' + esc(a.getAttribute("href")) + '">Apri il profilo</a>';
      card.hidden = false;
    });
  }

  /* ---------- regioni e province della home: l'anteprima del territorio scelto ----------
     Le anteprime arrivano tutte nel JSON del blocco, gia' scritte dal server.
     Qui si ricompone la stessa scheda di home/_territori.html, e il clic sulla
     mappa sceglie invece di aprire: il profilo si apre dal bottone. */
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function initPicker(box) {
    var dataEl = box.querySelector("[data-picker-data]");
    var card = box.querySelector("[data-picker-card]");
    if (!dataEl || !card) return;
    var data = JSON.parse(dataEl.textContent);
    var select = box.querySelector("[data-picker-select]");
    var field = box.querySelector("[data-picker-field]");
    if (field) field.hidden = false;
    function render(key) {
      var p = data[key];
      if (!p) return;
      var facts = (p.facts || []).map(function (x) {
        var text = x.href ? '<a href="' + esc(x.href) + '">' + esc(x.text) + "</a>" : esc(x.text);
        return "<div><dt>" + esc(x.label) + "</dt><dd>" + text + (x.note ? ' <span class="terr__note">' + esc(x.note) + "</span>" : "") + "</dd></div>";
      }).join("");
      card.innerHTML =
        '<p class="terr__kicker">' + (p.area ? '<span class="area-dot area-dot--' + esc(p.area) + '" aria-hidden="true"></span>' : "") + esc(p.kicker) + "</p>" +
        '<h4 class="terr__name"><a href="' + esc(p.href) + '">' + esc(p.name) + "</a></h4>" +
        '<p class="terr__lead">' + esc(p.lead) + "</p>" +
        (facts ? '<dl class="terr__facts">' + facts + "</dl>" : "") +
        '<p class="terr__cta"><a class="btn" href="' + esc(p.href) + '">' + esc(p.cta) + "</a></p>";
      box.querySelectorAll("[data-navmap] a[data-key]").forEach(function (a) { a.classList.toggle("is-on", a.dataset.key === key); });
      if (select && select.value !== key) select.value = key;
    }
    // Dopo un Indietro il browser rimette nel campo la scelta di prima, mentre
    // il server ha estratto un altro territorio: vince il campo.
    var shown = box.querySelector("[data-navmap] a.is-on[data-key]");
    if (select && data[select.value] && (!shown || shown.dataset.key !== select.value)) render(select.value);
    box.addEventListener("click", function (ev) {
      var a = ev.target.closest("[data-navmap] a[data-key]");
      if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
      ev.preventDefault();
      render(a.dataset.key);
    });
    if (select) select.addEventListener("change", function () { render(select.value); });
  }

  /* ---------- schede (tab): regioni e province dell'indicatore in evidenza ----------
     Senza JavaScript ogni scheda e' un link alla pagina con quel livello; qui
     il clic mostra il pannello gia' in pagina, e le frecce passano da una
     scheda all'altra come chiede il pattern ARIA dei tab. */
  function initTabs(list) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll("[data-tab]"));
    if (tabs.length < 2) return;
    var scope = list.closest("article, section") || document;
    // I ruoli li mette il JavaScript: senza, restano due link tabulabili.
    list.setAttribute("role", "tablist");
    tabs.forEach(function (t) {
      var panel = document.getElementById(t.dataset.tab);
      t.setAttribute("role", "tab");
      t.setAttribute("aria-controls", t.dataset.tab);
      t.removeAttribute("aria-current");
      if (panel) { panel.setAttribute("role", "tabpanel"); panel.setAttribute("aria-labelledby", t.id); panel.tabIndex = 0; }
    });
    function show(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.classList.toggle("is-on", on);
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.dataset.tab);
        if (panel) panel.hidden = !on;
      });
      // Il titolo sopra le schede porta alla scheda sul livello mostrato.
      var shown = document.getElementById(tab.dataset.tab);
      if (shown && shown.dataset.href) {
        scope.querySelectorAll("[data-tab-href]").forEach(function (a) { a.setAttribute("href", shown.dataset.href); });
      }
      if (focus) tab.focus();
    }
    show(tabs.filter(function (t) { return t.classList.contains("is-on"); })[0] || tabs[0], false);
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
        ev.preventDefault();
        show(t, false);
      });
      t.addEventListener("keydown", function (ev) {
        var step = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
        if (ev.key === " ") { ev.preventDefault(); show(t, false); return; }
        if (!step) return;
        ev.preventDefault();
        show(tabs[(i + step + tabs.length) % tabs.length], true);
      });
    });
  }

  /* ---------- tabelle lunghe: chiuse sul telefono, sempre nel DOM ----------
     Solo al primo aggancio: un secondo init non richiude cio' che il lettore
     ha aperto. */
  // Chiusi sul telefono, anche in orizzontale: a 844x390 l'atlante con tutti
  // i temi aperti era lungo 63.000 pixel.
  function initCollapse(d) {
    if (matchMedia("(max-width: 599px), (pointer: coarse) and (max-height: 500px)").matches) d.open = false;
  }

  /* ---------- indice di pagina: la voce della sezione che si sta leggendo ---------- */
  function initToc(toc) {
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
    /* Sotto i 1200 la lista scorre di lato: la sfumatura dice da che parte
       ci sono altre voci. */
    var list = toc.querySelector("ol");
    if (list) {
      var edges = function () {
        var more = list.scrollWidth - list.clientWidth;
        list.classList.toggle("is-more-l", more > 1 && list.scrollLeft > 1);
        list.classList.toggle("is-more-r", more > 1 && list.scrollLeft < more - 1);
      };
      list.addEventListener("scroll", edges, { passive: true });
      addEventListener("resize", edges);
      edges();
    }
  }

  /* ---------- la famiglia della scheda: le pagine fra cui la striscia si ricompone ---------- */
  function familyPaths() {
    var fig = document.querySelector(".lead-figure[data-family]");
    if (!fig) return [];
    try { return JSON.parse(fig.dataset.family); } catch (e) { return []; }
  }
  function inFamily(url) {
    if (!url) return false;
    try { return familyPaths().indexOf(new URL(url, location.href).pathname) >= 0; } catch (e) { return false; }
  }
  function fromFamily() {
    var nav = window.navigation && navigation.activation && navigation.activation.from;
    return inFamily(nav ? nav.url : document.referrer) && (nav ? nav.url : document.referrer) !== location.href;
  }
  // La pagina che si lascia: se si va a una sorella, ogni punto della striscia
  // grande prende il suo nome di transizione e scivola nella posizione nuova.
  // L'altra meta' (pagereveal) sta in testa alla scheda.
  addEventListener("pageswap", function (e) {
    if (!e.viewTransition || !e.activation || !e.activation.entry || !inFamily(e.activation.entry.url)) return;
    document.querySelectorAll(".lead-figure .strip__dot").forEach(function (c) {
      if (c.getClientRects().length) c.style.viewTransitionName = "dot-" + c.dataset.key;
    });
  });

  /* ---------- il tuo territorio ----------
     Si sceglie una volta, dal profilo di una regione o di una provincia ("E'
     la mia"), e resta nel browser (`di:mio`, JSON con livello, chiave, nome e,
     per una provincia, la sua regione). Da li': un segno nella testata che
     porta al profilo, e in ogni scheda il territorio acceso in striscia, mappa
     e classifica, con una riga che dice dove sta. Una scheda solo regionale,
     con una provincia scelta, accende la sua regione. Niente passa dal server:
     la pagina per Google e' la stessa per tutti. */
  function readMine() {
    try { var v = JSON.parse(localStorage.getItem("di:mio") || "null"); return v && v.key && v.level ? v : null; }
    catch (e) { return null; }
  }
  function writeMine(v) {
    try { if (v) localStorage.setItem("di:mio", JSON.stringify(v)); else localStorage.removeItem("di:mio"); } catch (e) { /* senza storage non si ricorda */ }
    document.dispatchEvent(new CustomEvent("di:mio"));
  }
  function initMine(btn) {
    btn.hidden = false;
    var me = { level: btn.dataset.level, key: btn.dataset.key, name: btn.dataset.name };
    if (btn.dataset.region) { me.region = btn.dataset.region; me.regionName = btn.dataset.regionName; }
    var word = me.level === "provincia" ? "provincia" : "regione";
    function paint() {
      var m = readMine(), on = !!m && m.level === me.level && m.key === me.key;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.textContent = on ? "La tua " + word + ": togli la scelta" : "È la mia " + word;
    }
    btn.addEventListener("click", function () {
      var m = readMine();
      writeMine(m && m.level === me.level && m.key === me.key ? null : me);
    });
    document.addEventListener("di:mio", paint);
    paint();
  }
  function initMineChip() {
    var right = document.querySelector(".sitechrome .hdr__right");
    if (!right || document.querySelector(".mine-chip")) return;
    var chip = document.createElement("a");
    chip.className = "mine-chip";
    right.insertBefore(chip, right.firstChild);
    function paint() {
      var m = readMine();
      chip.hidden = !m;
      if (!m) return;
      chip.href = (m.level === "provincia" ? "/provincia/" : "/regione/") + m.key;
      chip.textContent = "La tua: " + m.name;
    }
    document.addEventListener("di:mio", paint);
    paint();
  }

  /* ---------- la striscia che diventa Italia ----------
     Nella figura d'apertura di una scheda regionale il comando "Striscia |
     Italia" ricompone gli stessi venti punti in una griglia a forma d'Italia
     (app/design/tiles.py). Il passaggio e' un volo: si misurano i punti e le
     caselle, e un segno per regione va dall'uno all'altra cambiando forma e
     colore (la ripartizione diventa il valore). Senza JavaScript il comando
     non c'e' e resta la striscia; con prefers-reduced-motion la vista cambia
     e basta. La scelta della vista si ricorda (`di:vista`), e toccare una
     casella sceglie il territorio come un punto della striscia. */
  function initTilemap(box) {
    var fig = box.closest(".lead-figure");
    var toggle = fig && fig.querySelector("[data-view-toggle]");
    var strip = fig && fig.querySelector(".chart--hero");
    if (!toggle || !strip) return;
    var page = fig.closest("[data-page-root]") || document;
    box.hidden = false;
    toggle.hidden = false;
    var still = matchMedia("(prefers-reduced-motion: reduce)");
    function tilesOf() { var m = {}; box.querySelectorAll(".tile[data-key]").forEach(function (t) { m[t.dataset.key] = t; }); return m; }
    function dotsOf() { var m = {}; strip.querySelectorAll(".strip__dot[data-key]").forEach(function (d) { m[d.dataset.key] = d; }); return m; }
    function apply(view) {
      fig.classList.toggle("is-tiles", view === "tiles");
      toggle.querySelectorAll("[data-view]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.view === view ? "true" : "false"); });
    }
    function fly(view) {
      var toTiles = view === "tiles";
      var fromEls = toTiles ? dotsOf() : tilesOf();
      var from = {};
      Object.keys(fromEls).forEach(function (k) {
        var el = fromEls[k], r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        from[k] = { r: r, color: toTiles ? cs.fill : cs.backgroundColor };
      });
      apply(view);
      var toEls = toTiles ? tilesOf() : dotsOf();
      var layer = document.createElement("div");
      layer.className = "morph-layer";
      layer.setAttribute("aria-hidden", "true");
      document.body.appendChild(layer);
      var targets = Object.keys(toEls).filter(function (k) { return from[k]; });
      targets.forEach(function (k) { toEls[k].style.visibility = "hidden"; });
      var runs = targets.map(function (k, i) {
        var el = toEls[k], b = el.getBoundingClientRect(), a = from[k].r, cs = getComputedStyle(el);
        var endColor = toTiles ? cs.backgroundColor : cs.fill;
        var endRadius = toTiles ? cs.borderRadius : "50%";
        var startRadius = toTiles ? "50%" : getComputedStyle(fromEls[k]).borderRadius;
        var mark = document.createElement("i");
        mark.style.left = b.left + "px"; mark.style.top = b.top + "px";
        mark.style.width = b.width + "px"; mark.style.height = b.height + "px";
        layer.appendChild(mark);
        var dx = (a.left + a.width / 2) - (b.left + b.width / 2), dy = (a.top + a.height / 2) - (b.top + b.height / 2);
        var sx = a.width / b.width, sy = a.height / b.height;
        return mark.animate([
          { transform: "translate(" + dx + "px," + dy + "px) scale(" + sx + "," + sy + ")", borderRadius: startRadius, backgroundColor: from[k].color },
          { transform: "none", borderRadius: endRadius, backgroundColor: endColor }
        ], { duration: 650, delay: i * 12, easing: "cubic-bezier(0.2, 0.7, 0.2, 1)", fill: "both" }).finished;
      });
      Promise.all(runs).then(done, done);
      function done() {
        targets.forEach(function (k) { toEls[k].style.visibility = ""; });
        layer.remove();
      }
    }
    function show(view, animate) {
      if (fig.classList.contains("is-tiles") === (view === "tiles")) return;
      if (animate && !still.matches && Element.prototype.animate) fly(view); else apply(view);
      try { localStorage.setItem("di:vista", view); } catch (e) { /* senza storage non si ricorda */ }
    }
    toggle.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-view]");
      if (b) show(b.dataset.view, true);
    });
    box.addEventListener("click", function (ev) {
      var t = ev.target.closest(".tile[data-key]");
      var cur = t && liveExplore.get(page);
      if (!t || !cur || !cur.select) return;
      cur.select.value = cur.select.value === t.dataset.key ? "" : t.dataset.key;
      cur.highlight(cur.select.value);
    });
    var kept = null;
    try { kept = localStorage.getItem("di:vista"); } catch (e) { kept = null; }
    if (kept === "tiles") show("tiles", false);
  }

  /* ---------- la striscia che resta ----------
     Scende sotto la testata quando la striscia grande esce dallo schermo verso
     l'alto, e se ne va quando comincia l'analisi (o la nota sul metodo). Il
     suo posto lo dice il CSS (`--sticky-top`, chrome.css): qui si decide solo
     se c'e', e se c'e' la sua altezza va in `--stripbar-h`, che le ancore e la
     mappa ferma del modulo contano. Sui telefoni bassi (in orizzontale) non
     scende: con testata e barra delle sezioni lo schermo restava a meta'. */
  function initStripbar(bar) {
    var fig = document.querySelector(".lead-figure");
    var stop = document.getElementById("analisi") || document.getElementById("come-leggere");
    if (!fig) return;
    var low = matchMedia("(max-height: 500px)");
    var ticking = false;
    function update() {
      ticking = false;
      var top = parseFloat(getComputedStyle(bar).top) || 0;
      var past = fig.getBoundingClientRect().bottom < top;
      var before = !stop || stop.getBoundingClientRect().top > top + 80;
      var on = past && before && !low.matches;
      bar.classList.toggle("is-on", on);
      document.documentElement.style.setProperty("--stripbar-h", on ? bar.offsetHeight + "px" : "0px");
    }
    addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener("resize", update);
    update();
  }

  /* ---------- la testata che si ritira, sul telefono ----------
     Scendendo la testata esce dallo schermo, risalendo torna: la barra delle
     sezioni e la striscia salgono con lei, perche' leggono `--hdr-h`
     (chrome.css). Mai nei primi 120 pixel, mai col menu aperto o col fuoco
     dentro la testata, e solo sotto i 960 pixel o su un telefono in
     orizzontale. Una volta per documento. */
  var hdrOff = false;
  function initHdr() {
    var root = document.documentElement;
    var hdr = document.querySelector(".sitechrome .hdr");
    if (!hdr || root.hasAttribute("data-hdr-hide")) return;
    root.setAttribute("data-hdr-hide", "");
    var small = matchMedia("(max-width: 959px), (pointer: coarse) and (max-height: 500px)");
    var drawer = document.getElementById("ds-drawer");
    var last = scrollY, ticking = false;
    function set(off) {
      if (off === hdrOff) return;
      hdrOff = off;
      root.classList.toggle("is-hdr-off", off);
      document.dispatchEvent(new CustomEvent("di:hdr", { detail: { off: off } }));
    }
    function update() {
      ticking = false;
      var y = scrollY;
      var busy = (drawer && !drawer.hidden) || hdr.contains(document.activeElement);
      if (!small.matches || y < 120 || busy) { set(false); last = y; return; }
      if (Math.abs(y - last) < 8) return;
      set(y > last);
      last = y;
    }
    addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    hdr.addEventListener("focusin", function () { set(false); });
    small.addEventListener("change", update);
  }

  /* ---------- torna su: sulle pagine lunghe, dopo due schermate ----------
     Una volta per documento. Porta a `data-totop` del <main> (l'atlante lo
     manda ai filtri) o all'inizio del contenuto. Sotto i 960 pixel e' solo la
     freccia, e compare quando si risale (quando torna la testata): mentre si
     legge verso il basso copriva le cifre a destra delle classifiche. */
  function initTotop() {
    var main = document.getElementById("contenuto");
    if (!main || document.querySelector(".totop")) return;
    if (document.documentElement.scrollHeight < innerHeight * 5) return;
    var target = main.getAttribute("data-totop") || "#contenuto";
    var label = main.getAttribute("data-totop-label") || "Torna su";
    var a = document.createElement("a");
    a.className = "totop";
    a.href = target;
    a.setAttribute("aria-label", label);
    a.innerHTML = '<span aria-hidden="true">\u2191</span><span class="totop__t">' + esc(label) + "</span>";
    document.body.appendChild(a);
    var small = matchMedia("(max-width: 959px)");
    var last = scrollY, ticking = false, rising = false;
    function update() {
      ticking = false;
      var y = scrollY;
      if (Math.abs(y - last) >= 8) { rising = y < last; last = y; }
      a.classList.toggle("is-on", y > innerHeight * 2 && (!small.matches || rising));
    }
    addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
  }

  /* ---------- gli agganci, nell'ordine di sempre ---------- */
  function init(root) {
    root = root || document;
    each(root, "[data-map]", initMap);
    each(root, "[data-explore]", initExplore);
    each(root, "[data-navmap]", initNavmap);
    each(root, "[data-picker]", initPicker);
    each(root, "[data-tabs]", initTabs);
    each(root, "details[data-collapse-mobile]", initCollapse);
    each(root, ".toc", initToc);
  }

  window.DiV1 = { init: init, choroScale: choroScale, choroStep: choroStep, choroLegend: choroLegend };
  init(document);
  initTotop();
  initHdr();
  each(document, "[data-stripbar]", initStripbar);
  each(document, "[data-tilemap]", initTilemap);
  each(document, "[data-mine-set]", initMine);
  initMineChip();
})();
