import React from "react";
import { Modal } from "../shared.jsx";

export default function ArchiveModal({ list, currentPuzzleId, onPick, onClose }) {
  return (
    <Modal title="Sfide passate" onClose={onClose} labelledBy="game-archive-title">
      {list === null && (
        <div className="skel-bars" style={{ marginTop: 0 }} aria-hidden="true">
          <span style={{ height: 44 }} />
          <span style={{ height: 44 }} />
          <span style={{ height: 44 }} />
        </div>
      )}
      {list !== null && list.length === 0 && <p>Nessuna sfida passata disponibile ancora.</p>}
      {list !== null && list.length > 0 && (
        <ul className="game-archive-list">
          {list.map((item) => (
            <li key={item.date}>
              <button
                type="button"
                className={currentPuzzleId === `daily:${item.date}` ? "is-active" : ""}
                onClick={() => onPick(item.date)}
              >
                <span>Sfida #{item.number}</span>
                <span>{item.date}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
