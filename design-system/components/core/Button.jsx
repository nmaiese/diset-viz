import React, { useState } from "react";

/**
 * Divario Italia — Button.
 * Square, hairline-bordered controls. The single accent carries primary
 * actions; everything else is an outlined panel that warms to the accent
 * on hover. No rounded corners.
 */
export function Button({
  children,
  variant = "secondary", // primary | secondary | outline | ghost
  size = "md",           // sm | md
  iconLeft = null,
  iconRight = null,
  disabled = false,
  onClick,
  type = "button",
  style = {},
  ...rest
}) {
  const [hover, setHover] = useState(false);

  const sizes = {
    sm: { padding: "8px 13px", fontSize: "13.5px" },
    md: { padding: "11px 18px", fontSize: "14px" },
  };

  const base = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "6px",
    fontFamily: "var(--font-body)",
    fontWeight: 700,
    lineHeight: 1,
    borderRadius: 0,
    border: "1px solid transparent",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.4 : 1,
    transition: "border-color var(--dur) ease, color var(--dur) ease, background var(--dur) ease, filter var(--dur) ease",
    ...sizes[size],
  };

  const variants = {
    primary: {
      background: "var(--accent)",
      color: "#fff",
      borderColor: "var(--accent)",
      ...(hover && !disabled ? { filter: "brightness(1.06)" } : null),
    },
    secondary: {
      background: "var(--panel)",
      color: "var(--ink)",
      borderColor: "var(--ink)",
      ...(hover && !disabled ? { background: "var(--accent-soft)" } : null),
    },
    outline: {
      background: "var(--panel)",
      color: hover && !disabled ? "var(--accent)" : "var(--ink-soft)",
      borderColor: hover && !disabled ? "var(--accent)" : "var(--line)",
    },
    ghost: {
      background: "transparent",
      color: "var(--accent)",
      borderColor: "transparent",
      padding: size === "sm" ? "2px 0" : "4px 0",
      textDecoration: hover && !disabled ? "underline" : "none",
    },
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ ...base, ...variants[variant], ...style }}
      {...rest}
    >
      {iconLeft}
      {children}
      {iconRight}
    </button>
  );
}