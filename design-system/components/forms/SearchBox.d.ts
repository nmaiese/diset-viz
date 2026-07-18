import * as React from "react";

export interface SearchBoxProps {
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  /** Override the default search glyph */
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

/** Full-width search input with a leading glyph inside a hairline panel. */
export function SearchBox(props: SearchBoxProps): JSX.Element;