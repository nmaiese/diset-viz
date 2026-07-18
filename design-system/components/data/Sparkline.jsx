import React from "react";

/**
 * Divario Italia — Sparkline.
 * A tiny SVG trend line (national-average series) with an end dot. Ink-soft
 * by default; pass color="var(--accent)" to echo a hover/active row.
 * `data` is an array of numbers or {value} points.
 */
export function Sparkline({ data = [], width = 150, height = 40, color = "var(--ink-soft)", style = {} }) {
  const points = data
    .map((d) => (typeof d === "number" ? d : d && d.value))
    .filter((v) => typeof v === "number" && isFinite(v));

  if (points.length < 2) {
    return <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", ...style }} aria-hidden="true" />;
  }

  const pad = 3;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const n = points.length;
  const x = (i) => pad + (i / (n - 1)) * (width - pad * 2);
  const y = (v) => height - pad - ((v - min) / span) * (height - pad * 2);
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Andamento medio nazionale"
      style={{ display: "block", ...style }}
    >
      <path d={d} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={x(n - 1)} cy={y(points[n - 1])} r="2.6" fill={color} />
    </svg>
  );
}