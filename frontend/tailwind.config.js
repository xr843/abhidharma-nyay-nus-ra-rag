/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef7ee',
          100: '#fdedd6',
          200: '#f9d7ad',
          300: '#f5b978',
          400: '#f09341',
          500: '#ec751b',
          600: '#dd5b11',
          700: '#b74410',
          800: '#923615',
          900: '#762f14',
          950: '#401508',
        },
        buddhist: {
          gold: '#c9a227',
          maroon: '#8b0000',
          saffron: '#f4c430',
          lotus: '#e8b4b8',
        }
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'Source Han Serif CN', 'serif'],
        sans: ['Noto Sans SC', 'Source Han Sans CN', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

