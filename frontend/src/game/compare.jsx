import React, { useEffect, useRef, useState } from "react";
import { fetchJson, formatValue, trackGameEvent, SourceStrip, SubmitScoreModal } from "./shared.jsx";

const API = {
  round: (difficulty, token) =>
    `/api/game/compare/round?difficulty=${difficulty}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/compare/answer",
};

const STORAGE_STATS_KEY = "di-compare-stats";
const STORAGE_ONBOARDED_KEY = "di-compare-onboarded";
const ROUND_MS = 10000;
const TICK_MS = 100;

function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return { bestStreak: 0, totalRounds: 0, totalCorrect: 0, ...parsed };
  } catch {
    return { bestStreak: 0, totalRounds: 0, totalCorrect: 0 };
  }
}

function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile: il record resta in memoria per la sessione.
  }
}

function difficultyForStreak(streak) {
  return Math.min(Math.floor(streak / 3), 4);
}

const DIFFICULTY_LABELS = ["Riscaldamento", "Facile", "Media", "Difficile", "Estrema"];

// Il cronometro nella barra di stato mostra i secondi in stile 0:06, come nel
// design "Chi è maggiore?": arrotonda per eccesso i millisecondi rimasti così
// il salto a 0 coincide con lo scadere effettivo del round.
function formatClock(ms) {
  const seconds = Math.max(0, Math.ceil(ms / 1000));
  return `0:${String(seconds).padStart(2, "0")}`;
}

export default function CompareApp() {
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | answering | revealed | error
  const [result, setResult] = useState(null);
  const [choice, setChoice] = useState(null);
  const [streak, setStreak] = useState(0);
  const [stats, setStats] = useState(loadStats);
  const [timeLeft, setTimeLeft] = useState(ROUND_MS);
  const [sessionBest, setSessionBest] = useState(0);
  const [showScoreModal, setShowScoreModal] = useState(false);
  // Contatori della sessione corrente, mostrati nella barra di stato in cima
  // (Round / Serie / Punti): ripartono a ogni caricamento della pagina, a
  // differenza dei record salvati in localStorage.
  const [roundNumber, setRoundNumber] = useState(0);
  const [sessionPoints, setSessionPoints] = useState(0);
  const [hasPlayedBefore] = useState(() => {
    try {
      return !!window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  const stateRef = useRef({ status: "idle", round: null, streak: 0 });
  const timerRef = useRef(null);
  const tokenRef = useRef(null);
  const promptedBestRef = useRef(0);

  useEffect(() => {
    stateRef.current = { status, round, streak };
  }, [status, round, streak]);

  useEffect(() => {
    return () => {
      window.clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (status !== "answering") return undefined;
    timerRef.current = window.setInterval(() => {
      setTimeLeft((prev) => {
        const next = prev - TICK_MS;
        if (next <= 0) {
          window.clearInterval(timerRef.current);
          submitAnswer("timeout");
          return 0;
        }
        return next;
      });
    }, TICK_MS);
    return () => window.clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  // Comando da tastiera mostrato nell'HUD (← A · B →): frecce o i tasti A/B
  // scelgono la regione mentre il round è aperto. Registrato una sola volta,
  // legge lo stato corrente da stateRef per non re-agganciarsi a ogni render.
  useEffect(() => {
    function onKeyDown(event) {
      if (stateRef.current.status !== "answering") return;
      const key = event.key.toLowerCase();
      if (key === "arrowleft" || key === "a") {
        event.preventDefault();
        submitAnswer("region_a");
      } else if (key === "arrowright" || key === "b") {
        event.preventDefault();
        submitAnswer("region_b");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startGame() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // Il pannello con le regole si ripresenterà alla prossima visita, nessun danno.
    }
    trackGameEvent("compare_start", {});
    loadRound(0);
  }

  function loadRound(difficulty) {
    setStatus("loading");
    setResult(null);
    setChoice(null);
    setTimeLeft(ROUND_MS);
    fetchJson(API.round(difficulty, tokenRef.current))
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setRoundNumber((n) => n + 1);
        setStatus("answering");
      })
      .catch(() => setStatus("error"));
  }

  function submitAnswer(picked) {
    const { status: current, round: currentRound } = stateRef.current;
    if (current !== "answering" || !currentRound) return;
    window.clearInterval(timerRef.current);
    setStatus("loading");
    setChoice(picked);
    fetchJson(API.answer, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        indicator_id: currentRound.indicator.id,
        year: currentRound.indicator.year,
        region_a_key: currentRound.region_a.region_key,
        region_b_key: currentRound.region_b.region_key,
        choice: picked,
        token: tokenRef.current,
      }),
    })
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
        const prevStreak = stateRef.current.streak;
        const nextStreak = data.correct ? prevStreak + 1 : 0;
        setStreak(nextStreak);
        if (data.correct) setSessionPoints((p) => p + 1);
        setStats((prev) => {
          const next = {
            bestStreak: Math.max(prev.bestStreak, nextStreak),
            totalRounds: prev.totalRounds + 1,
            totalCorrect: prev.totalCorrect + (data.correct ? 1 : 0),
          };
          saveStats(next);
          return next;
        });
        if (data.session) {
          setSessionBest(data.session.best);
          // La serie appena finita ha battuto il record di questa sessione:
          // proponiamo la classifica invece di aspettare che l'utente la cerchi.
          if (!data.correct && data.session.best > promptedBestRef.current && data.session.best >= 3) {
            promptedBestRef.current = data.session.best;
            setShowScoreModal(true);
          }
        }
        trackGameEvent("compare_answer", {
          result: data.correct ? "correct" : picked === "timeout" ? "timeout" : "wrong",
          streak: nextStreak,
          difficulty: currentRound.difficulty,
        });
      })
      .catch(() => setStatus("error"));
  }

  function nextRound() {
    loadRound(difficultyForStreak(streak));
  }

  const timerPct = Math.max(0, (timeLeft / ROUND_MS) * 100);
  const level = round ? round.difficulty : 0;
  const isLowTime = status === "answering" && timeLeft <= 3000;
  const accuracy = stats.totalRounds > 0
    ? Math.round((stats.totalCorrect / stats.totalRounds) * 100)
    : 0;

  function regionClass(side) {
    const base = "qz-region";
    if (status !== "revealed" || !result) return base;
    const isWinner = result.winner === side;
    const wasPicked = choice === side;
    let cls = `${base} is-revealed`;
    if (isWinner) cls += " is-winner";
    if (wasPicked && !result.correct) cls += " is-picked-wrong";
    return cls;
  }

  return (
    <div className="compare-app">
      {status === "idle" && (
        <div className="compare-start">
          <h2>Chi è maggiore?</h2>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Un indicatore, due regioni.</strong> Tocca la regione che secondo te ha il valore
              più alto. Conta il numero, anche quando un valore alto non rappresenta un risultato migliore.
              Hai dieci secondi.
            </li>
            <li>
              <strong>La serie cresce, la sfida pure.</strong> Ogni risposta giusta di fila alza la
              difficoltà: le coppie diventano sempre più vicine in classifica.
            </li>
            <li>
              <strong>Un errore azzera la serie.</strong> Il tuo record resta salvato su questo
              dispositivo. Da tastiera usa le frecce o i tasti A e B.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={startGame}>
            {hasPlayedBefore ? "Inizia" : "Inizia a giocare"}
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="compare-status">
          <p className="game-error">Qualcosa non ha funzionato. Riprova.</p>
          <button type="button" className="game-btn" onClick={() => loadRound(difficultyForStreak(streak))}>
            Riprova
          </button>
        </div>
      )}

      {round && status !== "error" && (
        <>
          <div className="qz-status">
            <span className="qz-badge">Round <strong>{roundNumber}</strong></span>
            <span className="qz-badge">Serie <strong>{streak}</strong></span>
            <span className="qz-badge">Punti <strong>{sessionPoints}</strong></span>
            <span className="qz-badge qz-badge--level">{DIFFICULTY_LABELS[level]}</span>
            <div className="qz-timer">
              <span className={isLowTime ? "qz-clock is-low" : "qz-clock"}>{formatClock(timeLeft)}</span>
              <span className="qz-timer-bar">
                <i
                  className={status === "answering" ? "" : "is-paused"}
                  style={{ width: `${timerPct}%` }}
                />
              </span>
            </div>
          </div>

          <div className="qz-question">
            <small>Indicatore Istat · {round.indicator.year}</small>
            <h2>{round.indicator.name}</h2>
            {(round.indicator.description || round.indicator.value_explanation) && (
              <p className="desc">
                {[round.indicator.description, round.indicator.value_explanation].filter(Boolean).join(" ")}
              </p>
            )}
            <SourceStrip
              year={round.indicator.year}
              sourceLabel={round.indicator.source_label}
              sourceUrl={round.indicator.source_url}
            />
          </div>

          <div className="qz-vs">
            <button
              type="button"
              className={regionClass("region_a")}
              disabled={status !== "answering"}
              onClick={() => submitAnswer("region_a")}
            >
              <span className="code">A</span>
              <span className="name">{round.region_a.region}</span>
              {round.region_a.geo_area && <span className="macro">{round.region_a.geo_area}</span>}
              {status === "revealed" && result && (
                <span className="value">{formatValue(result.region_a.value, round.indicator.unit)}</span>
              )}
              {status === "revealed" && result && result.winner === "region_a" && (
                <span className="crown">maggiore</span>
              )}
            </button>
            <div className="divider">VS</div>
            <button
              type="button"
              className={regionClass("region_b")}
              disabled={status !== "answering"}
              onClick={() => submitAnswer("region_b")}
            >
              <span className="code">B</span>
              <span className="name">{round.region_b.region}</span>
              {round.region_b.geo_area && <span className="macro">{round.region_b.geo_area}</span>}
              {status === "revealed" && result && (
                <span className="value">{formatValue(result.region_b.value, round.indicator.unit)}</span>
              )}
              {status === "revealed" && result && result.winner === "region_b" && (
                <span className="crown">maggiore</span>
              )}
            </button>
          </div>

          <div className="compare-feedback" aria-live="polite">
            {status === "revealed" && result && (
              <p className={result.correct ? "compare-verdict is-correct" : "compare-verdict is-wrong"}>
                {result.correct
                  ? "Giusto!"
                  : choice === "timeout"
                  ? "Tempo scaduto."
                  : "Sbagliato."}
                {" "}
                {result[result.winner].region} ha il valore più alto.
                {!result.correct && streak === 0 && stats.bestStreak > 0 && " Serie azzerata."}
              </p>
            )}
          </div>

          {status === "revealed" && (
            <button type="button" className="game-btn compare-next" onClick={nextRound}>
              {result && result.correct ? "Avanti" : "Ricomincia"}
            </button>
          )}

          <div className="qz-hud">
            <div><small>Serie attuale</small><strong className="streak">{streak}</strong></div>
            <div><small>Record personale</small><strong className="best">{stats.bestStreak}</strong></div>
            <div><small>Accuratezza</small><strong>{accuracy}%</strong></div>
            <div className="qz-hud-cmd"><small>Comando</small><strong>← A · B →</strong></div>
          </div>

          {sessionBest > 0 && (
            <button type="button" className="game-btn game-btn--ghost compare-lb-cta" onClick={() => setShowScoreModal(true)}>
              Entra in classifica
            </button>
          )}
        </>
      )}

      {status === "loading" && !round && (
        <div aria-hidden="true">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 12, width: "45%" }} />
            <span style={{ height: 22, width: "70%" }} />
          </div>
          <div className="qz-vs" style={{ marginTop: 18 }}>
            <span className="skel-bar" style={{ height: 140 }} />
            <div className="divider">VS</div>
            <span className="skel-bar" style={{ height: 140 }} />
          </div>
        </div>
      )}

      {showScoreModal && (
        <SubmitScoreModal
          mode="compare"
          token={tokenRef.current}
          score={sessionBest}
          scoreLabel={`${sessionBest} risposte di fila`}
          onClose={() => setShowScoreModal(false)}
        />
      )}
    </div>
  );
}
