// Controllo login/account nel masthead, su OGNI pagina server-rendered.
//
// Vive in un placeholder gia' reso dal server (#site-auth) a dimensioni fisse:
// il modulo e' async e getUser() pure, quindi senza il placeholder il masthead
// salterebbe a ogni caricamento. Riempiamo il placeholder, non lo creiamo.
//
// Ottimizzazione peso: se in localStorage NON c'e' una sessione Supabase, l'utente
// e' anonimo e mostriamo "Accedi" SENZA scaricare @supabase/supabase-js (208kB).
// La libreria si carica solo (a) se c'e' gia' una sessione da risolvere, oppure
// (b) al clic su "Accedi". Cosi' le pagine pubbliche anonime restano leggere.

import {
  getAccessToken,
  getUser,
  isAuthConfigured,
  onAuthChange,
  signInWithGoogle,
  signOut,
} from "../shared/supabase.js";

const root = document.getElementById("site-auth");

function hasStoredSession() {
  // Supabase salva la sessione sotto una chiave `sb-<ref>-auth-token`. La
  // cerchiamo senza caricare la libreria.
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      if (k && /^sb-.*-auth-token$/.test(k)) return true;
    }
  } catch {
    /* localStorage negato: trattiamo come anonimo */
  }
  return false;
}

function loginButton() {
  root.innerHTML =
    '<button type="button" class="site-auth__login" id="site-auth-login">Accedi</button>';
  document.getElementById("site-auth-login").onclick = () => signInWithGoogle();
}

function accountControl(user) {
  const label = user.email || "Account";
  root.innerHTML =
    '<div class="site-auth__menu">' +
    '<button type="button" class="site-auth__btn" id="site-auth-toggle" aria-haspopup="true" aria-expanded="false">' +
    '<span class="site-auth__avatar" aria-hidden="true">' + escapeHtml(initial(label)) + "</span>" +
    '<span class="site-auth__label">' + escapeHtml(label) + "</span>" +
    "</button>" +
    '<div class="site-auth__dropdown" id="site-auth-dropdown" hidden>' +
    '<a class="site-auth__item" href="/atlante?fav=1">I miei preferiti</a>' +
    '<button type="button" class="site-auth__item" id="site-auth-logout">Esci</button>' +
    "</div>" +
    "</div>";
  const toggle = document.getElementById("site-auth-toggle");
  const dropdown = document.getElementById("site-auth-dropdown");
  toggle.onclick = () => {
    const open = dropdown.hasAttribute("hidden");
    if (open) dropdown.removeAttribute("hidden");
    else dropdown.setAttribute("hidden", "");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  };
  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) {
      dropdown.setAttribute("hidden", "");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
  document.getElementById("site-auth-logout").onclick = () => signOut();
}

function initial(s) {
  return (s || "?").trim().charAt(0).toUpperCase() || "?";
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// Segnala al server il login (upsert profilo + last_seen), best-effort.
async function pingProfile() {
  try {
    const token = await getAccessToken();
    if (!token) return;
    // Seed del nickname dal locale del gioco, solo alla creazione del profilo.
    let nick = "";
    try {
      nick = window.localStorage.getItem("di-nickname") || "";
    } catch {
      /* localStorage negato */
    }
    const q = nick ? `?nick=${encodeURIComponent(nick)}` : "";
    await fetch(`/api/auth/me${q}`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    /* il profilo non deve mai bloccare la UI */
  }
}

async function render() {
  const user = await getUser();
  if (user) {
    accountControl(user);
    pingProfile();
  } else {
    loginButton();
  }
}

if (root && isAuthConfigured()) {
  if (hasStoredSession()) {
    // C'e' una sessione da risolvere: carica supabase e mostra l'account.
    render();
    onAuthChange(() => render());
  } else {
    // Anonimo: bottone Accedi, e NIENTE supabase caricato (onAuthChange
    // forzerebbe l'import). La libreria arriva solo al clic su "Accedi".
    loginButton();
  }
}

// --- Stella preferiti sulle pagine indicatore (Fase 5.1) ---
// Solo con login. Da anonimo un clic invita ad accedere (e solo allora carica
// supabase). Da loggato mostra lo stato e fa toggle via /api/favorites.
async function authFetch(url, options = {}) {
  const token = await getAccessToken();
  if (!token) return null;
  return fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
  });
}

function wireFavoriteStar() {
  const star = document.getElementById("fav-star");
  if (!star || !isAuthConfigured()) return;
  const indicatorId = star.getAttribute("data-indicator-id");
  if (!indicatorId) return;
  star.hidden = false;

  function paint(on) {
    star.setAttribute("aria-pressed", on ? "true" : "false");
    star.classList.toggle("is-on", !!on);
    star.textContent = on ? "★" : "☆"; // ★ / ☆
    star.setAttribute("aria-label", on ? "Togli dai preferiti" : "Aggiungi ai preferiti");
  }

  let known = false; // stato preferito conosciuto (solo da loggato)

  async function refresh() {
    if (!hasStoredSession()) return; // anonimo: stella vuota, nessun caricamento
    try {
      const res = await authFetch("/api/favorites");
      if (!res || !res.ok) return;
      const data = await res.json();
      known = (data.favorites || []).includes(indicatorId);
      paint(known);
    } catch {
      /* niente stato: resta vuota */
    }
  }

  star.addEventListener("click", async () => {
    if (!hasStoredSession()) {
      signInWithGoogle(); // carica supabase e porta al login; al ritorno si aggiorna
      return;
    }
    const next = !known;
    paint(next); // ottimistico
    try {
      const res = next
        ? await authFetch("/api/favorites", { method: "POST", body: JSON.stringify({ indicator_id: indicatorId }) })
        : await authFetch(`/api/favorites/${encodeURIComponent(indicatorId)}`, { method: "DELETE" });
      if (!res || !res.ok) throw new Error("fav failed");
      known = next;
    } catch {
      paint(!next); // rollback
    }
  });

  refresh();
}

wireFavoriteStar();
