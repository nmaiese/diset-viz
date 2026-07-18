import React from "react";

/**
 * Divario Italia — Toggle.
 * The one rounded element in the system: a labelled on/off switch. Off is a
 * hairline track; on turns the track and border accent. Rendered as a button
 * with aria-pressed.
 */
export function Toggle({ checked = false, onChange, children, disabled = false, style = {}, ...rest }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-pressed={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange && onChange(!checked)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "9px",
        padding: "10px 14px",
        border: `1px solid ${checked ? "var(--accent)" : "var(--line)"}`,
        background: "var(--panel)",
        fontSize: "14px",
        color: checked ? "var(--ink)" : "var(--ink-soft)",
        fontFamily: "var(--font-body)",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.4 : 1,
        borderRadius: 0,
        ...style,
      }}
      {...rest}
    >
      <span
        aria-hidden="true"
        style={{
          position: "relative",
          width: "32px",
          height: "18px",
          borderRadius: "999px",
          background: checked ? "var(--accent)" : "var(--line)",
          transition: "background 160ms ease",
          flex: "0 0 auto",
        }}
      >
        <span
          style={{
            position: "absolute",
            top: "2px",
            left: "2px",
            width: "14px",
            height: "14px",
            borderRadius: "50%",
            background: "var(--panel)",
            transform: checked ? "translateX(14px)" : "translateX(0)",
            transition: "transform 160ms ease",
          }}
        />
      </span>
      {children}
    </button>
  );
}