import React from "react";

/**
 * Divario Italia — SearchBox.
 * The full-width search input from the atlas command bar: a leading search
 * glyph and a borderless input inside a hairline panel.
 */
export function SearchBox({
  value,
  onChange,
  placeholder = "Cerca…",
  icon = null,
  style = {},
  ...rest
}) {
  const defaultIcon = (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--muted)", flex: "0 0 auto" }}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "14px 16px",
        background: "var(--panel)",
        border: "1px solid var(--line)",
        borderRadius: 0,
        ...style,
      }}
    >
      {icon || defaultIcon}
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        aria-label={placeholder}
        style={{
          width: "100%",
          border: 0,
          background: "transparent",
          outline: "none",
          fontSize: "16px",
          fontFamily: "var(--font-body)",
          color: "var(--ink)",
        }}
        {...rest}
      />
    </label>
  );
}