import * as React from "react";

export interface CoveragePillProps {
  children?: React.ReactNode;
  /** default = neutral mono pill; complete = accent-outlined; partial = ink-soft % */
  state?: "default" | "complete" | "partial";
  /** Optional leading icon (e.g. a lucide <Check size={12}/>) */
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

/** Small mono metadata pill: region count, year span, completeness badge. */
export function CoveragePill(props: CoveragePillProps): JSX.Element;