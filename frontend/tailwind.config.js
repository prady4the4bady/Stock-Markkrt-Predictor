/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Neon accent colors
                neon: {
                    cyan: '#00f5ff',
                    purple: '#bf00ff',
                    pink: '#ff00f5',
                    green: '#00ff88',
                    orange: '#ff6b00',
                },
                // Dark glass theme
                glass: {
                    50: 'rgba(255, 255, 255, 0.05)',
                    100: 'rgba(255, 255, 255, 0.1)',
                    200: 'rgba(255, 255, 255, 0.2)',
                    300: 'rgba(255, 255, 255, 0.3)',
                    dark: 'rgba(10, 10, 20, 0.8)',
                    darker: 'rgba(5, 5, 15, 0.95)',
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'mesh': 'linear-gradient(135deg, #0a0a14 0%, #1a0a2e 50%, #0a1428 100%)',
            },
            boxShadow: {
                'neon-cyan': '0 0 20px rgba(0, 245, 255, 0.3), 0 0 40px rgba(0, 245, 255, 0.1)',
                'neon-purple': '0 0 20px rgba(191, 0, 255, 0.3), 0 0 40px rgba(191, 0, 255, 0.1)',
                'neon-green': '0 0 20px rgba(0, 255, 136, 0.3), 0 0 40px rgba(0, 255, 136, 0.1)',
                'glow': '0 0 60px rgba(0, 245, 255, 0.1)',
            },
            animation: {
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'float': 'float 6s ease-in-out infinite',
                'glow': 'glow 2s ease-in-out infinite alternate',
                'gradient': 'gradient 8s linear infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-10px)' },
                },
                glow: {
                    '0%': { boxShadow: '0 0 20px rgba(0, 245, 255, 0.2)' },
                    '100%': { boxShadow: '0 0 40px rgba(0, 245, 255, 0.4)' },
                },
                gradient: {
                    '0%': { backgroundPosition: '0% 50%' },
                    '50%': { backgroundPosition: '100% 50%' },
                    '100%': { backgroundPosition: '0% 50%' },
                },
            },
            backdropBlur: {
                xs: '2px',
            }
        },
    },
    plugins: [],
}
