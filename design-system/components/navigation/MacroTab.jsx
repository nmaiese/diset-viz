import React, { useState } from "react";

/**
 * Divario Italia — MacroTab.
 * A segmented spine tab (macro-area filter). Hairline panel that warms to
 * the accent on hover and inverts to ink when active. Optional mono count.
 */
export function MacroTab({ children, count = null, active = false, onClick, style = {}, ...rest }) {
  const [hover, setHover] = useState(false);
  const isActive = active;
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        padding: "7px 13px",
        border: `1px solid ${isActive ? "var(--ink)" : hover ? "var(--accent)" : "var(--line)"}`,
        background: isActive ? "var(--ink)" : "var(--panel)",
        color: isActive ? "var(--paper)" : hover ? "var(--ink)" : "var(--ink-soft)",
        fontFamily: "var(--font-mono)",
        fontSize: "12.5px",
        cursor: "pointer",
        borderRadius: 0,
        transition: "border-color 140ms ease, color 140ms ease, background 140ms ease",
        ...style,
      }}
      {...rest}
    >
      {children}
      {count != null && (
        <em style={{ fontStyle: "normal", color: isActive ? "rgba(251,250,247,0.7)" : "var(--muted)" }}>
          {count}
        </em>
      )}
    </button>
  );
}