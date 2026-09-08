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
        ink: "#020403",
        surface: "#050806",
        panel: "#07100a",
        line: "#163322",
        accent: "#00ff66",
        accentSoft: "#45ff8a",
        success: "#19c96b",
        warning: "#f59e0b",
        danger: "#ef4444",
        critical: "#dc2626"
      },
      fontFamily: {
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        body: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["SFMono-Regular", "Cascadia Code", "Roboto Mono", "Menlo", "monospace"]
      },
      boxShadow: {
        panel: "0 20px 60px rgba(0, 0, 0, 0.5)",
        glow: "0 0 0 1px rgba(0, 255, 102, 0.22), 0 0 34px rgba(0, 255, 102, 0.12)"
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
