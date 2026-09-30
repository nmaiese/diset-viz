import React from "react";
import { formatValue, SourceStrip } from "../shared.jsx";
import { ordinal } from "./helpers.js";

// Il nome dell'indizio e' un link alla scheda dell'indicatore anche durante la
// partita. Si apre in un'altra scheda: la partita resta dov'e', e l'allenamento
// non ha un salvataggio che sopravviva a una navigazione.
function NomeIndizio({ clue }) {
  if (!clue.path) return clue.name;
  return (
    <a href={clue.path} target="_blank" rel="noopener noreferrer">
      {clue.name}
      <span className="visually-hidden"> (si apre in una nuova scheda)</span>
    </a>
  );
}

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
                  <td className="v"><span aria-hidden="true">?</span></td>
                </tr>
              );
            }
            const isLatest = i === latestIndex && playing;
            return (
              <tr key={clue.id} className={isLatest ? "latest" : ""}>
                <td className="n">{i + 1}</td>
                <td>
                  <strong>{clue.theme}</strong> · <NomeIndizio clue={clue} />
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
            <strong>Indizio {clues.length}</strong> · <NomeIndizio clue={latest} />
            {latest.description ? `: ${latest.description}` : "."}
            {latest.reading ? ` ${latest.reading}` : ""}{" "}
            <span className="qz-clue-rank">{ordinal(latest.rank)} su {latest.region_count ?? latest.province_count}</span>
          </p>
          <SourceStrip year={latest.year} sourceLabel={latest.source_label} sourceUrl={latest.source_url} />
        </div>
      )}
    </>
  );
}
