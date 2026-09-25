/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        lagoa: "#0F7A8C",
        terracota: "#9C5227",
        areia: "#FDFBF6",
        grafite: "#1F2A2E",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Sora", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
