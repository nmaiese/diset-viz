import React from "react";

/**
 * Divario Italia — Insight.
 * A stat block with a mono label, a big mono value, and a caption. Accent
 * left border by default; `variant="region"` fills accent-soft and enlarges
 * the value for the focused-region readout.
 */
export function Insight({ label, value, caption, variant = "default", children, style = {}, ...rest }) {
  const isRegion = variant === "region";
  return (
    <div
      style={{
        display: "grid",
        gap: "4px",
        padding: "12px 14px",
        background: isRegion ? "var(--accent-soft)" : "var(--paper)",
        borderLeft: `3px solid ${isRegion ? "var(--accent)" : "var(--line)"}`,
        borderRadius: 0,
        ...style,
      }}
      {...rest}
    >
      <small style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--muted)", fontSize: "12px" }}>
        {label}
      </small>
      <strong style={{ fontFamily: "var(--font-mono)", fontSize: isRegion ? "24px" : "17px", overflowWrap: "anywhere" }}>
        {value}
      </strong>
      {caption && <span style={{ color: "var(--muted)", fontSize: "13px" }}>{caption}</span>}
      {children}
    </div>
  );
}