import * as React from "react";

export interface DataCardProps {
  /** Archivo card title */
  title?: React.ReactNode;
  /** Mono uppercase kicker above the title (e.g. year / unit) */
  kicker?: React.ReactNode;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

/** Panel wrapper for a visualization: hairline border, mono kicker + Archivo title. */
export function DataCard(props: DataCardProps): JSX.Element;