import React from "react";

/**
 * Divario Italia — Eyebrow.
 * The uppercase Space Mono kicker above headlines. Accent by default
 * (hero, blog), muted for quieter section labels.
 */
export function Eyebrow({ children, tone = "accent", as = "p", style = {}, ...rest }) {
  const Tag = as;
  const tones = {
    accent: "var(--accent)",
    muted: "var(--muted)",
  };
  return (
    <Tag
      style={{
        margin: 0,
        fontFamily: "var(--font-mono)",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontSize: "12px",
        color: tones[tone],
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}