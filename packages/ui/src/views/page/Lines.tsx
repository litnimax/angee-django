import type { ReactNode } from "react";
import type { Row } from "@angee/metadata";

import type { ColumnDescriptor } from "./Column";
import { PAGE_ELEMENT_SLOT } from "./types";

/** The form facts a lines footer reads besides the live rows. */
export interface LinesFooterContext {
  /** The loaded record on an edit form; `null` while creating. */
  record: Row | null;
  isCreate: boolean;
}

/**
 * Declarative overrides for a form's editable document lines (F6). Declared as
 * a `Form` child on a resource whose metadata carries `linesResource`; without
 * a `Lines` declaration the composer renders every metadata column in metadata
 * order, exactly as before.
 *
 * `Column` children pick the rendered columns: their order is the column order,
 * and each may override the metadata-derived header, widget, width, and
 * read-only state, or attach a `resolve` hook seeding sibling cells (see
 * `ColumnProps`). A declared field that is not an editable child column fails
 * fast. `footer` renders under the rows and receives the live row values — the
 * document-totals slot; the composing view owns the money math.
 */
export interface LinesProps {
  /** Section heading; defaults to the composer's translated "Lines" label. */
  label?: ReactNode;
  /**
   * Totals footer under the rows. Receives the live line rows (so totals
   * recompute as cells change) and the form facts a preview call needs (the
   * record's company on an edit form); the composer owns rendering, not the
   * math.
   */
  footer?: (rows: readonly Row[], context: LinesFooterContext) => ReactNode;
  /** `Column` declarations overriding the metadata-derived column set. */
  children?: ReactNode;
}

/** The parsed `Lines` declaration a form view consumes. */
export interface LinesDescriptor {
  label?: ReactNode;
  footer?: (rows: readonly Row[], context: LinesFooterContext) => ReactNode;
  /** Declared column overrides, in render order; empty = metadata order. */
  columns: readonly ColumnDescriptor[];
}

function LinesMarker(_props: LinesProps): null {
  return null;
}

/**
 * Marker element for the form's editable-lines section. Parsed by the page
 * declaration walker; renders nothing itself.
 */
export const Lines = Object.assign(LinesMarker, {
  [PAGE_ELEMENT_SLOT]: "lines" as const,
});
