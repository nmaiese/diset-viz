import React, { forwardRef } from "react";
import { createPortal } from "react-dom";

// I tasti in basso, nella zona del pollice (`#mappa-azioni`, sotto la mappa). "Conferma" e' alto 48 px
// e NON e' `disabled` quando manca la scelta: un bottone disabilitato non prende il focus, e Tab deve
// poterlo raggiungere. Ha `aria-disabled`, e senza una scelta il click dice cosa manca (lo decide chi lo usa).
export const Conferma = forwardRef(function Conferma({ pronta, occupato, onConferma }, ref) {
  return (
    <button
      type="button"
      ref={ref}
      className="game-btn mappa-conferma"
      aria-disabled={pronta && !occupato ? undefined : "true"}
      aria-busy={occupato ? "true" : undefined}
      onClick={() => {
        if (!occupato) onConferma();
      }}
    >
      Conferma
    </button>
  );
});

export const Avanti = forwardRef(function Avanti({ etichetta, onAvanti }, ref) {
  return (
    <button type="button" ref={ref} className="game-btn mappa-avanti" onClick={onAvanti}>
      {etichetta}
    </button>
  );
});

// Il portale: i figli finiscono nel `<div id="mappa-azioni">` del template, che sta dopo la mappa.
export function InAzioni({ children }) {
  const ospite = typeof document !== "undefined" ? document.getElementById("mappa-azioni") : null;
  return ospite ? createPortal(children, ospite) : null;
}
