import type { ReactNode } from "react";
import type { Tone } from "../../lib/tones";
import type { WidgetOption } from "../../widgets/types";

import { PAGE_ELEMENT_SLOT } from "./types";

export type PageColumnAlign = "left" | "center" | "right";

/** The live row facts a line column's `resolve` hook reads besides the changed cell. */
export interface LineCellResolveContext {
  /** The edited row's values, with the changed cell already applied. */
  row: Record<string, unknown>;
  /** The edited row's position in the line set. */
  index: number;
  /** Every current line row, in order. */
  rows: readonly Record<string, unknown>[];
}

/**
 * An async row-defaults hook for a line cell: given the changed cell value,
 * return a `{fieldName: value}` map of sibling cells to seed on the same row.
 * See `ColumnProps.resolve`.
 */
export type LineCellResolve = (
  value: unknown,
  context: LineCellResolveContext,
) =>
  | Record<string, unknown>
  | null
  | undefined
  | Promise<Record<string, unknown> | null | undefined>;
export type ColumnAggregate =
  | "count"
  | "sum"
  | "avg"
  | "min"
  | "max"
  | (string & {});

export interface ColumnProps<
  TRow extends object = Record<string, unknown>,
> {
  field: string;
  header?: ReactNode;
  /** Keep an accessible table header while visually hiding its label. */
  headerVisuallyHidden?: boolean;
  widget?: string;
  /** Options passed to enum-like cell widgets; derived from SDL when omitted. */
  options?: readonly WidgetOption[];
  sortable?: boolean;
  aggregate?: ColumnAggregate;
  align?: PageColumnAlign;
  render?: (row: TRow) => ReactNode;
  tone?: Record<string, Tone>;
  /**
   * Lines composer only: the CSS grid track this column occupies (e.g. `"96px"`,
   * `"2fr"`, `"minmax(0, 2fr)"`). Defaults to an equal `minmax(0, 1fr)` share.
   */
  width?: string;
  /** Lines composer only: render this column's cells read-only. */
  readOnly?: boolean;
  /**
   * Lines composer only: seed sibling cells of the same row when this cell
   * changes, resolving defaults asynchronously (a product lookup filling label,
   * UoM, price, taxes). Follows the computed-default law: a returned entry is
   * applied only to cells of that row the user has not manually edited this
   * session; entries for the changed cell itself are ignored; stale in-flight
   * results drop.
   */
  resolve?: LineCellResolve;
}

export interface ColumnDescriptor<
  TRow extends object = Record<string, unknown>,
> {
  field: string;
  /** Concrete GraphQL leaf paths selected when `field` names an object relation. */
  selectionPaths?: readonly string[];
  header?: ReactNode;
  /** Keep an accessible table header while visually hiding its label. */
  headerVisuallyHidden?: boolean;
  widget?: string;
  /** Options passed to enum-like cell widgets; derived from SDL when omitted. */
  options?: readonly WidgetOption[];
  sortable?: boolean;
  aggregate?: ColumnAggregate;
  align?: PageColumnAlign;
  render?: (row: TRow) => ReactNode;
  tone?: Record<string, Tone>;
  /** Money widget: path to the FK owning the row's currency (see `WidgetField.currencyField`). */
  currencyField?: string;
  /** Lines composer only: the CSS grid track this column occupies (see `ColumnProps.width`). */
  width?: string;
  /** Lines composer only: render this column's cells read-only (see `ColumnProps.readOnly`). */
  readOnly?: boolean;
  /** Lines composer only: async sibling-cell defaults on change (see `ColumnProps.resolve`). */
  resolve?: LineCellResolve;
}

/**
 * The tone a column's `tone` map assigns to a cell value: the descriptor answers
 * about its own value→tone vocabulary (a nullish value reads as the empty label),
 * falling back to `neutral`. The one owner of the `column.tone[label] ?? "neutral"`
 * read — both the table cell and the board lane dot route through it. Returns
 * `undefined` when the column declares no tone map (the caller renders plainly).
 */
export function columnTone<TRow extends object>(
  column: ColumnDescriptor<TRow>,
  value: unknown,
): Tone | undefined {
  if (!column.tone) return undefined;
  const label = value == null ? "" : String(value);
  return column.tone[label] ?? "neutral";
}

function ColumnMarker<
  TRow extends object = Record<string, unknown>,
>(_props: ColumnProps<TRow>): null {
  return null;
}

export const Column = Object.assign(ColumnMarker, {
  [PAGE_ELEMENT_SLOT]: "column" as const,
});
