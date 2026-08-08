import { expectValidBaseAddon } from "@angee/app/testing";
import { describe, expect, test } from "vitest";

import companies from "./index";

describe("companies addon manifest", () => {
  test("satisfies the rendered-addon invariants", () => {
    expect(() => expectValidBaseAddon(companies)).not.toThrow();
  });

  test("registers the companies resource page", () => {
    expect((companies.routes ?? []).map((route) => route.name)).toEqual([
      "companies.companies",
      "companies.companies.record",
    ]);
  });

  test("overlays the parties rail instead of standing up its own app", () => {
    // The chrome derives the app rail from the menu roots; a structural
    // directory of one page belongs under the rail parties owns, beside the
    // organizations it links (the nexus precedent).
    const menus = companies.menus ?? [];
    expect(menus.map((item) => item.parentId)).toEqual(["parties"]);
    expect(menus.some((item) => item.children)).toBe(false);
  });

  test("declares a glyph for every menu item it contributes", () => {
    for (const item of companies.menus ?? []) {
      expect(item.icon, `${item.id} declares no icon`).toBeTruthy();
      expect(Object.keys(companies.icons ?? {})).toContain(item.icon);
    }
  });
});
