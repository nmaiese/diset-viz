// Hover/click/touch behaviour for the server-rendered choropleth (/ and
// /divari-regionali). Region fills are set inline per-page (see _map_panel.html);
// this wires the shared .rmap-region behaviour and writes into the side readout
// panel instead of a floating tooltip, to match the two-up map/readout layout.
//
// The readout has ONE current state, resolved from two independent inputs:
// mouse hover and keyboard focus. Restoring the hint on every mouseleave/blur
// (the previous behaviour) wiped a still-focused region when the mouse left a
// different one, and vice versa. Here we track `hovered` and `focused`
// separately and repaint from whichever is active, focus winning.
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
  var hovered = null; // info under the mouse
  var focused = null; // info with keyboard focus
  var touchedKey = null; // region previewed by the last tap (two-tap navigation)

  function paint() {
    var info = focused || hovered;
    if (!info) {
      readout.innerHTML = hintHtml;
      return;
    }
    readout.innerHTML =
      "<span class=\"home-map-readout__name\">" + info.name + "</span>" +
      "<span class=\"home-map-readout__value\">" + info.value + (info.unit ? " " + info.unit : "") + "</span>" +
      "<span class=\"home-map-readout__rank\">" + info.rank + "ª su " + info.total + " regioni</span>" +
      "<span class=\"home-map-readout__go\">Clicca per il profilo →</span>";
  }

  function go(key) {
    window.location.href = "/regione/" + key;
  }

  map.querySelectorAll(".rmap-region").forEach(function (el) {
    var key = el.getAttribute("data-key");
    var info = byKey[key];
    if (!info) return;
    el.classList.add("is-clickable");
    el.setAttribute("tabindex", "0");
    el.setAttribute("role", "link");
    el.setAttribute("aria-label", info.name + ": " + info.value + (info.unit ? " " + info.unit : ""));

    el.addEventListener("mouseenter", function () { hovered = info; paint(); });
    el.addEventListener("mouseleave", function () { hovered = null; paint(); });
    el.addEventListener("focus", function () { focused = info; paint(); });
    el.addEventListener("blur", function () { focused = null; paint(); });
    el.addEventListener("click", function () { go(key); });
    el.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        go(key);
      }
    });

    // Touch: a first tap previews the value in the readout (no navigation),
    // a second tap on the same region opens its profile. Without this a tap
    // navigated instantly and the readout never showed on mobile. Navigation
    // is driven from touchend, with preventDefault to suppress the synthetic
    // click so it does not fire twice.
    el.addEventListener("touchend", function (evt) {
      evt.preventDefault();
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

  // A tap outside any region clears the touch preview and the readout.
  map.addEventListener("touchend", function (evt) {
    if (evt.target.closest && evt.target.closest(".rmap-region")) return;
    touchedKey = null;
    hovered = null;
    paint();
  }, { passive: true });
})();
