import React from "react";
import { Modal } from "../shared.jsx";

// Le quattro macro-aree del catalogo, come in app/taxonomy.py (MACRO_AREAS).
const MACRO_AREE = ["Economia e opportunità", "Persone e conoscenza", "Territorio e servizi", "Comunità e benessere"];

// Una schermata sola: le aree da cui arrivano gli indizi e la regola in tre righe.
export default function OnboardingModal({ onClose }) {
  return (
    <Modal title="Come si gioca" onClose={onClose} labelledBy="game-onboarding-title">
      <p>Una regione italiana è nascosta. I sei indizi sono dati Istat, presi dalle quattro aree del sito:</p>
      <ul className="game-onboarding-aree">
        {MACRO_AREE.map((area) => (
          <li key={area}>{area}</li>
        ))}
      </ul>
      <ol className="game-onboarding-steps">
        <li>Hai sei tentativi. Ogni errore svela un indizio in più.</li>
        <li>Per ogni indizio vedi se il dato della tua regione è più alto o più basso di quello nascosto.</li>
        <li>Dal terzo errore scopri anche se la regione nascosta è nella tua stessa ripartizione.</li>
      </ol>
      <button type="button" className="game-btn" onClick={onClose}>Ho capito, gioco</button>
    </Modal>
  );
}
