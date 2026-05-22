/** @type {import('tailwindcss').Config} */
export default {
  // Tell Tailwind which files contain class names — it removes unused ones at build time
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Add custom colours or spacing here when the design grows
    },
  },
  plugins: [],
}
