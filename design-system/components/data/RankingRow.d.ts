import * as React from "react";

export interface RankingRowProps {
  rank: number | string;
  region: React.ReactNode;
  /** Formatted value (mono, tabular) */
  value: React.ReactNode;
  /** Bar fill fraction 0..1 */
  fraction?: number;
  active?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  style?: React.CSSProperties;
}

/** A row in the regional ranking: rank, region, track bar, mono value. */
export function RankingRow(props: RankingRowProps): JSX.Element;