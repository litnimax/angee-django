/**
 * Applies an appearance template at runtime.
 *
 * The whole template lands as ONE <style> element appended last, so it wins on
 * cascade order without `!important` and lifts cleanly when switched.
 *
 * `shared` tokens go to both blocks; `light` and `dark` go to `:root` and
 * `[data-theme="dark"]` respectively. That keeps the stock light/dark toggle
 * meaningful inside every template instead of flattening it.
 *
 * Selection currently persists in localStorage. Productising this means moving
 * it to a resource row so it becomes per-organisation data — only the source of
 * the id changes, not the mechanism below.
 */

import { readCustomTemplate } from "./custom";
import { CUSTOM_TEMPLATE_ID, DEFAULT_TEMPLATE_ID, findTemplate, type AppearanceTemplate } from "./templates";

/** Resolve a template id, including the generated one held in storage. */
function resolve(id: string): AppearanceTemplate | undefined {
  return id === CUSTOM_TEMPLATE_ID ? readCustomTemplate() ?? undefined : findTemplate(id);
}

const STYLE_ID = "angee-appearance-style";
const FONT_ID = "angee-appearance-font";
const STORAGE_KEY = "angee.appearance.template";

function serialise(vars: Record<string, string>): string {
  return Object.entries(vars)
    .map(([name, value]) => `  ${name}: ${value};`)
    .join("\n");
}

export function readStoredTemplateId(): string {
  if (typeof localStorage === "undefined") return DEFAULT_TEMPLATE_ID;
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored !== null && resolve(stored) ? stored : DEFAULT_TEMPLATE_ID;
}

export function applyTemplate(id: string, options: { persist?: boolean; switchScheme?: boolean } = {}): void {
  if (typeof document === "undefined") return;
  const { persist = true, switchScheme = true } = options;
  const template = resolve(id) ?? findTemplate(DEFAULT_TEMPLATE_ID);
  if (!template) return;

  document.getElementById(STYLE_ID)?.remove();
  document.getElementById(FONT_ID)?.remove();

  if (template.font) {
    const link = document.createElement("link");
    link.id = FONT_ID;
    link.rel = "stylesheet";
    link.href = `https://fonts.googleapis.com/css2?family=${template.font}&display=swap`;
    document.head.appendChild(link);
  }

  // Only an explicit pick moves the scheme, and only towards the template's
  // preference. A later manual light/dark toggle must stay authoritative.
  if (switchScheme && template.prefersDark) {
    document.documentElement.dataset["theme"] = "dark";
  }

  const light = serialise({ ...template.shared, ...template.light });
  const dark = serialise({ ...template.shared, ...template.dark });
  if (light || dark || template.css) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      `:root {\n${light}\n}\n[data-theme="dark"] {\n${dark}\n}\n${template.css ?? ""}`;
    document.head.appendChild(style);
  }

  if (persist && typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, template.id);
  }
}

/**
 * Applies the stored template on load. Carbon is the default, so this runs on a
 * fresh install too — and it must not force the scheme, or it would override the
 * user's light/dark choice on every reload.
 */
export function bootAppearance(): void {
  applyTemplate(readStoredTemplateId(), { persist: false, switchScheme: false });
}
