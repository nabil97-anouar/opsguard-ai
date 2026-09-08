"use client";

import { useEffect, useRef } from "react";

const GLYPHS = "01ABCDEFGHIJKLMNOPQRSTUVWXYZ#$%*+";

export function MatrixRainBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const context = canvas.getContext("2d");
    if (!context) return;

    let frame = 0;
    let timer = 0;
    let drops: number[] = [];
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(canvas.clientWidth * ratio);
      canvas.height = Math.floor(canvas.clientHeight * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      drops = Array.from({ length: Math.ceil(canvas.clientWidth / 24) }, () => Math.random() * -30);
    };
    const draw = () => {
      if (document.hidden || reducedMotion.matches) return;
      context.fillStyle = "rgba(2, 4, 3, 0.09)";
      context.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
      context.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
      context.fillStyle = "rgba(0, 255, 102, 0.32)";
      drops.forEach((drop, index) => {
        const glyph = GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        context.fillText(glyph, index * 24, drop * 18);
        drops[index] = drop * 18 > canvas.clientHeight && Math.random() > 0.985 ? 0 : drop + 0.28;
      });
      frame = window.requestAnimationFrame(draw);
    };
    const restart = () => {
      window.cancelAnimationFrame(frame);
      if (!document.hidden && !reducedMotion.matches) frame = window.requestAnimationFrame(draw);
    };
    resize();
    restart();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", restart);
    reducedMotion.addEventListener("change", restart);
    timer = window.setTimeout(restart, 20);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", restart);
      reducedMotion.removeEventListener("change", restart);
    };
  }, []);

  return <canvas ref={canvasRef} className="matrix-rain" aria-hidden="true" />;
}
