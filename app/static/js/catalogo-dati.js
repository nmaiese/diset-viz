/*
 * Il filtro del catalogo dati (/catalogo-dati).
 *
 * Senza JavaScript il campo resta nascosto e le voci ci sono tutte, per tema:
 * il filtro e' una scorciatoia, non l'unico modo di trovare una voce. Cerca
 * nel nome e nella fonte, ignorando maiuscole e accenti ("mobilita" trova
 * "Mobilità"). Un tema senza voci da mostrare sparisce, uno con voci si apre
 * (sul telefono i temi partono chiusi, v1.js), e il conteggio si aggiorna
 * sotto il campo e accanto a ogni tema.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-cat]");
  if (!root) return;
  var box = root.querySelector("[data-cat-controls]");
  var input = root.querySelector("[data-cat-q]");
  var live = root.querySelector("[data-cat-live]");
  var empty = root.querySelector("[data-cat-empty]");
  var groups = Array.prototype.slice.call(root.querySelectorAll("[data-cat-group]"));
  if (!box || !input || !live) return;

  function fold(value) {
    return (value || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  }
  function label(n, one, many) { return n + " " + (n === 1 ? one : many); }

  var rows = groups.map(function (g) {
    return {
      group: g,
      n: g.querySelector("[data-cat-n]"),
      items: Array.prototype.slice.call(g.querySelectorAll("[data-cat-item]")).map(function (li) {
        return { li: li, key: fold(li.getAttribute("data-name")) };
      })
    };
  });

  function apply() {
    var query = fold(input.value);
    var shown = 0;
    rows.forEach(function (r) {
      var count = 0;
      r.items.forEach(function (it) {
        var ok = !query || it.key.indexOf(query) !== -1;
        it.li.hidden = !ok;
        if (ok) count += 1;
      });
      r.group.hidden = count === 0;
      if (r.n) r.n.textContent = label(count, "indicatore", "indicatori");
      if (query && count > 0) r.group.open = true;
      shown += count;
    });
    live.textContent = shown === 0 ? "Nessun indicatore trovato" : label(shown, "indicatore", "indicatori");
    if (empty) empty.hidden = shown !== 0;
  }

  box.hidden = false;
  box.addEventListener("submit", function (event) { event.preventDefault(); });
  input.addEventListener("input", apply);
})();
