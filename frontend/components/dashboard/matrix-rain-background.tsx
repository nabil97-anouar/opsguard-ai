"use client";

import { useEffect, useRef } from "react";
import { advanceRain, createRainStreams, rainGlyph, type RainMode } from "@/lib/matrix-rain";

export function MatrixRainBackground({ mode = "full" }: { mode?: RainMode }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let streams = createRainStreams(0, 0);
    let frame = 0;
    let previousTime = 0;
    let clock = 0;
    let width = 0;
    let height = 0;

    const paint = () => {
      context.fillStyle = "#010503";
      context.fillRect(0, 0, width, height);
      context.font = "16px ui-monospace, SFMono-Regular, Menlo, monospace";
      context.textAlign = "center";
      for (const stream of streams) {
        const intensity = stream.depth * (mode === "calm" ? 0.65 : 1);
        for (let position = stream.length; position >= 0; position -= 1) {
          const y = stream.head - position * 18;
          if (y < -18 || y > height + 18) continue;
          const fade = Math.pow(1 - position / (stream.length + 1), 1.7);
          context.fillStyle = position === 0
            ? `rgba(213,255,224,${intensity})`
            : `rgba(0,${position < 4 ? 255 : 220},${position < 4 ? 110 : 67},${fade * intensity})`;
          context.shadowBlur = position === 0 && stream.depth === 1 ? 9 : 0;
          context.shadowColor = "#00ff66";
          context.fillText(rainGlyph(stream.seed, position, clock), stream.x, y);
        }
      }
      context.shadowBlur = 0;
    };
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      streams = createRainStreams(width, height);
      paint();
    };
    const draw = (timestamp: number) => {
      if (document.hidden || reducedMotion.matches || mode === "paused") return;
      if (!previousTime) previousTime = timestamp;
      const elapsed = timestamp - previousTime;
      // 30 FPS cap; cap resume deltas so a hidden window never jumps ahead.
      if (elapsed >= 1000 / 30) {
        const seconds = Math.min(elapsed / 1000, 0.1);
        clock += seconds;
        advanceRain(streams, seconds, height, mode);
        paint();
        previousTime = timestamp;
      }
      frame = window.requestAnimationFrame(draw);
    };
    const restart = () => {
      window.cancelAnimationFrame(frame);
      previousTime = 0;
      paint();
      if (!document.hidden && !reducedMotion.matches && mode !== "paused") {
        frame = window.requestAnimationFrame(draw);
      }
    };
    resize();
    restart();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", restart);
    reducedMotion.addEventListener("change", restart);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", restart);
      reducedMotion.removeEventListener("change", restart);
    };
  }, [mode]);

  return <canvas ref={canvasRef} className="matrix-rain" aria-hidden="true" data-rain-mode={mode} />;
}
