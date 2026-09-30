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

// Il valore: il numero in evidenza e l'unita' sotto, piccola, cosi' la colonna dei nomi non si stringe.
// Letto da un lettore di schermo e' "13,8 numero per mille abitanti", come `formatValue`.
function Valore({ clue }) {
  const intero = formatValue(clue.value, clue.unit);
  const numero = formatValue(clue.value, "");
  const unita = intero.startsWith(numero) ? intero.slice(numero.length).trim() : "";
  // Un'unita' breve ("%") resta accanto al numero: sotto, da sola, si leggerebbe come una riga persa.
  if (!unita || unita.length <= 3) return intero;
  return (
    <>
      <span className="v-num">{numero}</span>{" "}
      <span className="v-unita">{unita}</span>
    </>
  );
}

// La tabella dei sei indizi, compatta: il nome e il valore, una riga ciascuno (quelli non ancora
// svelati restano bloccati). Il tema si vede solo dove c'e' posto (guess.css lo toglie da telefono).
// L'indizio appena svelato entra con un'evidenza che svanisce, e solo se si e' in partita.
export function TabellaIndizi({ clues, total, playing }) {
  const latestIndex = clues.length - 1;
  return (
    <table className="qz-clues" aria-label="Indizi">
      <tbody>
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
                <span className="qz-tema"><strong>{clue.theme}</strong> · </span>
                <NomeIndizio clue={clue} />
              </td>
              <td className="v"><Valore clue={clue} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// "Che cosa misura" dell'ultimo indizio svelato, in un riquadro chiuso: la spiegazione e' lunga e
// da telefono non deve stare fra la tabella e il campo di risposta. La `key` (l'id dell'indizio)
// lo richiude a ogni indizio nuovo. Senza testi, resta la posizione e la fonte: mai un punto da solo.
export function CheCosaMisura({ clues, game }) {
  const latest = clues[clues.length - 1];
  if (!latest) return null;
  const testo = [latest.description, latest.reading].filter(Boolean).join(" ");
  return (
    <details className="qz-clue-desc" key={latest.id}>
      <summary>Che cosa misura</summary>
      <p>
        <strong>Indizio {clues.length}</strong> · <NomeIndizio clue={latest} />
        {testo ? `: ${testo}` : ""}{" "}
        <span className="qz-clue-rank">{ordinal(latest.rank)} su {latest.region_count ?? latest.province_count}</span>
      </p>
      <SourceStrip year={latest.year} sourceLabel={latest.source_label} sourceUrl={latest.source_url} game={game} />
    </details>
  );
}

export default TabellaIndizi;
