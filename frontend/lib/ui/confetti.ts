import type { Options } from "canvas-confetti";

export async function startRealisticConfetti(durationMs = 3000): Promise<() => void> {
  if (typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return () => undefined;
  }

  const { default: confetti } = await import("canvas-confetti");
  const count = 1000;
  const defaults: Options = {
    zIndex: 1700,
  };

  const fire = (particleRatio: number, options: Options) => {
    const particleCount = Math.floor((count * particleRatio) / 2);
    void confetti({
      ...defaults,
      ...options,
      particleCount,
      angle: 30,
      origin: { x: 0.04, y: 0.72 },
    });
    void confetti({
      ...defaults,
      ...options,
      particleCount,
      angle: 150,
      origin: { x: 0.96, y: 0.72 },
    });
  };

  fire(0.25, { spread: 26, startVelocity: 75 });
  fire(0.2, { spread: 60, startVelocity: 65 });
  fire(0.35, { spread: 100, startVelocity: 60, decay: 0.91, scalar: 0.8 });
  fire(0.1, { spread: 120, startVelocity: 50, decay: 0.92, scalar: 1.2 });
  fire(0.1, { spread: 120, startVelocity: 70 });

  const timeout = window.setTimeout(() => confetti.reset(), durationMs);

  return () => {
    window.clearTimeout(timeout);
    confetti.reset();
  };
}
