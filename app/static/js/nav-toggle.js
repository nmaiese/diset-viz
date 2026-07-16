// Menu hamburger del masthead condiviso da tutte le pagine server-rendered.
// Pure vanilla JS, stesso comportamento del toggle React della SPA
// (frontend/src/main.jsx, componente SiteHeader): apri/chiudi al click,
// chiudi al click fuori e con Escape.
(function () {
  var toggle = document.querySelector(".masthead__toggle");
  var nav = document.getElementById("masthead-nav");
  var header = document.querySelector(".masthead");
  if (!toggle || !nav || !header) return;

  function isOpen() {
    return nav.classList.contains("is-open");
  }

  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }

  toggle.addEventListener("click", function () {
    setOpen(!isOpen());
  });

  document.addEventListener("pointerdown", function (evt) {
    if (isOpen() && !header.contains(evt.target)) setOpen(false);
  });

  document.addEventListener("keydown", function (evt) {
    if (evt.key === "Escape" && isOpen()) setOpen(false);
  });

  nav.addEventListener("click", function (evt) {
    if (evt.target.tagName === "A") setOpen(false);
  });
})();
