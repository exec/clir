/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Menlo", "monospace"],
      },
      colors: {
        ink: { 50: "#fafaf9", 900: "#0a0a0b" },
        accent: { DEFAULT: "#22d3ee", dark: "#0891b2" },
      },
    },
  },
  plugins: [],
};
