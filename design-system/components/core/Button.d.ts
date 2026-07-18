import * as React from "react";

export interface ButtonProps {
  children?: React.ReactNode;
  /** primary = accent fill; secondary = ink-outlined panel; outline = hairline panel that warms to accent; ghost = link-like */
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md";
  /** Icon element rendered before the label (e.g. a lucide <ArrowLeft/>) */
  iconLeft?: React.ReactNode;
  /** Icon element rendered after the label */
  iconRight?: React.ReactNode;
  disabled?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  type?: "button" | "submit" | "reset";
  style?: React.CSSProperties;
}

/**
 * Square, hairline-bordered button. Primary uses the single brand accent;
 * outline/secondary variants warm to the accent on hover.
 * @startingPoint section="Core" subtitle="Buttons — primary, secondary, outline, ghost" viewport="700x150"
 */
export function Button(props: ButtonProps): JSX.Element;