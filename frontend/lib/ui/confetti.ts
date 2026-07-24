export async function startRealisticConfetti(durationMs = 3000): Promise<() => void> {
  if (typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return () => undefined;
  }

  const { default: confetti } = await import("canvas-confetti");
  const animationEnd = Date.now() + durationMs;
  const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 1700 };
  let stopped = false;

  const randomInRange = (min: number, max: number) => Math.random() * (max - min) + min;
  const fire = () => {
    if (stopped) return;
    const timeLeft = animationEnd - Date.now();
    if (timeLeft <= 0) return;
    const particleCount = Math.max(8, 50 * (timeLeft / durationMs));
    void confetti({
      ...defaults,
      particleCount,
      origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
    });
    void confetti({
      ...defaults,
      particleCount,
      origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
    });
  };

  fire();
  const interval = window.setInterval(fire, 250);
  const timeout = window.setTimeout(() => {
    stopped = true;
    window.clearInterval(interval);
  }, durationMs);

  return () => {
    stopped = true;
    window.clearInterval(interval);
    window.clearTimeout(timeout);
  };
}
