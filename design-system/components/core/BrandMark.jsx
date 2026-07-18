import React from "react";

/**
 * Divario Italia — BrandMark.
 * Full brand lockup: the Italy+bars mark (green top / red bottom split by
 * an accent diagonal) followed by the Archivo wordmark "DIVARIO ITALIA".
 * `showText={false}` renders the mark alone for compact placements.
 * The mark is a raster (../assets/logo-mark.png relative to the template that
 * imports it — the design system exposes it as `assets/logo-mark.png`).
 */
export function BrandMark({
  showText = true,
  title = "Divario Italia",
  subtitle = "Atlante degli indicatori territoriali",
  size = 40,
  href = "/",
  markSrc,
  style = {},
  ...rest
}) {
  // Auto-resolve mark path from the DS bundle location so the same
  // component works from templates/<slug>/ (../../assets/…) AND from the
  // project root (assets/…). Consumers can override with markSrc.
  const resolvedMark = (() => {
    if (markSrc) return markSrc;
    if (typeof document === "undefined") return "assets/logo-mark.png";
    const bundleScript = document.querySelector(
      'script[src*="_ds_bundle.js"]'
    );
    if (bundleScript) {
      try {
        return new URL("assets/logo-mark.png", bundleScript.src).toString();
      } catch (_e) {}
    }
    return new URL(
      "assets/logo-mark.png",
      document.baseURI.replace(/[^/]+$/, "")
    ).toString();
  })();

  const wordSize = Math.round(size * 0.42);

  return (
    <a
      href={href}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: `${Math.round(size * 0.28)}px`,
        color: "var(--ink)",
        textDecoration: "none",
        lineHeight: 1,
        ...style,
      }}
      {...rest}
    >
      <img
        src={resolvedMark}
        alt=""
        width={size}
        height={size}
        style={{ display: "block", flex: "0 0 auto", objectFit: "contain" }}
      />
      {showText && (
        <span style={{ display: "grid", lineHeight: 1.05 }}>
          <strong
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: `${wordSize}px`,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
              color: "var(--ink)",
            }}
          >
            {title}
          </strong>
          {subtitle && (
            <small
              style={{
                marginTop: "3px",
                fontFamily: "var(--font-mono)",
                color: "var(--muted)",
                fontSize: `${Math.max(10, Math.round(size * 0.28))}px`,
                letterSpacing: "0.02em",
                fontWeight: 400,
              }}
            >
              {subtitle}
            </small>
          )}
        </span>
      )}
    </a>
  );
}