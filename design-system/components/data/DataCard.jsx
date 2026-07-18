import React from "react";

/**
 * Divario Italia — DataCard.
 * The panel wrapper for a visualization: hairline border, a mono kicker over
 * an Archivo title, then the chart/content as children.
 */
export function DataCard({ title, kicker, children, style = {}, ...rest }) {
  return (
    <article
      style={{
        background: "var(--panel)",
        border: "1px solid var(--line)",
        padding: "18px",
        minWidth: 0,
        borderRadius: 0,
        ...style,
      }}
      {...rest}
    >
      {(title || kicker) && (
        <header style={{ marginBottom: "14px" }}>
          {kicker && (
            <small
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--muted)",
              }}
            >
              {kicker}
            </small>
          )}
          {title && (
            <h3 style={{ margin: "3px 0 0", fontFamily: "var(--font-display)", fontSize: "21px", letterSpacing: "-0.01em" }}>
              {title}
            </h3>
          )}
        </header>
      )}
      {children}
    </article>
  );
}