import { Badge, Button, SurfacePanel, cn, textRoleVariants } from "@angee/ui";
import { useState, type ReactElement } from "react";

import { applyTemplate, readStoredTemplateId } from "../appearance/apply";
import {
  APPEARANCE_TEMPLATES,
  contrastRatio,
  type AppearanceTemplate,
} from "../appearance/templates";

/** Stock token values, used when a template leaves a surface untouched. */
const STOCK_LIGHT = { rail: "#0a0c10", canvas: "#f7f8fa", sheet: "#ffffff" } as const;
const STOCK_DARK = { rail: "#07090c", canvas: "#0a0c10", sheet: "#181b21" } as const;

interface Swatch {
  rail: string;
  canvas: string;
  sheet: string;
}

function swatch(template: AppearanceTemplate, mode: "light" | "dark"): Swatch {
  const vars = mode === "light" ? template.light : template.dark;
  const stock = mode === "light" ? STOCK_LIGHT : STOCK_DARK;
  return {
    rail: vars["--surface-rail"] ?? stock.rail,
    canvas: vars["--surface-canvas"] ?? stock.canvas,
    sheet: vars["--surface-sheet"] ?? stock.sheet,
  };
}

/** Half a shell miniature: rail, canvas, sheet and the action colour. The values
 *  are read from the template itself, so the thumbnail cannot drift from what
 *  the template will really paint. */
function SchemeHalf({
  colours,
  brand,
  side,
}: {
  colours: Swatch;
  brand: string;
  side: "left" | "right";
}): ReactElement {
  return (
    <span
      className="flex h-full flex-1"
      style={{ background: colours.canvas }}
      aria-hidden
    >
      {side === "left" ? (
        <span className="h-full w-5 flex-none" style={{ background: colours.rail }} />
      ) : null}
      <span className="flex flex-1 flex-col justify-between p-2">
        <span
          className="block h-3 w-3/4 rounded-4"
          style={{ background: colours.sheet, boxShadow: "0 0 0 1px rgb(128 128 128 / 0.25)" }}
        />
        <span className="block h-4 w-14 rounded-6" style={{ background: brand }} />
      </span>
      {side === "right" ? (
        <span className="h-full w-5 flex-none" style={{ background: colours.rail }} />
      ) : null}
    </span>
  );
}

function TemplateCard({
  template,
  active,
  onSelect,
}: {
  template: AppearanceTemplate;
  active: boolean;
  onSelect: (id: string) => void;
}): ReactElement {
  const ratio = contrastRatio(template.brand, template.onBrand);
  const passes = ratio >= 4.5;

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => onSelect(template.id)}
      className={cn(
        "group flex flex-col overflow-hidden rounded-8 border text-left outline-none transition-colors",
        "focus-visible:focus-ring",
        active ? "border-brand shadow-md" : "border-border hover:border-strong",
      )}
    >
      {/* Both schemes side by side — every template ships light and dark. */}
      <span className="flex h-24 w-full">
        <SchemeHalf colours={swatch(template, "light")} brand={template.brand} side="left" />
        <SchemeHalf colours={swatch(template, "dark")} brand={template.brand} side="right" />
      </span>

      <span className="flex flex-1 flex-col gap-1 border-t border-border bg-sheet p-3">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-13 font-semibold text-fg">{template.label}</span>
          {active ? <Badge tone="brand">active</Badge> : null}
          {template.prefersDark ? <Badge tone="info">dark by default</Badge> : null}
        </span>
        <span className={cn(textRoleVariants({ role: "caption" }), "block")}>
          {template.description}
        </span>
        <span
          className={cn(textRoleVariants({ role: "meta" }), "block")}
          style={{ color: passes ? "var(--success-text)" : "var(--warning-text)" }}
        >
          button contrast {ratio.toFixed(2)}:1 {passes ? "✓ AA" : "⚠ below AA"}
        </span>
      </span>
    </button>
  );
}

/**
 * Appearance — pick the design language of the whole product.
 *
 * A template is not a palette: it retunes the brand ramp, every surface, the
 * radius and spacing scales, the type family and the elevation model, in both
 * the light and the dark scheme. Because `@angee/ui` components reference
 * semantic tokens rather than literal colours, switching one re-skins every
 * screen of every addon with no rebuild — the composition stays static, only
 * data changes.
 */
export function AppearancePage(): ReactElement {
  const [activeId, setActiveId] = useState(() => readStoredTemplateId());

  function select(id: string): void {
    applyTemplate(id);
    setActiveId(id);
  }

  return (
    <div className="space-y-6 p-6">
      <SurfacePanel
        title="Design template"
        summary="Every template ships a light and a dark scheme. Applied instantly — no rebuild."
      >
        <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
          {APPEARANCE_TEMPLATES.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              active={template.id === activeId}
              onSelect={select}
            />
          ))}
        </div>
      </SurfacePanel>

      <SurfacePanel title="Your own design" summary="A theme built from your website or brand book.">
        <div className="p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="warning">Coming soon</Badge>
            <span className={cn(textRoleVariants({ role: "caption" }), "block")}>
              Point us at your website or upload a brand book — the palette, type
              and radii are extracted for you, both schemes are generated, and
              every colour pair is checked against WCAG.
            </span>
          </div>

          <div className="mt-3 flex max-w-xl gap-2">
            <input
              disabled
              placeholder="https://example.com"
              aria-label="Company website URL"
              className="h-8 flex-1 rounded-6 border border-border bg-inset px-2 text-13 text-fg disabled:cursor-not-allowed disabled:opacity-60"
            />
            <Button disabled>Build theme</Button>
          </div>
        </div>
      </SurfacePanel>
    </div>
  );
}
