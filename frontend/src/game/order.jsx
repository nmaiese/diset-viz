import React, { useEffect, useRef, useState } from "react";
import { fetchJson, formatValue, trackGameEvent, SourceStrip, SubmitScoreModal } from "./shared.jsx";

const API = {
  round: (count, token) =>
    `/api/game/order/round?count=${count}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/order/answer",
};

const STORAGE_STATS_KEY = "di-order-stats";
const STORAGE_ONBOARDED_KEY = "di-order-onboarded";

// Altezza di una riga trascinabile (item + gap) usata per calcolare gli
// spostamenti del drag con posizionamento assoluto, come nel design QuizOrdina.
const ROW = 68;

function shuffle(list) {
  const arr = [...list];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

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
  const [sequence, setSequence] = useState([]); // region_key nell'ordine corrente (lista completa, riordinabile)
  const [drag, setDrag] = useState(null); // { i, dy } durante il trascinamento
  const dragStartY = useRef(0);
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
        // La lista parte gia' piena, in ordine casuale: si riordina trascinando.
        setSequence(shuffle(data.regions.map((region) => region.region_key)));
        setDrag(null);
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  // Sposta un elemento della sequenza da una posizione all'altra.
  function moveItem(from, to) {
    const clamped = Math.max(0, Math.min(sequence.length - 1, to));
    if (clamped === from) return;
    setSequence((prev) => {
      const arr = [...prev];
      const [moved] = arr.splice(from, 1);
      arr.splice(clamped, 0, moved);
      return arr;
    });
  }

  function onDragDown(event, i) {
    if (status !== "ordering") return;
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // setPointerCapture puo' fallire su alcuni browser: il drag funziona comunque.
    }
    dragStartY.current = event.clientY;
    setDrag({ i, dy: 0 });
  }

  function onDragMove(event) {
    if (!drag) return;
    setDrag((prev) => (prev ? { ...prev, dy: event.clientY - dragStartY.current } : prev));
  }

  function onDragUp() {
    if (!drag) return;
    const to = drag.i + Math.round(drag.dy / ROW);
    moveItem(drag.i, to);
    setDrag(null);
  }

  // Riordino da tastiera: frecce su/giu' sulla riga a fuoco.
  function onItemKeyDown(event, i) {
    if (status !== "ordering") return;
    if (event.key === "ArrowUp") {
      event.preventDefault();
      moveItem(i, i - 1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      moveItem(i, i + 1);
    }
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
  const regionByKey = round
    ? Object.fromEntries(round.regions.map((region) => [region.region_key, region]))
    : {};

  // Posizione verticale di ogni riga: durante il drag le righe non trascinate
  // scorrono per fare posto, la riga trascinata segue il dito.
  function itemOffset(i) {
    let y = i * ROW;
    if (drag) {
      if (drag.i === i) return y + drag.dy;
      const target = Math.max(0, Math.min(sequence.length - 1, drag.i + Math.round(drag.dy / ROW)));
      if (drag.i < i && i <= target) y -= ROW;
      else if (target <= i && i < drag.i) y += ROW;
    }
    return y;
  }

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

      <div className="qz-ordina-grid">
        <div className="qz-ordina-main">

      {status === "idle" && (
        <div className="order-start">
          <h2>Ordina le regioni</h2>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Trascina per riordinare.</strong> Tieni premuto su una regione e spostala in alto
              o in basso, dal valore più alto al più basso. Conta il numero, anche quando un valore alto
              non rappresenta un risultato migliore. Da tastiera usa le frecce su e giù.
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
        <>
          <div className="qz-question">
            <small>Indicatore Istat · {round.indicator.year}</small>
            <h2>{round.indicator.name}</h2>
            <p className="desc">Trascina dal valore più alto al più basso. Punti per ogni posizione giusta.</p>
            <SourceStrip
              year={round.indicator.year}
              sourceLabel={round.indicator.source_label}
              sourceUrl={round.indicator.source_url}
            />
          </div>

          <div
            className="qz-list"
            style={{ height: sequence.length * ROW - (ROW - 60) }}
          >
            {sequence.map((regionKey, i) => {
              const region = regionByKey[regionKey];
              if (!region) return null;
              const revealed = status === "revealed" && resultBySide[regionKey];
              const dragging = drag && drag.i === i;
              let cls = "qz-item";
              if (dragging) cls += " is-dragging";
              if (revealed) cls += revealed.correct ? " correct" : " wrong";
              return (
                <div
                  key={regionKey}
                  className={cls}
                  style={{
                    transform: `translateY(${itemOffset(i)}px)`,
                    transition: dragging ? "none" : "transform 0.16s ease",
                    zIndex: dragging ? 5 : 1,
                  }}
                  role="button"
                  tabIndex={status === "ordering" ? 0 : -1}
                  aria-label={`${i + 1}° posto: ${region.region}. Usa le frecce su e giù per spostare.`}
                  onPointerDown={status === "ordering" ? (e) => onDragDown(e, i) : undefined}
                  onPointerMove={status === "ordering" ? onDragMove : undefined}
                  onPointerUp={status === "ordering" ? onDragUp : undefined}
                  onPointerCancel={status === "ordering" ? onDragUp : undefined}
                  onKeyDown={(e) => onItemKeyDown(e, i)}
                >
                  <span className="qz-item-rank">{i + 1}</span>
                  <span className="qz-item-name">
                    {region.region}
                    {region.geo_area && <em>{region.geo_area}</em>}
                  </span>
                  <span className="qz-item-val">
                    {revealed ? formatValue(revealed.value, round.indicator.unit) : "nascosto"}
                  </span>
                  {status === "ordering" ? (
                    <span className="qz-item-handle" aria-hidden="true">⋮⋮</span>
                  ) : (
                    <span className="qz-item-verdict" aria-hidden="true">
                      {revealed && (revealed.correct ? "✓" : `${revealed.correct_position}ª`)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {status === "ordering" && (
            <div className="qz-actions">
              <button type="button" className="game-btn" onClick={confirmOrder}>
                Verifica ordine
              </button>
              <button
                type="button"
                className="game-btn game-btn--ghost"
                onClick={() => setSequence((prev) => shuffle(prev))}
              >
                Mischia
              </button>
              <button type="button" className="game-btn game-btn--ghost" onClick={() => loadRound(count)}>
                Salta round
              </button>
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
          <div className="qz-list-skel" style={{ marginTop: 18 }}>
            {Array.from({ length: count }).map((_, i) => (
              <span key={i} className="skel-bar" style={{ height: 60 }} />
            ))}
          </div>
        </div>
      )}
        </div>

        <aside className="qz-side qz-ordina-side">
          <div className="qz-side-card">
            <p className="eb">Punteggio</p>
            <div className="qz-score-grid">
              <div><small>Record 3 regioni</small><strong>{stats.bestScore3}/3</strong></div>
              <div><small>Record 5 regioni</small><strong>{stats.bestScore5}/5</strong></div>
              <div><small>Serie perfetta</small><strong className="pos">{sessionBest}</strong></div>
              <div><small>Livello</small><strong className="ink">{count} reg.</strong></div>
            </div>
          </div>
          <div className="qz-side-card qz-side-card--accent">
            <p className="eb">Regole rapide</p>
            <ul className="qz-rules">
              <li>1 punto per ogni regione al posto giusto</li>
              <li>Round perfetto: tutte le posizioni corrette</li>
              <li>Nessuna penalità per gli errori</li>
            </ul>
          </div>
        </aside>
      </div>

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
