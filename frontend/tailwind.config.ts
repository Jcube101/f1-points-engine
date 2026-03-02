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
      screens: {
        xs: '390px', // iPhone 14 baseline
      },
    },
  },
  plugins: [
    // Hide scrollbars visually while keeping scroll functionality
    function({ addUtilities }: { addUtilities: (u: Record<string, unknown>) => void }) {
      addUtilities({
        '.scrollbar-none': {
          'scrollbar-width': 'none',
          '-ms-overflow-style': 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        },
      })
    },
  ],
}

export default config
