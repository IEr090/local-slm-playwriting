let canvas: HTMLCanvasElement | null = null;

/** Rendered width of `text` in `font` (CSS font shorthand), via an offscreen canvas. */
export function measureText(text: string, font: string): number {
  canvas ??= document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return text.length * 10;
  ctx.font = font;
  return ctx.measureText(text).width;
}
