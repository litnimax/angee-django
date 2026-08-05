/**
 * The generated ("custom") template: the inputs a site analysis produced, kept
 * so the theme survives a reload and can be re-derived or edited later.
 *
 * Only the *inputs* are stored, never the expanded token set. Regenerating from
 * `{brand, tint, font}` means an improvement to the generator reaches every
 * existing custom theme, instead of freezing whatever the generator emitted on
 * the day it was created.
 */

import {
  buildCustomTemplate,
  type AppearanceTemplate,
  type CustomThemeInput,
} from "./templates";

const STORAGE_KEY = "angee.appearance.custom";

export function readCustomInput(): CustomThemeInput | null {
  if (typeof localStorage === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CustomThemeInput;
    return typeof parsed?.brand === "string" ? parsed : null;
  } catch {
    return null;
  }
}

export function writeCustomInput(input: CustomThemeInput): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(input));
}

export function clearCustomInput(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

/** The stored custom template, expanded, or null when none was generated. */
export function readCustomTemplate(): AppearanceTemplate | null {
  const input = readCustomInput();
  return input ? buildCustomTemplate(input) : null;
}
