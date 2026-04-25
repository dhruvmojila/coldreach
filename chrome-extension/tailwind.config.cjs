/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx,html}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#5b8cff",
          dark: "#3b6fef",
        },
      },
    },
  },
  plugins: [],
};
