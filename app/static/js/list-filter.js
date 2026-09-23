/*
 * Filtra un elenco reso dal server mentre si scrive un nome.
 *
 * Senza JavaScript l'elenco e' intero e il campo resta nascosto: il filtro e'
 * una scorciatoia, non l'unico modo di trovare una voce. Il confronto ignora
 * maiuscole e accenti, cosi' "forli" trova "Forlì-Cesena".
 *
 *   <input data-list-filter="#elenco">
 *   <section data-filter-group> ... <li data-filter-name="Forlì-Cesena"> ...
 */
(function () {
  "use strict";

  function fold(value) {
    return (value || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  }

  document.querySelectorAll("[data-list-filter]").forEach(function (input) {
    var root = document.querySelector(input.getAttribute("data-list-filter"));
    if (!root) return;
    var empty = root.querySelector("[data-filter-empty]");
    var wrapper = input.closest("[hidden]");
    if (wrapper) wrapper.hidden = false;

    input.addEventListener("input", function () {
      var query = fold(input.value);
      var shown = 0;
      root.querySelectorAll("[data-filter-group]").forEach(function (group) {
        var visible = 0;
        group.querySelectorAll("[data-filter-name]").forEach(function (item) {
          var match = !query || fold(item.getAttribute("data-filter-name")).indexOf(query) !== -1;
          item.hidden = !match;
          if (match) visible += 1;
        });
        group.hidden = visible === 0;
        shown += visible;
      });
      if (empty) empty.hidden = shown !== 0;
    });
  });
})();
