import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        f1red: '#E8002D',
        f1dark: '#15151E',
        f1gray: '#1E1E2E',
      },
    },
  },
  plugins: [],
}

export default config
