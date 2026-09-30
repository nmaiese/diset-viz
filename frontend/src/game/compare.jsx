import React, { forwardRef, useCallback, useEffect, useRef, useState } from "react";
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
  SfidaCondivisa,
  useSfidaCondivisa,
  useTerritorioMio,
  fraseTerritorioMio,
} from "./shared.jsx";
import {
  ROUND_MS,
  avviaScadenza,
  campoFatto,
  chiediAvanti,
  coppiaDelTerritorio,
  primoTerritorioMio,
  tonoCompare,
} from "./compare-logica.js";

// Il parametro `game` di ogni evento GA4 (docs/tracking_spec.md).
const GIOCO = "compare";

const API = {
  round: (difficulty, token, timer) =>
    `/api/game/compare/round?difficulty=${difficulty}&timer=${timer ? 1 : 0}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/compare/answer",
  dailySession: (level, timer) =>
    `/api/game/compare/daily/session?level=${encodeURIComponent(level)}&timer=${timer ? 1 : 0}`,
  dailyAnswer: "/api/game/compare/daily/answer",
  // La sfida di oggi senza aprire un round: serve solo per il numero, quando il link porta
  // un frammento `#sfida=`. Il conto alla rovescia di un round parte da `dailySession`.
  dailyOggi: "/api/game/compare/daily",
};

const STORAGE_STATS_KEY = "di-compare-stats";
const STORAGE_ONBOARDED_KEY = "di-compare-onboarded";

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
  round_already_bound: "La coppia dopo era già stata aperta. Riapri la sfida.",
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
      </p>
      {indicatore.path ? (
        <p className="qz-scheda-link">
          <a href={indicatore.path}>Apri la scheda dell&apos;indicatore</a>
        </p>
      ) : null}
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
        game={GIOCO}
      />
    </div>
  );
}

// Il riepilogo delle dieci coppie a fine partita: cosa hai risposto, cosa era
// giusto e che cosa misura ogni indicatore. È la parte che la partita lascia a
// chi la finisce, insieme al link alla sfida di domani. Il segno di una coppia
// sbagliata è un cerchio vuoto con la parola, non una croce: il risultato di
// una partita non è una colpa, e vale anche per chi ne ha sbagliate sei.
function Riepilogo({ domande, risposte, mio, livello, onRivedi }) {
  return (
    <section className="qz-riepilogo" aria-labelledby="qz-riepilogo-titolo">
      <h3 id="qz-riepilogo-titolo">Le dieci coppie</h3>
      <ol className="qz-riepilogo-lista">
        {risposte.map((risposta, indice) => {
          const domanda = domande[indice] || {};
          const lato = risposta.winner;
          const altro = lato === "a" ? "b" : "a";
          const conMio = coppiaDelTerritorio(mio, domanda, livello) !== null;
          return (
            <li key={indice} className={`${risposta.correct ? "is-correct" : "is-wrong"}${conMio ? " is-mio" : ""}`}>
              <p className="qz-riepilogo-riga">
                <span aria-hidden="true">{risposta.correct ? "✓" : "○"}</span>{" "}
                <span className="visually-hidden">{risposta.correct ? "Giusta. " : "Sbagliata. "}</span>
                <span className="qz-riepilogo-indicatore">{domanda.indicator ? domanda.indicator.name : ""}</span>
                {conMio && <span className="qz-mio-etichetta">Il tuo territorio</span>}
              </p>
              <p className="qz-riepilogo-valori">
                <strong>{risposta[lato].name}</strong> {formatValue(risposta[lato].value, risposta.indicator.unit)}
                {" · "}
                {risposta[altro].name} {formatValue(risposta[altro].value, risposta.indicator.unit)}
              </p>
              <SchedaIndicatore indicatore={risposta.indicator} />
            </li>
          );
        })}
      </ol>
      {onRivedi && (
        <button type="button" className="game-btn game-btn--ghost compare-rivedi" onClick={onRivedi}>
          Rivedi le stesse coppie
        </button>
      )}
    </section>
  );
}

// Fa scorrere la pagina sull'area di gioco: la testata e il titolo stanno sopra, il gioco
// conta. Con `prefers-reduced-motion: reduce` lo scorrimento e' immediato. Il margine sotto la
// testata che resta ferma lo da' `scroll-padding-top` del foglio del sito.
function scrollaSuIsola() {
  const isola = document.getElementById("compare-root");
  if (!isola || typeof isola.scrollIntoView !== "function") return;
  isola.scrollIntoView({ block: "start", behavior: prefersReducedMotion() ? "auto" : "smooth" });
}

// Il timer di un round. `attivo` lo accende (solo con il timer scelto e la domanda aperta),
// `chiave` lo fa ripartire a ogni coppia. Il conto e' di `compare-logica.js`: a scadenza
// assoluta, e la risposta di timeout parte UNA volta, fuori da qualsiasi updater di stato.
// Ritorna `[rimasto, azzera]`: `azzera()` riporta il conto a 10 s prima di una coppia nuova. Se
// il timer si riaccende sulla stessa coppia (un errore riprovabile) riparte da quanto restava.
function useTimerRound(attivo, chiave, onScadenza) {
  const [rimasto, setRimasto] = useState(ROUND_MS);
  const rimastoRef = useRef(ROUND_MS);
  const scadenzaRef = useRef(onScadenza);
  scadenzaRef.current = onScadenza;

  const azzera = useCallback(() => {
    rimastoRef.current = ROUND_MS;
    setRimasto(ROUND_MS);
  }, []);

  useEffect(() => {
    if (!attivo) return undefined;
    return avviaScadenza({
      ms: rimastoRef.current,
      onTick: (ms) => {
        rimastoRef.current = ms;
        setRimasto(ms);
      },
      onScadenza: () => scadenzaRef.current(),
    });
  }, [attivo, chiave]);

  return [rimasto, azzera];
}

// Cronometro e barra: ci sono solo mentre la domanda e' aperta. Dopo la risposta il tempo e'
// fermo e mostrarlo direbbe una cosa falsa.
function Cronometro({ rimasto }) {
  const pct = Math.max(0, (rimasto / ROUND_MS) * 100);
  const basso = rimasto <= 3000;
  return (
    <div className="qz-timer">
      <span className={basso ? "qz-clock is-low" : "qz-clock"}>{formatClock(rimasto)}</span>
      <span className="qz-timer-bar">
        <i style={{ width: `${pct}%` }} />
      </span>
    </div>
  );
}

// La barra "Avanti": ferma in fondo all'isola, dove arriva il pollice, larga quanto lo schermo
// su telefono. Il bottone e' alto 48 px. Il focus ci arriva dopo la risposta (da tastiera si
// preme Invio), e `aria-busy` dice che sta aspettando il server.
const BarraAvanti = forwardRef(function BarraAvanti({ etichetta, onClick, occupato, messaggio }, ref) {
  return (
    <div className="compare-next-bar">
      {messaggio && (
        <p className="game-error compare-next-errore" role="alert">
          {messaggio}
        </p>
      )}
      <button
        type="button"
        ref={ref}
        className="game-btn compare-next"
        onClick={onClick}
        disabled={occupato}
        aria-busy={occupato ? "true" : undefined}
      >
        {etichetta}
      </button>
    </div>
  );
});

// Il segno "il tuo territorio" nella coppia: un testo, non un colore.
function EtichettaMio() {
  return <span className="mio">Il tuo territorio</span>;
}

// La sfida del giorno: dieci coppie, le stesse per tutti, valutate dal server.
function SfidaDelGiorno({ livello, timer, onEsci, onAllena, sfida, onAvviata }) {
  const [sessione, setSessione] = useState(null);
  // caricamento | domanda | invio | rivelata | fine | errore | bloccata
  const [stato, setStato] = useState("caricamento");
  const [indice, setIndice] = useState(0);
  const [risposta, setRisposta] = useState(null);
  const [risposte, setRisposte] = useState([]);
  const [messaggio, setMessaggio] = useState("");
  const [scaduta, setScaduta] = useState(false);
  // "Avanti": null | invio | riprova | riapri
  const [avvio, setAvvio] = useState(null);
  const [messaggioAvvio, setMessaggioAvvio] = useState("");
  // L'ultima coppia si rivela come le altre; solo dopo la barra "Vedi il risultato" si passa alla fine.
  const [risultatoVisto, setRisultatoVisto] = useState(false);
  const mio = useTerritorioMio();

  const statoRef = useRef({ stato: "domanda", indice: 0 });
  const sessioneRef = useRef(null);
  const tokenRef = useRef(null);
  const ritentoRef = useRef({ id: null, tentativi: 0 });
  const domandaRef = useRef(null);
  const avantiRef = useRef(null);
  const rispondiRef = useRef(null);

  useEffect(() => {
    statoRef.current = { stato, indice };
  }, [stato, indice]);

  useEffect(() => {
    return () => window.clearTimeout(ritentoRef.current.id);
  }, []);

  // Il tempo lo scandisce il client per far avanzare la barra, ma la validita'
  // della risposta la decide il server (vedi `round_timing`): il client puo'
  // sbagliare il conto, non puo' far valere una risposta fuori tempo.
  const [timeLeft, azzeraTimer] = useTimerRound(timer && stato === "domanda", indice, () =>
    rispondiRef.current("timeout")
  );

  useEffect(() => {
    apri();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Stesse frecce e stessi tasti del round a serie, per chi gioca da tastiera. La risposta si
  // legge da un ref: questo effetto si registra una volta sola e vedrebbe la prima `rispondi`,
  // quella che non ha ancora la sessione e non risponde mai.
  useEffect(() => {
    function onKeyDown(event) {
      if (statoRef.current.stato !== "domanda") return;
      const key = event.key.toLowerCase();
      if (key === "arrowleft" || key === "a") {
        event.preventDefault();
        rispondiRef.current("region_a");
      } else if (key === "arrowright" || key === "b") {
        event.preventDefault();
        rispondiRef.current("region_b");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // A ogni coppia nuova (e all'apertura della sfida) la pagina torna sull'area di gioco: la
  // rivelazione della coppia prima e' piu' lunga, e senza questo la domanda nuova resterebbe
  // sopra la piega.
  useEffect(() => {
    if (!sessione) return;
    scrollaSuIsola();
    if (indice > 0 && domandaRef.current) domandaRef.current.focus({ preventScroll: true });
  }, [sessione, indice]);

  // Dopo la risposta il bottone scelto si disattiva e il focus cadrebbe sul body: va alla barra.
  useEffect(() => {
    if ((stato === "rivelata" || stato === "fine") && avantiRef.current) {
      avantiRef.current.focus({ preventScroll: true });
    }
  }, [stato]);

  // Dalla rivelazione dell'ultima coppia alla fine: il blocco cambia del tutto, si riparte dall'alto.
  useEffect(() => {
    if (risultatoVisto) scrollaSuIsola();
  }, [risultatoVisto]);

  useEffect(() => {
    if (indice > 0 && onAvviata) onAvviata();
  }, [indice, onAvviata]);

  function apri() {
    window.clearTimeout(ritentoRef.current.id);
    ritentoRef.current = { id: null, tentativi: 0 };
    setStato("caricamento");
    setSessione(null);
    sessioneRef.current = null;
    setScaduta(false);
    setMessaggio("");
    setAvvio(null);
    setMessaggioAvvio("");
    setRisultatoVisto(false);
    fetchJson(API.dailySession(livello, timer))
      .then((data) => {
        tokenRef.current = data.token;
        sessioneRef.current = data;
        statoRef.current = { stato: "domanda", indice: 0 };
        setSessione(data);
        setIndice(0);
        setRisposta(null);
        setRisposte([]);
        azzeraTimer();
        setStato("domanda");
        trackGameEvent("compare_start", { game: GIOCO, level: livello, mode: "sfida", total: data.total });
      })
      .catch(() => setStato("errore"));
  }

  // Un click o la scadenza: il guardiano e' sincrono (si scrive nel ref prima di rendere),
  // cosi' un click e la scadenza nello stesso istante mandano UNA richiesta sola.
  function rispondi(scelta) {
    const corrente = statoRef.current;
    if (corrente.stato !== "domanda" || !sessioneRef.current) return;
    statoRef.current = { ...corrente, stato: "invio" };
    window.clearTimeout(ritentoRef.current.id);
    ritentoRef.current = { id: null, tentativi: 0 };
    setStato("invio");
    setMessaggio("");
    invia(scelta, corrente.indice);
  }
  rispondiRef.current = rispondi;

  function invia(scelta, domandaIndice) {
    const corrente = sessioneRef.current;
    postSfida(API.dailyAnswer, {
      puzzle_id: corrente.puzzle_id,
      q: domandaIndice,
      choice: scelta,
      token: tokenRef.current,
    }).then(({ ok, status, data }) => {
      if (ok) {
        tokenRef.current = data.token;
        statoRef.current = { stato: data.finished ? "fine" : "rivelata", indice: domandaIndice };
        setRisposta(data);
        setRisposte((precedenti) => [...precedenti, data]);
        setStato(data.finished ? "fine" : "rivelata");
        trackGameEvent("compare_answer", {
          game: GIOCO,
          result: data.correct ? "correct" : scelta === "timeout" ? "timeout" : "wrong",
          streak: data.score ? data.score.correct : 0,
          difficulty: corrente.difficulty,
          level: livello,
          mode: "sfida",
        });
        notifyAchievements(data.achievements, GIOCO);
        return;
      }
      // Un doppio invio della stessa coppia è un 409 e un token già usato è un
      // 400 `token_invalid`: in entrambi i casi il primo invio ha già fatto
      // testo, quindi si torna alla domanda senza dire nulla a chi gioca.
      if (status === 409 || data.error === "token_invalid") {
        statoRef.current = { stato: "domanda", indice: domandaIndice };
        setStato("domanda");
        return;
      }
      setMessaggio(ERRORI_SFIDA[data.error] || "Qualcosa non ha funzionato. Riprova.");
      if (ERRORI_RIPROVABILI.has(data.error)) {
        if (scelta === "timeout") {
          // Il tempo e' gia' finito per il client: rimettere la domanda in `domanda` farebbe
          // scattare la scadenza a ogni tick. Si riprova una volta ogni secondo e mezzo, poche volte.
          if (ritentoRef.current.tentativi < 3) {
            ritentoRef.current = {
              tentativi: ritentoRef.current.tentativi + 1,
              id: window.setTimeout(() => invia("timeout", domandaIndice), 1500),
            };
            return;
          }
        } else {
          statoRef.current = { stato: "domanda", indice: domandaIndice };
          setStato("domanda");
          return;
        }
      }
      setStato("bloccata");
      setScaduta(true);
    });
  }

  // "Avanti": il server lega la coppia dopo solo con `next`, e il tempo della prossima parte
  // quando arriva la sua risposta, non quando si tocca il bottone.
  function avanti() {
    if (stato === "fine") {
      setRisultatoVisto(true);
      return;
    }
    if (stato !== "rivelata" || avvio === "invio") return;
    setAvvio("invio");
    setMessaggioAvvio("");
    chiediAvanti({ post: postSfida, token: tokenRef.current, puzzleId: sessioneRef.current.puzzle_id, q: indice }).then(
      (esito) => {
        if (esito.ok) {
          tokenRef.current = esito.token;
          statoRef.current = { stato: "domanda", indice: indice + 1 };
          azzeraTimer();
          setAvvio(null);
          setIndice(indice + 1);
          setRisposta(null);
          setStato("domanda");
          return;
        }
        if (esito.riprova) {
          setAvvio("riprova");
          setMessaggioAvvio("Non sono riuscito a passare alla coppia dopo.");
          return;
        }
        setAvvio("riapri");
        setMessaggioAvvio(ERRORI_SFIDA[esito.errore] || "La sfida non può proseguire. Riaprila.");
      }
    );
  }

  const domanda = sessione ? sessione.questions[indice] : null;
  const giuste = risposte.filter((r) => r.correct).length;
  const allenamento = sessione ? !sessione.leaderboard : false;
  const rivelata = stato === "rivelata" || stato === "fine";
  const fine = stato === "fine" && risultatoVisto && risposta && risposta.summary;
  const tuoTerritorio = domanda ? coppiaDelTerritorio(mio, domanda, livello) : null;
  const territorioFine = fine ? primoTerritorioMio(mio, sessione.questions, livello) : null;

  function latoClass(lato) {
    let cls = "qz-region";
    if (tuoTerritorio === lato) cls += " is-mio";
    if (!rivelata || !risposta) return cls;
    if (risposta.winner === lato) cls += " is-revealed is-winner";
    else cls += " is-revealed";
    // `choice` e' "region_a" o "region_b" (il vocabolario del round a serie), il lato e' "a" o "b".
    if (risposta.choice === `region_${lato}`) cls += risposta.correct ? " is-picked-right" : " is-picked-wrong";
    return cls;
  }

  // L'hub sa che oggi hai giocato (solo la sfida in classifica, non l'allenamento).
  const finita = stato === "fine" && risposta && risposta.summary;
  useEffect(() => {
    if (!finita || allenamento) return;
    // L'hub ha due icone (giusto, sbagliato) e nessuna neutra: un parziale non e' una croce, quindi
    // solo lo zero pieno e' "sbagliato". Un terzo stato lo deve dare l'hub (`oggi.js`, non di questo file).
    segnaGiocata("compare", finita.date, {
      ok: tonoCompare(finita.score.correct, finita.score.total) !== "nullo",
      testo: `${finita.score.correct} su ${finita.score.total}`,
    });
  }, [finita, allenamento]);

  function bottoneLato(chiave) {
    const vista = rivelata && risposta ? risposta[chiave] : domanda[chiave];
    return (
      <button
        type="button"
        className={latoClass(chiave)}
        disabled={stato !== "domanda"}
        onClick={() => rispondi(chiave === "a" ? "region_a" : "region_b")}
      >
        <span className="code">{chiave.toUpperCase()}</span>
        <span className="name">{vista.name}</span>
        {vista.region && <span className="macro">{vista.region}</span>}
        {tuoTerritorio === chiave && <EtichettaMio />}
        {rivelata && risposta && <span className="value">{formatValue(risposta[chiave].value, risposta.indicator.unit)}</span>}
        {rivelata && risposta && risposta.winner === chiave && <span className="crown">maggiore</span>}
      </button>
    );
  }

  return (
    <div className="compare-app">
      <div className="qz-status">
        <span className="qz-badge">
          Sfida <strong>{sessione ? sessione.number : "-"}</strong>
        </span>
        <span className="qz-badge">
          Coppia <strong>{sessione ? indice + 1 : "-"}</strong> di <strong>{sessione ? sessione.total : "-"}</strong>
        </span>
        <span className="qz-badge">
          Giuste <strong>{sessione ? giuste : "-"}</strong>
        </span>
        <span className="qz-badge qz-badge--level">{sessione ? sessione.level_label : ""}</span>
        {timer && stato === "domanda" && <Cronometro rimasto={timeLeft} />}
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
            <span className="skel-bar" style={{ height: 96 }} />
            <div className="divider">VS</div>
            <span className="skel-bar" style={{ height: 96 }} />
          </div>
        </div>
      )}

      {domanda && !fine && (
        <>
          <div className="qz-question" key={`domanda-${indice}`} ref={domandaRef} tabIndex={-1}>
            <small>
              {domanda.indicator.family ? `${domanda.indicator.family} · ` : ""}
              {domanda.indicator.year}
            </small>
            <h2>{domanda.indicator.name}</h2>
          </div>

          <div className="qz-vs">
            {bottoneLato("a")}
            <div className="divider" aria-hidden="true">VS</div>
            {bottoneLato("b")}
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

          {rivelata && avvio !== "riapri" && (
            <BarraAvanti
              ref={avantiRef}
              etichetta={stato === "fine" ? "Vedi il risultato" : avvio === "riprova" ? "Riprova" : "Avanti"}
              onClick={avanti}
              occupato={avvio === "invio"}
              messaggio={messaggioAvvio}
            />
          )}
          {rivelata && avvio === "riapri" && (
            <BarraAvanti ref={avantiRef} etichetta="Riapri la sfida di oggi" onClick={apri} messaggio={messaggioAvvio} />
          )}

          <div className="qz-hud qz-hud--comando">
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
            game={GIOCO}
            won={fine.score.correct * 2 > fine.score.total}
            tono={tonoCompare(fine.score.correct, fine.score.total)}
            titolo={`${fine.score.correct} su ${fine.score.total}`}
            dettaglio={`Sfida del giorno numero ${fine.number} · ${dataInItaliano(fine.date)} · ${
              allenamento ? "allenamento, fuori classifica" : sessione.level_label
            }`}
            fatto={campoFatto(risposta)}
            sfida={sfida ? { punteggio: sfida.punteggio, tuo: fine.score.correct, game: GIOCO } : undefined}
            nextPuzzleAt={fine.next_puzzle_at}
            condividi={{
              gameName: "Chi è maggiore?",
              game: GIOCO,
              puzzleNumber: fine.number,
              punteggio: fine.score.correct,
              esiti: risposte.map((r) => r.esito),
              summary: `${fine.score.correct} su ${fine.score.total}`,
              url: urlDelLivello(livello),
              eventName: "compare_share",
              eventParams: { level: livello },
            }}
            onPlayAgain={onAllena}
            playAgainLabel="Allenati con coppie nuove"
          />
          {territorioFine && <p className="qz-fine-mio">{fraseTerritorioMio(territorioFine)}</p>}
          <Riepilogo domande={sessione.questions} risposte={risposte} mio={mio} livello={livello} onRivedi={apri} />
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
  const [sessionBest, setSessionBest] = useState(0);
  const [showScoreModal, setShowScoreModal] = useState(false);
  // Contatori della sessione corrente, mostrati nella barra di stato in cima
  // (Round / Serie / Punti): ripartono a ogni caricamento della pagina, a
  // differenza dei record salvati in localStorage.
  const [roundNumber, setRoundNumber] = useState(0);
  const [sessionPoints, setSessionPoints] = useState(0);
  const mio = useTerritorioMio();

  const stateRef = useRef({ status: "loading", round: null, streak: 0 });
  const tokenRef = useRef(null);
  const promptedBestRef = useRef(0);
  const domandaRef = useRef(null);
  const avantiRef = useRef(null);
  const rispondiRef = useRef(null);

  // Senza timer l'allenamento non scade mai: il conto si accende solo se il timer e' scelto.
  const [timeLeft, azzeraTimer] = useTimerRound(timer && status === "answering", roundNumber, () =>
    rispondiRef.current("timeout")
  );

  // Il primo round parte appena il componente è montato: la scelta fra sfida
  // del giorno e allenamento l'ha già fatta chi ha premuto il bottone.
  useEffect(() => {
    trackGameEvent("compare_start", { game: GIOCO, level: "regioni", mode: "allenamento" });
    loadRound(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    stateRef.current = { status, round, streak };
  }, [status, round, streak]);

  // Comando da tastiera mostrato nell'HUD (← A · B →): frecce o i tasti A/B
  // scelgono la regione mentre il round è aperto. Registrato una sola volta,
  // legge lo stato corrente da stateRef e la risposta da un ref per non
  // re-agganciarsi a ogni render.
  useEffect(() => {
    function onKeyDown(event) {
      if (stateRef.current.status !== "answering") return;
      const key = event.key.toLowerCase();
      if (key === "arrowleft" || key === "a") {
        event.preventDefault();
        rispondiRef.current("region_a");
      } else if (key === "arrowright" || key === "b") {
        event.preventDefault();
        rispondiRef.current("region_b");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Stessa regola della sfida: a ogni round la pagina torna sull'area di gioco, e dopo la
  // risposta il focus va al bottone "Avanti".
  useEffect(() => {
    if (!round) return;
    scrollaSuIsola();
    if (roundNumber > 1 && domandaRef.current) domandaRef.current.focus({ preventScroll: true });
  }, [round, roundNumber]);

  useEffect(() => {
    if (status === "revealed" && avantiRef.current) avantiRef.current.focus({ preventScroll: true });
  }, [status]);

  function loadRound(difficulty) {
    setStatus("loading");
    setResult(null);
    setChoice(null);
    azzeraTimer();
    fetchJson(API.round(difficulty, tokenRef.current, timer))
      .then((data) => {
        tokenRef.current = data.token;
        stateRef.current = { ...stateRef.current, status: "answering", round: data };
        setRound(data);
        setRoundNumber((n) => n + 1);
        setStatus("answering");
      })
      .catch(() => setStatus("error"));
  }

  function submitAnswer(picked) {
    const { status: current, round: currentRound } = stateRef.current;
    if (current !== "answering" || !currentRound) return;
    // Guardiano sincrono: un click e la scadenza insieme mandano UNA richiesta.
    stateRef.current = { ...stateRef.current, status: "loading" };
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
        notifyAchievements(data.achievements, GIOCO);
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
          game: GIOCO,
          result: data.correct ? "correct" : picked === "timeout" ? "timeout" : "wrong",
          streak: nextStreak,
          difficulty: currentRound.difficulty,
          level: "regioni",
          mode: "allenamento",
        });
      })
      .catch(() => setStatus("error"));
  }
  rispondiRef.current = submitAnswer;

  function nextRound() {
    loadRound(difficultyForStreak(streak));
  }

  const level = round ? round.difficulty : 0;
  const accuracy = stats.totalRounds > 0
    ? Math.round((stats.totalCorrect / stats.totalRounds) * 100)
    : 0;
  const tuoTerritorio = round
    ? coppiaDelTerritorio(
        mio,
        { a: { key: round.region_a.region_key }, b: { key: round.region_b.region_key } },
        "regioni"
      )
    : null;

  function regionClass(side) {
    let cls = "qz-region";
    if (tuoTerritorio === (side === "region_a" ? "a" : "b")) cls += " is-mio";
    if (status !== "revealed" || !result) return cls;
    const isWinner = result.winner === side;
    const wasPicked = choice === side;
    cls += " is-revealed";
    if (isWinner) cls += " is-winner";
    if (wasPicked) cls += result.correct ? " is-picked-right" : " is-picked-wrong";
    return cls;
  }

  function regione(side, dato, chiave) {
    return (
      <button
        type="button"
        className={regionClass(side)}
        disabled={status !== "answering"}
        onClick={() => submitAnswer(side)}
      >
        <span className="code">{side === "region_a" ? "A" : "B"}</span>
        <span className="name">{dato.region}</span>
        {dato.geo_area && <span className="macro">{dato.geo_area}</span>}
        {tuoTerritorio === chiave && <EtichettaMio />}
        {status === "revealed" && result && (
          <span className="value">{formatValue(result[side].value, round.indicator.unit)}</span>
        )}
        {status === "revealed" && result && result.winner === side && <span className="crown">maggiore</span>}
      </button>
    );
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
            {timer && status === "answering" && <Cronometro rimasto={timeLeft} />}
          </div>

          {!timer && <p className="compare-notice">{NOTA_ALLENAMENTO}</p>}

          <div className="qz-question" key={`round-${roundNumber}`} ref={domandaRef} tabIndex={-1}>
            <small>
              {round.indicator.source_label ? `Indicatore ${round.indicator.source_label} · ` : ""}
              {round.indicator.year}
            </small>
            <h2>{round.indicator.name}</h2>
          </div>

          <div className="qz-vs">
            {regione("region_a", round.region_a, "a")}
            <div className="divider" aria-hidden="true">VS</div>
            {regione("region_b", round.region_b, "b")}
          </div>

          {(round.indicator.description || round.indicator.value_explanation) && (
            <div className="qz-misura">
              <p className="desc">
                {[round.indicator.description, round.indicator.value_explanation].filter(Boolean).join(" ")}
              </p>
              <SourceStrip
                year={round.indicator.year}
                sourceLabel={round.indicator.source_label}
                sourceUrl={round.indicator.source_url}
                game={GIOCO}
              />
            </div>
          )}

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
            <BarraAvanti
              ref={avantiRef}
              etichetta={result && result.correct ? "Avanti" : "Ricomincia"}
              onClick={nextRound}
            />
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
            <span className="skel-bar" style={{ height: 96 }} />
            <div className="divider">VS</div>
            <span className="skel-bar" style={{ height: 96 }} />
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
  // La sfida condivisa (`#sfida=7-12`): il numero di oggi lo dice il server, mai la data del
  // browser. Lo si chiede solo se il link porta un frammento, e senza aprire un round.
  const [numeroOggi, setNumeroOggi] = useState(null);
  const [avviata, setAvviata] = useState(false);
  const [hasPlayedBefore] = useState(() => {
    try {
      return !!window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!/^#sfida=/.test(window.location.hash)) return;
    fetchJson(API.dailyOggi)
      .then((data) => setNumeroOggi(data && Number.isInteger(data.number) ? data.number : null))
      .catch(() => {
        // Senza il numero di oggi non c'e' sfida: il gioco parte lo stesso.
      });
  }, []);

  // La partita comincia alla seconda coppia, non alla prima risposta: togliere il riquadro
  // mentre si rivela la prima coppia sposterebbe i bottoni sotto il dito.
  const sfida = useSfidaCondivisa({ game: GIOCO, numeroOggi, avviata });
  const segnaAvviata = useCallback(() => setAvviata(true), []);

  function segnaGiocato() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // Il pannello con le regole si ripresenterà alla prossima visita, nessun danno.
    }
  }

  const riquadro = <SfidaCondivisa sfida={sfida} game={GIOCO} avviata={avviata || modalita === "allenamento"} />;

  if (modalita === "sfida") {
    return (
      <>
        {riquadro}
        <SfidaDelGiorno
          livello={livello}
          timer={timer}
          sfida={sfida}
          onAvviata={segnaAvviata}
          onEsci={() => setModalita(null)}
          onAllena={() => setModalita("allenamento")}
        />
      </>
    );
  }
  if (modalita === "allenamento") {
    return <Allenamento timer={timer} onEsci={() => setModalita(null)} />;
  }

  return (
    <>
      {riquadro}
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
    </>
  );
}
