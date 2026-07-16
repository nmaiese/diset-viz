import React, { useEffect, useRef, useState } from "react";
import { fetchJson, formatValue, prefersReducedMotion, trackGameEvent, Modal } from "./main.jsx";

const API = {
  round: (difficulty) => `/api/game/compare/round?difficulty=${difficulty}`,
  answer: "/api/game/compare/answer",
};

const STORAGE_STATS_KEY = "di-compare-stats";
const STORAGE_ONBOARDED_KEY = "di-compare-onboarded";
const ROUND_MS = 10000;
const TICK_MS = 100;
const NEXT_ROUND_DELAY_MS = 2600;

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

export default function CompareApp() {
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | answering | revealed | error
  const [result, setResult] = useState(null);
  const [choice, setChoice] = useState(null);
  const [streak, setStreak] = useState(0);
  const [stats, setStats] = useState(loadStats);
  const [timeLeft, setTimeLeft] = useState(ROUND_MS);
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try {
      return !window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  const stateRef = useRef({ status: "loading", round: null, streak: 0 });
  const timerRef = useRef(null);
  const advanceRef = useRef(null);

  useEffect(() => {
    stateRef.current = { status, round, streak };
  }, [status, round, streak]);

  useEffect(() => {
    trackGameEvent("compare_start", {});
    loadRound(0);
    return () => {
      window.clearInterval(timerRef.current);
      window.clearTimeout(advanceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Il countdown parte solo a partita attiva e senza onboarding aperto:
  // non è giusto far scorrere il tempo mentre l'utente legge le regole.
  useEffect(() => {
    if (status !== "answering" || showOnboarding) return undefined;
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
  }, [status, showOnboarding]);

  function loadRound(difficulty) {
    setStatus("loading");
    setResult(null);
    setChoice(null);
    setTimeLeft(ROUND_MS);
    fetchJson(API.round(difficulty))
      .then((data) => {
        setRound(data);
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
      }),
    })
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        const prevStreak = stateRef.current.streak;
        const nextStreak = data.correct ? prevStreak + 1 : 0;
        setStreak(nextStreak);
        setStats((prev) => {
          const next = {
            bestStreak: Math.max(prev.bestStreak, nextStreak),
            totalRounds: prev.totalRounds + 1,
            totalCorrect: prev.totalCorrect + (data.correct ? 1 : 0),
          };
          saveStats(next);
          return next;
        });
        trackGameEvent("compare_answer", {
          result: data.correct ? "correct" : picked === "timeout" ? "timeout" : "wrong",
          streak: nextStreak,
          difficulty: currentRound.difficulty,
        });
        advanceRef.current = window.setTimeout(() => {
          const { status: still } = stateRef.current;
          if (still === "revealed") loadRound(difficultyForStreak(nextStreak));
        }, NEXT_ROUND_DELAY_MS);
      })
      .catch(() => setStatus("error"));
  }

  function nextRound() {
    window.clearTimeout(advanceRef.current);
    loadRound(difficultyForStreak(streak));
  }

  function closeOnboarding() {
    setShowOnboarding(false);
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // Il modal si ripresenterà alla prossima visita, nessun danno.
    }
  }

  const timerPct = Math.max(0, (timeLeft / ROUND_MS) * 100);
  const level = round ? round.difficulty : 0;
  const winnerKey = result ? result[result.winner].region_key : null;

  function cardClass(side) {
    const base = side === "region_a" ? "compare-card compare-card--a" : "compare-card compare-card--b";
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
      <div className="compare-scorebar">
        <div className="compare-score">
          <strong>{streak}</strong>
          <span>Serie</span>
        </div>
        <div className="compare-score">
          <strong>{stats.bestStreak}</strong>
          <span>Record</span>
        </div>
        <div className="compare-level" aria-label={`Difficoltà ${DIFFICULTY_LABELS[level]}`}>
          <span className="compare-level-label">{DIFFICULTY_LABELS[level]}</span>
          <span className="compare-level-dots" aria-hidden="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <i key={i} className={i <= level ? "is-on" : ""} />
            ))}
          </span>
        </div>
      </div>

      {status === "error" && (
        <div className="compare-status">
          <p className="game-error">Qualcosa non ha funzionato. Riprova.</p>
          <button type="button" className="game-btn" onClick={() => loadRound(difficultyForStreak(streak))}>
            Nuovo round
          </button>
        </div>
      )}

      {round && status !== "error" && (
        <>
          <div className="compare-question">
            <span className="compare-kicker">Quale regione ha il valore più alto?</span>
            <h2>{round.indicator.name}</h2>
            <p className="compare-meta">
              {round.indicator.macro_area} · {round.indicator.theme} · {round.indicator.year}
              {round.indicator.unit && ` · ${round.indicator.unit}`}
            </p>
          </div>

          <div className="compare-timer" role="presentation">
            <div
              className={status === "answering" ? "compare-timer-fill" : "compare-timer-fill is-paused"}
              style={{ width: `${timerPct}%` }}
            />
          </div>

          <div className="compare-cards">
            {["region_a", "region_b"].map((side) => {
              const region = round[side];
              const revealed = status === "revealed" && result;
              return (
                <button
                  key={side}
                  type="button"
                  className={cardClass(side)}
                  disabled={status !== "answering"}
                  onClick={() => submitAnswer(side)}
                >
                  <strong className="compare-region-name">{region.region}</strong>
                  {revealed && (
                    <span className="compare-value">
                      {formatValue(result[side].value, round.indicator.unit)}
                    </span>
                  )}
                  {revealed && result.winner === side && <span className="compare-crown">maggiore</span>}
                </button>
              );
            })}
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
              Prossimo round
            </button>
          )}
        </>
      )}

      {status === "loading" && !round && <p className="game-loading">Preparazione del round...</p>}

      {showOnboarding && (
        <Modal title="Chi è maggiore?" onClose={closeOnboarding} labelledBy="compare-onboarding-title">
          <ol className="game-onboarding-steps">
            <li>
              <strong>Un indicatore, due regioni.</strong> Tocca la regione che secondo te ha il valore
              più alto. Hai dieci secondi.
            </li>
            <li>
              <strong>La serie cresce, la sfida pure.</strong> Ogni risposta giusta di fila alza la
              difficoltà: le coppie diventano sempre più vicine in classifica.
            </li>
            <li>
              <strong>Un errore azzera la serie.</strong> Il tuo record resta salvato su questo
              dispositivo.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={closeOnboarding}>Ho capito, gioco</button>
        </Modal>
      )}
    </div>
  );
}
