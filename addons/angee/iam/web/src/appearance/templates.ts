/**
 * Appearance templates — a design language expressed purely as token overrides.
 *
 * `@angee/ui` components never name a colour, radius or size directly: they
 * reference semantic tokens, and those resolve through the primitive ramps in
 * `angee/web/ui/src/styles/tokens.css`. Overriding the primitives therefore
 * re-skins every screen of every addon at once, with no rebuild.
 *
 * Each template carries THREE layers:
 *   · `shared` — brand ramp, shape, density, type, motion. Theme-independent.
 *   · `light`  — surfaces, borders and text for the light scheme.
 *   · `dark`   — the same set for the dark scheme.
 *
 * They are emitted as `:root { shared + light }` and
 * `[data-theme="dark"] { shared + dark }`, so the stock light/dark toggle keeps
 * working inside every template rather than being flattened by it.
 *
 * Every colour token MUST be a plain colour. `--surface-rail` and friends are
 * consumed as colour values, so a `linear-gradient(...)` silently drops the
 * declaration and leaves the rail transparent — which reads as "the icons
 * disappeared".
 */

export interface AppearanceTemplate {
  id: string;
  label: string;
  /** Brand fill used for primary actions, in both schemes. */
  brand: string;
  /** Text drawn on the brand fill; dark when the brand is too light for white. */
  onBrand: string;
  /** Selecting this template switches the app to the dark scheme. */
  prefersDark?: boolean;
  /** Google Fonts family spec, e.g. `Rubik:wght@400;500;600;700`. */
  font?: string;
  description: string;
  shared: Record<string, string>;
  light: Record<string, string>;
  dark: Record<string, string>;
  css?: string;
}

// ---------------------------------------------------------------- colour math

function hexToRgb(hex: string): [number, number, number] {
  const raw = hex.replace("#", "");
  const full = raw.length === 3 ? raw.split("").map((c) => c + c).join("") : raw;
  const n = Number.parseInt(full, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function luminance(hex: string): number {
  const channels = hexToRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * (channels[0] ?? 0) + 0.7152 * (channels[1] ?? 0) + 0.0722 * (channels[2] ?? 0);
}

/** WCAG contrast ratio. Surfaced in the UI so a brand colour cannot quietly
 *  produce unreadable buttons — the usual failure mode of "themeable" products. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Perceptually even ramp from one base colour. `color-mix(in oklab, …)` is the
 *  technique tokens.css already uses; sRGB blending muddies the mid stops. */
function ramp(hex: string): Record<string, string> {
  const stops: readonly (readonly [number, string | null, number])[] = [
    [50, "white", 92], [100, "white", 84], [200, "white", 68], [300, "white", 48],
    [400, "white", 25], [500, null, 0], [600, "black", 14], [700, "black", 28],
    [800, "black", 42], [900, "black", 55],
  ];
  const out: Record<string, string> = {};
  for (const [step, towards, pct] of stops) {
    out[`--b-${step}`] =
      towards === null ? hex : `color-mix(in oklab, ${hex} ${100 - pct}%, ${towards})`;
  }
  return out;
}

function radii(scale: number): Record<string, string> {
  return Object.fromEntries(
    [2, 4, 6, 8, 10, 12].map((r) => [`--r-${r}`, `${Math.round(r * scale)}px`]),
  );
}

function density(k: number): Record<string, string> {
  const sp = Object.fromEntries(
    [1, 2, 3, 4, 5, 6, 8, 10].map((s) => [`--sp-${s}`, `${Math.round(s * 4 * k)}px`]),
  );
  return {
    ...sp,
    "--topbar-h": `${Math.round(42 * k)}px`,
    "--controlpanel-h": `${Math.round(48 * k)}px`,
  };
}

const FLAT_LIGHT: Record<string, string> = {
  "--elevation-xs": "none",
  "--elevation-sm": "none",
  "--elevation-md": "0 0 0 1px rgb(0 0 0 / 0.08)",
  "--elevation-lg": "0 0 0 1px rgb(0 0 0 / 0.12)",
  "--elevation-popover": "0 0 0 1px rgb(0 0 0 / 0.16)",
};

const FLAT_DARK: Record<string, string> = {
  "--elevation-xs": "none",
  "--elevation-sm": "none",
  "--elevation-md": "0 0 0 1px rgb(255 255 255 / 0.10)",
  "--elevation-lg": "0 0 0 1px rgb(255 255 255 / 0.14)",
  "--elevation-popover": "0 0 0 1px rgb(255 255 255 / 0.18)",
};

const SOFT_LIGHT: Record<string, string> = {
  "--elevation-xs": "0 1px 2px rgb(0 0 0 / 0.04)",
  "--elevation-sm": "0 1px 3px rgb(0 0 0 / 0.06)",
  "--elevation-md": "0 6px 18px rgb(0 0 0 / 0.09)",
  "--elevation-lg": "0 16px 40px rgb(0 0 0 / 0.14)",
  "--elevation-popover": "0 8px 24px rgb(0 0 0 / 0.12)",
};

/** Dark scheme needs heavier, more opaque shadows: on a dark canvas a 9% black
 *  drop is invisible, so depth has to be carried by stronger falloff. */
const SOFT_DARK: Record<string, string> = {
  "--elevation-xs": "0 1px 2px rgb(0 0 0 / 0.40)",
  "--elevation-sm": "0 2px 6px rgb(0 0 0 / 0.45)",
  "--elevation-md": "0 8px 24px rgb(0 0 0 / 0.50)",
  "--elevation-lg": "0 20px 48px rgb(0 0 0 / 0.58)",
  "--elevation-popover": "0 12px 32px rgb(0 0 0 / 0.52)",
};

export interface Scheme {
  canvas: string;
  sheet: string;
  sheet2: string;
  inset: string;
  popover?: string;
  rail: string;
  railHi: string;
  /** On-rail text. Must read on the rail AND on the light brand pill that the
   *  collapsed-panel toggles use — stock picks a mid grey for exactly that reason. */
  onRail: string;
  onRailMuted: string;
  borderOnRail: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textSubtle: string;
  borderSubtle: string;
  borderDefault: string;
  borderStrong: string;
  brandSoft: string;
  brandSoftText: string;
}

function scheme(s: Scheme): Record<string, string> {
  return {
    "--surface-canvas": s.canvas,
    "--surface-sheet": s.sheet,
    "--surface-sheet-2": s.sheet2,
    "--surface-inset": s.inset,
    "--surface-popover": s.popover ?? s.sheet,
    "--surface-rail": s.rail,
    "--surface-rail-hi": s.railHi,
    "--text-on-rail": s.onRail,
    "--text-on-rail-mut": s.onRailMuted,
    "--text-on-rail-hi": "#ffffff",
    "--border-on-rail": s.borderOnRail,
    "--text-primary": s.textPrimary,
    "--text-secondary": s.textSecondary,
    "--text-muted": s.textMuted,
    "--text-subtle": s.textSubtle,
    "--border-subtle": s.borderSubtle,
    "--border-default": s.borderDefault,
    "--border-strong": s.borderStrong,
    "--brand-soft": s.brandSoft,
    "--brand-soft-text": s.brandSoftText,
  };
}

// ----------------------------------------------------------------- templates

export const APPEARANCE_TEMPLATES: readonly AppearanceTemplate[] = [
  {
    id: "carbon",
    label: "Carbon",
    brand: "#0f62fe",
    onBrand: "#ffffff",
    font: "IBM+Plex+Sans:wght@400;500;600;700",
    description: "Engineering end of the scale: square corners, flat surfaces, dense grid.",
    shared: {
      ...ramp("#0f62fe"),
      "--r-2": "0px", "--r-4": "0px", "--r-6": "0px",
      "--r-8": "0px", "--r-10": "0px", "--r-12": "0px",
      ...density(0.92),
      "--font-sans": '"IBM Plex Sans", system-ui, -apple-system, sans-serif',
      "--font-mono": '"IBM Plex Mono", ui-monospace, Menlo, monospace',
      "--dur-fast": "70ms", "--dur-base": "110ms", "--dur-slow": "180ms",
      "--ring": "0 0 0 2px #0f62fe",
    },
    light: {
      ...scheme({
        canvas: "#f4f4f4", sheet: "#ffffff", sheet2: "#f9f9f9", inset: "#ededed",
        rail: "#161616", railHi: "#262626",
        onRail: "#c6c6c6", onRailMuted: "#8d8d8d", borderOnRail: "#393939",
        textPrimary: "#161616", textSecondary: "#393939",
        textMuted: "#6f6f6f", textSubtle: "#8d8d8d",
        borderSubtle: "#e8e8e8", borderDefault: "#dcdcdc", borderStrong: "#c6c6c6",
        brandSoft: "#edf5ff", brandSoftText: "#0043ce",
      }),
      ...FLAT_LIGHT,
    },
    dark: {
      // IBM's Gray 100 ladder: layered greys instead of one flat black, so
      // panels stay separable without shadows.
      ...scheme({
        canvas: "#161616", sheet: "#262626", sheet2: "#2c2c2c", inset: "#333333",
        popover: "#262626",
        rail: "#0b0b0b", railHi: "#1f1f1f",
        onRail: "#c6c6c6", onRailMuted: "#8d8d8d", borderOnRail: "#393939",
        textPrimary: "#f4f4f4", textSecondary: "#c6c6c6",
        textMuted: "#a8a8a8", textSubtle: "#8d8d8d",
        borderSubtle: "#333333", borderDefault: "#393939", borderStrong: "#525252",
        brandSoft: "#1c2b47", brandSoftText: "#a6c8ff",
      }),
      ...FLAT_DARK,
    },
    css: `
      ::selection { background: color-mix(in oklab, #0f62fe 22%, transparent); }
      :focus-visible { outline: 2px solid #0f62fe; outline-offset: 1px; }
    `,
  },

  {
    id: "angee",
    label: "Angee",
    brand: "#5b5bd6",
    onBrand: "#ffffff",
    description: "The stock design language — cool neutrals, Inter, moderate radii.",
    // Empty everywhere: the stock tokens already define both schemes, so the
    // cleanest "no template" is genuinely no declarations.
    shared: {},
    light: {},
    dark: {},
  },

  {
    id: "coca-cola",
    label: "Coca-Cola",
    brand: "#e4002b",
    onBrand: "#ffffff",
    font: "Rubik:wght@400;500;600;700",
    description: "A warm brand world: cream canvas, red accent, soft depth, Rubik.",
    shared: {
      ...ramp("#e4002b"),
      ...radii(1.5),
      ...density(1.08),
      "--font-sans": '"Rubik", system-ui, -apple-system, "Segoe UI", sans-serif',
    },
    light: {
      ...scheme({
        canvas: "#faf5f2", sheet: "#ffffff", sheet2: "#fbf7f5", inset: "#f3ebe7",
        // Warm near-black, not red: red stays the ACTION colour. A red rail plus
        // red buttons flattens hierarchy and reads as costume, not brand.
        rail: "#231110", railHi: "#3a1614",
        onRail: "#d9cbc7", onRailMuted: "#9c8b86", borderOnRail: "#3d211e",
        textPrimary: "#1c1210", textSecondary: "#4a3733",
        textMuted: "#7a6560", textSubtle: "#9c8b86",
        borderSubtle: "#f0e6e1", borderDefault: "#e5d7d1", borderStrong: "#d4c0b8",
        brandSoft: "#fdeceb", brandSoftText: "#a30020",
      }),
      ...SOFT_LIGHT,
    },
    dark: {
      ...scheme({
        canvas: "#17100e", sheet: "#211714", sheet2: "#261b18", inset: "#2e211d",
        rail: "#140c0b", railHi: "#2b1a17",
        onRail: "#d9cbc7", onRailMuted: "#9c8b86", borderOnRail: "#33221f",
        textPrimary: "#f5ece9", textSecondary: "#d3c2bd",
        textMuted: "#a89792", textSubtle: "#8a7873",
        borderSubtle: "#2b1f1c", borderDefault: "#382823", borderStrong: "#4a3630",
        brandSoft: "#3a1418", brandSoftText: "#ff9aa5",
      }),
      ...SOFT_DARK,
    },
    css: `::selection { background: color-mix(in oklab, #e4002b 22%, transparent); }`,
  },

  {
    id: "aurora",
    label: "Aurora",
    // #0e9f6e would be prettier but lands at 3.39:1 on white — unreadable buttons.
    brand: "#078052",
    onBrand: "#ffffff",
    font: "Manrope:wght@400;500;600;700;800",
    description: "Calm and product-like: deep emerald, airy spacing, Manrope.",
    shared: {
      ...ramp("#078052"),
      ...radii(1.4),
      ...density(1.16),
      "--font-sans": '"Manrope", system-ui, -apple-system, sans-serif',
    },
    light: {
      ...scheme({
        canvas: "#f2f7f5", sheet: "#ffffff", sheet2: "#f7fbf9", inset: "#e8f1ed",
        rail: "#10352b", railHi: "#1b4a3d",
        onRail: "#c6d8d1", onRailMuted: "#8aa79c", borderOnRail: "#1d4638",
        textPrimary: "#0f1f1a", textSecondary: "#31463f",
        textMuted: "#5f7a71", textSubtle: "#8aa79c",
        borderSubtle: "#e6efeb", borderDefault: "#d7e5df", borderStrong: "#bcd2c9",
        brandSoft: "#e6f6ef", brandSoftText: "#05603a",
      }),
      ...SOFT_LIGHT,
    },
    dark: {
      ...scheme({
        canvas: "#0b1613", sheet: "#122019", sheet2: "#16261e", inset: "#1b2e25",
        rail: "#081210", railHi: "#173029",
        onRail: "#c6d8d1", onRailMuted: "#8aa79c", borderOnRail: "#1e332b",
        textPrimary: "#e9f3ee", textSecondary: "#c2d5cc",
        textMuted: "#95aca3", textSubtle: "#7b928a",
        borderSubtle: "#1a2b24", borderDefault: "#22382e", borderStrong: "#2f4b3e",
        brandSoft: "#0d3527", brandSoftText: "#6ee7b7",
      }),
      ...SOFT_DARK,
    },
    css: `::selection { background: color-mix(in oklab, #078052 22%, transparent); }`,
  },

  {
    id: "midnight",
    label: "Midnight",
    brand: "#8b7bff",
    // A bright violet cannot carry white text at AA. Rather than dulling the
    // brand, the label goes dark — the same call tokens.css makes for amber
    // (`--on-warning: var(--n-900)` — "amber-500 fails white-on-amber").
    onBrand: "#14111f",
    prefersDark: true,
    font: "Plus+Jakarta+Sans:wght@400;500;600;700",
    description: "Blue-violet: dark by default, light scheme included.",
    shared: {
      ...ramp("#8b7bff"),
      "--text-on-brand": "#14111f",
      "--on-brand": "#14111f",
      ...radii(1.3),
      ...density(1.06),
      "--font-sans": '"Plus Jakarta Sans", system-ui, -apple-system, sans-serif',
    },
    light: {
      ...scheme({
        canvas: "#f4f4fb", sheet: "#ffffff", sheet2: "#f9f9fd", inset: "#eeeef8",
        rail: "#1b2036", railHi: "#2a3252",
        onRail: "#c9cee4", onRailMuted: "#8d95b4", borderOnRail: "#2b3350",
        textPrimary: "#16182a", textSecondary: "#3a3f5c",
        textMuted: "#666c8c", textSubtle: "#8d95b4",
        borderSubtle: "#e9e9f4", borderDefault: "#dcdcee", borderStrong: "#c3c3de",
        brandSoft: "#eeecff", brandSoftText: "#4a3fb0",
      }),
      ...SOFT_LIGHT,
    },
    dark: {
      ...scheme({
        canvas: "#0c0f18", sheet: "#141824", sheet2: "#181d2b", inset: "#1d2333",
        popover: "#171c29",
        rail: "#12172a", railHi: "#232a45",
        onRail: "#c3c9e0", onRailMuted: "#8b93b0", borderOnRail: "#242b45",
        textPrimary: "#e6e9f5", textSecondary: "#b9c0d8",
        textMuted: "#8b93b0", textSubtle: "#767d99",
        borderSubtle: "#1e2434", borderDefault: "#272e42", borderStrong: "#333c56",
        brandSoft: "#211f3d", brandSoftText: "#b3a8ff",
      }),
      ...SOFT_DARK,
    },
    css: `::selection { background: color-mix(in oklab, #8b7bff 30%, transparent); }`,
  },
];

/** Carbon is the product default. */
export const DEFAULT_TEMPLATE_ID = "carbon";

export function findTemplate(id: string): AppearanceTemplate | undefined {
  return APPEARANCE_TEMPLATES.find((t) => t.id === id);
}
