import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        hive: {
          bg: '#0a0a0f',
          card: '#12121a',
          border: '#1e1e2e',
          accent: '#f59e0b',
          green: '#22c55e',
          red: '#ef4444',
          blue: '#3b82f6',
          muted: '#6b7280',
          text: '#e5e7eb',
        },
      },
    },
  },
  plugins: [],
}
export default config
