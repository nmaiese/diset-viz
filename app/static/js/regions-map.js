// Hover tooltips + click navigation for the clickable region map on /regioni.
// Pure vanilla JS; the SVG paths are pre-projected and carry data-key, the
// per-region preview data is embedded as JSON in #regions-overview.
(function () {
  var dataEl = document.getElementById("regions-overview");
  var map = document.querySelector(".regions-map");
  var tooltip = document.querySelector(".rmap-tooltip");
  if (!dataEl || !map || !tooltip) return;

  var overview = {};
  try {
    overview = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  function themeLine(label, themes) {
    if (!themes || !themes.length) return "";
    return '<span class="rmap-' + label + '">' + (label === "strong" ? "Forte" : "Debole") +
      ": " + themes.join(", ") + "</span>";
  }

  function showTooltip(key, evt) {
    var info = overview[key];
    if (!info) return;
    tooltip.innerHTML = "<strong>" + info.region + "</strong>" +
      themeLine("strong", info.strong) + themeLine("weak", info.weak);
    tooltip.hidden = false;
    moveTooltip(evt);
  }

  function moveTooltip(evt) {
    var wrap = map.parentElement.getBoundingClientRect();
    var x = evt.clientX - wrap.left + 14;
    var y = evt.clientY - wrap.top + 14;
    // Keep the tooltip inside the map container.
    x = Math.min(x, wrap.width - tooltip.offsetWidth - 8);
    tooltip.style.left = Math.max(8, x) + "px";
    tooltip.style.top = y + "px";
  }

  var regions = map.querySelectorAll(".rmap-region");
  regions.forEach(function (el) {
    var key = el.getAttribute("data-key");
    var info = overview[key];
    if (info) {
      el.classList.add("is-clickable");
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "link");
      el.setAttribute("aria-label", info.region);
    }
    el.addEventListener("mouseenter", function (evt) { showTooltip(key, evt); });
    el.addEventListener("mousemove", moveTooltip);
    el.addEventListener("mouseleave", function () { tooltip.hidden = true; });
    el.addEventListener("click", function () { if (info) window.location.href = info.path; });
    el.addEventListener("keydown", function (evt) {
      if ((evt.key === "Enter" || evt.key === " ") && info) {
        evt.preventDefault();
        window.location.href = info.path;
      }
    });
  });
})();
