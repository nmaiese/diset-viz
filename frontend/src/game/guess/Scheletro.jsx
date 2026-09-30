import React from "react";

// Lo scheletro di una partita che si carica. Compare dopo 150 ms (guess.css, `qz-scheletro-appare`):
// una sfida che arriva subito non lampeggia, una lenta ha qualcosa da mostrare.
export default function Scheletro() {
  return (
    <div className="qz-scheletro" aria-hidden="true">
      <div className="game-head">
        <span className="skel-bar" style={{ height: 22, width: "40%" }} />
        <div className="game-attempts">
          {Array.from({ length: 6 }).map((_, i) => (
            <span key={i} className="seg" />
          ))}
        </div>
      </div>
      <div className="skel-bars" style={{ marginTop: 18 }}>
        <span style={{ height: 96 }} />
        <span style={{ height: 96 }} />
      </div>
    </div>
  );
}
