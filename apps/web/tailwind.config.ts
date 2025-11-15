import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#030712",
        surface: "rgba(15, 23, 42, 0.9)",
        accent: "#22d3ee",
        accentSoft: "#0ea5e9"
      },
      fontFamily: {
        sans: ["system-ui", "sans-serif"]
      },
      boxShadow: {
        "futuristic": "0 0 40px rgba(34, 211, 238, 0.35)"
      }
    }
  },
  plugins: []
};

export default config;
