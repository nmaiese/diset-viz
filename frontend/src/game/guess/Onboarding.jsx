import React from "react";
import { Modal } from "../shared.jsx";

export default function OnboardingModal({ onClose }) {
  return (
    <Modal title="Come si gioca" onClose={onClose} labelledBy="game-onboarding-title">
      <ol className="game-onboarding-steps">
        <li>
          <strong>Un indizio alla volta.</strong> Ogni sfida nasconde una regione italiana dietro sei indicatori
          Istat, uno per ogni macro-area: economia, lavoro e istruzione, società, ambiente, demografia e
          salute, istituzioni.
        </li>
        <li>
          <strong>Indovina o sbaglia, impari comunque.</strong> Ogni tentativo sbagliato rivela un nuovo indizio
          e ti dice se il tuo valore è più alto o più basso di quello della regione misteriosa. Dal terzo
          errore scopri anche la ripartizione geografica.
        </li>
        <li>
          <strong>Sei tentativi.</strong> Alla fine trovi il profilo completo della regione, con tutti gli
          indicatori usati e il confronto con la media semplice delle regioni.
        </li>
      </ol>
      <button type="button" className="game-btn" onClick={onClose}>Ho capito, gioco</button>
    </Modal>
  );
}
