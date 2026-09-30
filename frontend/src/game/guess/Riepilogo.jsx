import React from "react";
import { formatValue } from "../shared.jsx";

// "Che cosa misura" di un indicatore: la descrizione, come si legge il valore e
// la lettura, i tre testi che il backend passa a ogni riga del recap.
function CheCosaMisura({ row }) {
  const testi = [row.description, row.value_explanation, row.reading].filter(Boolean);
  if (!testi.length) return null;
  return (
    <p className="game-recap-misura">
      <strong>Che cosa misura.</strong> {testi.join(" ")}
    </p>
  );
}

// Gli indicatori della sfida uno per uno, a fine partita: valore del territorio,
// media dei territori, anno e "Che cosa misura", con il link alla scheda.
//   rows       [{ id, name, path, value, unit, year, media, description, value_explanation, reading }]
//   soggetto   nome del territorio misterioso ("Toscana")
//   mediaLabel "Media delle regioni" o "Media delle province"
export default function Riepilogo({ rows, soggetto, mediaLabel }) {
  return (
    <section className="game-recap" aria-label="Gli indicatori della sfida">
      <h3>Gli indicatori, uno per uno</h3>
      <ol className="game-recap-list">
        {rows.map((row) => (
          <li key={row.id}>
            <p className="game-recap-nome">
              <a href={row.path}>{row.name}</a>
            </p>
            <p className="game-recap-valori">
              <span>{soggetto}: <strong>{formatValue(row.value, row.unit)}</strong></span>
              <span>{mediaLabel}: {formatValue(row.media, row.unit)}</span>
              {row.year && <span>Anno {row.year}</span>}
            </p>
            <CheCosaMisura row={row} />
          </li>
        ))}
      </ol>
    </section>
  );
}
