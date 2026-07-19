import React, { useEffect, useRef, useState } from "react";
import { fetchJson, formatValue, trackGameEvent, SourceStrip, SubmitScoreModal } from "./shared.jsx";

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
  const [sequence, setSequence] = useState([]); // region_key nell'ordine toccato
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
    setStatus("loading");
    setResult(null);
    setSequence([]);
    submittingRef.current = false;
    fetchJson(API.round(n, tokenRef.current))
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function toggleRegion(regionKey) {
    if (status !== "ordering") return;
    setSequence((prev) => {
      const idx = prev.indexOf(regionKey);
      if (idx >= 0) return prev.filter((key) => key !== regionKey);
      if (prev.length >= round.count) return prev;
      return [...prev, regionKey];
    });
  }

  function confirmOrder() {
    if (status !== "ordering" || sequence.length !== round.count || submittingRef.current) return;
    submittingRef.current = true;
    setStatus("loading");
    fetchJson(API.answer, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        indicator_id: round.indicator.id,
        year: round.indicator.year,
        region_keys: sequence,
        token: tokenRef.current,
      }),
    })
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
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
        <span className="order-best">Record: {best}/{count}</span>
        {sessionBest > 0 && <span className="order-best">Serie perfetta: {sessionBest}</span>}
        {sessionBest > 0 && (
          <button type="button" className="game-tab game-tab--ghost" onClick={() => setShowScoreModal(true)}>
            Entra in classifica
          </button>
        )}
      </div>

      {status === "idle" && (
        <div className="order-start">
          <h2>Ordina le regioni</h2>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Tocca in sequenza.</strong> Prima la regione che pensi abbia il valore più alto,
              poi la seconda e così via. Conta il numero, anche quando un valore alto non rappresenta
              un risultato migliore. Un secondo tocco toglie la regione dalla sequenza.
            </li>
            <li>
              <strong>Conferma quando l'ordine è completo.</strong> Vedrai la classifica reale con i
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
        <>
          <div className="qz-question">
            <small>Indicatore Istat · {round.indicator.year}</small>
            <h2>{round.indicator.name}</h2>
            <p className="desc">Tocca le regioni in ordine, dal valore più alto al più basso.</p>
            <SourceStrip
              year={round.indicator.year}
              sourceLabel={round.indicator.source_label}
              sourceUrl={round.indicator.source_url}
            />
          </div>

          <div className={`order-cards order-cards--${round.count}`}>
            {round.regions.map((region) => {
              const pos = sequence.indexOf(region.region_key);
              const revealed = status === "revealed" && resultBySide[region.region_key];
              let cls = "order-card";
              if (pos >= 0 && status === "ordering") cls += " is-picked";
              if (revealed) {
                cls += revealed.correct ? " is-correct" : " is-wrong";
              }
              return (
                <button
                  key={region.region_key}
                  type="button"
                  className={cls}
                  disabled={status !== "ordering"}
                  onClick={() => toggleRegion(region.region_key)}
                  aria-pressed={pos >= 0}
                >
                  {pos >= 0 && status === "ordering" && (
                    <span className="order-pos-badge">{pos + 1}</span>
                  )}
                  {revealed && (
                    <span className="order-pos-badge order-pos-badge--result">
                      {revealed.guessed_position}
                    </span>
                  )}
                  <strong className="order-region-name">{region.region}</strong>
                  {region.geo_area && <span className="order-region-macro">{region.geo_area}</span>}
                  {revealed && (
                    <span className="order-card-result">
                      <span className="order-value">{formatValue(revealed.value, round.indicator.unit)}</span>
                      <span className="order-verdict-line">
                        {revealed.correct
                          ? "posizione giusta"
                          : `era ${revealed.correct_position}ª`}
                      </span>
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {status === "ordering" && (
            <div className="order-actions">
              <button
                type="button"
                className="game-btn"
                disabled={sequence.length !== round.count}
                onClick={confirmOrder}
              >
                Conferma ordine
              </button>
              {sequence.length > 0 && (
                <button type="button" className="game-btn game-btn--ghost" onClick={() => setSequence([])}>
                  Svuota selezione
                </button>
              )}
              <span className="order-progress">
                {sequence.length} di {round.count} in sequenza
              </span>
            </div>
          )}

          {(round.indicator.description || round.indicator.value_explanation) && (
            <p className="quiz-description-compact">
              {[round.indicator.description, round.indicator.value_explanation].filter(Boolean).join(" ")}
            </p>
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
        </>
      )}

      {status === "loading" && !round && (
        <div aria-hidden="true">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 12, width: "55%" }} />
            <span style={{ height: 22, width: "70%" }} />
          </div>
          <div className={`order-cards order-cards--${count}`} style={{ marginTop: 18 }}>
            {Array.from({ length: count }).map((_, i) => (
              <span key={i} className="skel-bar" style={{ height: 96 }} />
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
