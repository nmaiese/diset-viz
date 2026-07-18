import * as React from "react";

export interface TagProps {
  children?: React.ReactNode;
  /** solid = accent-soft filled theme tag; pill = hairline mono pill for listings */
  variant?: "solid" | "pill";
  style?: React.CSSProperties;
}

/** Category / theme chip in Space Mono. */
export function Tag(props: TagProps): JSX.Element;