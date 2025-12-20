/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // 背景基调：深空灰蓝
        'void': '#030508',
        'void-light': '#0a0c10',
        // 功能色：低饱和度科幻色
        'sci-blue': '#3b82f6',
        'sci-green': '#10b981',
        'sci-red': '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '24px', // Sci-Fi 风格大圆角
      },
      backdropBlur: {
        'xs': '2px',
        'xl': '20px', // 深度磨砂
      }
    },
  },
  plugins: [],
}
