// Hover tooltip for the score choropleth on /qualita-della-vita/classifica/regioni.
// Pure vanilla JS; region fills are set inline per-page (score color scale),
// this only wires up the shared .rmap-tooltip hover/click behaviour.
(function () {
  var dataEl = document.getElementById("quality-map-data");
  var map = document.querySelector(".quality-map-wrap .regions-map");
  var tooltip = document.querySelector(".quality-map-wrap .rmap-tooltip");
  if (!dataEl || !map || !tooltip) return;

  var byKey = {};
  try {
    byKey = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  function moveTooltip(evt) {
    var wrap = map.parentElement.getBoundingClientRect();
    var x = evt.clientX - wrap.left + 14;
    var y = evt.clientY - wrap.top + 14;
    x = Math.min(x, wrap.width - tooltip.offsetWidth - 8);
    tooltip.style.left = Math.max(8, x) + "px";
    tooltip.style.top = y + "px";
  }

  map.querySelectorAll(".rmap-region").forEach(function (el) {
    var key = el.getAttribute("data-key");
    var info = byKey[key];
    if (!info) return;
    el.classList.add("is-clickable");
    el.setAttribute("tabindex", "0");
    el.setAttribute("role", "link");
    el.setAttribute("aria-label", info.name + ": " + info.score);
    el.addEventListener("mouseenter", function (evt) {
      tooltip.innerHTML = "<strong>" + info.name + "</strong><span>Punteggio " + info.score + "/100, " + info.rank + "ª posizione</span>";
      tooltip.hidden = false;
      moveTooltip(evt);
    });
    el.addEventListener("mousemove", moveTooltip);
    el.addEventListener("mouseleave", function () { tooltip.hidden = true; });
    el.addEventListener("click", function () { window.location.href = "/regione/" + key; });
    el.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        window.location.href = "/regione/" + key;
      }
    });
  });
})();
