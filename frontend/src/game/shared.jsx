import React, { useEffect, useRef, useState } from "react";

const STORAGE_NICKNAME_KEY = "di-nickname";

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
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ event: name, ...eventParams });
  if (typeof window.gtag === "function") {
    try {
      window.gtag("event", name, {
        ...eventParams,
        send_to: "G-THTPZZ02QH",
      });
    } catch {
      // Se il Google Tag non è ancora disponibile, il push nel dataLayer resta.
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

export function SourceStrip({ year, sourceLabel, sourceUrl }) {
  return (
    <p className="quiz-source">
      <span className="quiz-source-year">Anno {year}</span>
      {sourceLabel && sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
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
            ✕
          </button>
        </div>
        <div className="game-modal-body">{children}</div>
      </div>
    </div>
  );
}

export function loadNickname() {
  try {
    return window.localStorage.getItem(STORAGE_NICKNAME_KEY) || "";
  } catch {
    return "";
  }
}

export function saveNickname(nickname) {
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

  async function submit(event) {
    event.preventDefault();
    setStatus("sending");
    setError("");
    try {
      const response = await fetch("/api/game/leaderboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      ) : (
        <form className="submit-score-form" onSubmit={submit}>
          <p>
            Il tuo risultato: <strong>{scoreLabel}</strong>
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
