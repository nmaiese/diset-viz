import React, { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3 } from "lucide-react";
import { FinePartita, Modal, fetchJson, formatValue, prefersReducedMotion, trackGameEvent } from "../shared.jsx";
import { comparisonArrow, comparisonText, dataInChiaro, normalize, ordinal } from "./helpers.js";
import { oggiRoma } from "./serie.js";
import {
  API_PROVINCIA,
  LIVELLI,
  caricaProgresso,
  caricaStatistiche,
  direzione,
  livelloSalvato,
  nomeLivello,
  onboardingFatto,
  registraPartita,
  salvaLivello,
  salvaProgresso,
  segnaOnboarding,
  testoDistanza,
} from "./provincia.js";
import { useMappaProvince } from "./MappaProvince.jsx";
import Completamento from "./Completamento.jsx";
import TabellaIndizi from "./TabellaIndizi.jsx";
import Riepilogo from "./Riepilogo.jsx";
import { DistributionChart } from "./Statistiche.jsx";

const GAME_NAME = "Indovina la Provincia";
const MAX_SUGGERIMENTI = 6;

const MESSAGGI_ERRORE = {
  sfida_scaduta: "La sfida è cambiata. Ricarica la pagina per giocare quella di oggi.",
  token_superato: "Questo tentativo risulta già registrato. Ricarica la pagina per riprendere.",
  provincia_gia_tentata: "Hai già provato questa provincia.",
  provincia_non_valida: "Questa provincia non è fra quelle del livello scelto.",
  partita_conclusa: "La partita di oggi è già conclusa.",
  rate_limited: "Troppi tentativi in poco tempo. Riprova fra un minuto.",
};

// Un tentativo: niente token, che resta nel salvataggio a parte.
function senzaToken(risultato) {
  const { token, ...resto } = risultato;
  return resto;
}

async function inviaTentativo(token, provinceKey) {
  const res = await fetch(API_PROVINCIA.guess, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, province_key: provinceKey }),
  });
  let dati = null;
  try {
    dati = await res.json();
  } catch {
    dati = null;
  }
  if (!res.ok) {
    const errore = new Error(dati?.error || "errore");
    errore.code = dati?.error;
    throw errore;
  }
  return dati;
}

function etichettaSuggerimento(provincia, livello) {
  return livello === "province" ? `${provincia.name} (${provincia.region})` : provincia.name;
}

export default function GiocoProvincia() {
  const [level, setLevel] = useState(livelloSalvato);
  const [puzzle, setPuzzle] = useState(null);
  const [token, setToken] = useState(null);
  const [clues, setClues] = useState([]);
  const [guesses, setGuesses] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | playing | won | lost | error
  const [solution, setSolution] = useState(null);
  const [recap, setRecap] = useState(null);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(-1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [liveMessage, setLiveMessage] = useState("");
  const [shake, setShake] = useState(false);
  const [stats, setStats] = useState(caricaStatistiche);
  const [showOnboarding, setShowOnboarding] = useState(() => !onboardingFatto());
  const [showStats, setShowStats] = useState(false);

  const cluesListRef = useRef(null);
  const statsRecordedRef = useRef(false);
  const latestRef = useRef({ status: "loading", submitting: false });

  const finished = status === "won" || status === "lost";
  const locked = guesses.length > 0 || finished;

  useEffect(() => {
    latestRef.current = { status, submitting };
  }, [status, submitting]);

  useEffect(() => {
    setHighlighted(-1);
  }, [query]);

  // La provincia e' la stessa ai due livelli: se oggi hai gia' iniziato, il livello
  // e' quello dell'inizio, e la partita si riprende dal salvataggio.
  useEffect(() => {
    const salvato = caricaProgresso(`daily:${oggiRoma()}`);
    if (salvato && salvato.level !== level) {
      setLevel(salvato.level);
      return undefined;
    }
    let attivo = true;
    setStatus("loading");
    setError(null);
    setLiveMessage("");
    fetchJson(API_PROVINCIA.daily(level))
      .then((data) => {
        if (!attivo) return;
        setPuzzle(data);
        const progresso = caricaProgresso(data.puzzle_id);
        if (progresso && progresso.level === level) {
          setToken(progresso.token);
          setClues(progresso.clues);
          setGuesses(progresso.guesses);
          setSolution(progresso.solution || null);
          setRecap(progresso.recap || null);
          statsRecordedRef.current = Boolean(progresso.statsRecorded);
          setStatus(progresso.status);
          return;
        }
        statsRecordedRef.current = false;
        setToken(data.token);
        setClues(data.clue ? [data.clue] : []);
        setGuesses([]);
        setSolution(null);
        setRecap(null);
        setStatus("playing");
        trackGameEvent("game_start", { mode: "daily", level });
      })
      .catch(() => {
        if (!attivo) return;
        setError("Non è stato possibile caricare la sfida. Riprova fra poco.");
        setStatus("error");
      });
    return () => {
      attivo = false;
    };
  }, [level]);

  // Scrolla solo il pannello indizi: un indizio nuovo non trascina la pagina
  // oltre il campo di risposta.
  useEffect(() => {
    const lista = cluesListRef.current;
    if (clues.length > 1 && lista) {
      lista.scrollTo({ top: lista.scrollHeight, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    }
  }, [clues.length]);

  const opzioni = puzzle?.provinces;

  const suggestions = useMemo(() => {
    const q = normalize(query.trim());
    if (!q || !opzioni) return [];
    const tentate = new Set(guesses.map((g) => g.province_key));
    const trovate = opzioni.filter((p) => !tentate.has(p.key) && normalize(p.name).includes(q));
    // Prima quelle che iniziano come la ricerca.
    trovate.sort((a, b) => Number(!normalize(a.name).startsWith(q)) - Number(!normalize(b.name).startsWith(q)));
    return trovate.slice(0, MAX_SUGGERIMENTI).map((p) => ({ key: p.key, label: etichettaSuggerimento(p, level) }));
  }, [query, opzioni, guesses, level]);

  useMappaProvince({ options: opzioni, region: puzzle?.region, guesses, status, solution });

  function scegliLivello(nuovo) {
    if (locked || nuovo === level) return;
    salvaLivello(nuovo);
    setLevel(nuovo);
  }

  function registraFine(won, attempts) {
    if (statsRecordedRef.current) return;
    statsRecordedRef.current = true;
    setStats((prev) => registraPartita(prev, { won, attempts }));
  }

  function salva(next) {
    if (!puzzle) return;
    salvaProgresso(puzzle.puzzle_id, {
      level,
      token: next.token,
      clues: next.clues,
      guesses: next.guesses,
      status: next.status,
      solution: next.solution,
      recap: next.recap,
      statsRecorded: statsRecordedRef.current,
    });
  }

  function submitGuess(provinceKey) {
    if (!puzzle || latestRef.current.submitting || latestRef.current.status !== "playing") return;
    const attempt = guesses.length + 1;
    setSubmitting(true);
    setError(null);
    inviaTentativo(token, provinceKey)
      .then((result) => {
        const tentativo = senzaToken(result);
        const nextGuesses = [...guesses, tentativo];
        const nextClues = result.next_clue ? [...clues, result.next_clue] : clues;
        const nextStatus = result.finished ? (result.correct ? "won" : "lost") : "playing";
        setGuesses(nextGuesses);
        setClues(nextClues);
        setToken(result.token);
        setStatus(nextStatus);
        setQuery("");
        setHighlighted(-1);
        trackGameEvent("game_guess", { mode: "daily", level, attempt, correct: result.correct });

        if (result.correct) {
          setLiveMessage(`Hai indovinato! La provincia era ${result.province}.`);
        } else if (result.finished) {
          setLiveMessage(`Tentativi esauriti. La provincia era ${result.solution?.province || ""}.`);
        } else {
          setLiveMessage(
            `Tentativo ${attempt}: ${result.province} non è la provincia. ${testoDistanza(result)}. `
            + `${result.same_region ? "Stessa regione." : "Un'altra regione."} Nuovo indizio rivelato.`
          );
          setShake(true);
          window.setTimeout(() => setShake(false), 420);
        }

        if (result.finished) {
          setSolution(result.solution);
          setRecap(result.recap);
          registraFine(result.correct, attempt);
          trackGameEvent("game_finish", { mode: "daily", level, won: result.correct, attempts: attempt });
        }
        salva({
          token: result.token, clues: nextClues, guesses: nextGuesses, status: nextStatus,
          solution: result.solution, recap: result.recap,
        });
      })
      .catch((e) => setError(MESSAGGI_ERRORE[e.code] || "Il tentativo non è andato a buon fine. Riprova."))
      .finally(() => setSubmitting(false));
  }

  const highlightBucket = finished ? (status === "won" ? String(guesses.length) : "fail") : null;

  return (
    <div className="game-app guess-app">
      <div className="game-toolbar" role="group" aria-label="Livello di gioco">
        {LIVELLI.map((l) => (
          <button
            key={l.key}
            type="button"
            aria-pressed={level === l.key}
            aria-disabled={locked && level !== l.key}
            disabled={locked && level !== l.key}
            className={level === l.key ? "game-tab is-active" : "game-tab"}
            onClick={() => scegliLivello(l.key)}
          >
            {l.label}
          </button>
        ))}
        <span className="game-toolbar-spacer" />
        <button
          type="button"
          className="game-icon-btn"
          onClick={() => { setShowStats(true); trackGameEvent("game_stats_open", { mode: "daily", level }); }}
          aria-label="Statistiche"
        >
          <BarChart3 size={16} strokeWidth={2} />
        </button>
        <button type="button" className="game-icon-btn" onClick={() => setShowOnboarding(true)} aria-label="Come si gioca">
          ?
        </button>
      </div>
      {locked && (
        <p className="game-livello-nota">
          La provincia di oggi è la stessa a tutti e due i livelli: hai già iniziato, quindi il livello resta quello
          {" "}{nomeLivello(level)}.
        </p>
      )}

      <div className="visually-hidden" aria-live="polite">{liveMessage}</div>

      {status === "loading" && (
        <div aria-hidden="true">
          <div className="game-head">
            <span className="skel-bar" style={{ height: 22, width: "40%" }} />
            <div className="game-attempts">
              {Array.from({ length: 6 }).map((_, i) => (
                <span key={i} className="seg" />
              ))}
            </div>
          </div>
          <div className="skel-bars" style={{ marginTop: 18 }}>
            <span style={{ height: 96 }} />
            <span style={{ height: 96 }} />
          </div>
        </div>
      )}
      {status === "error" && (
        <>
          <p className="game-error">{error}</p>
          <button type="button" className="game-btn" onClick={() => window.location.reload()}>Riprova</button>
        </>
      )}

      {(status === "playing" || finished) && puzzle && (
        <>
          <header className="game-head">
            <h2>
              Sfida n. {puzzle.number}
              {puzzle.date && <span className="game-date"> · {dataInChiaro(puzzle.date)}</span>}
            </h2>
            {puzzle.region && (
              <p className="game-regione-nota">
                La provincia misteriosa è in <strong>{puzzle.region.name}</strong>.
              </p>
            )}
            <div className="game-attempts-row">
              <span className="game-attempts-label">
                {finished ? "Partita conclusa" : `Tentativo ${guesses.length + 1} di ${puzzle.attempts_total}`}
              </span>
              <div className="game-attempts" aria-hidden="true">
                {Array.from({ length: puzzle.attempts_total }).map((_, i) => {
                  const g = guesses[i];
                  const cls = !g ? "seg" : g.correct ? "seg is-correct" : "seg is-wrong";
                  return <span key={i} className={cls} />;
                })}
              </div>
            </div>
          </header>

          {/* La mappa (#game-map-frame) e' il fratello server-renderizzato di
              #game-root, come in Indovina la Regione: useMappaProvince la
              rende viva dall'esterno. */}
          <div className="game-panel">
            <p className="qz-section-label">Indizi svelati</p>
            <TabellaIndizi clues={clues} total={puzzle.attempts_total} playing={status === "playing"} bodyRef={cluesListRef} />

            {status === "playing" && (
              <Completamento
                label="La tua ipotesi"
                ariaLabel="Indovina la provincia"
                placeholder="Scrivi il nome di una provincia..."
                query={query}
                onQuery={setQuery}
                suggestions={suggestions}
                highlighted={highlighted}
                onHighlight={setHighlighted}
                onPick={submitGuess}
                disabled={submitting}
                shake={shake}
                error={error}
              />
            )}

            {guesses.length > 0 && <TentativiProvincia guesses={guesses} />}

            {finished && solution && (
              <FineProvincia
                won={status === "won"}
                puzzle={puzzle}
                level={level}
                solution={solution}
                recap={recap}
                guesses={guesses}
                stats={stats}
                highlightBucket={highlightBucket}
              />
            )}
          </div>
        </>
      )}

      {showOnboarding && (
        <Modal
          title="Come si gioca"
          labelledBy="game-onboarding-title"
          onClose={() => { setShowOnboarding(false); segnaOnboarding(); }}
        >
          <ol className="game-onboarding-steps">
            <li>Una provincia italiana è nascosta, e cambia ogni giorno a mezzanotte di Roma. Hai sei tentativi.</li>
            <li>Scrivi il nome di una provincia e scegline una dall'elenco. La mappa segna il tentativo con un numero.</li>
            <li>
              Ogni errore ti dice a che distanza sei, in chilometri approssimati, e in quale direzione cercare.
              Svela anche un indizio nuovo, un dato Istat.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={() => { setShowOnboarding(false); segnaOnboarding(); }}>
            Ho capito, gioco
          </button>
        </Modal>
      )}

      {showStats && (
        <Modal title="Le tue statistiche" onClose={() => setShowStats(false)} labelledBy="game-stats-title">
          <div className="game-stats-numbers game-stats-numbers--due">
            <div><strong>{stats.played}</strong><span>Partite</span></div>
            <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
          </div>
          <DistributionChart distribution={stats.distribution} highlightBucket={null} />
          <p className="game-stats-note">
            Le statistiche restano su questo browser. La serie e la classifica di Indovina la Provincia arrivano più avanti.
          </p>
        </Modal>
      )}
    </div>
  );
}

// Lo storico dei tentativi: per ognuno la distanza e la direzione, se e' nella
// stessa regione, e il confronto indizio per indizio. L'esito si legge dal testo
// e dall'icona, non dal solo colore.
function TentativiProvincia({ guesses }) {
  return (
    <section className="game-history" aria-label="Tentativi">
      {guesses.map((g, i) => {
        const punto = direzione(g.direction);
        const ultimo = i === guesses.length - 1;
        return (
          <div key={g.province_key} className={g.correct ? "guess-row is-correct" : "guess-row is-wrong"}>
            <p className="guess-titolo">
              <img
                className="guess-icona"
                src={g.correct ? "/static/img/gioco/stato-giusto.svg" : "/static/img/gioco/stato-sbagliato.svg"}
                alt=""
                width="18"
                height="18"
              />
              <strong>{i + 1}. {g.province}</strong>
              <span className="guess-esito">{g.correct ? "Giusto" : "Non è questa"}</span>
            </p>
            {!g.correct && (
              <p className="guess-distanza">
                {punto && <span className="guess-freccia" aria-hidden="true">{punto.freccia}</span>}
                <span>{testoDistanza(g)}.</span>{" "}
                <span>{g.same_region ? "Stessa regione." : "Un'altra regione."}</span>
              </p>
            )}
            {!g.correct && (
              <details className="guess-confronto" open={ultimo}>
                <summary>Confronto degli indizi</summary>
                <ul className="guess-feedback">
                  {g.feedback.map((f) => (
                    <li key={f.id}>
                      <span className="guess-symbol" aria-hidden="true">{comparisonArrow(f.comparison)}</span>
                      <span className="guess-feedback-body">
                        <strong>{f.name}</strong>
                        <span className="guess-feedback-detail">
                          {formatValue(f.guess_value, f.unit)}
                          {Number.isFinite(f.guess_rank) && ` · ${ordinal(f.guess_rank)} su ${f.province_count}`}
                          {" "}({comparisonText(f.comparison)}
                          {Number.isFinite(f.mystery_rank) && `, misteriosa ${ordinal(f.mystery_rank)}`})
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        );
      })}
    </section>
  );
}

function titoloEsito(won, tentativi) {
  if (!won) return "Provincia non indovinata";
  return tentativi === 1 ? "Indovinata al primo tentativo" : `Indovinata in ${tentativi} tentativi`;
}

function FineProvincia({ won, puzzle, level, solution, recap, guesses, stats, highlightBucket }) {
  const condividi = {
    gameName: GAME_NAME,
    puzzleNumber: puzzle.number,
    esiti: guesses.map((g) => (g.correct ? "exact" : "miss")),
    summary: `${won ? guesses.length : "X"} su ${puzzle.attempts_total}, livello ${nomeLivello(level)}`,
    url: `${window.location.origin}/quiz/indovina-la-provincia`,
    eventParams: { mode: "daily", level },
  };
  return (
    <div className="game-result">
      <FinePartita
        won={won}
        titolo={titoloEsito(won, guesses.length)}
        dettaglio={`La provincia era ${solution.province}, in ${solution.region}.`}
        territori={[
          { name: `Scheda di ${solution.province}`, path: solution.path },
          { name: `Scheda di ${solution.region}`, path: solution.region_path },
        ]}
        nextPuzzleAt={puzzle.next_puzzle_at}
        condividi={condividi}
      />

      {recap && (
        <Riepilogo
          soggetto={solution.province}
          mediaLabel="Media delle province"
          rows={recap.map((row) => ({ ...row, media: row.province_avg }))}
        />
      )}

      <div className="game-stats-inline">
        <div className="game-stats-numbers game-stats-numbers--due">
          <div><strong>{stats.played}</strong><span>Partite</span></div>
          <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
        </div>
        <DistributionChart distribution={stats.distribution} highlightBucket={highlightBucket} />
      </div>
    </div>
  );
}
