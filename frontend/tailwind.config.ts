import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      /* Athena design tokens — to be populated from design system */
      colors: {},
      fontFamily: {},
    },
  },
  plugins: [],
};

export default config;
