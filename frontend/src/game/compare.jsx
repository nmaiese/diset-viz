import React, { useEffect, useRef, useState } from "react";
import { getAccessToken } from "../shared/supabase.js";
import { segnaGiocata } from "./oggi.js";
import {
  fetchJson,
  formatValue,
  trackGameEvent,
  SourceStrip,
  SubmitScoreModal,
  prefersReducedMotion,
  postGame,
  notifyAchievements,
  FinePartita,
} from "./shared.jsx";

const API = {
  round: (difficulty, token, timer) =>
    `/api/game/compare/round?difficulty=${difficulty}&timer=${timer ? 1 : 0}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/compare/answer",
  dailySession: (level, timer) =>
    `/api/game/compare/daily/session?level=${encodeURIComponent(level)}&timer=${timer ? 1 : 0}`,
  dailyAnswer: "/api/game/compare/daily/answer",
};

const STORAGE_STATS_KEY = "di-compare-stats";
const STORAGE_ONBOARDED_KEY = "di-compare-onboarded";
const ROUND_MS = 10000;
const TICK_MS = 100;

// I tre livelli della sfida del giorno. Il server li accetta tutti e li porta
// dentro il token firmato: qui si sceglie il livello, non si sceglie la coppia.
const LIVELLI = [
  { id: "regioni", label: "Regioni", aiuto: "Due regioni italiane, sugli indicatori disponibili per tutte." },
  { id: "stessa_regione", label: "Stessa regione", aiuto: "Due province della regione scelta per quel giorno." },
  { id: "province", label: "Province", aiuto: "Due province qualsiasi d'Italia." },
];

// Senza timer la partita è allenamento: si gioca lo stesso, ma non entra in
// classifica e non finisce fra i record del giorno. Il testo è quello che il
// server rimanda come avviso (`notice`), detto anche qui prima di iniziare.
const NOTA_ALLENAMENTO =
  "Senza timer è allenamento: la partita non va in classifica.";

// Gli errori della sfida del giorno hanno tutti un nome. Quelli che capitano per
// un doppio invio (click e scadenza insieme) si ignorano in silenzio: non sono un
// errore di chi gioca e non devono interrompere la partita.
const ERRORI_SFIDA = {
  round_already_answered: "",
  token_invalid: "",
  puzzle_changed: "La sfida del giorno è cambiata mentre giocavi. Riapri la partita.",
  late: "Il tempo è scaduto: la risposta è troppo tardi.",
  timeout_too_early: "Il tempo non era ancora scaduto.",
  rate_limited: "Troppe risposte in poco tempo. Riprova fra un minuto.",
  training_session: NOTA_ALLENAMENTO,
  bad_request: "Risposta non valida.",
};

// Errori che si possono riprovare subito sulla stessa coppia: il server non ha
// consumato il round. Tutti gli altri lo bloccano, e l'unica strada è riaprire
// la sfida, quindi non ripartono neanche il cronometro (un timeout a cronometro
// fermo ripeterebbe la stessa richiesta per sempre).
const ERRORI_RIPROVABILI = new Set(["timeout_too_early", "rate_limited"]);

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

// POST che non butta via il corpo degli errori: la sfida del giorno ha nomi di
// errore che il client deve poter distinguere (`late` da `round_already_answered`)
// e `postGame` solleva un'eccezione che non porta con sé la risposta. Stessi
// header di `postGame`: con un account il server attribuisce statistiche e
// achievement, senza resta anonimo.
async function postSfida(url, body) {
  let auth = {};
  try {
    const token = await getAccessToken();
    if (token) auth = { Authorization: `Bearer ${token}` };
  } catch {
    // Nessuna sessione: gioco anonimo, nessun header.
  }
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: {} };
  }
}

function dataInItaliano(iso) {
  if (!iso) return "";
  const giorno = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(giorno.getTime())) return "";
  return giorno.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

// Link alla stessa pagina al livello con cui si è giocato: chi riceve il
// risultato ritrova la sfida dello stesso livello.
function urlDelLivello(livello) {
  if (typeof window === "undefined") return undefined;
  return `${window.location.origin}${window.location.pathname}?level=${encodeURIComponent(livello)}`;
}

function livelloDaUrl() {
  if (typeof window === "undefined") return "regioni";
  const scelto = new URLSearchParams(window.location.search).get("level");
  return LIVELLI.some((l) => l.id === scelto) ? scelto : "regioni";
}

// "Che cosa misura" più il link alla scheda dell'indicatore: la parte che
// spiega il numero, non il colore della risposta.
//
// I link alle schede dei territori non compaiono qui ma solo dopo la risposta:
// la scheda di un territorio contiene il suo valore e aprirla prima
// spoilererebbe la coppia.
function SchedaIndicatore({ indicatore }) {
  return (
    <div className="qz-scheda">
      <p className="qz-scheda-indicatore">
        <strong>{indicatore.name}</strong>
        {indicatore.year ? ` · ${indicatore.year}` : ""}
        {indicatore.path ? (
          <>
            {" "}
            <a href={indicatore.path}>Apri la scheda dell&apos;indicatore</a>
          </>
        ) : null}
      </p>
      {indicatore.description && (
        <>
          <p className="qz-scheda-misura">Che cosa misura</p>
          <p className="desc">{indicatore.description}</p>
        </>
      )}
      <SourceStrip
        year={indicatore.year}
        sourceLabel={indicatore.source_label}
        sourceUrl={indicatore.source_url}
      />
    </div>
  );
}

// Il riepilogo delle dieci coppie a fine partita: cosa hai risposto, cosa era
// giusto e che cosa misura ogni indicatore. È la parte che la partita lascia a
// chi la finisce, insieme al link alla sfida di domani.
function Riepilogo({ domande, risposte }) {
  return (
    <section className="qz-riepilogo" aria-labelledby="qz-riepilogo-titolo">
      <h3 id="qz-riepilogo-titolo">Le dieci coppie</h3>
      <ol className="qz-riepilogo-lista">
        {risposte.map((risposta, indice) => {
          const domanda = domande[indice] || {};
          const lato = risposta.winner;
          return (
            <li key={indice} className={risposta.correct ? "is-correct" : "is-wrong"}>
              <p className="qz-riepilogo-riga">
                <span aria-hidden="true">{risposta.correct ? "✓" : "✗"}</span>{" "}
                <span className="visually-hidden">{risposta.correct ? "Giusta. " : "Sbagliata. "}</span>
                <span className="qz-riepilogo-indicatore">{domanda.indicator ? domanda.indicator.name : ""}</span>
              </p>
              <p className="qz-riepilogo-valori">
                <strong>{risposta[lato].name}</strong> {formatValue(risposta[lato].value, risposta.indicator.unit)}
                {" · "}
                {risposta[lato === "a" ? "b" : "a"].name}{" "}
                {formatValue(risposta[lato === "a" ? "b" : "a"].value, risposta.indicator.unit)}
              </p>
              <SchedaIndicatore indicatore={risposta.indicator} />
            </li>
          );
        })}
      </ol>
    </section>
  );
}

// La sfida del giorno: dieci coppie, le stesse per tutti, valutate dal server.
function SfidaDelGiorno({ livello, timer, onEsci }) {
  const [sessione, setSessione] = useState(null);
  // caricamento | domanda | invio | rivelata | fine | errore
  const [stato, setStato] = useState("caricamento");
  const [indice, setIndice] = useState(0);
  const [risposta, setRisposta] = useState(null);
  const [risposte, setRisposte] = useState([]);
  const [messaggio, setMessaggio] = useState("");
  const [scaduta, setScaduta] = useState(false);
  const [timeLeft, setTimeLeft] = useState(ROUND_MS);

  const statoRef = useRef({ stato: "domanda", indice: 0 });
  const timerRef = useRef(null);
  const tokenRef = useRef(null);

  useEffect(() => {
    statoRef.current = { stato, indice };
  }, [stato, indice]);

  useEffect(() => {
    return () => {
      window.clearInterval(timerRef.current);
    };
  }, []);

  // Il tempo lo scandisce il client per far avanzare la barra, ma la validita'
  // della risposta la decide il server (vedi `round_timing`): il client puo'
  // sbagliare il conto, non puo' far valere una risposta fuori tempo.
  useEffect(() => {
    if (!timer || stato !== "domanda") return undefined;
    timerRef.current = window.setInterval(() => {
      setTimeLeft((prev) => {
        const next = prev - TICK_MS;
        if (next <= 0) {
          window.clearInterval(timerRef.current);
          rispondi("timeout");
          return 0;
        }
        return next;
      });
    }, TICK_MS);
    return () => window.clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stato, indice, timer]);

  useEffect(() => {
    apri();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Stesse frecce e stessi tasti del round a serie, per chi gioca da tastiera.
  useEffect(() => {
    function onKeyDown(event) {
      if (statoRef.current.stato !== "domanda") return;
      const key = event.key.toLowerCase();
      if (key === "arrowleft" || key === "a") {
        event.preventDefault();
        rispondi("region_a");
      } else if (key === "arrowright" || key === "b") {
        event.preventDefault();
        rispondi("region_b");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function apri() {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    setStato("caricamento");
    setScaduta(false);
    setMessaggio("");
    fetchJson(API.dailySession(livello, timer))
      .then((data) => {
        tokenRef.current = data.token;
        setSessione(data);
        setIndice(0);
        setRisposta(null);
        setRisposte([]);
        setTimeLeft(ROUND_MS);
        setStato("domanda");
        trackGameEvent("compare_start", { level: livello, mode: "sfida", total: data.total });
      })
      .catch(() => setStato("errore"));
  }

  function rispondi(scelta) {
    const { stato: attuale, indice: domanda } = statoRef.current;
    if (attuale !== "domanda" || !sessione) return;
    window.clearInterval(timerRef.current);
    setStato("invio");
    setMessaggio("");
    postSfida(API.dailyAnswer, {
      puzzle_id: sessione.puzzle_id,
      q: domanda,
      choice: scelta,
      token: tokenRef.current,
    }).then(({ ok, status, data }) => {
      if (ok) {
        tokenRef.current = data.token;
        setRisposta(data);
        setRisposte((precedenti) => [...precedenti, data]);
        setStato(data.finished ? "fine" : "rivelata");
        trackGameEvent("compare_answer", {
          result: data.correct ? "correct" : scelta === "timeout" ? "timeout" : "wrong",
          streak: data.score ? data.score.correct : 0,
          difficulty: sessione.difficulty,
          level: livello,
          mode: "sfida",
        });
        notifyAchievements(data.achievements);
        return;
      }
      // Un doppio invio della stessa coppia è un 409 e un token già usato è un
      // 400 `token_invalid`: in entrambi i casi il primo invio ha già fatto
      // testo, quindi si torna alla domanda senza dire nulla a chi gioca.
      if (status === 409 || data.error === "token_invalid") {
        setStato("domanda");
        return;
      }
      setMessaggio(ERRORI_SFIDA[data.error] || "Qualcosa non ha funzionato. Riprova.");
      if (ERRORI_RIPROVABILI.has(data.error)) {
        setStato("domanda");
        return;
      }
      setStato("bloccata");
      setScaduta(true);
    });
  }

  function avanti() {
    setIndice((i) => i + 1);
    setRisposta(null);
    setTimeLeft(ROUND_MS);
    setStato("domanda");
  }

  const domanda = sessione ? sessione.questions[indice] : null;
  const punteggio = risposta && risposta.score ? risposta.score : { correct: 0, total: 10 };
  const allenamento = sessione ? !sessione.leaderboard : false;
  const timerPct = Math.max(0, (timeLeft / ROUND_MS) * 100);
  const isLowTime = stato === "domanda" && timer && timeLeft <= 3000;
  const rivelata = stato === "rivelata" || stato === "fine";

  function latoClass(lato) {
    let cls = "qz-region";
    if (!rivelata || !risposta) return cls;
    if (risposta.winner === lato) cls += " is-revealed is-winner";
    else cls += " is-revealed";
    if (risposta.choice === lato && !risposta.correct) cls += " is-picked-wrong";
    return cls;
  }

  const fine = stato === "fine" && risposta && risposta.summary;

  // L'hub sa che oggi hai giocato (solo la sfida in classifica, non l'allenamento).
  useEffect(() => {
    if (!fine || allenamento) return;
    segnaGiocata("compare", fine.date, {
      ok: fine.score.correct * 2 > fine.score.total,
      testo: `${fine.score.correct} su ${fine.score.total}`,
    });
  }, [fine, allenamento]);

  return (
    <div className="compare-app">
      <div className="qz-status">
        <span className="qz-badge">
          Sfida <strong>{sessione ? sessione.number : "-"}</strong>
        </span>
        <span className="qz-badge">
          Coppia <strong>{indice + 1}</strong> di <strong>{sessione ? sessione.total : 10}</strong>
        </span>
        <span className="qz-badge">
          Giuste <strong>{punteggio.correct}</strong>
        </span>
        <span className="qz-badge qz-badge--level">{sessione ? sessione.level_label : ""}</span>
        {timer && (
          <div className="qz-timer">
            <span className={isLowTime ? "qz-clock is-low" : "qz-clock"}>{formatClock(timeLeft)}</span>
            <span className="qz-timer-bar">
              <i className={stato === "domanda" ? "" : "is-paused"} style={{ width: `${timerPct}%` }} />
            </span>
          </div>
        )}
      </div>

      {allenamento && <p className="compare-notice">{NOTA_ALLENAMENTO}</p>}

      {stato === "errore" && (
        <div className="compare-status">
          <p className="game-error">Non sono riuscito ad aprire la sfida del giorno. Riprova.</p>
          <button type="button" className="game-btn" onClick={apri}>
            Riprova
          </button>
        </div>
      )}

      {stato === "caricamento" && !sessione && (
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

      {domanda && !fine && (
        <>
          <div className="qz-question">
            <small>
              {domanda.indicator.family ? `${domanda.indicator.family} · ` : ""}
              {domanda.indicator.year}
            </small>
            <h2>{domanda.indicator.name}</h2>
          </div>

          <div className="qz-vs">
            <button
              type="button"
              className={latoClass("a")}
              disabled={stato !== "domanda"}
              onClick={() => rispondi("region_a")}
            >
              <span className="code">A</span>
              <span className="name">{rivelata && risposta ? risposta.a.name : domanda.a.name}</span>
              {(rivelata && risposta ? risposta.a.region : domanda.a.region) && (
                <span className="macro">
                  {(rivelata && risposta ? risposta.a.region : domanda.a.region)}
                </span>
              )}
              {rivelata && risposta && (
                <span className="value">{formatValue(risposta.a.value, risposta.indicator.unit)}</span>
              )}
              {rivelata && risposta && risposta.winner === "a" && <span className="crown">maggiore</span>}
            </button>
            <div className="divider">VS</div>
            <button
              type="button"
              className={latoClass("b")}
              disabled={stato !== "domanda"}
              onClick={() => rispondi("region_b")}
            >
              <span className="code">B</span>
              <span className="name">{rivelata && risposta ? risposta.b.name : domanda.b.name}</span>
              {(rivelata && risposta ? risposta.b.region : domanda.b.region) && (
                <span className="macro">
                  {(rivelata && risposta ? risposta.b.region : domanda.b.region)}
                </span>
              )}
              {rivelata && risposta && (
                <span className="value">{formatValue(risposta.b.value, risposta.indicator.unit)}</span>
              )}
              {rivelata && risposta && risposta.winner === "b" && <span className="crown">maggiore</span>}
            </button>
          </div>

          <div className="compare-feedback" aria-live="polite">
            {messaggio && <p className="game-error">{messaggio}</p>}
            {scaduta && (
              <button type="button" className="game-btn" onClick={apri}>
                Riapri la sfida di oggi
              </button>
            )}
            {rivelata && risposta && (
              <>
                <p className={risposta.correct ? "compare-verdict is-correct" : "compare-verdict is-wrong"}>
                  <span aria-hidden="true">{risposta.correct ? "✓" : "✗"}</span>{" "}
                  <span className="visually-hidden">{risposta.correct ? "Giusto. " : "Sbagliato. "}</span>
                  {risposta.correct
                    ? "Giusto."
                    : risposta.choice === "timeout"
                    ? "Tempo scaduto."
                    : "Sbagliato."}{" "}
                  {risposta[risposta.winner].name} ha il valore più alto.
                </p>
                {risposta.notice === "training_session" && (
                  <p className="compare-notice">{NOTA_ALLENAMENTO}</p>
                )}
                <SchedaIndicatore indicatore={risposta.indicator} />
                <ul className="qz-territori">
                  {[risposta.a, risposta.b].map((territorio) => (
                    <li key={territorio.key}>
                      {territorio.path ? (
                        <a href={territorio.path}>{territorio.name}</a>
                      ) : (
                        <span>{territorio.name}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          {rivelata && (
            <button type="button" className="game-btn compare-next" onClick={avanti}>
              Avanti
            </button>
          )}

          <div className="qz-hud">
            <div className="qz-hud-cmd">
              <small>Comando</small>
              <strong>← A · B →</strong>
            </div>
          </div>
        </>
      )}

      {fine && (
        <>
          <FinePartita
            won={fine.score.correct * 2 > fine.score.total}
            titolo={`${fine.score.correct} su ${fine.score.total}`}
            dettaglio={`Sfida del giorno numero ${fine.number} · ${dataInItaliano(fine.date)} · ${
              allenamento ? "allenamento, fuori classifica" : sessione.level_label
            }`}
            nextPuzzleAt={fine.next_puzzle_at}
            condividi={{
              gameName: "Chi è maggiore?",
              puzzleNumber: fine.number,
              esiti: risposte.map((r) => r.esito),
              summary: `${fine.score.correct} su ${fine.score.total}`,
              url: urlDelLivello(livello),
              eventName: "compare_share",
              eventParams: { level: livello },
            }}
            onPlayAgain={apri}
            playAgainLabel="Rivedi le stesse coppie"
          />
          <Riepilogo domande={sessione.questions} risposte={risposte} />
        </>
      )}

      <button type="button" className="game-btn game-btn--ghost compare-esci" onClick={onEsci}>
        Cambia livello o modalità
      </button>
    </div>
  );
}

// Il round a serie, com'era: un errore azzera la serie, la difficoltà sale di tre
// risposte giuste di fila, i record stanno su questo dispositivo.
function Allenamento({ timer, onEsci }) {
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | answering | revealed | error
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

  const stateRef = useRef({ status: "loading", round: null, streak: 0 });
  const timerRef = useRef(null);
  const tokenRef = useRef(null);
  const promptedBestRef = useRef(0);

  // Il primo round parte appena il componente è montato: la scelta fra sfida
  // del giorno e allenamento l'ha già fatta chi ha premuto il bottone.
  useEffect(() => {
    trackGameEvent("compare_start", { level: "regioni", mode: "allenamento" });
    loadRound(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  function loadRound(difficulty) {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    setStatus("loading");
    setResult(null);
    setChoice(null);
    setTimeLeft(ROUND_MS);
    fetchJson(API.round(difficulty, tokenRef.current, timer))
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
    postGame(API.answer, {
      indicator_id: currentRound.indicator.id,
      year: currentRound.indicator.year,
      region_a_key: currentRound.region_a.region_key,
      region_b_key: currentRound.region_b.region_key,
      choice: picked,
      token: tokenRef.current,
    })
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
        notifyAchievements(data.achievements);
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
          level: "regioni",
          mode: "allenamento",
        });
      })
      .catch(() => setStatus("error"));
  }

  function nextRound() {
    loadRound(difficultyForStreak(streak));
  }

  const timerPct = Math.max(0, (timeLeft / ROUND_MS) * 100);
  const level = round ? round.difficulty : 0;
  const isLowTime = status === "answering" && timer && timeLeft <= 3000;
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
            {timer && (
              <div className="qz-timer">
                <span className={isLowTime ? "qz-clock is-low" : "qz-clock"}>{formatClock(timeLeft)}</span>
                <span className="qz-timer-bar">
                  <i
                    className={status === "answering" ? "" : "is-paused"}
                    style={{ width: `${timerPct}%` }}
                  />
                </span>
              </div>
            )}
          </div>

          {!timer && <p className="compare-notice">{NOTA_ALLENAMENTO}</p>}

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
                <span aria-hidden="true">{result.correct ? "✓" : "✗"}</span>{" "}
                <span className="visually-hidden">{result.correct ? "Giusto. " : "Sbagliato. "}</span>
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

      <button type="button" className="game-btn game-btn--ghost compare-esci" onClick={onEsci}>
        Torna alla scelta della modalità
      </button>
    </div>
  );
}

export default function CompareApp() {
  const [modalita, setModalita] = useState(null); // null | sfida | allenamento
  const [livello, setLivello] = useState(livelloDaUrl);
  const [timer, setTimer] = useState(true);
  const [hasPlayedBefore] = useState(() => {
    try {
      return !!window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  function segnaGiocato() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // Il pannello con le regole si ripresenterà alla prossima visita, nessun danno.
    }
  }

  if (modalita === "sfida") {
    return <SfidaDelGiorno livello={livello} timer={timer} onEsci={() => setModalita(null)} />;
  }
  if (modalita === "allenamento") {
    return <Allenamento timer={timer} onEsci={() => setModalita(null)} />;
  }

  return (
    <div className="compare-app">
      <div className="compare-start">
        <h2>Chi è maggiore?</h2>
        <ol className="game-onboarding-steps">
          <li>
            <strong>Un indicatore, due territori.</strong> Tocca quello che secondo te ha il valore
            più alto. Conta il numero, anche quando un valore alto non rappresenta un risultato migliore.
          </li>
          <li>
            <strong>La sfida del giorno è la stessa per tutti.</strong> Dieci coppie, una al giorno,
            e le stesse coppie per chiunque apra la pagina. Da tastiera usa le frecce o i tasti A e B.
          </li>
          <li>
            <strong>L&apos;allenamento non ha fine.</strong> Un errore azzera la serie e la difficoltà sale
            di tre risposte giuste di fila. Il tuo record resta salvato su questo dispositivo.
          </li>
        </ol>

        <fieldset className="compare-scelta-livello">
          <legend>Livello della sfida</legend>
          {LIVELLI.map((opzione) => (
            <label key={opzione.id} className={livello === opzione.id ? "is-active" : ""}>
              <input
                type="radio"
                name="compare-level"
                value={opzione.id}
                checked={livello === opzione.id}
                onChange={() => setLivello(opzione.id)}
              />
              <span className="compare-scelta-label">{opzione.label}</span>
              <span className="compare-scelta-aiuto">{opzione.aiuto}</span>
            </label>
          ))}
        </fieldset>

        <label className="compare-scelta-timer">
          <input type="checkbox" checked={timer} onChange={(e) => setTimer(e.target.checked)} />
          <span>Timer di dieci secondi</span>
        </label>
        {!timer && <p className="compare-notice">{NOTA_ALLENAMENTO}</p>}

        <div className="compare-scelta-azioni">
          <button
            type="button"
            className="game-btn"
            onClick={() => {
              segnaGiocato();
              setModalita("sfida");
            }}
          >
            {hasPlayedBefore ? "Sfida del giorno" : "Inizia con la sfida del giorno"}
          </button>
          <button
            type="button"
            className="game-btn game-btn--ghost"
            onClick={() => {
              segnaGiocato();
              setModalita("allenamento");
            }}
          >
            Allenamento a serie
          </button>
        </div>
        <p className="compare-scelta-nota">
          L&apos;allenamento si gioca fra regioni, con la serie che cresce. Il livello vale per la sfida del giorno.
        </p>
      </div>
    </div>
  );
}