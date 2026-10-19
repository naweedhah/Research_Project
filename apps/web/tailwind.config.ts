import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F4F7FA",
        ink: "#102A4C",
        muted: "#5C6E82",
        line: "#D7E2EC",
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
          warning: "#C4842A",
          danger: "#C45A52",
          ok: "#0F8A78",
          info: "#3E75B8",
          cyan: "#45C4BB",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,42,76,0.04), 0 18px 50px rgba(25,48,72,0.08)",
        elevated: "0 24px 70px rgba(16,42,76,0.14)",
      },
      borderRadius: {
        xl: "1.25rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
