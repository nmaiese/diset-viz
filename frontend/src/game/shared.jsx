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

export function trackGameEvent(name, params = {}) {
  if (typeof window === "undefined") return;
  const eventParams = {
    page_type: "game",
    page_path: window.location.pathname,
    page_title: document.title,
    ...params,
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
export function notifyAchievements(list) {
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
    icon.textContent = achievement.icon || "🏅";
    const text = document.createElement("div");
    text.className = "achv-toast-text";
    const kicker = document.createElement("strong");
    kicker.textContent = "Traguardo sbloccato";
    const title = document.createElement("span");
    title.textContent = achievement.title || "";
    text.appendChild(kicker);
    text.appendChild(title);
    toast.appendChild(icon);
    toast.appendChild(text);
    stack.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("is-in"));
    const life = 4200 + index * 400;
    setTimeout(() => {
      toast.classList.remove("is-in");
      setTimeout(() => toast.remove(), 320);
    }, life);
    trackGameEvent("achievement_unlocked", { achievement_id: achievement.id });
  });
}

export function SourceStrip({ year, sourceLabel, sourceUrl }) {
  return (
    <p className="quiz-source">
      <span className="quiz-source-year">Anno {year}</span>
      {sourceLabel && sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="quiz-source-link"
          onClick={() => trackGameEvent("quiz_source_click", { source: sourceLabel })}
        >
          Fonte: {sourceLabel}
        </a>
      )}
    </p>
  );
}

export function Modal({ title, onClose, children, labelledBy }) {
  const ref = useRef(null);
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="game-modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === ref.current) onClose();
      }}
      ref={ref}
    >
      <div className="game-modal" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
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
      trackGameEvent("leaderboard_submit", { mode, score });
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
  const titolo = puzzleNumber ? `${gameName} n. ${puzzleNumber}` : gameName;
  return [titolo, summary, glifi, url].filter(Boolean).join("\n");
}

// Condividi: il bottone che condivide il risultato e dice com'è andata.
//
// Props
//   gameName      string, nome del gioco ("Indovina la Regione"). Obbligatoria.
//   puzzleNumber  number | string, numero della sfida. Opzionale.
//   esiti         array di "exact" | "higher" | "lower" | "miss", uno per
//                 tentativo o round, in ordine. Vuoto: nessuna riga di forme.
//   summary       string, riga di sintesi senza spoiler ("4 su 6"). Opzionale.
//   url           string, link alla pagina del gioco. Default: pagina corrente.
//   eventName     string, evento GA4 al successo. Default "game_share".
//   eventParams   object, parametri aggiuntivi dell'evento.
//   label         string, testo del bottone. Default "Condividi".
//
// Usa `navigator.share` dove c'è, altrimenti gli appunti. L'esito è dichiarato
// in una regione `aria-live="polite"`, visibile a tutti. Un annullamento del
// foglio di condivisione non è un errore e non scrive niente.
export function Condividi({
  gameName,
  puzzleNumber,
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
    const link = url || (typeof window !== "undefined" ? window.location.href : "");
    const text = testoCondivisione({ gameName, puzzleNumber, esiti, summary, url: link });
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ text });
        setEsito("Risultato condiviso.");
        trackGameEvent(eventName, { ...eventParams, method: "share" });
        return;
      } catch (error) {
        if (error && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      setEsito("Risultato copiato negli appunti.");
      trackGameEvent(eventName, { ...eventParams, method: "clipboard" });
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

// FinePartita: la schermata che chiude una partita, uguale per i tre giochi.
//
// Props
//   won            boolean, l'esito. Decide icona e parola, mai il colore da solo.
//   titolo         string, riga di risultato ("Indovinata in 3 tentativi"). Obbligatoria.
//   dettaglio      string, riga sotto il titolo. Opzionale.
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
export function FinePartita({
  won,
  titolo,
  dettaglio = "",
  dato,
  territori = [],
  nextPuzzleAt,
  condividi,
  onPlayAgain,
  playAgainLabel = "Gioca ancora",
}) {
  const secondi = useCountdown(nextPuzzleAt);
  return (
    <section className="qz-fine" aria-labelledby="qz-fine-titolo">
      <h2 id="qz-fine-titolo" className="qz-fine-titolo">
        <span aria-hidden="true">{won ? "✓" : "✗"}</span>{" "}
        <span className="visually-hidden">{won ? "Giusto. " : "Sbagliato. "}</span>
        {titolo}
      </h2>
      {dettaglio && <p className="qz-fine-dettaglio">{dettaglio}</p>}

      {dato && (
        <div className="qz-fine-dato">
          <p className="qz-fine-valore">
            <strong>{dato.name}</strong>: {formatValue(dato.value, dato.unit)}
          </p>
          <SourceStrip year={dato.year} sourceLabel={dato.sourceLabel} sourceUrl={dato.sourceUrl} />
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
        {condividi && <Condividi {...condividi} />}
        {onPlayAgain && (
          <button type="button" className="btn" onClick={onPlayAgain}>
            {playAgainLabel}
          </button>
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
