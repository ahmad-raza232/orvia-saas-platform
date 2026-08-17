/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        olive: {
          DEFAULT: '#556B2F',
          hover: '#445526',
          dark: '#3A4A20',
          muted: '#6B8044',
          light: '#E7EED8',
        },
        peach: {
          DEFAULT: '#FFDAB9',
          soft: '#FFF1E3',
          deep: '#F0C9A0',
        },
        canvas: '#F7F1E9',
        surface: '#FFFCFA',
        muted: '#F3EBE1',
        ink: {
          DEFAULT: '#1C1917',
          secondary: '#57534E',
          muted: '#78716C',
        },
        line: '#E6DDD2',
        success: {
          DEFAULT: '#3F6B3A',
          soft: '#E7F0E4',
        },
        warning: {
          DEFAULT: '#B45309',
          soft: '#F8EBD8',
        },
        danger: {
          DEFAULT: '#B42318',
          soft: '#F8E4E1',
        },
        info: {
          DEFAULT: '#3D5A80',
          soft: '#E4EBF4',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        display: ['clamp(2.75rem, 6vw, 4.75rem)', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
        h1: ['clamp(2rem, 3.5vw, 2.75rem)', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
        h2: ['clamp(1.6rem, 2.5vw, 2.15rem)', { lineHeight: '1.2', letterSpacing: '-0.02em' }],
        h3: ['1.25rem', { lineHeight: '1.35', letterSpacing: '-0.01em' }],
      },
      borderRadius: {
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '20px',
      },
      boxShadow: {
        xs: '0 1px 2px rgba(28, 25, 23, 0.04)',
        sm: '0 6px 20px rgba(28, 25, 23, 0.05)',
        md: '0 12px 36px rgba(28, 25, 23, 0.07)',
        focus: '0 0 0 4px rgba(85, 107, 47, 0.18)',
      },
      maxWidth: {
        container: '72rem',
      },
      transitionDuration: {
        DEFAULT: '200ms',
      },
    },
  },
  plugins: [],
};
