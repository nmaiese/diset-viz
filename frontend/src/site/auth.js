// Controllo login/account nel masthead, su OGNI pagina server-rendered.
//
// Vive in un placeholder già reso dal server (#site-auth) a dimensioni fisse:
// il modulo è async e getUser() pure, quindi senza il placeholder il masthead
// salterebbe a ogni caricamento. Riempiamo il placeholder, non lo creiamo.
//
// Ottimizzazione peso: se in localStorage NON c'è una sessione Supabase, l'utente
// è anonimo e mostriamo "Accedi" SENZA scaricare @supabase/supabase-js (208kB).
// La libreria si carica solo (a) se c'è già una sessione da risolvere, oppure
// (b) al clic su "Accedi". Così le pagine pubbliche anonime restano leggere.

import {
  getAccessToken,
  getUser,
  isAuthConfigured,
  onAuthChange,
  signInWithGoogle,
  signOut,
  syncProfile,
  mergeLocalStatsOnce,
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

function isOAuthReturn() {
  // Ritorno dal login Google: Supabase rimanda con ?code=... (PKCE) o
  // #access_token=... (implicito). In quel caso DOBBIAMO inizializzare il client
  // (anche se non c'è ancora sessione salvata) per consumare il codice e
  // persistere la sessione, altrimenti il login "non attacca".
  try {
    const s = window.location.search || "";
    const h = window.location.hash || "";
    return /[?&](code|error)=/.test(s) || /access_token=|error=/.test(h);
  } catch {
    return false;
  }
}

function cleanOAuthUrl() {
  // Toglie i parametri OAuth dall'URL così un refresh non li ri-processa.
  try {
    const url = new URL(window.location.href);
    ["code", "state", "error", "error_description"].forEach((p) => url.searchParams.delete(p));
    url.hash = "";
    window.history.replaceState({}, document.title, url.pathname + url.search);
  } catch {
    /* best effort */
  }
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
    '<a class="site-auth__item" href="/account">Il mio account</a>' +
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

async function render() {
  const user = await getUser();
  if (user) {
    accountControl(user);
    syncProfile(); // upsert profilo, best-effort
    mergeLocalStatsOnce(user.id); // fonde i progressi locali una volta (silenzioso qui)
  } else {
    loginButton();
  }
}

if (root && isAuthConfigured()) {
  if (hasStoredSession() || isOAuthReturn()) {
    // Sessione da risolvere, o ritorno dal login da consumare: carica supabase,
    // processa l'eventuale codice OAuth (persiste la sessione) e mostra l'account.
    if (isOAuthReturn()) {
      // getUser() forza l'inizializzazione del client, che con detectSessionInUrl
      // scambia il codice e salva la sessione; poi puliamo l'URL.
      render().then(cleanOAuthUrl);
    } else {
      render();
    }
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

// --- Pagina account (Fase 5.3) ---
async function wireAccountPage() {
  const el = document.getElementById("account-root");
  if (!el || !isAuthConfigured()) return;
  if (!hasStoredSession()) {
    el.innerHTML =
      '<p>Accedi per gestire il tuo account.</p>' +
      '<button type="button" class="account-btn" id="account-login">Accedi con Google</button>';
    const b = document.getElementById("account-login");
    if (b) b.onclick = () => signInWithGoogle();
    return;
  }
  const user = await getUser();
  if (!user) {
    el.innerHTML = '<p>Sessione scaduta. <button type="button" class="site-auth__login" id="account-login">Accedi</button></p>';
    const b = document.getElementById("account-login");
    if (b) b.onclick = () => signInWithGoogle();
    return;
  }
  const [meRes, favRes, playerRes] = await Promise.all([
    authFetch("/api/auth/me"), authFetch("/api/favorites"), authFetch("/api/player/me"),
  ]);
  const me = meRes && meRes.ok ? await meRes.json() : {};
  const fav = favRes && favRes.ok ? await favRes.json() : { favorites: [] };
  const player = playerRes && playerRes.ok ? await playerRes.json() : { achievements: [] };
  const nickname = (me.profile && me.profile.nickname) || "";
  const favCount = (fav.favorites || []).length;
  const achList = player.achievements || [];
  const achUnlocked = achList.filter((a) => a.unlocked).length;

  el.innerHTML =
    '<section class="account-block"><h2>Profilo</h2>' +
    '<p class="account-email">' + escapeHtml(user.email || "") + "</p>" +
    '<label for="account-nick">Nickname pubblico</label>' +
    '<div class="account-nick-row">' +
    '<input id="account-nick" type="text" maxlength="16" value="' + escapeHtml(nickname) + '" placeholder="Il tuo nome in classifica">' +
    '<button type="button" class="account-btn" id="account-nick-save">Salva</button></div>' +
    '<p class="account-nick-msg" id="account-nick-msg"></p></section>' +
    '<section class="account-block"><h2>Preferiti</h2>' +
    "<p>Hai <strong>" + favCount + "</strong> " + (favCount === 1 ? "indicatore preferito" : "indicatori preferiti") + ".</p>" +
    '<a class="account-btn account-btn--ghost" href="/atlante?fav=1">Vedi nell\'atlante</a></section>' +
    '<section class="account-block"><h2>Traguardi</h2>' +
    "<p><strong>" + achUnlocked + "/" + achList.length + "</strong> sbloccati.</p>" +
    '<a class="account-btn account-btn--ghost" href="/quiz">Vai ai giochi</a></section>' +
    '<section class="account-block"><h2>I tuoi dati</h2>' +
    '<div class="account-data-cta">' +
    '<button type="button" class="account-btn account-btn--ghost" id="account-export">Esporta i miei dati</button>' +
    '<button type="button" class="account-danger" id="account-delete">Elimina account</button></div>' +
    '<p class="account-note">La cancellazione elimina definitivamente profilo, preferiti, statistiche, traguardi e punteggi, e il tuo accesso Google al sito.</p></section>';

  document.getElementById("account-nick-save").onclick = async () => {
    const msg = document.getElementById("account-nick-msg");
    const val = document.getElementById("account-nick").value;
    const res = await authFetch("/api/player/nickname", { method: "PATCH", body: JSON.stringify({ nickname: val }) });
    msg.textContent = res && res.ok ? "Nickname salvato." : "Nickname non valido o non ammesso.";
  };
  document.getElementById("account-export").onclick = async () => {
    const res = await authFetch("/api/account/export");
    if (!res || !res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "divario-italia-dati-account.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  document.getElementById("account-delete").onclick = async () => {
    if (!window.confirm("Eliminare l'account e tutti i dati? L'operazione non è reversibile.")) return;
    const res = await authFetch("/api/account", { method: "DELETE" });
    if (res && res.ok) {
      await signOut();
      window.location.href = "/";
    }
  };
}

wireAccountPage();
