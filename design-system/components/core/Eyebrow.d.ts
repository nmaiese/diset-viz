import * as React from "react";

export interface EyebrowProps {
  children?: React.ReactNode;
  /** accent = terracotta kicker (hero/blog); muted = quiet section label */
  tone?: "accent" | "muted";
  /** Element to render as (default "p"; use "span" inline) */
  as?: keyof JSX.IntrinsicElements;
  style?: React.CSSProperties;
}

/** Uppercase Space Mono kicker set above headlines. */
export function Eyebrow(props: EyebrowProps): JSX.Element;