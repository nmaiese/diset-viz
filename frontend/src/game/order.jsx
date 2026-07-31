import React, { useEffect, useRef, useState } from "react";
import { fetchJson, formatValue, trackGameEvent, SourceStrip, SubmitScoreModal, prefersReducedMotion, postGame, notifyAchievements } from "./shared.jsx";

const API = {
  round: (count, token) =>
    `/api/game/order/round?count=${count}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/order/answer",
};

const STORAGE_STATS_KEY = "di-order-stats";
const STORAGE_ONBOARDED_KEY = "di-order-onboarded";

function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return { bestScore3: 0, bestScore5: 0, totalRounds: 0, totalPositionsCorrect: 0, ...parsed };
  } catch {
    return { bestScore3: 0, bestScore5: 0, totalRounds: 0, totalPositionsCorrect: 0 };
  }
}

function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile: il record resta in memoria per la sessione.
  }
}

export default function OrderApp() {
  const [count, setCount] = useState(3);
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | ordering | revealed | error
  const [orderKeys, setOrderKeys] = useState([]); // region_key nell'ordine corrente (dal più alto al più basso, secondo il giocatore)
  const [dragIndex, setDragIndex] = useState(null);
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(loadStats);
  const [sessionBest, setSessionBest] = useState(0);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [started, setStarted] = useState(false);
  const [hasPlayedBefore] = useState(() => {
    try {
      return !!window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  const submittingRef = useRef(false);
  const tokenRef = useRef(null);
  const promptedBestRef = useRef(0);

  useEffect(() => {
    if (!started) return;
    trackGameEvent("order_start", { count });
    loadRound(count);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, started]);

  function startGame() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // Il pannello con le regole si ripresenterà alla prossima visita, nessun danno.
    }
    setStarted(true);
  }

  function loadRound(n) {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    setStatus("loading");
    setResult(null);
    setDragIndex(null);
    submittingRef.current = false;
    fetchJson(API.round(n, tokenRef.current))
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setOrderKeys(data.regions.map((r) => r.region_key));
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function moveItem(index, direction) {
    if (status !== "ordering") return;
    const target = index + direction;
    if (target < 0 || target >= orderKeys.length) return;
    setOrderKeys((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function shuffleOrder() {
    if (status !== "ordering") return;
    setOrderKeys((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [next[i], next[j]] = [next[j], next[i]];
      }
      return next;
    });
  }

  function handleDragStart(index) {
    if (status !== "ordering") return;
    setDragIndex(index);
  }

  function handleDragOver(e) {
    if (status !== "ordering") return;
    e.preventDefault();
  }

  function handleDrop(index) {
    if (status !== "ordering" || dragIndex === null || dragIndex === index) {
      setDragIndex(null);
      return;
    }
    setOrderKeys((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDragIndex(null);
  }

  function confirmOrder() {
    if (status !== "ordering" || orderKeys.length !== round.count || submittingRef.current) return;
    submittingRef.current = true;
    setStatus("loading");
    postGame(API.answer, {
      indicator_id: round.indicator.id,
      year: round.indicator.year,
      region_keys: orderKeys,
      token: tokenRef.current,
    })
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
        notifyAchievements(data.achievements);
        setStats((prev) => {
          const bestKey = round.count === 3 ? "bestScore3" : "bestScore5";
          const next = {
            ...prev,
            [bestKey]: Math.max(prev[bestKey], data.score),
            totalRounds: prev.totalRounds + 1,
            totalPositionsCorrect: prev.totalPositionsCorrect + data.score,
          };
          saveStats(next);
          return next;
        });
        if (data.session) {
          setSessionBest(data.session.best);
          const isPerfect = data.score === data.total;
          if (!isPerfect && data.session.best > promptedBestRef.current && data.session.best >= 2) {
            promptedBestRef.current = data.session.best;
            setShowScoreModal(true);
          }
        }
        trackGameEvent("order_answer", { score: data.score, total: data.total });
      })
      .catch(() => setStatus("error"));
  }

  const best = count === 3 ? stats.bestScore3 : stats.bestScore5;
  const resultBySide = result
    ? Object.fromEntries(result.positions.map((p) => [p.region_key, p]))
    : {};
  const regionByKey = round
    ? Object.fromEntries(round.regions.map((r) => [r.region_key, r]))
    : {};

  return (
    <div className="order-app">
      <div className="order-toolbar">
        <div className="order-counts" role="tablist" aria-label="Livello di difficoltà">
          {[3, 5].map((n) => (
            <button
              key={n}
              type="button"
              role="tab"
              aria-selected={count === n}
              className={count === n ? "game-tab is-active" : "game-tab"}
              onClick={() => setCount(n)}
            >
              {n} regioni
            </button>
          ))}
        </div>
        {sessionBest > 0 && (
          <button
            type="button"
            className="game-tab game-tab--ghost"
            style={{ marginLeft: "auto" }}
            onClick={() => setShowScoreModal(true)}
          >
            Entra in classifica
          </button>
        )}
      </div>

      {status === "idle" && (
        <div className="order-start">
          <h2>Ordina le regioni</h2>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Trascina o usa le frecce.</strong> Le regioni partono in ordine casuale: trascina le
              righe con l'icona ⋮⋮, oppure sposta ogni riga su o giù, finché non sono in ordine dal
              valore più alto al più basso secondo la tua ipotesi.
            </li>
            <li>
              <strong>Verifica quando l'ordine ti convince.</strong> Vedrai la classifica reale con i
              valori Istat.
            </li>
            <li>
              <strong>Un punto per ogni posizione azzeccata.</strong> Parti da tre regioni, passa a
              cinque quando ti senti pronto.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={startGame}>
            {hasPlayedBefore ? "Inizia" : "Inizia a giocare"}
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="order-status">
          <p className="game-error">Qualcosa non ha funzionato. Riprova.</p>
          <button type="button" className="game-btn" onClick={() => loadRound(count)}>
            Riprova
          </button>
        </div>
      )}

      {round && status !== "error" && (
        <div className="order-layout">
          <div className="order-main">
            <div className="order-question">
              <span className="order-kicker">
                Trascina o usa le frecce per ordinare, dal valore più alto al più basso
              </span>
              <h2>{round.indicator.name}</h2>
              <p className="order-meta">
                {round.indicator.macro_area} · {round.indicator.theme}
                {round.indicator.unit && ` · ${round.indicator.unit}`}
              </p>
              <SourceStrip
                year={round.indicator.year}
                sourceLabel={round.indicator.source_label}
                sourceUrl={round.indicator.source_url}
              />
              <div className="quiz-explanation">
                {round.indicator.description && (
                  <p className="quiz-description">
                    <strong>Che cosa misura.</strong> {round.indicator.description}
                  </p>
                )}
                {round.indicator.value_explanation && (
                  <p className="quiz-value-hint">
                    <strong>Come leggere il valore.</strong> {round.indicator.value_explanation}
                  </p>
                )}
                <p className="quiz-rule-note">
                  Ordina i numeri dal più alto al più basso, non dal risultato migliore al peggiore.
                </p>
              </div>
            </div>

            <div className="order-list">
              {orderKeys.map((key, idx) => {
                const region = regionByKey[key];
                if (!region) return null;
                const revealed = status === "revealed" && resultBySide[key];
                let cls = "order-row";
                if (status === "ordering") cls += " is-draggable";
                if (dragIndex === idx) cls += " is-dragging";
                if (revealed) cls += revealed.correct ? " is-correct" : " is-wrong";
                return (
                  <div
                    key={key}
                    className={cls}
                    draggable={status === "ordering"}
                    onDragStart={() => handleDragStart(idx)}
                    onDragOver={handleDragOver}
                    onDrop={() => handleDrop(idx)}
                    onDragEnd={() => setDragIndex(null)}
                  >
                    <span className="order-rank">{idx + 1}</span>
                    <strong className="order-row-name">{region.region}</strong>
                    <span className="order-row-value">
                      {revealed ? formatValue(revealed.value, round.indicator.unit) : "nascosto"}
                      {revealed && (
                        <span className="order-row-status">
                          {revealed.correct ? "posizione corretta" : `era ${revealed.correct_position}ª`}
                        </span>
                      )}
                    </span>
                    <span className="order-row-controls">
                      {status === "ordering" && (
                        <>
                          <button
                            type="button"
                            className="order-move-btn"
                            aria-label={`Sposta ${region.region} più in alto`}
                            disabled={idx === 0}
                            onClick={() => moveItem(idx, -1)}
                          >
                            ▲
                          </button>
                          <button
                            type="button"
                            className="order-move-btn"
                            aria-label={`Sposta ${region.region} più in basso`}
                            disabled={idx === orderKeys.length - 1}
                            onClick={() => moveItem(idx, 1)}
                          >
                            ▼
                          </button>
                          <span className="order-handle" aria-hidden="true">⋮⋮</span>
                        </>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>

            {status === "ordering" && (
              <div className="order-actions">
                <button type="button" className="game-btn" onClick={confirmOrder}>
                  Verifica ordine
                </button>
                <button type="button" className="game-btn game-btn--ghost" onClick={shuffleOrder}>
                  Mischia
                </button>
                <button type="button" className="game-btn game-btn--ghost" onClick={() => loadRound(count)}>
                  Salta round
                </button>
              </div>
            )}

            <div className="order-feedback" aria-live="polite">
              {status === "revealed" && result && (
                <p className={result.score === result.total ? "order-verdict is-perfect" : "order-verdict"}>
                  {result.score === result.total
                    ? `Perfetto! ${result.score} su ${result.total}.`
                    : `${result.score} su ${result.total} posizioni corrette.`}
                </p>
              )}
            </div>

            {status === "revealed" && result && (
              <>
                <div className="order-solution">
                  <h3>La classifica reale</h3>
                  <ol>
                    {result.correct_order.map((row) => (
                      <li key={row.region_key}>
                        <span>{row.region}</span>
                        <strong>{formatValue(row.value, round.indicator.unit)}</strong>
                      </li>
                    ))}
                  </ol>
                </div>
                <button type="button" className="game-btn order-next" onClick={() => loadRound(count)}>
                  {result.score === result.total ? "Avanti" : "Ricomincia"}
                </button>
              </>
            )}
          </div>

          <aside className="order-side">
            <div className="card">
              <p className="order-side-eyebrow">Punteggio</p>
              <div className="order-score-grid">
                <div>
                  <small>Record</small>
                  <strong>{best}/{count}</strong>
                </div>
                <div>
                  <small>Serie perfetta</small>
                  <strong>{sessionBest}</strong>
                </div>
              </div>
            </div>
            <div className="card order-rules-card">
              <p className="order-side-eyebrow">Regole rapide</p>
              <ul>
                <li>+1 per ogni regione nella posizione esatta</li>
                <li>Punteggio massimo: {round.count}</li>
                <li>Nessuna penalità per un ordine sbagliato</li>
              </ul>
            </div>
          </aside>
        </div>
      )}

      {status === "loading" && !round && (
        <div aria-hidden="true">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 12, width: "55%" }} />
            <span style={{ height: 22, width: "70%" }} />
          </div>
          <div className="order-list" style={{ marginTop: 18 }}>
            {Array.from({ length: count }).map((_, i) => (
              <span key={i} className="skel-bar" style={{ height: 56 }} />
            ))}
          </div>
        </div>
      )}

      {showScoreModal && (
        <SubmitScoreModal
          mode="order"
          token={tokenRef.current}
          score={sessionBest}
          scoreLabel={`${sessionBest} round perfetti di fila`}
          onClose={() => setShowScoreModal(false)}
        />
      )}
    </div>
  );
}
