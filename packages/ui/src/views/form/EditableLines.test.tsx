// @vitest-environment happy-dom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useForm } from "react-hook-form";
import type { DataResourceLinesMetadata } from "@angee/metadata";
import { afterEach, describe, expect, test } from "vitest";

import { AppRuntimeProvider } from "../../runtime";
import { defaultWidgets } from "../../widgets";
import type { ColumnDescriptor } from "../page";
import { EditableLines } from "./EditableLines";

const LINES: DataResourceLinesMetadata = {
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
      name: "note",
      kind: "scalar",
      scalar: "String",
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
};

function Host({
  footer,
  columns,
}: {
  footer?: (rows: readonly Record<string, unknown>[]) => React.ReactNode;
  columns?: readonly ColumnDescriptor[];
}): React.ReactElement {
  const form = useForm<Record<string, unknown>>({
    defaultValues: {
      lines: [
        { label: "Widget", quantity: 2, note: "n1", position: 0 },
        { label: "Gadget", quantity: 5, note: "n2", position: 1 },
      ],
    },
  });
  return (
    <AppRuntimeProvider runtime={{ widgets: defaultWidgets }}>
      <EditableLines
        control={form.control}
        name="lines"
        lines={LINES}
        footer={footer}
        columns={columns}
        setValue={(name, value, options) =>
          form.setValue(name as never, value as never, options)
        }
      />
    </AppRuntimeProvider>
  );
}

afterEach(cleanup);

describe("EditableLines", () => {
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

describe("EditableLines — column overrides", () => {
  test("declared columns pick the order, header, width, and read-only state", () => {
    const { container } = render(
      <Host
        columns={[
          { field: "quantity", header: "Qty", width: "96px" },
          { field: "label", readOnly: true },
        ]}
      />,
    );

    expect(screen.getByText("Qty")).toBeTruthy();
    expect(screen.queryByText("Quantity")).toBeNull();
    // Declared order: quantity first, then label.
    const headers = [...container.querySelectorAll("span.truncate")].map(
      (node) => node.textContent,
    );
    expect(headers).toEqual(["Qty", "Label"]);
    // Width lands in the grid template; the label cells render read-only.
    const grid = container.querySelector('[style*="96px"]');
    expect(grid).toBeTruthy();
    expect(screen.queryByDisplayValue("Widget")).toBeNull();
    expect(screen.getByText("Widget")).toBeTruthy();
  });

  test("an override naming a non-column field fails fast", () => {
    expect(() =>
      render(<Host columns={[{ field: "nope" }]} />),
    ).toThrowError(/not an editable child column/);
  });
});

describe("EditableLines — cell resolve", () => {
  test("seeds sibling cells of the row, skipping the changed cell itself", async () => {
    render(
      <Host
        columns={[
          {
            field: "label",
            resolve: (value) =>
              Promise.resolve({ note: "seeded", label: `${String(value)}!` }),
          },
          { field: "note" },
        ]}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Widget"), {
      target: { value: "Bolt" },
    });

    // note (untouched) is seeded on the same row; label keeps the user's value.
    await waitFor(() => {
      expect(screen.getByDisplayValue("seeded")).toBeTruthy();
    });
    expect(screen.getByDisplayValue("Bolt")).toBeTruthy();
    expect(screen.queryByDisplayValue("Bolt!")).toBeNull();
    // The sibling row's note is untouched.
    expect(screen.getByDisplayValue("n2")).toBeTruthy();
  });

  test("never overwrites a cell the user edited earlier in the session", async () => {
    render(
      <Host
        columns={[
          {
            field: "label",
            resolve: () => Promise.resolve({ note: "seeded" }),
          },
          { field: "note" },
        ]}
      />,
    );

    // The user sets the note by hand first, then changes the label.
    fireEvent.change(screen.getByDisplayValue("n1"), {
      target: { value: "manual" },
    });
    fireEvent.change(screen.getByDisplayValue("Widget"), {
      target: { value: "Bolt" },
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Bolt")).toBeTruthy();
    });
    // The resolver result must not clobber the manual note.
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(screen.getByDisplayValue("manual")).toBeTruthy();
    expect(screen.queryByDisplayValue("seeded")).toBeNull();
  });
});
