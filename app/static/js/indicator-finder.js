/*
 * Indicator finder (progressive enhancement).
 *
 * Brings the atlas catalog search onto the indicator page: type to find any other
 * indicator and jump straight to its canonical page. With JavaScript disabled the
 * form submits to /atlante, which runs the very same search server-side, so the
 * behaviour degrades to exactly what the atlas offered before.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-indicator-search]");
  if (!form) return;
  var input = form.querySelector("[data-search-input]");
  var results = form.querySelector("[data-search-results]");
  if (!input || !results) return;

  var timer = null;
  var controller = null;

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function hide() {
    results.hidden = true;
    results.innerHTML = "";
  }

  function render(items) {
    if (!items.length) {
      results.innerHTML = '<p class="indicator-finder__empty">Nessun indicatore trovato.</p>';
      results.hidden = false;
      return;
    }
    results.innerHTML = items.slice(0, 8).map(function (it) {
      var meta = [it.theme, it.catalog_family_label].filter(Boolean).join(" · ");
      return (
        '<a class="indicator-finder__result" role="option" href="' + it.path + '">' +
        '<span class="indicator-finder__name">' + escapeHtml(it.name) + "</span>" +
        '<span class="indicator-finder__meta">' + escapeHtml(meta) + "</span></a>"
      );
    }).join("");
    results.hidden = false;
  }

  function search(query) {
    if (controller) controller.abort();
    controller = new AbortController();
    fetch("/api/search?q=" + encodeURIComponent(query), { signal: controller.signal })
      .then(function (r) { return r.json(); })
      .then(function (d) { render(d.results || []); })
      .catch(function () { /* aborted or offline: keep last state */ });
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    clearTimeout(timer);
    if (q.length < 2) { hide(); return; }
    timer = setTimeout(function () { search(q); }, 180);
  });

  input.addEventListener("focus", function () {
    if (input.value.trim().length >= 2 && results.innerHTML) results.hidden = false;
  });

  document.addEventListener("click", function (evt) {
    if (!form.contains(evt.target)) hide();
  });

  input.addEventListener("keydown", function (evt) {
    if (evt.key === "Escape") { hide(); input.blur(); }
  });

  // On submit, jump to the top result when JS produced one; otherwise let the
  // form fall through to /atlante?q=... (the same search, server-side).
  form.addEventListener("submit", function (evt) {
    var first = results.querySelector(".indicator-finder__result");
    if (first) {
      evt.preventDefault();
      window.location.assign(first.getAttribute("href"));
    }
  });
})();
