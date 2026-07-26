// The mobile navigation drawer, opened by the hamburger in the masthead.
//
// It replaced the bottom tab bar, which could only ever hold five destinations.
// The drawer is the only nav that needs JavaScript, so the site footer keeps the
// same links: with the script blocked the hamburger is inert but every section
// stays reachable from the bottom of the page.
//
// aria-modal="true" is a promise to the assistive technology that nothing behind
// the dialog is reachable, so the focus trap below is part of the contract, not
// a nicety.
(function () {
  var toggle = document.getElementById("menu-toggle");
  var menu = document.getElementById("mobile-menu");
  if (!toggle || !menu) return;
  var close = document.getElementById("menu-close");
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled])';

  function isOpen() { return !menu.hidden; }

  function open() {
    if (isOpen()) return;
    menu.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    document.body.classList.add("menu-open");
    // The close button, not the search field: focusing an input here pops the
    // on-screen keyboard over the menu the reader just asked to see.
    (close || menu).focus();
  }

  function shut(returnFocus) {
    if (!isOpen()) return;
    menu.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-open");
    if (returnFocus) toggle.focus();
  }

  if (close && !close.hasAttribute("tabindex")) close.setAttribute("tabindex", "0");

  toggle.addEventListener("click", function () {
    if (isOpen()) shut(true); else open();
  });
  if (close) close.addEventListener("click", function () { shut(true); });

  document.addEventListener("keydown", function (evt) {
    if (!isOpen()) return;
    if (evt.key === "Escape") {
      shut(true);
      return;
    }
    if (evt.key !== "Tab") return;
    var items = Array.prototype.filter.call(
      menu.querySelectorAll(FOCUSABLE),
      function (node) { return node.offsetParent !== null; }
    );
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (evt.shiftKey && document.activeElement === first) {
      evt.preventDefault();
      last.focus();
    } else if (!evt.shiftKey && document.activeElement === last) {
      evt.preventDefault();
      first.focus();
    }
  });

  // Above 760px the stylesheet hides the drawer and lifts the scroll lock, so a
  // menu left open across a rotation would keep claiming aria-expanded="true"
  // over something nobody can see.
  window.addEventListener("resize", function () {
    if (isOpen() && window.innerWidth > 760) shut(false);
  });
})();
