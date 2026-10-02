/** @type {import('tailwindcss').Config} */
const cssVar = (name) => `var(--${name})`;

const surfaces = {
  page: cssVar("color-bg-page"),
  surface: cssVar("color-bg-surface"),
  subtle: cssVar("color-bg-subtle"),
  header: cssVar("color-bg-header"),
  action: cssVar("color-action-primary"),
  "action-hover": cssVar("color-action-primary-hover"),
  "action-active": cssVar("color-action-primary-active"),
  "action-secondary": cssVar("color-action-secondary"),
  online: cssVar("color-indicator-online"),
  "accent-subtle": cssVar("color-accent-subtle-bg"),
  "neutral-subtle": cssVar("color-neutral-subtle-bg"),
  "status-success": cssVar("color-status-success-bg"),
  "status-warning": cssVar("color-status-warning-bg"),
  "status-error": cssVar("color-status-error-bg"),
  "status-info": cssVar("color-status-info-bg"),
  "occupancy-low": cssVar("color-occupancy-low-bg"),
  "occupancy-medium": cssVar("color-occupancy-medium-bg"),
  "occupancy-full": cssVar("color-occupancy-full-bg"),
};

const texts = {
  primary: cssVar("color-text-primary"),
  secondary: cssVar("color-text-secondary"),
  muted: cssVar("color-text-muted"),
  link: cssVar("color-text-link"),
  "on-action": cssVar("color-text-on-action"),
  "on-header": cssVar("color-text-on-header"),
  "accent-subtle": cssVar("color-accent-subtle-fg"),
  "neutral-subtle": cssVar("color-neutral-subtle-fg"),
  "status-success": cssVar("color-status-success-fg"),
  "status-warning": cssVar("color-status-warning-fg"),
  "status-error": cssVar("color-status-error-fg"),
  "status-info": cssVar("color-status-info-fg"),
  "occupancy-low": cssVar("color-occupancy-low-fg"),
  "occupancy-medium": cssVar("color-occupancy-medium-fg"),
  "occupancy-full": cssVar("color-occupancy-full-fg"),
};

const borders = {
  subtle: cssVar("color-border-subtle"),
  strong: cssVar("color-border-strong"),
  focus: cssVar("color-focus-ring"),
  attention: cssVar("color-border-attention"),
};

const spacingScale = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16];

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: { transparent: "transparent", current: "currentColor", inherit: "inherit" },
    backgroundColor: ({ theme }) => ({ ...theme("colors"), ...surfaces }),
    textColor: ({ theme }) => ({ ...theme("colors"), ...texts }),
    borderColor: ({ theme }) => ({ ...theme("colors"), ...borders }),
    divideColor: ({ theme }) => ({ ...theme("colors"), ...borders }),
    ringColor: ({ theme }) => ({ ...theme("colors"), ...borders }),
    outlineColor: ({ theme }) => ({ ...theme("colors"), ...borders }),
    spacing: {
      px: "1px",
      ...Object.fromEntries(spacingScale.map((n) => [n, cssVar(`space-${n}`)])),
    },
    fontFamily: {
      sans: [cssVar("font-sans")],
      display: [cssVar("font-display")],
      mono: [cssVar("font-mono")],
    },
    fontSize: {
      xs: [cssVar("text-xs"), cssVar("leading-normal")],
      sm: [cssVar("text-sm"), cssVar("leading-normal")],
      base: [cssVar("text-base"), cssVar("leading-normal")],
      lg: [cssVar("text-lg"), cssVar("leading-normal")],
      xl: [cssVar("text-xl"), cssVar("leading-tight")],
      "2xl": [cssVar("text-2xl"), cssVar("leading-tight")],
      "3xl": [cssVar("text-3xl"), cssVar("leading-tight")],
    },
    fontWeight: {
      normal: cssVar("font-weight-regular"),
      medium: cssVar("font-weight-medium"),
      semibold: cssVar("font-weight-semibold"),
      bold: cssVar("font-weight-bold"),
    },
    borderRadius: {
      none: "0",
      sm: cssVar("radius-sm"),
      md: cssVar("radius-md"),
      lg: cssVar("radius-lg"),
      full: cssVar("radius-full"),
    },
    boxShadow: {
      none: "none",
      sm: cssVar("shadow-sm"),
      md: cssVar("shadow-md"),
      lg: cssVar("shadow-lg"),
    },
    zIndex: {
      base: cssVar("z-base"),
      dropdown: cssVar("z-dropdown"),
      sticky: cssVar("z-sticky"),
      overlay: cssVar("z-overlay"),
      modal: cssVar("z-modal"),
      toast: cssVar("z-toast"),
    },
    transitionDuration: {
      fast: cssVar("duration-fast"),
      DEFAULT: cssVar("duration-base"),
      slow: cssVar("duration-slow"),
    },
    screens: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px" },
    extend: {
      width: {
        sidebar: cssVar("size-sidebar"),
        panel: cssVar("size-panel"),
        search: cssVar("size-search"),
      },
    },
  },
  plugins: [],
};
