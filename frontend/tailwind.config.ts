import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        "athena-bg": "var(--color-bg-primary)",
        "athena-surface": "var(--color-bg-surface)",
        "athena-elevated": "var(--color-bg-elevated)",
        "athena-accent": "var(--color-accent)",
        "athena-accent-hover": "var(--color-accent-hover)",
        "athena-text": "var(--color-text-primary)",
        "athena-text-secondary": "var(--color-text-secondary)",
        "athena-border": "var(--color-border)",
        "athena-success": "var(--color-success)",
        "athena-warning": "var(--color-warning)",
        "athena-error": "var(--color-error)",
        "athena-critical": "var(--color-critical)",
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
