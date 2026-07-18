import * as React from "react";

export interface SparklineProps {
  /** Series as raw numbers or {value} points */
  data?: Array<number | { value: number }>;
  width?: number;
  height?: number;
  /** Stroke + dot color; pass var(--accent) to echo an active row */
  color?: string;
  style?: React.CSSProperties;
}

/** Tiny trend line with an end dot, used in the indicator index. */
export function Sparkline(props: SparklineProps): JSX.Element;