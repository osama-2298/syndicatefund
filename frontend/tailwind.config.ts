import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        syn: {
          bg: '#09090b',
          surface: '#0f0f13',
          elevated: '#18181b',
          border: '#27272a',
          'border-subtle': '#1c1c1f',
          accent: '#8b5cf6',
          'accent-hover': '#7c3aed',
          'accent-muted': 'rgba(139, 92, 246, 0.25)',
          secondary: '#06b6d4',
          success: '#22c55e',
          danger: '#ef4444',
          warning: '#f59e0b',
          text: '#fafafa',
          'text-secondary': '#a1a1aa',
          'text-tertiary': '#52525b',
          muted: '#71717a',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
export default config
