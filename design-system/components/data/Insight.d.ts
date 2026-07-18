import * as React from "react";

export interface InsightProps {
  /** Mono label (may include a leading icon) */
  label?: React.ReactNode;
  /** The headline value (mono, tabular) */
  value?: React.ReactNode;
  /** Caption line beneath the value */
  caption?: React.ReactNode;
  /** default = accent left rule on paper; region = accent-soft fill, larger value */
  variant?: "default" | "region";
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

/** Stat block: mono label, big mono value, caption; region variant is the focused readout. */
export function Insight(props: InsightProps): JSX.Element;