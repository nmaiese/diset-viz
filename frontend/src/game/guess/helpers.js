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

const MESI = [
  "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
  "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
];

// "2026-09-12" diventa "12 settembre". La data si spezza a mano: con `new Date`
// la stringa ISO e' mezzanotte UTC e in un fuso a ovest mostrerebbe il giorno prima.
export function dataInChiaro(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!m) return "";
  return `${Number(m[3])} ${MESI[Number(m[2]) - 1]}`;
}
