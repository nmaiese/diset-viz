import * as React from "react";

export interface MacroTabProps {
  children?: React.ReactNode;
  /** Optional mono count shown after the label */
  count?: number | string | null;
  active?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  style?: React.CSSProperties;
}

/**
 * Segmented macro-area filter tab: hairline panel, accent on hover, ink when active.
 * @startingPoint section="Navigation" subtitle="Segmented macro-area filter tabs" viewport="700x120"
 */
export function MacroTab(props: MacroTabProps): JSX.Element;