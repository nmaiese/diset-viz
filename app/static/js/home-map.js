// Hover/click behaviour for the homepage's indicator choropleth (/).
// Region fills are set inline per-page (see home.html); this only wires up
// the shared .rmap-region hover/click behaviour and updates the side readout
// panel, mirroring quality-map.js but writing into a panel instead of a
// floating tooltip, to match the two-up map/readout layout of the hero.
(function () {
  var dataEl = document.getElementById("home-map-data");
  var map = document.querySelector(".home-map-body .regions-map");
  var readout = document.getElementById("home-map-readout");
  if (!dataEl || !map || !readout) return;

  var byKey = {};
  try {
    byKey = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  var hintHtml = readout.innerHTML;

  function render(info) {
    readout.innerHTML =
      "<span class=\"home-map-readout__name\">" + info.name + "</span>" +
      "<span class=\"home-map-readout__value\">" + info.value + (info.unit ? " " + info.unit : "") + "</span>" +
      "<span class=\"home-map-readout__rank\">" + info.rank + "ª su " + info.total + " regioni</span>" +
      "<span class=\"home-map-readout__go\">Clicca per il profilo →</span>";
  }

  map.querySelectorAll(".rmap-region").forEach(function (el) {
    var key = el.getAttribute("data-key");
    var info = byKey[key];
    if (!info) return;
    el.classList.add("is-clickable");
    el.setAttribute("tabindex", "0");
    el.setAttribute("role", "link");
    el.setAttribute("aria-label", info.name + ": " + info.value + (info.unit ? " " + info.unit : ""));
    el.addEventListener("mouseenter", function () { render(info); });
    el.addEventListener("focus", function () { render(info); });
    el.addEventListener("mouseleave", function () { readout.innerHTML = hintHtml; });
    el.addEventListener("blur", function () { readout.innerHTML = hintHtml; });
    el.addEventListener("click", function () { window.location.href = "/regione/" + key; });
    el.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        window.location.href = "/regione/" + key;
      }
    });
  });
})();
