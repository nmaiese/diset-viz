import React, { useCallback, useEffect, useRef, useState } from "react";
import { oggiRoma, segnaGiocata } from "../oggi.js";
import {
  FinePartita,
  SfidaCondivisa,
  fraseTerritorioMio,
  notifyAchievements,
  prefersReducedMotion,
  trackGameEvent,
  useSfidaCondivisa,
  useTerritorioMio,
} from "../shared.jsx";
import { apriSessione, dimenticaPartita, leggiSalvata, rispondi, salvaPartita } from "./api.js";
import { Avanti, Conferma, InAzioni } from "./Azioni.jsx";
import { Domanda } from "./Domanda.jsx";
import { creaMappa } from "./mappaMuta.js";
import {
  GIOCO,
  OPZIONI,
  applicaRisposta,
  decisioneErroreRisposta,
  erroreRiprovabile,
  esitiPerCondivisione,
  messaggioErrore,
  messaggioRiapertura,
  nuovaPartita,
  opzione,
  parametriRisposta,
  riassunto,
  territoriFinali,
  territorioMioFra,
  testoHub,
  titoloFine,
  tonoFine,
  tonoPartita,
} from "./partita.js";
import { Rivelazione } from "./Rivelazione.jsx";
import { SenzaMappa } from "./SenzaMappa.jsx";

function dataInItaliano(iso) {
  if (!iso) return "";
  const giorno = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(giorno.getTime())) return "";
  return giorno.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

// Porta la pagina sull'area di gioco: la domanda e la mappa devono stare sopra la piega. Con
// `prefers-reduced-motion: reduce` lo scorrimento e' immediato.
function scrollaSuIsola() {
  const isola = document.getElementById("game-root");
  if (!isola || typeof isola.scrollIntoView !== "function") return;
  isola.scrollIntoView({ block: "start", behavior: prefersReducedMotion() ? "auto" : "smooth" });
}

// La mappa del template e il suo hook: creata una volta, distrutta allo smontaggio.
function useMappa(onCambio) {
  const mappa = useRef(null);
  const cambio = useRef(onCambio);
  cambio.current = onCambio;
  useEffect(() => {
    const svg = document.getElementById("mappa-svg");
    if (!svg) return undefined;
    mappa.current = creaMappa(svg, {
      onCambio: (stato) => cambio.current(stato),
      suggerimento: document.getElementById("mappa-suggerimento"),
    });
    return () => {
      mappa.current.distruggi();
      mappa.current = null;
    };
  }, []);
  return mappa;
}

function mostraMappa(visibile) {
  const cornice = document.getElementById("mappa-cornice");
  if (cornice) cornice.hidden = !visibile;
}

// La scelta dell'esercizio, prima di cominciare. Tre esercizi, e il terzo e' un altro: lo dice.
function Scelta({ scelta, onScegli, onInizia, occupato, errore, sfida, avviata }) {
  return (
    <div className="mappa-scelta">
      <SfidaCondivisa sfida={sfida} game={GIOCO} avviata={avviata} />
      <h2 className="mappa-scelta-titolo">La sfida di oggi</h2>
      <fieldset className="mappa-scelta-livello">
        <legend>Come vuoi giocare</legend>
        {OPZIONI.map((o) => (
          <label key={o.id} className={scelta === o.id ? "is-active" : ""}>
            <input type="radio" name="mappa-opzione" value={o.id} checked={scelta === o.id} onChange={() => onScegli(o.id)} />
            <span className="mappa-scelta-label">{o.titolo}</span>
            <span className="mappa-scelta-aiuto">{o.aiuto}</span>
          </label>
        ))}
      </fieldset>
      {errore && <p className="game-error" role="alert">{errore}</p>}
      <button type="button" className="game-btn mappa-inizia" onClick={onInizia} aria-busy={occupato ? "true" : undefined} disabled={occupato}>
        {errore ? "Riprova" : "Inizia la sfida del giorno"}
      </button>
    </div>
  );
}

function Partita({ partita, sfida, avviso, onPartita, onCambiaOpzione, onRiapri, onRiprendi, mappa, vistaMappa }) {
  const iso = partita.date;
  // La domanda mostrata resta quella appena risposta finche' non si preme "Avanti": la partita
  // ha gia' la domanda dopo, ma la rivelazione parla di quella di prima.
  const [domanda, setDomanda] = useState(partita.question);
  const [stato, setStato] = useState(partita.fine ? "fine" : "domanda"); // domanda | invio | rivelata | fine
  const [risposta, setRisposta] = useState(null);
  const [scelta, setScelta] = useState(null); // la regione scelta senza mappa
  const [messaggio, setMessaggio] = useState(avviso || "");
  const [riaprire, setRiaprire] = useState(false);
  // L'ultima risposta non e' arrivata e si puo' rimandare: sotto il messaggio c'e' "Riprova".
  const [riprovabile, setRiprovabile] = useState(false);
  const [vista, setVista] = useState({ vista: "italia", selezionata: null });
  const mio = useTerritorioMio();

  const domandaRef = useRef(null);
  const avantiRef = useRef(null);
  const confermaRef = useRef(null);
  const statoRef = useRef(stato);
  statoRef.current = stato;
  const partitaRef = useRef(partita);
  partitaRef.current = partita;
  const modalita = partita.mode;
  const conMappa = modalita === "map";

  // Il cambio di vista o di selezione della mappa arriva da `useMappa` del padre.
  useEffect(() => {
    vistaMappa.current = setVista;
    return () => {
      vistaMappa.current = null;
    };
  }, [vistaMappa]);

  // Una domanda nuova (o la ripresa): la mappa riparte dall'Italia, o dal riquadro della regione
  // detta al livello facile. Senza mappa la cornice sta nascosta.
  useEffect(() => {
    if (stato === "fine") {
      mostraMappa(false);
      if (mappa.current) mappa.current.blocca();
      return;
    }
    mostraMappa(conMappa);
    if (!conMappa) {
      if (mappa.current) mappa.current.blocca();
      return;
    }
    if (stato === "domanda" && mappa.current && domanda) {
      mappa.current.inizia({ regione: partita.level === "regione" ? domanda.region_key : undefined });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domanda, stato === "fine", conMappa]);

  useEffect(() => {
    scrollaSuIsola();
    if (domandaRef.current && domanda && domanda.index > 0) domandaRef.current.focus({ preventScroll: true });
  }, [domanda, stato === "fine"]);

  useEffect(() => {
    if ((stato === "rivelata") && avantiRef.current) avantiRef.current.focus({ preventScroll: true });
  }, [stato]);

  const selezionata = conMappa ? vista.selezionata : scelta;
  const pronta = Boolean(selezionata);

  function riapri(testo) {
    setMessaggio(testo);
    setRiaprire(true);
    setStato("domanda");
  }

  async function conferma() {
    if (statoRef.current !== "domanda") return;
    if (!pronta) {
      setMessaggio(conMappa ? "Scegli prima una provincia." : "Scegli prima una regione.");
      return;
    }
    setMessaggio("");
    setRiprovabile(false);
    statoRef.current = "invio";
    setStato("invio");
    const corrente = partitaRef.current;
    const corpo = {
      token: corrente.token,
      puzzle_id: corrente.puzzle_id,
      q: domanda.index,
      ...(conMappa ? { province_key: selezionata } : { region_key: selezionata }),
    };
    const { ok, status, data } = await rispondi(corpo);
    if (!ok) {
      // La partita ripresa da sola e ancora senza una risposta buona non si riprende una seconda volta.
      const decisione = decisioneErroreRisposta(
        { status, error: data.error },
        { giaRiaperta: Boolean(avviso) && corrente.risposte.length === 0 },
      );
      if (decisione === "riprendi") {
        // La risposta e' arrivata al server ma non a noi (o il token e' superato): quello salvato non
        // serve piu'. Si apre una sessione nuova, dicendolo.
        onRiprendi(messaggioErrore("round_already_answered"));
        return;
      }
      if (decisione === "riapri") {
        riapri(messaggioRiapertura(data.error, { status }));
        return;
      }
      statoRef.current = "domanda";
      setStato("domanda");
      setMessaggio(messaggioErrore(data.error, status));
      setRiprovabile(erroreRiprovabile(data.error));
      return;
    }
    let inVista = null;
    if (conMappa && mappa.current) {
      inVista = mappa.current.rivela({ giusta: data.right.key, scelta: data.chosen.key }).giustaInVista;
    }
    const reselezioni = conMappa && mappa.current ? mappa.current.reselezioni() : 0;
    const aggiornata = applicaRisposta(corrente, data);
    partitaRef.current = aggiornata;
    onPartita(aggiornata);
    salvaPartita(aggiornata);
    setRisposta(data);
    statoRef.current = "rivelata";
    setStato("rivelata");
    trackGameEvent("map_answer", parametriRisposta(corrente, data, {
      reselects: reselezioni,
      ...(inVista === null ? {} : { in_view: inVista }),
    }));
    if (data.finished && data.summary) {
      const { score, esiti } = data.summary;
      segnaGiocata(GIOCO, data.summary.date, {
        ok: true,
        tono: tonoPartita(score.points, score.max),
        testo: testoHub(score.points, score.max, corrente.mode),
      });
      trackGameEvent("map_finish", {
        game: GIOCO,
        mode: "daily",
        level: corrente.level,
        answer_mode: corrente.mode,
        score: score.points,
        total: score.max,
        exact: esiti.filter((e) => e === "exact").length,
      });
      notifyAchievements(data.summary.achievements, GIOCO);
    }
  }

  function avanti() {
    if (stato !== "rivelata") return;
    if (partita.fine) {
      setStato("fine");
      return;
    }
    setRisposta(null);
    setScelta(null);
    setMessaggio("");
    setDomanda(partita.question);
    setStato("domanda");
  }

  function indietro() {
    if (!mappa.current || statoRef.current !== "domanda") return;
    trackGameEvent("map_back", { game: GIOCO, mode: "daily", level: partita.level, index: domanda ? domanda.index : 0 });
    mappa.current.vaiItalia({ focus: true });
  }

  const rivelata = stato === "rivelata";
  const tuttaFatta = rivelata && partita.fine;

  if (stato === "fine" && partita.fine) {
    return <Fine partita={partita} sfida={sfida} mio={mio} onCambiaOpzione={onCambiaOpzione} />;
  }

  return (
    <div className="mappa-app">
      <Domanda partita={partita} domanda={domanda} vista={vista.vista} selezionata={selezionata} rivelata={rivelata} ref={domandaRef} />
      {!conMappa && (
        <SenzaMappa regioni={partita.regions || []} scelta={scelta} onScegli={setScelta} disabilitato={stato !== "domanda"} />
      )}
      {messaggio && <p className="game-error" role="alert">{messaggio}</p>}
      {riprovabile && !riaprire && stato === "domanda" && (
        <button type="button" className="game-btn" onClick={conferma}>Riprova</button>
      )}
      {riaprire && (
        <button type="button" className="game-btn" onClick={onRiapri}>Riapri la sfida di oggi</button>
      )}
      <InAzioni>
        <Rivelazione risposta={rivelata ? risposta : null} modalita={modalita} />
        {!riaprire && (
          <div className="mappa-barra">
            {rivelata ? (
              <Avanti ref={avantiRef} etichetta={tuttaFatta ? "Vedi il risultato" : "Avanti"} onAvanti={avanti} />
            ) : (
              <>
                {/* Conferma prima di Indietro nel DOM: da tastiera Tab dalla mappa arriva subito a Conferma */}
                <Conferma ref={confermaRef} pronta={pronta} occupato={stato === "invio"} onConferma={conferma} />
                {conMappa && vista.vista !== "italia" && (
                  <button type="button" className="game-btn game-btn--ghost mappa-indietro" onClick={indietro} aria-disabled={stato === "invio" ? "true" : undefined}>
                    Indietro
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </InAzioni>
    </div>
  );
}

function Fine({ partita, sfida, mio, onCambiaOpzione }) {
  const { score, esiti, number, date, next_puzzle_at: prossima } = partita.fine;
  const tono = tonoPartita(score.points, score.max);
  // La sfida condivisa ricevuta vale solo per la mappa a tutta Italia: il frammento non porta il
  // livello, e il confronto ha senso fra due partite uguali.
  const piena = partita.level === "italia" && partita.mode === "map";
  const nomeMio = territorioMioFra(mio, partita.risposte);
  return (
    <>
      <FinePartita
        game={GIOCO}
        won={tono === "giusto"}
        tono={tonoFine(tono)}
        titolo={titoloFine(score.points, score.max)}
        dettaglio={`${riassunto(esiti, partita.mode)}. Sfida del giorno numero ${number}, ${dataInItaliano(date)}. ${opzione(partita.level, partita.mode).titolo}.`}
        sfida={piena && sfida ? { punteggio: sfida.punteggio, tuo: score.points, game: GIOCO } : undefined}
        territori={territoriFinali(partita.risposte)}
        nextPuzzleAt={prossima}
        condividi={{
          gameName: "Dov'è la provincia?",
          game: GIOCO,
          puzzleNumber: number,
          ...(piena ? { punteggio: score.points } : {}),
          esiti: esitiPerCondivisione(esiti, partita.mode),
          summary: `${testoHub(score.points, score.max, partita.mode)}. Un simbolo per domanda.`,
          eventName: "map_share",
          eventParams: { level: partita.level, answer_mode: partita.mode },
        }}
      />
      {nomeMio && <p className="qz-fine-mio">{fraseTerritorioMio(nomeMio)}</p>}
      <p className="mappa-altro-esercizio">
        <button type="button" className="game-btn game-btn--ghost" onClick={onCambiaOpzione}>Gioca un altro esercizio</button>
      </p>
    </>
  );
}

export default function GiocoMappa() {
  const [scelta, setScelta] = useState(OPZIONI[0].id);
  const [fase, setFase] = useState("scelta"); // scelta | caricamento | gioco
  const [partita, setPartita] = useState(null);
  const [generazione, setGenerazione] = useState(0);
  const [errore, setErrore] = useState("");
  // Il testo della partita ripresa da sola: sta qui perche' `Partita` si rimonta (`key`).
  const [avviso, setAvviso] = useState("");
  const [numeroOggi, setNumeroOggi] = useState(null);
  const preaperta = useRef(null);
  const vistaMappa = useRef(null);

  const mappa = useMappa((stato) => {
    if (vistaMappa.current) vistaMappa.current(stato);
  });

  // Un link con `#sfida=` si valida contro il numero della sfida di oggi. Non c'e' una rotta che lo
  // dica senza aprire una partita: se il frammento c'e', se ne apre una (italia, mappa) e la si tiene
  // per quando si preme "Inizia", cosi' non se ne apre una seconda.
  useEffect(() => {
    if (!/^#sfida=/.test(window.location.hash)) return;
    apriSessione("italia", "map").then(({ ok, data }) => {
      if (!ok) return;
      preaperta.current = data;
      setNumeroOggi(Number.isInteger(data.number) ? data.number : null);
    });
  }, []);

  const avviata = fase !== "scelta";
  const sfida = useSfidaCondivisa({ game: GIOCO, numeroOggi, avviata });

  const inizia = useCallback(async (id, avvisoIniziale = "") => {
    const o = OPZIONI.find((x) => x.id === id) || OPZIONI[0];
    const iso = oggiRoma();
    setErrore("");
    setAvviso(avvisoIniziale);
    setFase("caricamento");
    const salvata = leggiSalvata(o.livello, o.modalita, iso);
    if (salvata) {
      setGenerazione((g) => g + 1);
      setPartita(salvata);
      setFase("gioco");
      return;
    }
    let sessione = null;
    if (o.livello === "italia" && o.modalita === "map" && preaperta.current) {
      sessione = preaperta.current;
      preaperta.current = null;
    } else {
      const { ok, status, data } = await apriSessione(o.livello, o.modalita);
      if (!ok) {
        setErrore(messaggioErrore(data.error, status));
        setFase("scelta");
        return;
      }
      sessione = data;
    }
    const nuova = nuovaPartita(sessione);
    salvaPartita(nuova);
    setGenerazione((g) => g + 1);
    setPartita(nuova);
    setFase("gioco");
    trackGameEvent("map_start", { game: GIOCO, mode: "daily", level: o.livello, answer_mode: o.modalita, total: nuova.total });
  }, []);

  // Dimentica la partita salvata e ne apre una nuova. Con `testo` la partita nuova parte dicendolo.
  const riprendi = useCallback((testo = "") => {
    if (partita) dimenticaPartita(partita.level, partita.mode, partita.date);
    inizia(opzione(partita ? partita.level : "italia", partita ? partita.mode : "map").id, testo);
  }, [inizia, partita]);

  const riapri = useCallback(() => riprendi(""), [riprendi]);

  const cambiaOpzione = useCallback(() => {
    mostraMappa(true);
    if (mappa.current) mappa.current.blocca();
    setPartita(null);
    setFase("scelta");
    scrollaSuIsola();
  }, [mappa]);

  // Senza partita la mappa e' ferma e dice di scegliere come giocare: la si vede, ma non si tocca.
  useEffect(() => {
    if (fase === "scelta" && mappa.current) mappa.current.blocca();
  }, [fase, mappa]);

  if (fase === "gioco" && partita) {
    return (
      <Partita
        key={generazione}
        partita={partita}
        sfida={sfida}
        avviso={avviso}
        onPartita={setPartita}
        onCambiaOpzione={cambiaOpzione}
        onRiapri={riapri}
        onRiprendi={riprendi}
        mappa={mappa}
        vistaMappa={vistaMappa}
      />
    );
  }
  return (
    <Scelta
      scelta={scelta}
      onScegli={setScelta}
      onInizia={() => inizia(scelta)}
      occupato={fase === "caricamento"}
      errore={errore}
      sfida={sfida}
      avviata={avviata}
    />
  );
}
