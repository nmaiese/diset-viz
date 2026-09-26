/* L'isola di /temi: il campo "Cerca un tema" filtra le schede gia' in pagina.
   Senza JavaScript il campo resta nascosto e i temi ci sono tutti. Confronta
   il testo cercato col nome del tema e con gli indicatori che la scheda nomina. */
(function () {
  "use strict";
  var form = document.querySelector("[data-temi-filter]");
  if (!form) return;
  var input = form.querySelector("input[type='search']");
  var live = form.querySelector("[data-temi-live]");
  var empty = document.querySelector("[data-temi-empty]");
  var areas = Array.prototype.slice.call(document.querySelectorAll("[data-temi-area]"));
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-temi-theme]"));
  var total = cards.length;

  function norm(text) {
    return (text || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  }
  var haystack = cards.map(function (card) {
    var examples = Array.prototype.map.call(card.querySelectorAll(".temi-card__examples a"), function (a) {
      return a.textContent;
    }).join(" ");
    return norm(card.getAttribute("data-temi-theme") + " " + examples);
  });

  function apply() {
    var q = norm(input.value);
    var shown = 0;
    cards.forEach(function (card, i) {
      var match = !q || haystack[i].indexOf(q) !== -1;
      card.hidden = !match;
      if (match) shown += 1;
    });
    areas.forEach(function (area) {
      area.hidden = !area.querySelector("[data-temi-theme]:not([hidden])");
    });
    if (empty) empty.hidden = shown > 0;
    if (live) live.textContent = shown === total ? total + " temi" : shown + (shown === 1 ? " tema su " : " temi su ") + total;
  }

  form.hidden = false;
  input.addEventListener("input", apply);
})();
