import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#E8EEF5",
        ink: "#10233A",
        muted: "#5A6B7C",
        line: "#D5DEE8",
        navy: {
          50: "#EAF2FA",
          100: "#D5E4F4",
          700: "#134E7A",
          800: "#0E3A67",
          900: "#0A2748",
        },
        teal: {
          DEFAULT: "#0F766E",
          50: "#F0FDFA",
          100: "#CCFBF1",
          700: "#0F766E",
          800: "#115E59",
          900: "#134E4A",
        },
        clinical: {
          warning: "#B45309",
          danger: "#B91C1C",
          ok: "#047857",
          info: "#1D4ED8",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,39,72,0.04), 0 12px 32px rgba(10,39,72,0.08)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;
