import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#e6edf5',
          100: '#ccdaeb',
          200: '#99b5d7',
          300: '#6690c3',
          400: '#336baf',
          500: '#003366',
          600: '#002952',
          700: '#001f3d',
          800: '#001429',
          900: '#000a14',
        },
        accent: {
          50:  '#fff3ee',
          100: '#ffe7dc',
          200: '#ffcfb9',
          300: '#ffb796',
          400: '#ff9f73',
          500: '#FF6B35',
          600: '#e5532b',
          700: '#b33d1d',
          800: '#802c13',
          900: '#4d1a0b',
        },
        surface: {
          light: '#F8F6F1',
          dark:  '#0A0F1A',
        },
      },
      fontFamily: {
        sans:    ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        serif:   ['Playfair Display', 'Georgia', 'serif'],
        mono:    ['IBM Plex Mono', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      spacing: {
        sidebar: '272px',
      },
      boxShadow: {
        card:     '0 1px 3px 0 rgba(0,51,102,0.08), 0 1px 2px -1px rgba(0,51,102,0.06)',
        'card-hover': '0 4px 16px 0 rgba(0,51,102,0.14), 0 2px 6px -1px rgba(0,51,102,0.10)',
        sidebar:  '1px 0 0 0 rgba(0,51,102,0.08)',
      },
      backgroundImage: {
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-16px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.4' },
        },
      },
      animation: {
        'fade-in':       'fade-in 0.35s ease-out both',
        'slide-in-left': 'slide-in-left 0.3s ease-out both',
        'shimmer':       'shimmer 1.8s linear infinite',
        'pulse-dot':     'pulse-dot 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
