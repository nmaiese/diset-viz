import React, { forwardRef } from "react";
import { opzione, testoDomanda, testoIstruzione } from "./partita.js";

// "Domanda 3 di 10" e la domanda. Il focus ci arriva a ogni domanda nuova (tabIndex -1), cosi' chi usa
// la tastiera o un lettore di schermo sente la domanda prima di cercare sulla mappa. Il totale e il
// punteggio massimo vengono dal server: finche' non ci sono, un trattino.
export const Domanda = forwardRef(function Domanda({ partita, domanda, vista, selezionata, rivelata }, ref) {
  const indice = domanda ? domanda.index + 1 : null;
  return (
    <div className="mappa-domanda-blocco">
      <p className="mappa-stato">
        <span className="qz-badge">Domanda <strong>{indice ?? "-"}</strong> di <strong>{partita.total ?? "-"}</strong></span>
        <span className="qz-badge">Punti <strong>{partita.punti}</strong> su <strong>{partita.points_max ?? "-"}</strong></span>
        <span className="qz-badge qz-badge--level">{opzione(partita.level, partita.mode).titolo}</span>
      </p>
      <h2 className="mappa-domanda" ref={ref} tabIndex={-1}>{testoDomanda(domanda)}</h2>
      <p className="mappa-istruzione" role="status" aria-live="polite">
        {rivelata ? "" : testoIstruzione({ modalita: partita.mode, vista, selezionata })}
      </p>
    </div>
  );
});
