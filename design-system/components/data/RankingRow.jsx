import React, { useState } from "react";

/**
 * Divario Italia — RankingRow.
 * A row in the regional classifica: rank number, region name, a track bar
 * filled to `fraction` (0..1), and the mono value. Active/hover tints
 * accent-soft and the bar fill goes accent.
 */
export function RankingRow({ rank, region, value, fraction = 0, active = false, onClick, style = {}, ...rest }) {
  const [hover, setHover] = useState(false);
  const lit = active || hover;
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "28px minmax(92px, 1fr) minmax(80px, 1.1fr) minmax(74px, auto)",
        alignItems: "center",
        gap: "10px",
        width: "100%",
        border: `1px solid ${lit ? "rgba(228,87,46,0.3)" : "transparent"}`,
        background: lit ? "var(--accent-soft)" : "transparent",
        textAlign: "left",
        padding: "7px 8px",
        cursor: "pointer",
        borderRadius: 0,
        fontFamily: "var(--font-body)",
        ...style,
      }}
      {...rest}
    >
      <span style={{ fontFamily: "var(--font-mono)", color: "var(--muted)", fontSize: "13px" }}>{rank}</span>
      <span style={{ color: "var(--ink)", fontSize: "14px" }}>{region}</span>
      <span style={{ height: "9px", background: "var(--grid)", overflow: "hidden" }}>
        <i
          style={{
            display: "block",
            height: "100%",
            width: `${Math.max(fraction * 100, 2)}%`,
            background: active ? "var(--accent)" : "var(--ink)",
          }}
        />
      </span>
      <strong style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: "13px" }}>{value}</strong>
    </button>
  );
}