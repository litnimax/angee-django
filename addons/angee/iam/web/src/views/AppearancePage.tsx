import { Alert, Badge, Button, SurfacePanel, cn, textRoleVariants } from "@angee/ui";
import { useMemo, useState, type ReactElement } from "react";

import { applyTemplate, readStoredTemplateId } from "../appearance/apply";
import { clearCustomInput, readCustomInput, writeCustomInput } from "../appearance/custom";
import {
  APPEARANCE_TEMPLATES,
  buildCustomTemplate,
  contrastRatio,
  CUSTOM_TEMPLATE_ID,
  DEFAULT_TEMPLATE_ID,
  type AppearanceTemplate,
} from "../appearance/templates";

/** Stock token values, used when a template leaves a surface untouched. */
const STOCK_LIGHT = { rail: "#0a0c10", canvas: "#f7f8fa", sheet: "#ffffff" } as const;
const STOCK_DARK = { rail: "#07090c", canvas: "#0a0c10", sheet: "#181b21" } as const;

interface BrandCandidate {
  hex: string;
  weight: number;
  score: number;
}

interface Analysis {
  url: string;
  siteName: string | null;
  logo: string | null;
  brandCandidates: BrandCandidate[];
  neutralTint: string | null;
  fonts: string[];
  sampledStylesheets: number;
  coloursSeen: number;
  error?: string;
}

type WizardStatus = "idle" | "loading" | "review" | "error";

// ------------------------------------------------------------------ previews

function swatch(template: AppearanceTemplate, mode: "light" | "dark"): {
  rail: string;
  canvas: string;
  sheet: string;
} {
  const vars = mode === "light" ? template.light : template.dark;
  const stock = mode === "light" ? STOCK_LIGHT : STOCK_DARK;
  return {
    rail: vars["--surface-rail"] ?? stock.rail,
    canvas: vars["--surface-canvas"] ?? stock.canvas,
    sheet: vars["--surface-sheet"] ?? stock.sheet,
  };
}

function SchemeHalf({
  template,
  mode,
}: {
  template: AppearanceTemplate;
  mode: "light" | "dark";
}): ReactElement {
  const colours = swatch(template, mode);
  return (
    <span className="flex h-full flex-1" style={{ background: colours.canvas }} aria-hidden>
      {mode === "light" ? (
        <span className="h-full w-5 flex-none" style={{ background: colours.rail }} />
      ) : null}
      <span className="flex flex-1 flex-col justify-between p-2">
        <span
          className="block h-3 w-3/4 rounded-4"
          style={{ background: colours.sheet, boxShadow: "0 0 0 1px rgb(128 128 128 / 0.25)" }}
        />
        <span className="block h-4 w-14 rounded-6" style={{ background: template.brand }} />
      </span>
      {mode === "dark" ? (
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
      <span className="flex h-24 w-full">
        <SchemeHalf template={template} mode="light" />
        <SchemeHalf template={template} mode="dark" />
      </span>

      <span className="flex flex-1 flex-col gap-1 border-t border-border bg-sheet p-3">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-13 font-semibold text-fg">{template.label}</span>
          {active ? <Badge tone="brand">active</Badge> : null}
          {template.id === CUSTOM_TEMPLATE_ID ? <Badge tone="accent">generated</Badge> : null}
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

// -------------------------------------------------------------------- wizard

function Wizard({ onApplied }: { onApplied: (id: string) => void }): ReactElement {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<WizardStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [brand, setBrand] = useState<string | null>(null);
  const [font, setFont] = useState<string | null>(null);

  const draft = useMemo(
    () =>
      brand
        ? buildCustomTemplate({
            brand,
            tint: analysis?.neutralTint ?? null,
            font,
            label: analysis?.siteName?.split(/[|·—-]/)[0]?.trim() || "Custom",
          })
        : null,
    [brand, font, analysis],
  );

  async function analyse(): Promise<void> {
    setStatus("loading");
    setError(null);
    try {
      const response = await fetch(`/appearance/extract?url=${encodeURIComponent(url.trim())}`);
      const body = (await response.json()) as Analysis;
      if (!response.ok || body.error) {
        setError(body.error ?? `The analysis failed (HTTP ${response.status}).`);
        setStatus("error");
        return;
      }
      if (body.brandCandidates.length === 0) {
        setError("No brand colour could be read from that site — try the marketing page rather than an app subdomain.");
        setStatus("error");
        return;
      }
      setAnalysis(body);
      setBrand(body.brandCandidates[0]?.hex ?? null);
      setFont(body.fonts[0] ?? null);
      setStatus("review");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setStatus("error");
    }
  }

  function apply(): void {
    if (!brand) return;
    writeCustomInput({
      brand,
      tint: analysis?.neutralTint ?? null,
      font,
      label: draft?.label,
    });
    applyTemplate(CUSTOM_TEMPLATE_ID);
    onApplied(CUSTOM_TEMPLATE_ID);
  }

  function reset(): void {
    setStatus("idle");
    setAnalysis(null);
    setBrand(null);
    setFont(null);
    setError(null);
  }

  return (
    <div className="space-y-4 p-4">
      {/* Step 1 — the address */}
      <div className="flex max-w-2xl flex-wrap items-center gap-2">
        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && url.trim()) void analyse();
          }}
          placeholder="https://example.com"
          aria-label="Company website URL"
          className="h-8 min-w-64 flex-1 rounded-6 border border-border bg-inset px-2 text-13 text-fg outline-none focus-visible:focus-ring"
        />
        <Button disabled={!url.trim() || status === "loading"} onClick={() => void analyse()}>
          {status === "loading" ? "Analysing…" : "Analyse site"}
        </Button>
        {status === "review" ? (
          <Button variant="ghost" onClick={reset}>
            Start over
          </Button>
        ) : null}
      </div>

      {status === "error" && error ? (
        <Alert tone="danger" title="Could not build a theme">
          {error}
        </Alert>
      ) : null}

      {/* Step 2 — what the site yielded */}
      {status === "review" && analysis ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            {analysis.logo ? (
              <img
                src={analysis.logo}
                alt=""
                className="h-8 w-8 rounded-4 border border-border object-contain"
              />
            ) : null}
            <div className="min-w-0">
              <div className="truncate text-13 font-semibold text-fg">
                {analysis.siteName ?? analysis.url}
              </div>
              <div className={cn(textRoleVariants({ role: "meta" }), "block")}>
                {analysis.coloursSeen} colours across {analysis.sampledStylesheets} stylesheet
                {analysis.sampledStylesheets === 1 ? "" : "s"}
                {analysis.neutralTint ? " · greys lean " : " · neutral greys"}
                {analysis.neutralTint ? (
                  <span
                    className="ml-1 inline-block h-2 w-4 rounded-2 align-middle"
                    style={{ background: analysis.neutralTint }}
                  />
                ) : null}
              </div>
            </div>
          </div>

          <div>
            <div className={cn(textRoleVariants({ role: "caption" }), "mb-1 block")}>
              Brand colour — ranked by how much the site actually uses it
            </div>
            <div className="flex flex-wrap gap-2">
              {analysis.brandCandidates.map((candidate) => (
                <button
                  key={candidate.hex}
                  type="button"
                  aria-pressed={candidate.hex === brand}
                  onClick={() => setBrand(candidate.hex)}
                  title={`${candidate.hex} · used ${candidate.weight}×`}
                  className={cn(
                    "flex items-center gap-2 rounded-6 border px-2 py-1 text-12 outline-none transition-colors focus-visible:focus-ring",
                    candidate.hex === brand ? "border-brand bg-brand-soft text-brand-soft-text" : "border-border bg-sheet text-fg",
                  )}
                >
                  <span
                    className="h-4 w-4 rounded-full"
                    style={{ background: candidate.hex, boxShadow: "0 0 0 1px rgb(0 0 0 / 0.12) inset" }}
                  />
                  {candidate.hex}
                </button>
              ))}
            </div>
          </div>

          {analysis.fonts.length > 0 ? (
            <div>
              <div className={cn(textRoleVariants({ role: "caption" }), "mb-1 block")}>
                Type — loaded from Google Fonts when the family is published there
              </div>
              <div className="flex flex-wrap gap-2">
                {[...analysis.fonts, null].map((candidate) => (
                  <button
                    key={candidate ?? "system"}
                    type="button"
                    aria-pressed={candidate === font}
                    onClick={() => setFont(candidate)}
                    className={cn(
                      "rounded-6 border px-2 py-1 text-12 outline-none transition-colors focus-visible:focus-ring",
                      candidate === font ? "border-brand bg-brand-soft text-brand-soft-text" : "border-border bg-sheet text-fg",
                    )}
                  >
                    {candidate ?? "System font"}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {/* Step 3 — the generated theme */}
          {draft ? (
            <div className="flex flex-wrap items-start gap-4 rounded-8 border border-border bg-sheet-2 p-3">
              <span className="flex h-24 w-64 overflow-hidden rounded-6 border border-border">
                <SchemeHalf template={draft} mode="light" />
                <SchemeHalf template={draft} mode="dark" />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <div className="text-13 font-semibold text-fg">{draft.label}</div>
                <div className={cn(textRoleVariants({ role: "caption" }), "block")}>
                  {draft.description}
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button onClick={apply}>Apply theme</Button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------- page

/**
 * Appearance — pick the design language of the whole product.
 *
 * A template retunes the brand ramp, every surface, the radius and spacing
 * scales, the type family and the elevation model, in both schemes. Because
 * `@angee/ui` components reference semantic tokens rather than literal colours,
 * switching one re-skins every screen of every addon with no rebuild: the
 * composition stays static and only data changes.
 */
export function AppearancePage(): ReactElement {
  const [activeId, setActiveId] = useState(() => readStoredTemplateId());
  const [customInput, setCustomInput] = useState(() => readCustomInput());

  const custom = useMemo(
    () => (customInput ? buildCustomTemplate(customInput) : null),
    [customInput],
  );

  function select(id: string): void {
    applyTemplate(id);
    setActiveId(id);
  }

  function onApplied(id: string): void {
    setCustomInput(readCustomInput());
    setActiveId(id);
  }

  function discardCustom(): void {
    clearCustomInput();
    setCustomInput(null);
    if (activeId === CUSTOM_TEMPLATE_ID) select(DEFAULT_TEMPLATE_ID);
  }

  const templates: AppearanceTemplate[] = custom
    ? [custom, ...APPEARANCE_TEMPLATES]
    : [...APPEARANCE_TEMPLATES];

  return (
    <div className="space-y-6 p-6">
      <SurfacePanel
        title="Design template"
        summary="Every template ships a light and a dark scheme. Applied instantly — no rebuild."
      >
        <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              active={template.id === activeId}
              onSelect={select}
            />
          ))}
        </div>
      </SurfacePanel>

      <SurfacePanel
        title="Your own design"
        summary="Point us at a website — the palette, greys and type are read from it and turned into a theme."
      >
        <Wizard onApplied={onApplied} />
        {custom ? (
          <div className="flex items-center gap-2 border-t border-border px-4 py-3">
            <span className={cn(textRoleVariants({ role: "caption" }), "block flex-1")}>
              A generated theme is stored for this browser. Only the extracted facts are
              kept, so it is rebuilt — and improves — with the generator.
            </span>
            <Button variant="ghost" onClick={discardCustom}>
              Discard
            </Button>
          </div>
        ) : null}
      </SurfacePanel>
    </div>
  );
}
