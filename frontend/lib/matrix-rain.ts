export type RainMode = "full" | "calm" | "paused";

export const MATRIX_GLYPHS = "01234567890101アイウエオカキクケコサシスセソタチツテトナニヌネノ<>[]{}:+";

export type RainStream = {
  x: number;
  head: number;
  speed: number;
  length: number;
  seed: number;
  depth: number;
};

// A stable initial field is already visible on the first frame, including when
// motion is disabled. Motion advances in seconds, not in animation frames.
export function createRainStreams(width: number, height: number): RainStream[] {
  const streams: RainStream[] = [];
  for (let column = 0; column < Math.ceil(width / 22); column += 1) {
    const seed = (column * 7919 + 193) % 104729;
    streams.push({
      x: column * 22 + 6,
      head: (seed % Math.max(1, height + 400)) - 100,
      speed: 45 + (seed % 112),
      length: 16 + (seed % 23),
      seed,
      depth: column % 4 === 0 ? 0.42 : column % 3 === 0 ? 0.7 : 1,
    });
  }
  return streams;
}

export function advanceRain(streams: RainStream[], elapsedSeconds: number, height: number, mode: RainMode): void {
  if (mode === "paused") return;
  const multiplier = mode === "calm" ? 0.32 : 1;
  for (const stream of streams) {
    stream.head += stream.speed * elapsedSeconds * multiplier;
    const span = height + stream.length * 18;
    if (stream.head > span) stream.head %= span;
  }
}

export function rainGlyph(seed: number, position: number, time: number): string {
  const index = Math.abs(seed + position * 13 + Math.floor(time * 5) * 7) % MATRIX_GLYPHS.length;
  return MATRIX_GLYPHS[index];
}
