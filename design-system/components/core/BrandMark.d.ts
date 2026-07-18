import * as React from "react";

export interface BrandMarkProps {
  /** Show the Archivo wordmark + standfirst next to the mark */
  showText?: boolean;
  title?: string;
  subtitle?: string;
  /** Mark image size in px (wordmark scales with it) */
  size?: number;
  href?: string;
  /** Override the mark image URL (defaults to assets/logo-mark.png resolved from the document) */
  markSrc?: string;
  style?: React.CSSProperties;
}

/** Divario Italia brand lockup: Italy+bars mark and Archivo wordmark. */
export function BrandMark(props: BrandMarkProps): JSX.Element;