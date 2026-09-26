/* L'isola della pagina tema: il campo sopra "Tutti gli indicatori del tema"
   filtra le righe gia' in pagina sul loro `data-q` (nome e sottotema della
   fonte). Senza JavaScript il campo resta nascosto e le righe ci sono tutte. */
(function () {
  "use strict";
  var form = document.querySelector("[data-tema-filter]");
  if (!form) return;
  var input = form.querySelector("input[type='search']");
  var live = form.querySelector("[data-tema-live]");
  var empty = document.querySelector("[data-tema-empty]");
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-tema-group]"));
  var rows = Array.prototype.slice.call(document.querySelectorAll("[data-tema-row]"));
  var total = rows.length;

  function norm(text) {
    return (text || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  }
  var haystack = rows.map(function (row) { return norm(row.getAttribute("data-q")); });

  function apply() {
    var words = norm(input.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    rows.forEach(function (row, i) {
      var match = words.every(function (w) { return haystack[i].indexOf(w) !== -1; });
      row.hidden = !match;
      if (match) shown += 1;
    });
    groups.forEach(function (group) {
      group.hidden = !group.querySelector("[data-tema-row]:not([hidden])");
    });
    if (empty) empty.hidden = shown > 0;
    if (live) live.textContent = shown === total ? total + " indicatori" : shown + " indicatori su " + total;
  }

  form.hidden = false;
  input.addEventListener("input", apply);
})();
