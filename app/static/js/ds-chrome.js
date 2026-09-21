// Comportamenti del chrome condiviso (design system 2026).
//
// Tutto qui dentro e progressive enhancement: il markup in _ds_header.html
// funziona senza JavaScript. I menu a tendina sono <details>, la ricerca e un
// form verso /ricerca, il drawer e visibile via :target-less fallback (il
// bottone e nascosto ai soli utenti senza JS perche il menu completo e gia nel
// footer). Questo file aggiunge: tema scuro persistente, chiusura con Escape,
// focus trap del drawer e suggerimenti di ricerca.
(function () {
  "use strict";

  var THEME_KEY = "divario-theme";

  // --- tema chiaro / scuro -------------------------------------------------
  // Il valore e gia applicato inline in <head> per evitare il lampo di pagina
  // chiara; qui aggiorniamo solo lo stato dei bottoni e gestiamo il click.
  var themeButtons = Array.prototype.slice.call(
    document.querySelectorAll("[data-ds-theme-toggle]")
  );

  function readTheme() {
    try {
      return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
    } catch (e) {
      return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }
  }

  function paintThemeButtons(theme) {
    var dark = theme === "dark";
    var label = dark ? "Passa al tema chiaro" : "Passa al tema scuro";
    themeButtons.forEach(function (button) {
      button.setAttribute("aria-pressed", dark ? "true" : "false");
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
      var moon = button.querySelector(".ds-icon-moon");
      var sun = button.querySelector(".ds-icon-sun");
      if (moon) moon.hidden = dark;
      if (sun) sun.hidden = !dark;
    });
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (e) {}
    paintThemeButtons(theme);
  }

  paintThemeButtons(readTheme());
  themeButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      applyTheme(readTheme() === "dark" ? "light" : "dark");
    });
  });

  // --- menu a tendina ------------------------------------------------------
  // <details name="..."> gia si chiudono a vicenda dove il browser lo supporta.
  // Qui aggiungiamo la chiusura con Escape e il click fuori, e il mutuo
  // esclusivo per i browser che ignorano l'attributo name.
  var menus = Array.prototype.slice.call(document.querySelectorAll(".hdr__nav details.navlink"));

  function closeMenus(except) {
    menus.forEach(function (menu) {
      if (menu !== except) menu.open = false;
    });
  }

  menus.forEach(function (menu) {
    menu.addEventListener("toggle", function () {
      if (menu.open) closeMenus(menu);
    });
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest || !event.target.closest(".hdr__nav")) closeMenus(null);
  });

  // --- drawer mobile -------------------------------------------------------
  var drawer = document.getElementById("ds-drawer");
  var drawerOpener = document.querySelector("[data-ds-drawer-open]");
  var lastFocused = null;

  function focusables() {
    if (!drawer) return [];
    return Array.prototype.slice
      .call(drawer.querySelectorAll('a[href], button:not([disabled])'))
      .filter(function (el) { return el.offsetParent !== null; });
  }

  function openDrawer() {
    if (!drawer) return;
    lastFocused = document.activeElement;
    drawer.hidden = false;
    document.body.style.overflow = "hidden";
    if (drawerOpener) drawerOpener.setAttribute("aria-expanded", "true");
    var close = drawer.querySelector("[data-ds-drawer-close]");
    if (close) close.focus();
  }

  function closeDrawer() {
    if (!drawer || drawer.hidden) return;
    drawer.hidden = true;
    document.body.style.overflow = "";
    if (drawerOpener) drawerOpener.setAttribute("aria-expanded", "false");
    if (lastFocused && lastFocused.focus) lastFocused.focus();
    lastFocused = null;
  }

  if (drawerOpener) drawerOpener.addEventListener("click", openDrawer);
  if (drawer) {
    drawer.addEventListener("click", function (event) {
      // il click sulla scrim (il div esterno) chiude, quello sul pannello no
      if (event.target === drawer || event.target.closest("[data-ds-drawer-close]")) {
        closeDrawer();
      }
    });
    drawer.addEventListener("keydown", function (event) {
      if (event.key !== "Tab") return;
      var items = focusables();
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  // --- ricerca con suggerimenti -------------------------------------------
  // Il form resta un normale GET verso /ricerca: Invio funziona sempre, anche
  // mentre i suggerimenti stanno caricando o se la fetch fallisce.
  var searchForm = document.querySelector("[data-ds-search]");
  if (searchForm) {
    var input = searchForm.querySelector("input[name=q]");
    var panel = searchForm.querySelector(".searchpanel");
    var timer = null;
    var lastQuery = "";

    function hidePanel() {
      panel.hidden = true;
      panel.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
    }

    function renderResults(results, query) {
      if (!results.length) {
        panel.innerHTML =
          '<p class="sg__empty">Nessun indicatore trovato. Premi Invio per cercare in tutto il sito.</p>';
      } else {
        var html = '<div class="sg"><div class="sg__label">Indicatori</div>';
        results.slice(0, 6).forEach(function (item) {
          html +=
            '<a class="sg__item" role="option" href="' + item.path + '">' +
            "<span>" + escapeHtml(item.name) + "</span>" +
            '<span class="sg__kind">' + escapeHtml(item.theme || "Indicatore") + "</span>" +
            "</a>";
        });
        html += "</div>";
        html +=
          '<div class="sg"><a class="sg__item" role="option" href="/ricerca?q=' +
          encodeURIComponent(query) +
          '"><span>Cerca "' + escapeHtml(query) + '" in tutto il sito</span>' +
          '<span class="sg__kind">Tutti i risultati</span></a></div>';
        panel.innerHTML = html;
      }
      panel.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, function (character) {
        return {
          "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[character];
      });
    }

    function suggest() {
      var query = input.value.trim();
      if (query.length < 2) {
        hidePanel();
        return;
      }
      if (query === lastQuery) return;
      lastQuery = query;
      fetch("/api/search?q=" + encodeURIComponent(query), {
        headers: { Accept: "application/json" }
      })
        .then(function (response) { return response.ok ? response.json() : null; })
        .then(function (payload) {
          // una risposta in ritardo non deve sovrascrivere una query piu recente
          if (!payload || input.value.trim() !== query) return;
          renderResults(payload.results || [], query);
        })
        .catch(function () { hidePanel(); });
    }

    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(suggest, 180);
    });
    input.addEventListener("focus", function () {
      if (input.value.trim().length >= 2) suggest();
    });
    // il ritardo lascia partire il click su un suggerimento prima della chiusura
    input.addEventListener("blur", function () { window.setTimeout(hidePanel, 160); });
  }

  // --- Escape globale ------------------------------------------------------
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    closeMenus(null);
    if (drawer && !drawer.hidden) {
      event.preventDefault();
      closeDrawer();
    }
    var panel = document.querySelector("[data-ds-search] .searchpanel");
    if (panel && !panel.hidden) {
      panel.hidden = true;
      panel.innerHTML = "";
    }
  });
})();
