import React from "react";

// "Senza mappa: conta la regione". Un gruppo di radio nativi delle venti regioni (bersagli di
// 44 px, tastiera gratis): e' un altro esercizio, e la pagina lo dice. Le regioni vengono dal server.
export function SenzaMappa({ regioni, scelta, onScegli, disabilitato }) {
  return (
    <fieldset className="mappa-regioni" disabled={disabilitato}>
      <legend className="visually-hidden">Regioni</legend>
      {regioni.map((regione) => (
        <label key={regione.key} className={scelta === regione.key ? "mappa-regione-voce is-scelta" : "mappa-regione-voce"}>
          <input
            type="radio"
            name="mappa-regione"
            value={regione.key}
            checked={scelta === regione.key}
            onChange={() => onScegli(regione.key)}
          />
          <span>{regione.name}</span>
        </label>
      ))}
    </fieldset>
  );
}
