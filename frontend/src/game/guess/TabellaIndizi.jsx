import React from "react";
import { formatValue, SourceStrip } from "../shared.jsx";
import { ordinal } from "./helpers.js";

// La tabella dei sei indizi (quelli non ancora svelati restano bloccati) e la
// descrizione dell'ultimo svelato.
export default function TabellaIndizi({ clues, total, playing, bodyRef }) {
  const latest = clues[clues.length - 1];
  const latestIndex = clues.length - 1;
  return (
    <>
      <table className="qz-clues" aria-label="Indizi">
        <tbody ref={bodyRef}>
          {Array.from({ length: total }).map((_, i) => {
            const clue = clues[i];
            if (!clue) {
              return (
                <tr key={`locked-${i}`} className="locked">
                  <td className="n">{i + 1}</td>
                  <td className="theme">Indizio da svelare</td>
                  <td className="v">—</td>
                </tr>
              );
            }
            const isLatest = i === latestIndex && playing;
            return (
              <tr key={clue.id} className={isLatest ? "latest" : ""}>
                <td className="n">{i + 1}</td>
                <td>
                  <strong>{clue.theme}</strong> · {clue.name}
                </td>
                <td className="v">{formatValue(clue.value, clue.unit)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {latest && (
        <div className="qz-clue-desc">
          <p>
            <strong>Indizio {clues.length}</strong> · {latest.name}
            {latest.description ? `: ${latest.description}` : "."}
            {latest.reading ? ` ${latest.reading}` : ""}{" "}
            <span className="qz-clue-rank">{ordinal(latest.rank)} su {latest.region_count}</span>
          </p>
          <SourceStrip year={latest.year} sourceLabel={latest.source_label} sourceUrl={latest.source_url} />
        </div>
      )}
    </>
  );
}
