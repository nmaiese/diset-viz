import * as React from "react";

export interface SelectFieldProps {
  /** Field label; omit for a bare select */
  label?: React.ReactNode;
  value?: string | number;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  /** <option> elements */
  children?: React.ReactNode;
  /** stack = label above (detail controls); inline = label left (command bar) */
  layout?: "stack" | "inline";
  /** Optional leading icon in the label (e.g. lucide <Clock3/>) */
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

/** Labelled native select with a chevron overlay. */
export function SelectField(props: SelectFieldProps): JSX.Element;