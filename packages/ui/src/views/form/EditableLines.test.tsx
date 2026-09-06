// @vitest-environment happy-dom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import type { DataResourceLinesMetadata } from "@angee/metadata";
import { afterEach, describe, expect, test } from "vitest";

import { AppRuntimeProvider } from "../../runtime";
import { defaultWidgets, type WidgetRenderProps } from "../../widgets";
import { EditableLines } from "./EditableLines";

const LINES = {
  field: "lines",
  modelLabel: "demo.Line",
  positionField: "position",
  fields: [
    {
      name: "label",
      kind: "scalar",
      scalar: "String",
      readable: true,
      filterable: false,
      sortable: false,
      aggregatable: false,
      groupable: false,
      creatable: true,
      updatable: true,
      requiredOnCreate: true,
    },
    {
      name: "quantity",
      kind: "scalar",
      scalar: "Decimal",
      readable: true,
      filterable: false,
      sortable: false,
      aggregatable: false,
      groupable: false,
      creatable: true,
      updatable: true,
      requiredOnCreate: false,
    },
    {
      name: "position",
      kind: "scalar",
      scalar: "Int",
      readable: true,
      filterable: false,
      sortable: false,
      aggregatable: false,
      groupable: false,
      creatable: true,
      updatable: true,
      requiredOnCreate: false,
    },
  ],
} satisfies DataResourceLinesMetadata;

function Host({
  footer,
  inspectContext = false,
}: {
  inspectContext?: boolean;
  footer?: (rows: readonly Record<string, unknown>[]) => React.ReactNode;
}): React.ReactElement {
  const form = useForm<Record<string, unknown>>({
    defaultValues: {
      lines: [
        { label: "Widget", quantity: 2, position: 0 },
        { label: "Gadget", quantity: 5, position: 1 },
      ],
    },
  });
  const contextWidget = {
    read: ({ row, parentRow }: WidgetRenderProps) => (
      <span>
        {String((row as { label: string }).label)} / {String((parentRow as { company: string }).company)}
      </span>
    ),
  };
  const lines = inspectContext
    ? {
        ...LINES,
        fields: LINES.fields.map((field) =>
          field.name === "label" ? { ...field, widget: "demo.lines.context" } : field,
        ),
      }
    : LINES;
  return (
    <AppRuntimeProvider runtime={{ widgets: { ...defaultWidgets, "demo.lines.context": contextWidget } }}>
      <EditableLines
        control={form.control}
        name="lines"
        lines={lines}
        parentRow={{ company: "Acme" }}
        footer={footer}
      />
    </AppRuntimeProvider>
  );
}

afterEach(cleanup);

describe("EditableLines", () => {
  test("passes the live child and owning document to a registered widget", () => {
    render(<Host inspectContext />);
    expect(screen.getByText("Widget / Acme")).toBeTruthy();
    expect(screen.getByText("Gadget / Acme")).toBeTruthy();
  });
  test("renders one editable cell row per seeded line, hiding the position column", () => {
    render(<Host />);

    expect(screen.getByDisplayValue("Widget")).toBeTruthy();
    expect(screen.getByDisplayValue("Gadget")).toBeTruthy();
    // A drag handle per row; the `position` column renders no header/cell.
    expect(screen.getAllByLabelText("Reorder line")).toHaveLength(2);
    expect(screen.queryByText("Position")).toBeNull();
    expect(screen.getByText("Label")).toBeTruthy();
    expect(screen.getByText("Quantity")).toBeTruthy();
  });

  test("adds a blank row and removes a row", () => {
    render(<Host />);

    fireEvent.click(screen.getByRole("button", { name: "Add line" }));
    expect(screen.getAllByLabelText("Reorder line")).toHaveLength(3);

    fireEvent.click(screen.getAllByLabelText("Remove line")[0]!);
    expect(screen.getAllByLabelText("Reorder line")).toHaveLength(2);
  });

  test("renders the composer's footer with the live rows", () => {
    render(<Host footer={(rows) => <div>lines: {rows.length}</div>} />);
    expect(screen.getByText("lines: 2")).toBeTruthy();
  });
});
