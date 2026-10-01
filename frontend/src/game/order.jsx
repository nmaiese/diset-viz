import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  fetchJson,
  trackGameEvent,
  SourceStrip,
  SubmitScoreModal,
  prefersReducedMotion,
  postGame,
  notifyAchievements,
  FinePartita,
  SfidaCondivisa,
  useSfidaCondivisa,
  useTerritorioMio,
} from "./shared.jsx";
import { fraseTerritorioMio, trovaTerritorioMio } from "./puri.js";
import { oggiRoma, segnaGiocata } from "./oggi.js";
import {
  metaUnita,
  nomeTerritorio,
  percorsoTerritorio,
  righeEsito,
  segnoPosizione,
  tonoDaPunteggio,
  valoreConUnita,
} from "./order.puri.js";

const API = {
  round: (count, token) =>
    `/api/game/order/round?count=${count}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/order/answer",
};

const STORAGE_STATS_KEY = "di-order-stats";
const STORAGE_ONBOARDED_KEY = "di-order-onboarded";

// Il gioco dopo Ordina: e' quello che la scheda del giorno porta, e l'unico
// link che l'esito puo' promettere senza inventare.
const PROSSIMO_GIOCO = { label: "Prova Chi è maggiore?", href: "/quiz/chi-e-maggiore" };

const LIVELLI = [
  { id: "regioni", label: "Regioni", nome: "Regioni" },
  { id: "stessa_regione", label: "Stessa regione", nome: "territori della stessa regione" },
  { id: "province", label: "Province", nome: "Province" },
];

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
    // localStorage non disponibile
  }
}

// Il puntatore grossolano decide se la riga si trascina o si tocca due volte.
// La domanda non e' "lo schermo e' stretto": un tablet largo col dito resta
// touch, e li' la maniglia non c'e' da prendere.
function puntaGrossolana() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(pointer: coarse)").matches;
}

// La frase che il lettore di schermo sente alla fine: il numero di posizioni
// azzeccate, e nient'altro. Il tono lo dice il segno, qui la conta e basta.
function esitoParlato(score, total) {
  if (score >= total) return `Tutte le ${total} posizioni corrette.`;
  if (score <= 0) return `Nessuna posizione corretta: l'ordine giusto è qui sotto.`;
  return `${score} posizioni corrette su ${total}.`;
}

export default function OrderApp() {
  const [mode, setMode] = useState("daily"); // daily | practice
  const [level, setLevel] = useState("regioni"); // regioni | stessa_regione | province
  const [count, setCount] = useState(3); // 3 | 5 per allenamento
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | ordering | revealed | error
  const [orderKeys, setOrderKeys] = useState([]);
  const [dragIndex, setDragIndex] = useState(null);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(loadStats);
  const [sessionBest, setSessionBest] = useState(0);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [started, setStarted] = useState(false);
  const [avviata, setAvviata] = useState(false);
  const [coarse, setCoarse] = useState(puntaGrossolana);
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
  const righeRef = useRef(new Map());
  const flipRef = useRef(null);

  const mio = useTerritorioMio();
  const sfida = useSfidaCondivisa({ game: "order", numeroOggi: round?.number, avviata });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    const query = window.matchMedia("(pointer: coarse)");
    const aggiorna = () => setCoarse(query.matches);
    aggiorna();
    if (typeof query.addEventListener === "function") {
      query.addEventListener("change", aggiorna);
      return () => query.removeEventListener("change", aggiorna);
    }
    query.addListener(aggiorna);
    return () => query.removeListener(aggiorna);
  }, []);

  useEffect(() => {
    if (!started) return;
    trackGameEvent("order_start", { game: "order", mode, level, count: mode === "daily" ? 5 : count });
    if (mode === "daily") {
      loadDailySession(level);
    } else {
      loadPracticeRound(count);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, level, count, started]);

  // FLIP: la foto delle righe prima di spostarle, e la transizione indietro alla
  // fine. Senza, la riga spostata "salta" e non si capisce da dove arriva. Fuori
  // da `no-preference` la riga e' gia' nel posto giusto e non si muove: qui non
  // si mette nessuna animazione, solo il rimesso a posto del `transform`.
  useLayoutEffect(() => {
    const scatto = flipRef.current;
    if (!scatto) return undefined;
    flipRef.current = null;
    if (typeof window === "undefined" || prefersReducedMotion()) return undefined;
    const mosse = [];
    for (const [chiave, nodo] of righeRef.current) {
      if (!nodo) continue;
      const prima = scatto.prima.get(chiave);
      if (prima === undefined) continue;
      const spostamento = prima - nodo.getBoundingClientRect().top;
      if (!spostamento) continue;
      nodo.style.transition = "none";
      nodo.style.transform = `translateY(${spostamento}px)`;
      mosse.push(nodo);
    }
    if (!mosse.length) return undefined;
    const frame = window.requestAnimationFrame(() => {
      for (const nodo of mosse) {
        nodo.style.transition = "";
        nodo.style.transform = "";
      }
    });
    return () => window.cancelAnimationFrame(frame);
  });

  function territori() {
    return round?.territories || round?.regions || [];
  }

  function mappaTerritori() {
    const mappa = {};
    for (const territorio of territori()) {
      const chiave = territorio.key || territorio.region_key;
      if (chiave) mappa[chiave] = territorio;
    }
    return mappa;
  }

  // Le posizioni delle righe come sono adesso sullo schermo: il punto da cui
  // una riga parte, per poterla far tornare indietto con una transizione.
  function scattaPosizioni() {
    const scatto = new Map();
    for (const [chiave, nodo] of righeRef.current) {
      if (nodo) scatto.set(chiave, nodo.getBoundingClientRect().top);
    }
    return scatto;
  }

  function scrolledToGameArea() {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  }

  function startGame() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // localStorage non disponibile
    }
    setStarted(true);
  }

  function loadDailySession(lvl) {
    scrolledToGameArea();
    setStatus("loading");
    setResult(null);
    setDragIndex(null);
    setSelectedIdx(null);
    submittingRef.current = false;
    fetchJson(`/api/game/order/daily/session?level=${encodeURIComponent(lvl)}${tokenRef.current ? `&token=${encodeURIComponent(tokenRef.current)}` : ""}`)
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setOrderKeys((data.territories || []).map((t) => t.key));
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function loadPracticeRound(n) {
    scrolledToGameArea();
    setStatus("loading");
    setResult(null);
    setDragIndex(null);
    setSelectedIdx(null);
    submittingRef.current = false;
    fetchJson(API.round(n, tokenRef.current))
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setOrderKeys((data.regions || []).map((r) => r.region_key));
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function reloadCurrent() {
    if (mode === "daily") {
      loadDailySession(level);
    } else {
      loadPracticeRound(count);
    }
  }

  // Un solo modo per spostare una riga: tocco due volte, freccia o trascinamento
  // finiscono qui, e quindi nella stessa animazione e nello stesso annuncio.
  function spostaDa(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0) return;
    if (fromIdx >= orderKeys.length || toIdx >= orderKeys.length) return;
    const nome = nomeTerritorio(mappaTerritori()[orderKeys[fromIdx]]);
    flipRef.current = { prima: scattaPosizioni() };
    setOrderKeys((precedenti) => {
      const prossime = [...precedenti];
      const [mossa] = prossime.splice(fromIdx, 1);
      prossime.splice(toIdx, 0, mossa);
      return prossime;
    });
    setAnnouncement(`${nome || "Elemento"} spostato in posizione ${toIdx + 1}.`);
  }

  function handleRowClick(idx) {
    if (status !== "ordering") return;
    const nome = nomeTerritorio(mappaTerritori()[orderKeys[idx]]);
    if (selectedIdx === null) {
      setSelectedIdx(idx);
      setAnnouncement(`${nome || "Elemento"} in posizione ${idx + 1}. Dove la metti? Tocca la posizione di destinazione.`);
    } else if (selectedIdx === idx) {
      setSelectedIdx(null);
      setAnnouncement("Selezione annullata.");
    } else {
      spostaDa(selectedIdx, idx);
      setSelectedIdx(null);
    }
  }

  function moveItem(index, direction, event) {
    if (event) event.stopPropagation();
    if (status !== "ordering") return;
    spostaDa(index, index + direction);
  }

  function shuffleOrder() {
    if (status !== "ordering") return;
    flipRef.current = { prima: scattaPosizioni() };
    setOrderKeys((precedenti) => {
      const prossime = [...precedenti];
      for (let i = prossime.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [prossime[i], prossime[j]] = [prossime[j], prossime[i]];
      }
      return prossime;
    });
    setSelectedIdx(null);
    setAnnouncement("Ordine mescolato.");
  }

  function handleDragStart(index) {
    if (status !== "ordering") return;
    setDragIndex(index);
  }

  function handleDragOver(event) {
    if (status !== "ordering") return;
    event.preventDefault();
  }

  function handleDrop(index) {
    if (status !== "ordering" || dragIndex === null) {
      setDragIndex(null);
      return;
    }
    spostaDa(dragIndex, index);
    setDragIndex(null);
  }

  function confermaOrdine() {
    const atteso = mode === "daily" ? 5 : round?.count;
    if (status !== "ordering" || orderKeys.length !== atteso || submittingRef.current) return;
    submittingRef.current = true;
    setAvviata(true);
    setStatus("loading");

    const isDaily = mode === "daily";
    const url = isDaily ? "/api/game/order/daily/answer" : API.answer;
    const body = isDaily
      ? { level, region_keys: orderKeys, token: tokenRef.current }
      : {
          indicator_id: round.indicator.id,
          year: round.indicator.year,
          region_keys: orderKeys,
          token: tokenRef.current,
        };

    postGame(url, body)
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
        notifyAchievements(data.achievements);
        setAnnouncement(esitoParlato(data.score, data.total));
        setStats((prev) => {
          const currentCount = isDaily ? 5 : round.count;
          const bestKey = currentCount === 3 ? "bestScore3" : "bestScore5";
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
          if (!isDaily && !isPerfect && data.session.best > promptedBestRef.current && data.session.best >= 2) {
            promptedBestRef.current = data.session.best;
            setShowScoreModal(true);
          }
        }
        trackGameEvent("order_answer", { game: "order", mode, level, score: data.score, total: data.total });
        if (isDaily) segnaGiocata("order", oggiRoma(), { ok: data.score > 0, tono: data.score === data.total ? "giusto" : data.score === 0 ? "sbagliato" : "parziale", testo: `${data.score} su ${data.total} al posto giusto` });
      })
      .catch(() => {
        submittingRef.current = false;
        setStatus("error");
      });
  }

  function passaAllAllenamento() {
    setMode("practice");
    setCount(5);
  }

  const currentCount = mode === "daily" ? 5 : count;
  const best = currentCount === 3 ? stats.bestScore3 : stats.bestScore5;
  const indicatore = round?.indicator || {};
  const listaTerritori = territori();
  const resultBySide = result
    ? Object.fromEntries((result.positions || []).map((p) => [p.region_key, p]))
    : {};
  const indicatoreEsito = result?.indicator || {};
  const unitaEsito = indicatoreEsito.unit || indicatore.unit || "";
  const esito = status === "revealed" && result ? result : null;
  const righe = esito ? righeEsito(result.positions, result.correct_order, unitaEsito) : [];
  const mioNellaPartita = trovaTerritorioMio(
    mio,
    listaTerritori.map((t) => ({ ...t, key: t.key || t.region_key }))
  );
  const tono = esito ? tonoDaPunteggio(esito.score, esito.total) : "nullo";
  const perfetto = esito ? esito.score >= esito.total : false;
  const schede = new Map(
    listaTerritori
      .map((t) => [t.key || t.region_key, percorsoTerritorio(t)])
      .filter(([chiave, percorso]) => chiave && percorso)
  );

  return (
    <div className="order-app">
      <div className="visually-hidden" aria-live="polite">
        {announcement}
      </div>

      <SfidaCondivisa sfida={sfida} game="order" avviata={avviata} />

      <div className="order-toolbar">
        <div className="order-modes" role="group" aria-label="Modalità di gioco">
          <button
            type="button"
            aria-pressed={mode === "daily"}
            aria-label="Sfida del giorno"
            className={mode === "daily" ? "game-tab is-active" : "game-tab"}
            onClick={() => setMode("daily")}
          >
            Sfida del giorno
          </button>
          <button
            type="button"
            aria-pressed={mode === "practice"}
            aria-label="Allenamento libero"
            className={mode === "practice" ? "game-tab is-active" : "game-tab"}
            onClick={() => setMode("practice")}
          >
            Allenamento
          </button>
        </div>

        {mode === "daily" ? (
          <div className="order-counts" role="group" aria-label="Livello della sfida del giorno">
            {LIVELLI.map((lvl) => (
              <button
                key={lvl.id}
                type="button"
                aria-pressed={level === lvl.id}
                aria-label={`Sfida del giorno, ${lvl.nome}`}
                className={level === lvl.id ? "game-tab is-active" : "game-tab"}
                onClick={() => setLevel(lvl.id)}
              >
                {lvl.label}
              </button>
            ))}
          </div>
        ) : (
          <div className="order-counts" role="group" aria-label="Quanti territori ordinare">
            {[3, 5].map((n) => (
              <button
                key={n}
                type="button"
                aria-pressed={count === n}
                aria-label={`Allenamento con ${n} territori`}
                className={count === n ? "game-tab is-active" : "game-tab"}
                onClick={() => setCount(n)}
              >
                {n} territori
              </button>
            ))}
          </div>
        )}

        {mode === "practice" && sessionBest > 0 && (
          <button
            type="button"
            className="game-tab game-tab--ghost order-classifica-btn"
            onClick={() => setShowScoreModal(true)}
          >
            Entra in classifica
          </button>
        )}
      </div>

      {status === "idle" && (
        <div className="order-start">
          <p className="order-start-gesto">
            {coarse ? "Tocca un territorio, poi tocca dove metterlo." : "Trascina la maniglia, tocca due volte, o usa le frecce."}
          </p>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Ordina dal valore più alto al più basso.</strong> Non dal risultato migliore al peggiore.
            </li>
            <li>
              <strong>Verifica quando l'ordine ti convince.</strong> Vedi la classifica vera, riga per riga, con i valori e la fonte.
            </li>
            <li>
              <strong>Un punto per ogni posizione azzeccata.</strong> La sfida del giorno è uguale per tutti, l'allenamento è libero.
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
          <button type="button" className="game-btn" onClick={reloadCurrent}>
            Riprova
          </button>
        </div>
      )}

      {round && status !== "error" && (
        <div className="order-layout">
          <div className="order-main">
            {esito ? (
              <div className="order-esito">
                <FinePartita
                  game="order"
                  won={perfetto}
                  tono={tono}
                  titolo={`${esito.score} su ${esito.total} posizioni corrette`}
                  dettaglio={
                    mode === "daily"
                      ? (round.number ? `Sfida del giorno n. ${round.number}` : "")
                      : `Allenamento · ${righe.length} territori`
                  }
                  fatto={esito.fatto}
                  sfida={sfida ? { punteggio: sfida.punteggio, tuo: esito.score, game: "order" } : null}
                  nextPuzzleAt={mode === "daily" ? round.next_puzzle_at : undefined}
                  condividi={
                    mode === "daily" && round.number
                      ? {
                          gameName: "Ordina le regioni",
                          punteggio: esito.score,
                          puzzleNumber: round.number,
                          esiti: orderKeys.map((chiave) => (resultBySide[chiave]?.correct ? "exact" : "miss")),
                          summary: `${esito.score} su ${esito.total}`,
                          url: typeof window !== "undefined" ? window.location.href : "",
                          eventParams: { level },
                        }
                      : null
                  }
                  onPlayAgain={
                    mode === "daily" ? (perfetto ? undefined : passaAllAllenamento) : () => loadPracticeRound(count)
                  }
                  playAgainLabel={mode === "daily" ? "Allenati con altre regioni" : "Avanti"}
                  prossimo={mode === "daily" && perfetto ? PROSSIMO_GIOCO : undefined}
                />

                <section className="order-quadro">
                  <h3 className="order-quadro-titolo">Che cosa hai ordinato</h3>
                  <p className="order-quadro-riga">
                    <strong>{indicatoreEsito.name || indicatore.name}</strong>
                    {unitaEsito && ` · ${unitaEsito}`}
                    {indicatoreEsito.year || indicatore.year ? ` · anno ${indicatoreEsito.year || indicatore.year}` : ""}
                  </p>
                  <SourceStrip
                    year={indicatoreEsito.year || indicatore.year}
                    sourceLabel={indicatoreEsito.source_label || indicatore.source_label}
                    sourceUrl={indicatoreEsito.source_url || indicatore.source_url}
                    game="order"
                  />
                  {(indicatoreEsito.description || indicatore.description) && (
                    <p className="order-quadro-descrizione">{indicatoreEsito.description || indicatore.description}</p>
                  )}
                  {(indicatoreEsito.path || indicatore.path) && (
                    <p className="order-quadro-scheda">
                      <a href={indicatoreEsito.path || indicatore.path}>Apri la scheda dell'indicatore</a>
                    </p>
                  )}
                </section>

                <section className="order-quadro">
                  <h3 className="order-quadro-titolo">L'ordine giusto, riga per riga</h3>
                  <ol className="order-classifica">
                    {righe.map((riga, indice) => {
                      const segno = segnoPosizione(riga);
                      const mioEdE = !!mioNellaPartita && (mioNellaPartita.key || mioNellaPartita.region_key) === riga.chiave;
                      const percorso = schede.get(riga.chiave) || null;
                      return (
                        <li
                          key={riga.chiave}
                          className={`order-classifica-riga ${riga.esatta ? "is-correct" : "is-wrong"}${mioEdE ? " is-mio" : ""}`}
                          style={{ "--order-riga": indice }}
                        >
                          <span className="order-rank" aria-label={`Posizione ${riga.posizione}`}>{riga.posizione}</span>
                          <span className="order-classifica-nome">
                            {percorso ? <a href={percorso}>{riga.nome}</a> : riga.nome}
                            {mioEdE && <span className="order-mio-tag">il tuo territorio</span>}
                          </span>
                          <span className="order-classifica-valore">{valoreConUnita(riga.valore, riga.unita)}</span>
                          <span className="order-segno">
                            <span aria-hidden="true">{segno.glifo}</span> {segno.testo}
                          </span>
                        </li>
                      );
                    })}
                  </ol>
                </section>

                {mioNellaPartita && (
                  <p className="order-territorio-mio">{fraseTerritorioMio(nomeTerritorio(mioNellaPartita))}</p>
                )}
              </div>
            ) : (
              <>
                <div className="order-question">
                  <span className="order-kicker">
                    {mode === "daily"
                      ? (round.number ? `Sfida del giorno n. ${round.number}` : "Sfida del giorno")
                      : `Allenamento · ${round.count || count} territori`}
                  </span>
                  <h2>{indicatore.name}</h2>
                  <p className="order-meta">
                    {metaUnita([indicatore.macro_area, indicatore.theme, indicatore.unit])}
                  </p>
                  <SourceStrip
                    year={indicatore.year}
                    sourceLabel={indicatore.source_label}
                    sourceUrl={indicatore.source_url}
                    game="order"
                  />
                  <p className="order-regola">Ordina dal valore più alto al più basso.</p>
                  {(indicatore.description || indicatore.value_explanation) && (
                    <details className="order-altro">
                      <summary>Che cosa misura</summary>
                      <div className="quiz-explanation">
                        {indicatore.description && (
                          <p className="quiz-description">
                            <strong>Che cosa misura.</strong> {indicatore.description}
                          </p>
                        )}
                        {indicatore.value_explanation && (
                          <p className="quiz-value-hint">
                            <strong>Come leggere il valore.</strong> {indicatore.value_explanation}
                          </p>
                        )}
                      </div>
                    </details>
                  )}
                </div>

                <p className="order-suggerimento">
                  {selectedIdx !== null
                    ? "Dove la metti? Tocca la posizione di destinazione."
                    : coarse
                      ? "Tocca un territorio, poi tocca dove metterlo."
                      : "Trascina la maniglia o tocca due volte. Le frecce spostano una riga alla volta."}
                </p>

                <div className="order-list" role="list" aria-label="Territori da ordinare">
                  {orderKeys.map((chiave, idx) => {
                    const territorio = mappaTerritori()[chiave];
                    if (!territorio) return null;
                    let cls = "order-row";
                    if (status === "ordering") cls += " is-draggable";
                    if (dragIndex === idx) cls += " is-dragging";
                    if (selectedIdx === idx) cls += " is-selected";
                    const mioEdE =
                      !!mioNellaPartita && (mioNellaPartita.key || mioNellaPartita.region_key) === chiave;
                    if (mioEdE) cls += " is-mio";

                    const nome = nomeTerritorio(territorio);
                    const nomeRegione =
                      territorio.region && territorio.name && territorio.name !== territorio.region ? territorio.region : null;

                    return (
                      <div
                        key={chiave}
                        ref={(nodo) => {
                          if (nodo) righeRef.current.set(chiave, nodo);
                          else righeRef.current.delete(chiave);
                        }}
                        tabIndex={status === "ordering" ? 0 : -1}
                        role="listitem"
                        className={cls}
                        draggable={status === "ordering"}
                        onClick={() => handleRowClick(idx)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleRowClick(idx);
                          }
                        }}
                        onDragStart={() => handleDragStart(idx)}
                        onDragOver={handleDragOver}
                        onDrop={() => handleDrop(idx)}
                        onDragEnd={() => setDragIndex(null)}
                      >
                        <span className="order-rank" aria-label={`Posizione ${idx + 1} di ${orderKeys.length}`}>{idx + 1}</span>
                        <div className="order-row-testo">
                          <span className="order-row-name-riga">
                            <strong className="order-row-name">{nome}</strong>
                            {mioEdE && <span className="order-row-mio">il tuo territorio</span>}
                          </span>
                          {nomeRegione && <span className="order-row-region">{nomeRegione}</span>}
                        </div>
                        <div className="order-row-coda">
                          {status === "ordering" && (
                            <>
                              <span className="order-row-nascosto">nascosto</span>
                              <span className="order-row-controls">
                                <button
                                  type="button"
                                  className="order-move-btn"
                                  aria-label={`Sposta ${nome} più in alto`}
                                  disabled={idx === 0}
                                  onClick={(e) => moveItem(idx, -1, e)}
                                >
                                  ▲
                                </button>
                                <button
                                  type="button"
                                  className="order-move-btn"
                                  aria-label={`Sposta ${nome} più in basso`}
                                  disabled={idx === orderKeys.length - 1}
                                  onClick={(e) => moveItem(idx, 1, e)}
                                >
                                  ▼
                                </button>
                                <span className="order-handle" aria-hidden="true">⋮⋮</span>
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {status === "ordering" && (
                  <div className="order-actions">
                    <button type="button" className="game-btn" onClick={confermaOrdine}>
                      Verifica ordine
                    </button>
                    <button type="button" className="game-btn game-btn--ghost" onClick={shuffleOrder}>
                      Mischia
                    </button>
                    {mode === "practice" && (
                      <button type="button" className="game-btn game-btn--ghost" onClick={() => loadPracticeRound(count)}>
                        Salta round
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <aside className="order-side">
            <div className="card">
              <p className="order-side-eyebrow">Punteggio</p>
              <div className="order-score-grid">
                <div>
                  <small>Record</small>
                  <strong>{best}/{currentCount}</strong>
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
                <li>+1 per ogni territorio nella posizione esatta</li>
                <li>Punteggio massimo: {currentCount}</li>
                <li>{coarse ? "Tocca la riga, poi tocca la destinazione" : "Trascina, tocca due volte o usa le frecce"}</li>
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
            {Array.from({ length: currentCount }).map((_, i) => (
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
