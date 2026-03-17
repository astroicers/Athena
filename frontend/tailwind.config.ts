import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Core backgrounds
        "athena-bg": "var(--color-bg-primary)",
        "athena-surface": "var(--color-bg-surface)",
        "athena-elevated": "var(--color-bg-elevated)",
        "athena-surface-hover": "var(--color-bg-surface-hover)",
        "athena-overlay": "var(--color-bg-overlay)",
        // White opacity scale (backgrounds)
        "athena-white-5": "var(--color-white-5)",
        "athena-white-8": "var(--color-white-8)",
        "athena-white-10": "var(--color-white-10)",
        // Accent
        "athena-accent": "var(--color-accent)",
        "athena-accent-hover": "var(--color-accent-hover)",
        "athena-accent-bg": "var(--color-accent-bg)",
        // Text hierarchy
        "athena-text": "var(--color-text-primary)",
        "athena-text-secondary": "var(--color-text-secondary)",
        "athena-text-tertiary": "var(--color-text-tertiary)",
        "athena-text-ghost": "var(--color-text-ghost)",
        "athena-text-faint": "var(--color-text-faint)",
        "athena-text-muted": "var(--color-text-muted)",
        "athena-text-dim": "var(--color-text-dim)",
        "athena-text-soft": "var(--color-text-soft)",
        "athena-text-subtle": "var(--color-text-subtle)",
        // Border
        "athena-border": "var(--color-border)",
        // Status
        "athena-success": "var(--color-success)",
        "athena-success-bg": "var(--color-success-bg)",
        "athena-warning": "var(--color-warning)",
        "athena-warning-bg": "var(--color-warning-bg)",
        "athena-warning-alt": "var(--color-warning-alt)",
        "athena-error": "var(--color-error)",
        "athena-error-bg": "var(--color-error-bg)",
        "athena-critical": "var(--color-critical)",
        "athena-info": "var(--color-info)",
        // OODA phase colors
        "athena-phase-observe": "var(--color-phase-observe)",
        "athena-phase-orient": "var(--color-phase-orient)",
        "athena-phase-decide": "var(--color-phase-decide)",
        "athena-phase-act": "var(--color-phase-act)",
      },
      fontSize: {
        "athena-floor": "var(--fs-floor)",
        "athena-caption": "var(--fs-caption)",
        "athena-body": "var(--fs-body)",
        "athena-heading-card": "var(--fs-heading-card)",
        "athena-heading-section": "var(--fs-heading-section)",
        "athena-heading-page": "var(--fs-heading-page)",
        "athena-metric": "var(--fs-metric)",
        "athena-metric-label": "var(--fs-metric-label)",
      },
      fontFamily: {
        mono: ["var(--font-mono)"],
        sans: ["var(--font-sans)"],
      },
      borderRadius: {
        "athena-sm": "var(--radius-sm)",
        "athena-md": "var(--radius-md)",
        "athena-lg": "var(--radius-lg)",
      },
    },
  },
  plugins: [],
};

export default config;
