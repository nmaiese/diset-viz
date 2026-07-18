// Positions the accent underline beneath the active masthead link, mirroring
// the sliding nav-underline in the React atlas (frontend/src/main.jsx). Pure
// progressive enhancement: the server-rendered .is-active class already marks
// the current section without this script.
(function () {
  var nav = document.getElementById("masthead-nav");
  if (!nav) return;
  var underline = nav.querySelector(".nav-underline");
  var link = nav.querySelector("a.is-active");
  if (!underline || !link) return;

  function measure() {
    var navRect = nav.getBoundingClientRect();
    var linkRect = link.getBoundingClientRect();
    underline.style.width = (linkRect.width - 4) + "px";
    underline.style.transform = "translateX(" + (linkRect.left - navRect.left + 2) + "px)";
    underline.classList.add("is-visible");
  }

  measure();
  window.addEventListener("resize", measure);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(measure).catch(function () {});
  }
})();
