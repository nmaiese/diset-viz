import React from "react";

/**
 * Divario Italia — Tag.
 * The theme/category chip. `variant="solid"` is the accent-soft filled tag
 * used on the indicator header; `variant="pill"` is the hairline mono pill
 * used in listings and article cards.
 */
export function Tag({ children, variant = "solid", style = {}, ...rest }) {
  const base = {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontFamily: "var(--font-mono)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    borderRadius: 0,
    whiteSpace: "nowrap",
  };

  const variants = {
    solid: {
      padding: "6px 10px",
      fontSize: "11px",
      background: "var(--accent-soft)",
      color: "var(--accent)",
    },
    pill: {
      padding: "2px 8px",
      fontSize: "11px",
      border: "1px solid var(--line)",
      color: "var(--muted)",
      textTransform: "none",
      letterSpacing: 0,
    },
  };

  return (
    <span style={{ ...base, ...variants[variant], ...style }} {...rest}>
      {children}
    </span>
  );
}