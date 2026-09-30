// Piccole funzioni pure di Indovina la Regione: testo, confronti, countdown.

export function normalize(value) {
  return (value || "")
    .toString()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function ordinal(rank) {
  return Number.isFinite(rank) ? `${rank}ª` : "n.d.";
}

export function comparisonArrow(comparison) {
  if (comparison === "higher") return "↑";
  if (comparison === "lower") return "↓";
  if (comparison === "equal") return "=";
  return "?";
}

export function comparisonText(comparison) {
  if (comparison === "higher") return "più alta della misteriosa";
  if (comparison === "lower") return "più bassa della misteriosa";
  if (comparison === "equal") return "uguale alla misteriosa";
  return "dato non disponibile";
}

export function countdownParts(targetIso, nowMs) {
  if (!targetIso) return null;
  const diff = new Date(targetIso).getTime() - nowMs;
  if (!Number.isFinite(diff)) return null;
  const totalSec = Math.max(0, Math.floor(diff / 1000));
  const h = String(Math.floor(totalSec / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
  const s = String(totalSec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}
