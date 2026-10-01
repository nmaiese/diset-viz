import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { X } from "lucide-react";
import {
  getAccessToken,
  getUser,
  isAuthConfigured,
  onAuthChange,
  signInWithGoogle,
  signOut,
} from "../shared/supabase.js";
import {
  CHIAVE_TERRITORIO_MIO,
  DURATA_CONTEGGIO_MS,
  MASSIMI_SFIDA,
  countUpValue,
  fattoPresentabile,
  leggiSfida,
  linkConSfida,
  parametriEvento,
  parseTerritorioMio,
  testoConfrontoSfida,
  testoSfida,
  titoloContabile,
  tonoFinale,
  trovaTerritorioMio,
  fraseTerritorioMio,
} from "./puri.js";

// Le funzioni pure stanno in puri.js (le prova `node --test`): i giochi le prendono da qui.
export {
  MASSIMI_SFIDA,
  countUpValue,
  fattoPresentabile,
  fraseTerritorioMio,
  leggiSfida,
  linkConSfida,
  parseTerritorioMio,
  testoConfrontoSfida,
  testoSfida,
  trovaTerritorioMio,
};

const STORAGE_NICKNAME_KEY = "di-nickname";
const STORAGE_PENDING_KEY = "di-invio-pendente";
// Il token di sessione vale 12 ore (app/quiz_tokens.py): oltre non serve riprovare.
const PENDING_MAX_AGE_MS = 12 * 3600 * 1000;

// Header Authorization con il Bearer di Supabase, se c'è una sessione. Vuoto
// per gli anonimi: il gioco non richiede login, l'account è un extra.
async function authHeaders() {
  try {
    const token = await getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

// POST a un endpoint di gioco allegando il Bearer se c'è una sessione: così il
// server può attribuire statistiche e achievement all'account (anonimo = nessun
// header, comportamento invariato). Ritorna il JSON.
export async function postGame(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Request failed: ${url}`);
  return res.json();
}

// Controllo login/logout Google, minimale. Non compare affatto se Supabase non
// è configurato (isAuthConfigured() falso), così il gioco resta anonimo.
export function AuthControl() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthConfigured()) return undefined;
    let active = true;
    let unsub = () => {};
    getUser().then((u) => {
      if (active) {
        setUser(u);
        setReady(true);
      }
    });
    onAuthChange((u) => setUser(u)).then((fn) => {
      if (active) unsub = fn;
      else fn();
    });
    return () => {
      active = false;
      unsub();
    };
  }, []);

  if (!isAuthConfigured()) return null;

  const email = user?.email || "";
  return (
    <div className="game-auth" data-ready={ready ? "1" : "0"}>
      {user ? (
        <>
          <span className="game-auth__who">{email}</span>
          <button type="button" className="game-auth__btn" onClick={() => signOut()}>
            Esci
          </button>
        </>
      ) : (
        <button type="button" className="game-auth__btn" onClick={() => signInWithGoogle()}>
          Accedi con Google
        </button>
      )}
    </div>
  );
}

export async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

export function formatValue(value, unit) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n.d.";
  const decimals = Math.abs(value) >= 1000 ? 0 : 1;
  const formatted = value.toLocaleString("it-IT", { maximumFractionDigits: decimals, minimumFractionDigits: 0 });
  const lower = (unit || "").toLowerCase();
  if (lower.includes("percentuale")) return `${formatted}%`;
  return `${formatted} ${unit || ""}`.trim();
}

export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}

// Ogni evento del gioco porta `game`: "regione", "provincia", "compare", "order" o "mappa"
// (docs/tracking_spec.md). Un evento senza `game` o con un valore che non e' uno dei cinque
// parte lo stesso, senza il parametro, e in sviluppo lo dice nella console: una misura
// incompleta vale piu' di una misura persa, ma va corretta.
const ATTENZIONE_GIA_DATA = new Set();

export function trackGameEvent(name, params = {}) {
  if (typeof window === "undefined") return;
  const { valido, params: parametri } = parametriEvento(params);
  if (!valido && !ATTENZIONE_GIA_DATA.has(name)) {
    ATTENZIONE_GIA_DATA.add(name);
    if (import.meta.env && import.meta.env.DEV) {
      console.warn(`trackGameEvent("${name}"): manca il parametro \`game\` (regione, provincia, compare, order, mappa).`);
    }
  }
  const eventParams = {
    page_type: "game",
    page_path: window.location.pathname,
    page_title: document.title,
    ...parametri,
  };
  // Un solo canale verso GA4: `gtag("event")`, che il Google Tag mette lui
  // stesso nel dataLayer. Il container GTM (versione 8) non ha trigger sui
  // nomi del quiz, quindi un `dataLayer.push` dell'oggetto si aggiungeva
  // soltanto come secondo evento duplicato.
  if (typeof window.gtag === "function") {
    try {
      window.gtag("event", name, {
        ...eventParams,
        send_to: "G-THTPZZ02QH",
      });
    } catch {
      // Le metriche non devono mai bloccare il gioco.
    }
  }
  try {
    fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        params: eventParams,
        path: window.location.pathname,
        title: document.title,
      }),
      keepalive: true,
      credentials: "omit",
    }).catch(() => {});
  } catch {
    // Le metriche non devono mai bloccare il gioco.
  }
}

// Toast di sblocco achievement in DOM puro: ogni pagina gioco monta un proprio
// root React su un div diverso, quindi un toast imperativo appeso al body è il
// modo più semplice per mostrarlo da qualunque gioco.
//
// L'icona è l'SVG del traguardo (`icon_url`, una maschera che prende il colore del testo),
// non l'emoji: l'emoji resta solo se il server non manda l'SVG. Il toast entra in 0,3 s,
// l'icona fa UN pop, e esce in 200 ms. Il movimento sta tutto nel CSS, dentro
// `prefers-reduced-motion: no-preference`: con `reduce` compare e sparisce senza muoversi.
// Dentro il toast c'è il link ai traguardi, e finché ci si passa sopra o ci si ha il focus il
// toast non sparisce. `game` (opzionale) è il gioco che ha sbloccato, per l'evento GA4.
const ICONA_TRAGUARDO = /^\/static\/img\/[\w./-]+\.svg$/;
const VITA_TOAST_MS = 4200;
const USCITA_TOAST_MS = 200;
const TRAGUARDI_HREF = "/quiz#traguardi";

export function notifyAchievements(list, game) {
  if (!Array.isArray(list) || list.length === 0) return;
  if (typeof document === "undefined") return;
  let stack = document.getElementById("achv-toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.id = "achv-toast-stack";
    stack.className = "achv-toast-stack";
    stack.setAttribute("aria-live", "polite");
    document.body.appendChild(stack);
  }
  list.forEach((achievement, index) => {
    const toast = document.createElement("div");
    toast.className = "achv-toast";
    toast.setAttribute("role", "status");
    const icon = document.createElement("span");
    icon.className = "achv-toast-icon";
    icon.setAttribute("aria-hidden", "true");
    const url = achievement.icon_url;
    if (typeof url === "string" && ICONA_TRAGUARDO.test(url) && !url.includes("..")) {
      icon.classList.add("ico");
      icon.style.setProperty("--ico", `url(${url})`);
    } else {
      icon.textContent = achievement.icon || "";
    }
    const text = document.createElement("div");
    text.className = "achv-toast-text";
    const kicker = document.createElement("strong");
    kicker.textContent = "Traguardo sbloccato";
    const title = document.createElement("span");
    title.textContent = achievement.title || "";
    const link = document.createElement("a");
    link.className = "achv-toast-link";
    link.href = TRAGUARDI_HREF;
    link.textContent = "Guarda i traguardi";
    text.appendChild(kicker);
    text.appendChild(title);
    text.appendChild(link);
    toast.appendChild(icon);
    toast.appendChild(text);
    stack.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("is-in"));

    let trattenuto = false;
    let scaduto = false;
    function chiudi() {
      toast.classList.remove("is-in");
      toast.classList.add("is-out");
      setTimeout(() => toast.remove(), prefersReducedMotion() ? 0 : USCITA_TOAST_MS);
    }
    function rilascia() {
      trattenuto = false;
      if (scaduto) setTimeout(() => { if (!trattenuto) chiudi(); }, 1500);
    }
    toast.addEventListener("pointerenter", () => { trattenuto = true; });
    toast.addEventListener("pointerleave", rilascia);
    toast.addEventListener("focusin", () => { trattenuto = true; });
    toast.addEventListener("focusout", rilascia);
    setTimeout(() => {
      if (trattenuto) scaduto = true;
      else chiudi();
    }, VITA_TOAST_MS + index * 400);
    trackGameEvent("achievement_unlocked", { achievement_id: achievement.id, ...(game ? { game } : {}) });
  });
}

export function SourceStrip({ year, sourceLabel, sourceUrl, game }) {
  return (
    <p className="quiz-source">
      <span className="quiz-source-year">Anno {year}</span>
      {sourceLabel && sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="quiz-source-link"
          onClick={() => trackGameEvent("quiz_source_click", { source: sourceLabel, game })}
        >
          Fonte: {sourceLabel}
        </a>
      )}
    </p>
  );
}

const FOCALIZZABILI = [
  "a[href]", "button:not([disabled])", "input:not([disabled]):not([type=\"hidden\"])",
  "select:not([disabled])", "textarea:not([disabled])", "[tabindex]:not([tabindex=\"-1\"])",
].join(",");

function focalizzabili(radice) {
  return Array.from(radice.querySelectorAll(FOCALIZZABILI)).filter((el) => el.offsetParent !== null || el === document.activeElement);
}

// Il dialogo modale. Tastiera e lettore di schermo: all'apertura il focus entra nel dialogo
// (sul contenitore, non su un campo: sul telefono un campo aprirebbe la tastiera), Tab e
// Maiusc+Tab restano dentro, Esc chiude, e alla chiusura il focus torna all'elemento che
// l'aveva aperto (se e' ancora nella pagina).
export function Modal({ title, onClose, children, labelledBy }) {
  const ref = useRef(null);
  const dialogo = useRef(null);
  const alChiudere = useRef(onClose);
  useEffect(() => {
    alChiudere.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const apriDa = document.activeElement;
    const dlg = dialogo.current;
    if (dlg) dlg.focus();
    function onKeyDown(e) {
      if (e.key === "Escape") {
        alChiudere.current();
        return;
      }
      if (e.key !== "Tab" || !dlg) return;
      const dentro = focalizzabili(dlg);
      const attivo = document.activeElement;
      if (dentro.length === 0) {
        e.preventDefault();
        dlg.focus();
        return;
      }
      const primo = dentro[0];
      const ultimo = dentro[dentro.length - 1];
      const fuori = !dlg.contains(attivo);
      if (e.shiftKey && (attivo === primo || attivo === dlg || fuori)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && (attivo === ultimo || fuori)) {
        e.preventDefault();
        primo.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (apriDa && apriDa !== document.body && apriDa.isConnected && typeof apriDa.focus === "function") apriDa.focus();
    };
  }, []);

  return (
    <div
      className="game-modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === ref.current) onClose();
      }}
      ref={ref}
    >
      <div className="game-modal" role="dialog" aria-modal="true" aria-labelledby={labelledBy} tabIndex={-1} ref={dialogo}>
        <div className="game-modal-head">
          <h3 id={labelledBy}>{title}</h3>
          <button type="button" className="game-modal-close" onClick={onClose} aria-label="Chiudi">
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        <div className="game-modal-body">{children}</div>
      </div>
    </div>
  );
}

// Il territorio scelto dal giocatore sul sito ("E' la mia", chiave `di:mio`): si legge e
// basta, con lo stesso formato che scrive `app/static/js/v1.js`. Validato: un valore
// guasto o con markup e' `null`.
export function territorioMio() {
  try {
    return parseTerritorioMio(window.localStorage.getItem(CHIAVE_TERRITORIO_MIO));
  } catch {
    return null;
  }
}

// Il territorio del giocatore, aggiornato se lo cambia in un'altra scheda (`storage`) o nella
// stessa (l'evento `di:mio` di v1.js).
export function useTerritorioMio() {
  const [mio, setMio] = useState(territorioMio);
  useEffect(() => {
    const aggiorna = () => setMio(territorioMio());
    document.addEventListener("di:mio", aggiorna);
    window.addEventListener("storage", aggiorna);
    aggiorna();
    return () => {
      document.removeEventListener("di:mio", aggiorna);
      window.removeEventListener("storage", aggiorna);
    };
  }, []);
  return mio;
}

function loadNickname() {
  try {
    return window.localStorage.getItem(STORAGE_NICKNAME_KEY) || "";
  } catch {
    return "";
  }
}

function saveNickname(nickname) {
  try {
    window.localStorage.setItem(STORAGE_NICKNAME_KEY, nickname);
  } catch {
    // Il prossimo invio richiederà di ridigitare il nickname, nessun danno.
  }
}

const LEADERBOARD_ERROR_MESSAGES = {
  nickname_invalid: "Usa un nickname di 2-16 caratteri (lettere, numeri, spazi).",
  nickname_blocked: "Questo nickname non è ammesso, provane un altro.",
  token_invalid: "La sessione di gioco non è più valida: gioca un nuovo round per aggiornarla.",
  score_missing: "Rispondi almeno a un round prima di entrare in classifica.",
  rate_limited: "Troppi invii in poco tempo, riprova tra un minuto.",
};

// Modal di invio punteggio condiviso da "Chi è maggiore?" e "Ordina le
// regioni": lo score non è mai un dato del form, arriva già incorporato nel
// token di sessione firmato dal server (vedi app/quiz_tokens.py).
export function SubmitScoreModal({ mode, token, score, scoreLabel, onClose, onSubmitted }) {
  const [nickname, setNickname] = useState(loadNickname);
  const [status, setStatus] = useState("idle"); // idle | sending | done | error
  const [error, setError] = useState("");
  const [rank, setRank] = useState(null);
  // step: 'choice' (solo se auth configurata e non loggato) | 'form' | (done via status)
  const [step, setStep] = useState(isAuthConfigured() ? "loading" : "form");
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (!isAuthConfigured()) return;
    getUser().then((u) => {
      setUser(u);
      setStep(u ? "form" : "choice"); // loggato -> salva sull'account; anonimo -> scelta
    });
  }, []);

  async function submit(event) {
    event.preventDefault();
    setStatus("sending");
    setError("");
    try {
      // Se c'è una sessione Supabase, il Bearer lega il punteggio all'account;
      // senza, resta anonimo (il server tratta lo user_id come opzionale).
      const response = await fetch("/api/game/leaderboard", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(await authHeaders()) },
        body: JSON.stringify({ token, nickname }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(LEADERBOARD_ERROR_MESSAGES[data.error] || "Invio non riuscito, riprova.");
        setStatus("error");
        return;
      }
      saveNickname(nickname);
      setRank(data.rank_all);
      setStatus("done");
      trackGameEvent("leaderboard_submit", { mode, score, game: mode });
      if (onSubmitted) onSubmitted(data);
    } catch {
      setError("Invio non riuscito, riprova.");
      setStatus("error");
    }
  }

  return (
    <Modal title="Entra in classifica" onClose={onClose} labelledBy="submit-score-title">
      {status === "done" ? (
        <>
          <p>
            Punteggio salvato: <strong>{scoreLabel}</strong>
            {rank ? `. Posizione assoluta: ${rank}ª.` : "."}
          </p>
          <a className="game-btn" href="/quiz/classifica">Vedi la classifica</a>
        </>
      ) : step === "loading" ? (
        <p>Un momento...</p>
      ) : step === "choice" ? (
        <div className="submit-score-choice">
          <p>Il tuo risultato: <strong>{scoreLabel}</strong>. Come vuoi salvarlo?</p>
          <button type="button" className="game-btn" onClick={() => { salvaInvioPendente({ mode, token, score, scoreLabel }); signInWithGoogle(); }}>
            Accedi e salvalo sul mio account
          </button>
          <button type="button" className="game-btn game-btn--ghost" onClick={() => setStep("form")}>
            Solo in classifica pubblica (senza account)
          </button>
          <button type="button" className="game-btn game-btn--ghost" onClick={onClose}>
            Tieni solo su questo browser
          </button>
        </div>
      ) : (
        <form className="submit-score-form" onSubmit={submit}>
          <p>
            Il tuo risultato: <strong>{scoreLabel}</strong>
            {user && <> · salverai sul tuo account</>}
          </p>
          <label htmlFor="submit-score-nickname">Nickname pubblico</label>
          <input
            id="submit-score-nickname"
            type="text"
            required
            minLength={2}
            maxLength={16}
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="Il tuo nome in classifica"
          />
          {status === "error" && <p className="game-error">{error}</p>}
          <button type="submit" className="game-btn" disabled={status === "sending"}>
            {status === "sending" ? "Invio..." : "Invia punteggio"}
          </button>
        </form>
      )}
    </Modal>
  );
}

// Forme del risultato condivisibile: il significato non sta mai nel solo
// colore. Ogni forma ha un glifo per lo schermo e una parola per chi legge
// con un lettore di schermo o incolla il testo in un posto senza emoji.
export const FORME_RISULTATO = {
  exact: { glifo: "●", parola: "esatta" },
  higher: { glifo: "▲", parola: "più alta" },
  lower: { glifo: "▼", parola: "più bassa" },
  region: { glifo: "◐", parola: "regione giusta" },
  miss: { glifo: "○", parola: "sbagliata" },
};

export function formeRisultato(esiti) {
  const lista = Array.isArray(esiti) ? esiti : [];
  const valide = lista.map((esito) => FORME_RISULTATO[esito] || FORME_RISULTATO.miss);
  return {
    glifi: valide.map((forma) => forma.glifo).join(" "),
    parole: valide.map((forma) => forma.parola).join(", "),
  };
}

// Testo da condividere, senza spoiler: il numero della sfida, una riga di
// forme, il link. Mai il nome della regione o il valore da indovinare.
export function testoCondivisione({ gameName, puzzleNumber, esiti, summary, url }) {
  const { glifi } = formeRisultato(esiti);
  const titolo = puzzleNumber ? `Sfida Italia: ${gameName} n. ${puzzleNumber}` : `Sfida Italia: ${gameName}`;
  return [titolo, summary, glifi, url].filter(Boolean).join("\n");
}

// Condividi: il bottone che condivide il risultato e dice com'è andata.
//
// Props
//   gameName      string, nome del gioco ("Indovina la Regione"). Obbligatoria.
//   game          "regione" | "provincia" | "compare" | "order" | "mappa", il gioco per
//                 l'evento GA4 (vedi docs/tracking_spec.md). Anche in `eventParams.game`.
//   puzzleNumber  number | string, numero della sfida. Opzionale.
//   punteggio     number, intero, il punteggio di chi condivide. Se c'è (con `puzzleNumber`)
//                 il link porta il frammento `#sfida=<punteggio>-<numero>`: un frammento e non
//                 una query, perché la query finisce nei log del server con l'IP, e mai un
//                 nome. Senza, il link è quello pulito.
//   esiti         array di "exact" | "higher" | "lower" | "miss", uno per
//                 tentativo o round, in ordine. Vuoto: nessuna riga di forme.
//   summary       string, riga di sintesi senza spoiler ("4 su 6"). Opzionale.
//   url           string, link alla pagina del gioco. Default: pagina corrente. Un frammento
//                 che ci fosse già (la sfida che chi condivide ha ricevuto) si toglie sempre:
//                 chi ricondivide non ripropaga il punteggio di un altro.
//   eventName     string, evento GA4 al successo. Default "game_share".
//   eventParams   object, parametri aggiuntivi dell'evento.
//   label         string, testo del bottone. Default "Condividi".
//
// Usa `navigator.share` dove c'è, altrimenti gli appunti. L'esito è dichiarato
// in una regione `aria-live="polite"`, visibile a tutti. Un annullamento del
// foglio di condivisione non è un errore e non scrive niente.
export function Condividi({
  gameName,
  game,
  puzzleNumber,
  punteggio,
  esiti = [],
  summary = "",
  url,
  eventName = "game_share",
  eventParams = {},
  label = "Condividi",
}) {
  const [esito, setEsito] = useState("");
  const { parole } = formeRisultato(esiti);

  async function condividi() {
    const base = url || (typeof window !== "undefined" ? window.location.href : "");
    const link = linkConSfida(base, punteggio, Number(puzzleNumber));
    const text = testoCondivisione({ gameName, puzzleNumber, esiti, summary, url: link });
    const parametri = { ...eventParams, ...(game ? { game } : {}) };
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ text });
        setEsito("Risultato condiviso.");
        trackGameEvent(eventName, { ...parametri, method: "share" });
        return;
      } catch (error) {
        if (error && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      setEsito("Risultato copiato negli appunti.");
      trackGameEvent(eventName, { ...parametri, method: "clipboard" });
    } catch {
      setEsito("Non sono riuscito a condividere il risultato. Copia il testo a mano.");
    }
  }

  return (
    <div className="qz-condividi">
      <button type="button" className="btn btn-primary" onClick={condividi}>
        {label}
      </button>
      {parole && <span className="visually-hidden">Forme del risultato: {parole}.</span>}
      <p className="qz-condividi-esito" role="status" aria-live="polite">
        {esito}
      </p>
    </div>
  );
}

// -- La sfida condivisa -------------------------------------------------------------
//
// Contratto per i giochi a punteggio (Chi è maggiore?, Ordina, la modalità a mappa):
//
//   const sfida = useSfidaCondivisa({ game: "compare", numeroOggi: number, avviata });
//   <SfidaCondivisa sfida={sfida} game="compare" avviata={avviata} />     // in cima all'isola
//   <FinePartita game="compare" sfida={sfida && { punteggio: sfida.punteggio, tuo: punteggio }} ... />
//   <Condividi game="compare" punteggio={punteggio} puzzleNumber={number} ... />
//
//   game        "compare" | "order" | "mappa": il massimo del punteggio viene da
//               `MASSIMI_SFIDA[game]`, che dice anche quando un frammento è fuori scala.
//   numeroOggi  il numero della sfida di OGGI, come lo dice il server (`number` del payload),
//               mai la data del browser. Finché non c'è, niente sfida.
//   avviata     true appena la partita comincia (la prima risposta): il riquadro sparisce e il
//               frammento si toglie dall'URL con `history.replaceState`.
//   sfida       `{ punteggio, numero }` o `null`: resta in memoria anche dopo che il
//               frammento è stato tolto, così a fine partita c'è il confronto.
//
// Il punteggio del frammento non è firmato, quindi il testo non dice mai "un amico ha fatto":
// "La sfida condivisa: 7 su 10. Riesci a superarla?". Niente va al server e non c'è un'anteprima
// social dinamica. Eventi: `challenge_open` quando il riquadro compare, `challenge_finish` a fine
// partita (da `FinePartita`). Il punteggio della sfida ricevuta NON viaggia negli eventi: ogni evento
// finisce anche nel log del server (`/api/events`) accanto all'IP, e il frammento esiste apposta per
// non farlo. Nell'evento c'è il tuo punteggio e il confronto (`outcome`).
export function useSfidaCondivisa({ game, numeroOggi, avviata }) {
  const [sfida, setSfida] = useState(null);
  const letta = useRef(false);
  const massimo = MASSIMI_SFIDA[game];
  useEffect(() => {
    if (letta.current || avviata || typeof window === "undefined") return;
    const trovata = leggiSfida(window.location.hash, { massimo, numeroOggi });
    if (!trovata) return;
    letta.current = true;
    setSfida(trovata);
    trackGameEvent("challenge_open", { game });
  }, [game, massimo, numeroOggi, avviata]);
  useEffect(() => {
    if (!avviata || typeof window === "undefined") return;
    if (/^#sfida=/.test(window.location.hash)) {
      window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
    }
  }, [avviata]);
  return sfida;
}

export function SfidaCondivisa({ sfida, game, avviata }) {
  const massimo = MASSIMI_SFIDA[game];
  if (!sfida || avviata || !Number.isInteger(massimo)) return null;
  return (
    <aside className="qz-sfida" role="note" aria-label="Sfida condivisa">
      <p>{testoSfida(sfida.punteggio, massimo)}</p>
    </aside>
  );
}

// Secondi alla prossima sfida, ricalcolati ogni secondo. `iso` è
// `next_puzzle_at` (ISO UTC). Con `iso` mancante o illeggibile dà null.
export function useCountdown(iso) {
  const target = iso ? Date.parse(iso) : NaN;
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!Number.isFinite(target)) return undefined;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [target]);
  if (!Number.isFinite(target)) return null;
  return Math.max(0, Math.ceil((target - now) / 1000));
}

export function formatCountdown(secondi) {
  const ore = Math.floor(secondi / 3600);
  const minuti = Math.floor((secondi % 3600) / 60);
  const sec = secondi % 60;
  return [ore, minuti, sec].map((n) => String(n).padStart(2, "0")).join(":");
}

// Un numero che sale da 0 al valore in `durata` ms (ease-out), con `requestAnimationFrame`.
// Con `prefersReducedMotion()` dà subito il valore finale, senza nemmeno un frame. Un valore
// che non è un numero finito si restituisce com'è. Il calcolo è `countUpValue` (puri.js).
export function useCountUp(finale, durata = DURATA_CONTEGGIO_MS) {
  const valido = Number.isFinite(finale);
  const [valore, setValore] = useState(() => (!valido || prefersReducedMotion() ? finale : 0));
  useEffect(() => {
    if (!valido) return undefined;
    if (prefersReducedMotion()) {
      setValore(finale);
      return undefined;
    }
    let id = 0;
    let inizio = null;
    setValore(0);
    const passo = (adesso) => {
      if (inizio === null) inizio = adesso;
      setValore(countUpValue(finale, adesso - inizio, durata));
      if (adesso - inizio < durata) id = requestAnimationFrame(passo);
    };
    id = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(id);
  }, [finale, durata, valido]);
  return valido ? valore : finale;
}

const PAROLA_TONO = { pieno: "Giusto. ", parziale: "Risultato parziale. ", nullo: "Sbagliato. " };

// Il segno dell'esito: forma diversa per tono, mai il solo colore. ✓ per il pieno (si disegna),
// ● neutro per il parziale, ✗ per il nullo. Il tratto si anima nel CSS, solo con `no-preference`.
function SegnoEsito({ tono }) {
  return (
    <svg className={`qz-fine-segno qz-fine-segno--${tono}`} viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
      {tono === "pieno" && <path d="M5 12.5l4.5 4.5L19 7.5" pathLength="1" />}
      {tono === "parziale" && <circle cx="12" cy="12" r="6" />}
      {tono === "nullo" && <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />}
    </svg>
  );
}

// FinePartita: la schermata che chiude una partita, uguale per i giochi. Retrocompatibile: le
// props nuove sono tutte opzionali.
//
// Props
//   won            boolean, l'esito. Decide il tono se `tono` manca, mai il colore da solo.
//   tono           "pieno" | "parziale" | "nullo". Default: "pieno" se `won`, "nullo" se no.
//                  Un risultato parziale (4 su 10) è "parziale": un ● neutro, non una croce.
//   titolo         string, riga di risultato ("Indovinata in 3 tentativi"). Obbligatoria.
//                  Se contiene "N su M" ("7 su 10") il numero N conta da 0 al valore in 450 ms
//                  (cifre tabulari); con `prefers-reduced-motion: reduce` mostra subito il
//                  finale. Il testo per il lettore di schermo ha sempre il valore finale.
//   conta          boolean, false spegne il conteggio. Default true.
//   dettaglio      string, riga sotto il titolo. Opzionale.
//   fatto          string, il "fatto da portarti via": una frase sola, dopo l'esito, col link alla
//                  scheda (`dato.path`). SOLO se presente e presentabile: senza, o con un "n.d."
//                  o un carattere vietato dallo stile, la riga non esce. Viene dal server.
//   sfida          `{ punteggio, tuo, game? }`: la sfida condivisa ricevuta (da
//                  `useSfidaCondivisa`) e il punteggio di chi ha giocato. Mostra "Tu 8, la
//                  sfida condivisa 7" e manda `challenge_finish`. Senza, niente.
//   game           "regione" | "provincia" | "compare" | "order" | "mappa", per gli eventi GA4.
//   dato           oggetto del dato giusto, tutto insieme:
//                    name         string, nome dell'indicatore
//                    value        number, valore
//                    unit         string, unità (passa da formatValue)
//                    year         number | string, anno
//                    sourceLabel  string, fonte in chiaro
//                    sourceUrl    string, link alla fonte
//                    description  string, "Che cosa misura" (la `description` del payload)
//                    path         string, link canonico alla scheda indicatore
//   territori      array di { name, path }, schede dei territori coinvolti.
//   nextPuzzleAt   string ISO UTC, `next_puzzle_at`. Senza, niente countdown.
//   condividi      props di <Condividi>. Senza, niente bottone Condividi.
//   onPlayAgain    function, "Gioca ancora". Senza, il bottone non compare.
//   playAgainLabel string, default "Gioca ancora".
//   prossimo       `{ label, href }`: un prossimo passo che è un link ("Prova Ordina le regioni").
export function FinePartita({
  won,
  tono,
  titolo,
  conta = true,
  dettaglio = "",
  fatto,
  sfida,
  game,
  dato,
  territori = [],
  nextPuzzleAt,
  condividi,
  onPlayAgain,
  playAgainLabel = "Gioca ancora",
  prossimo,
}) {
  const secondi = useCountdown(nextPuzzleAt);
  const tonoEffettivo = tonoFinale(won, tono);
  const contabile = conta ? titoloContabile(titolo) : null;
  const valore = useCountUp(contabile ? contabile.valore : null);
  const frase = fattoPresentabile(fatto);
  const gioco = game || (condividi && (condividi.game || (condividi.eventParams && condividi.eventParams.game))) || undefined;
  const condividiProps = condividi && { game: gioco, ...condividi };

  const sfidaPunteggio = sfida && Number.isInteger(sfida.punteggio) ? sfida.punteggio : null;
  const sfidaTuo = sfida && Number.isInteger(sfida.tuo) ? sfida.tuo : null;
  const chiusa = useRef(false);
  useEffect(() => {
    if (sfidaPunteggio === null || sfidaTuo === null || chiusa.current) return;
    chiusa.current = true;
    trackGameEvent("challenge_finish", {
      game: (sfida && sfida.game) || gioco,
      score: sfidaTuo,
      outcome: sfidaTuo > sfidaPunteggio ? "superata" : sfidaTuo === sfidaPunteggio ? "pari" : "sotto",
    });
  }, [sfidaPunteggio, sfidaTuo, sfida, gioco]);

  return (
    <section className="qz-fine" aria-labelledby="qz-fine-titolo">
      <h2 id="qz-fine-titolo" className="qz-fine-titolo">
        <SegnoEsito tono={tonoEffettivo} />{" "}
        <span className="visually-hidden">{PAROLA_TONO[tonoEffettivo]}</span>
        {contabile ? (
          <>
            <span aria-hidden="true">
              {contabile.prima}
              <span className="qz-fine-cifra" style={{ minInlineSize: `${String(contabile.valore).length}ch` }}>{valore}</span>
              {contabile.dopo}
            </span>
            <span className="visually-hidden">{titolo}</span>
          </>
        ) : (
          titolo
        )}
      </h2>
      {dettaglio && <p className="qz-fine-dettaglio">{dettaglio}</p>}
      {sfidaPunteggio !== null && sfidaTuo !== null && (
        <p className="qz-fine-sfida">{testoConfrontoSfida(sfidaTuo, sfidaPunteggio)}</p>
      )}
      {frase && (
        <p className="qz-fine-fatto">
          {frase}
          {dato && dato.path && (
            <>
              {" "}
              <a href={dato.path}>Vai alla scheda</a>
            </>
          )}
        </p>
      )}

      {dato && (
        <div className="qz-fine-dato">
          <p className="qz-fine-valore">
            <strong>{dato.name}</strong>: {formatValue(dato.value, dato.unit)}
          </p>
          <SourceStrip year={dato.year} sourceLabel={dato.sourceLabel} sourceUrl={dato.sourceUrl} game={gioco} />
          {dato.description && (
            <>
              <h3 className="qz-fine-misura">Che cosa misura</h3>
              <p>{dato.description}</p>
            </>
          )}
          {dato.path && (
            <p>
              <a href={dato.path}>Apri la scheda dell'indicatore</a>
            </p>
          )}
        </div>
      )}

      {territori.length > 0 && (
        <ul className="qz-fine-territori" aria-label="Schede dei territori">
          {territori.map((territorio) => (
            <li key={territorio.path}>
              <a href={territorio.path}>{territorio.name}</a>
            </li>
          ))}
        </ul>
      )}

      {secondi !== null && (
        <p className="qz-fine-countdown" role="timer">
          {secondi > 0 ? `Prossima sfida tra ${formatCountdown(secondi)}` : "La nuova sfida è pronta."}
        </p>
      )}

      <div className="qz-fine-azioni">
        {condividiProps && <Condividi {...condividiProps} />}
        {onPlayAgain && (
          <button type="button" className="btn" onClick={onPlayAgain}>
            {playAgainLabel}
          </button>
        )}
        {prossimo && prossimo.href && prossimo.label && (
          <a className="btn" href={prossimo.href}>
            {prossimo.label}
          </a>
        )}
      </div>
    </section>
  );
}

// Il punteggio non si perde al redirect di Google. Il token di sessione e il
// punteggio vivono nello stato React, che il redirect azzera: prima di partire
// li si mette in sessionStorage (solo questa scheda, si svuota alla chiusura),
// e al ritorno, con la sessione, si riapre lo stesso modal di invio. Se nel
// frattempo il token e' scaduto, il server risponde token_invalid e il modal lo
// dice in chiaro.
function salvaInvioPendente(invio) {
  try {
    window.sessionStorage.setItem(STORAGE_PENDING_KEY, JSON.stringify({ ...invio, savedAt: Date.now() }));
  } catch {
    // Senza sessionStorage il punteggio si perde come prima: nessun danno nuovo.
  }
}

function leggiInvioPendente() {
  try {
    const invio = JSON.parse(window.sessionStorage.getItem(STORAGE_PENDING_KEY) || "null");
    if (!invio || !invio.token || Date.now() - invio.savedAt > PENDING_MAX_AGE_MS) return null;
    return invio;
  } catch {
    return null;
  }
}

function cancellaInvioPendente() {
  try {
    window.sessionStorage.removeItem(STORAGE_PENDING_KEY);
  } catch {
    // niente da fare
  }
}

function PendingSubmit({ invio, onDone }) {
  return (
    <SubmitScoreModal
      mode={invio.mode}
      token={invio.token}
      score={invio.score}
      scoreLabel={invio.scoreLabel}
      onClose={onDone}
      onSubmitted={cancellaInvioPendente}
    />
  );
}

// Ogni pagina del gioco importa questo modulo: al ritorno dal login riprende
// l'invio senza che le pagine debbano saperne niente.
function riprendiInvioPendente() {
  if (typeof window === "undefined" || !isAuthConfigured() || !leggiInvioPendente()) return;
  let aperto = false;
  function apri(user) {
    const invio = user && !aperto ? leggiInvioPendente() : null;
    if (!invio) return;
    aperto = true;
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = createRoot(host);
    const chiudi = () => {
      cancellaInvioPendente();
      root.unmount();
      host.remove();
    };
    root.render(<PendingSubmit invio={invio} onDone={chiudi} />);
  }
  getUser().then(apri).catch(() => {});
  onAuthChange(apri).catch(() => {});
}

riprendiInvioPendente();
