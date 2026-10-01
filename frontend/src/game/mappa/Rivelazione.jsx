import React from "react";
import { testoEsito } from "./partita.js";

// La forma dell'esito: mai il solo colore. Cerchio con spunta per l'esatta, mezzo cerchio per la
// stessa regione, croce per la sbagliata. Le stesse forme stanno sulla mappa (segni nell'<svg>).
function Segno({ segno }) {
  return (
    <svg className={`mappa-esito-segno mappa-esito-segno--${segno}`} viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
      {segno === "esatto" && (<><circle cx="12" cy="12" r="10" /><path d="M7 12.5l3.5 3.5L17 8.5" /></>)}
      {segno === "vicino" && (<><circle cx="12" cy="12" r="9" className="mappa-esito-contorno" /><path d="M12 3a9 9 0 0 1 0 18z" /></>)}
      {segno === "errore" && (<><rect x="3" y="3" width="18" height="18" /><path d="M8 8l8 8M16 8l-8 8" /></>)}
    </svg>
  );
}

// La rivelazione dopo una risposta, in una regione `aria-live`. Dice esito, punti e, sulla mappa, la
// distanza come stima (il testo e' di `testoEsito`), e linka la scheda della provincia giusta.
export function Rivelazione({ risposta, modalita }) {
  const esito = risposta ? testoEsito(risposta, modalita) : null;
  const sulla = modalita === "map" && risposta && risposta.esito !== "exact";
  return (
    <div className="mappa-rivelazione" aria-live="polite" aria-atomic="true">
      {esito && (
        <>
          <p className={`mappa-verdetto mappa-verdetto--${esito.segno}`}>
            <Segno segno={esito.segno} /> <strong>{esito.verdetto}</strong>
          </p>
          <p className="mappa-dettaglio">{esito.dettaglio}</p>
          {sulla && (
            <p className="mappa-legenda">Sulla mappa: il cerchio con la spunta è la provincia giusta, il quadrato con la croce è la tua scelta.</p>
          )}
          <p className="mappa-scheda">
            <a href={risposta.right.path}>Vai alla scheda: {risposta.right.name}</a>
          </p>
        </>
      )}
    </div>
  );
}
