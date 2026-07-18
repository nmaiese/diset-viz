import * as React from "react";

export interface ToggleProps {
  checked?: boolean;
  onChange?: (next: boolean) => void;
  children?: React.ReactNode;
  disabled?: boolean;
  style?: React.CSSProperties;
}

/** Labelled on/off switch — the one rounded element in the system. */
export function Toggle(props: ToggleProps): JSX.Element;