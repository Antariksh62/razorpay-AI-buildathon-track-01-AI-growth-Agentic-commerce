/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        razorpay: {
          blue: '#02042b',
          accent: '#3395ff',
          dark: '#0c0f1d',
          card: '#15192c',
          border: '#242b45',
        }
      }
    },
  },
  plugins: [],
}
