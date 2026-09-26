/* /divari-regionali: l'isola della mappa.

   La mappa della pagina e' la macro `ui.map` della 1.0, e v1.js ci mette il
   valore al passaggio del mouse. Qui c'e' solo il clic: una regione porta al
   suo profilo, come i nomi della classifica accanto, che sono gia' link e
   restano la strada della tastiera e dei lettori di schermo. Senza
   JavaScript la classifica basta. Il cambio d'indicatore e' il GET del form,
   senza isola. */
(function () {
  "use strict";
  var box = document.querySelector("[data-dr-map] [data-map]");
  if (!box) return;
  box.classList.add("is-linked");
  box.addEventListener("click", function (ev) {
    var shape = ev.target.closest("[data-key]");
    if (!shape || !shape.dataset.key) return;
    window.location.href = "/regione/" + encodeURIComponent(shape.dataset.key);
  });
})();
