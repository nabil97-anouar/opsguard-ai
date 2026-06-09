import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0a0a0a",
        surface: "#111111",
        panel: "#161b22",
        line: "#243041",
        accent: "#3b82f6",
        accentSoft: "#60a5fa",
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
        critical: "#dc2626"
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"]
      },
      boxShadow: {
        panel: "0 20px 60px rgba(2, 6, 23, 0.45)",
        glow: "0 0 0 1px rgba(96, 165, 250, 0.15), 0 20px 50px rgba(59, 130, 246, 0.18)"
      },
      backgroundImage: {
        grid: "linear-gradient(to right, rgba(148, 163, 184, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(148, 163, 184, 0.08) 1px, transparent 1px)"
      },
      animation: {
        float: "float 8s ease-in-out infinite",
        pulseSoft: "pulseSoft 3s ease-in-out infinite"
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" }
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" }
        }
      }
    }
  },
  plugins: []
};

export default config;
