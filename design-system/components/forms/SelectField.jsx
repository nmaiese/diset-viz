import React from "react";

/**
 * Divario Italia — SelectField.
 * A labelled native <select> with a chevron overlay. `layout="stack"` puts
 * the label above (detail controls); `layout="inline"` sits it to the left
 * (command bar). Label is Space Mono / uppercase for command-bar style or a
 * bold ink-soft caption when stacked.
 */
export function SelectField({
  label,
  value,
  onChange,
  children,
  layout = "stack",
  icon = null,
  style = {},
  ...rest
}) {
  const inline = layout === "inline";
  const chevron = (
    <svg
      aria-hidden="true"
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{
        position: "absolute",
        right: "12px",
        top: inline ? "50%" : "auto",
        bottom: inline ? "auto" : "13px",
        transform: inline ? "translateY(-50%)" : "none",
        pointerEvents: "none",
        color: "var(--muted)",
      }}
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );

  return (
    <label
      style={{
        position: "relative",
        display: inline ? "inline-flex" : "grid",
        alignItems: inline ? "center" : undefined,
        gap: inline ? "8px" : "6px",
        ...style,
      }}
      {...rest}
    >
      {label && (
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "12px",
            fontWeight: 700,
            color: "var(--muted)",
          }}
        >
          {icon}
          {label}
        </span>
      )}
      <span style={{ position: "relative", display: "grid" }}>
        <select
          value={value}
          onChange={onChange}
          style={{
            appearance: "none",
            WebkitAppearance: "none",
            border: "1px solid var(--line)",
            background: "var(--panel)",
            color: "var(--ink)",
            padding: "11px 38px 11px 13px",
            outline: "none",
            minWidth: "160px",
            fontFamily: "var(--font-body)",
            fontSize: "14px",
            borderRadius: 0,
          }}
        >
          {children}
        </select>
        {chevron}
      </span>
    </label>
  );
}