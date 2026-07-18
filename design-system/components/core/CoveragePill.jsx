import React from "react";

/**
 * Divario Italia — CoveragePill.
 * The mono metadata pill from the indicator index: region count, year span,
 * and a completeness badge. `state="complete"` outlines in accent with a
 * check; `state="partial"` shows the percentage in ink-soft.
 */
export function CoveragePill({ children, state = "default", icon = null, style = {}, ...rest }) {
  const base = {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "2px 7px",
    border: "1px solid var(--line)",
    fontFamily: "var(--font-mono)",
    fontSize: "11px",
    color: "var(--muted)",
    borderRadius: 0,
    whiteSpace: "nowrap",
  };

  const states = {
    default: null,
    complete: { color: "var(--accent)", borderColor: "var(--accent)" },
    partial: { color: "var(--ink-soft)" },
  };

  return (
    <span style={{ ...base, ...states[state], ...style }} {...rest}>
      {icon}
      {children}
    </span>
  );
}