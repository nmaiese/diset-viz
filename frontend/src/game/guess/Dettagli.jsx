import React from "react";

// Un riquadro chiuso della fine partita: il titolo dice che cosa c'e' dentro e quanto (il conteggio viene
// dai dati, mai scritto a mano). A partita finita l'esito sta in `FinePartita` e tutto il resto si apre
// a richiesta, cosi' da telefono l'esito, il nome e "Condividi" stanno in una schermata.
export default function Dettagli({ titolo, children }) {
  return (
    <details className="game-dettagli">
      <summary>{titolo}</summary>
      <div className="game-dettagli-corpo">{children}</div>
    </details>
  );
}
