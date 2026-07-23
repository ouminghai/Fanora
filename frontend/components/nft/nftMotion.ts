import type { PointerEvent, SyntheticEvent } from "react";

export function updateNftTilt<T extends HTMLElement>(event: PointerEvent<T>) {
  if (event.pointerType === "touch") return;
  const element = event.currentTarget;
  const rect = element.getBoundingClientRect();
  const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
  element.style.setProperty("--nft-rotate-x", `${((0.5 - y) * 6).toFixed(2)}deg`);
  element.style.setProperty("--nft-rotate-y", `${((x - 0.5) * 6).toFixed(2)}deg`);
  element.style.setProperty("--nft-glare-x", `${(x * 100).toFixed(1)}%`);
  element.style.setProperty("--nft-glare-y", `${(y * 100).toFixed(1)}%`);
  element.style.setProperty("--nft-glare-opacity", "1");
  element.style.boxShadow = "0 20px 52px rgba(5, 6, 25, .30), 0 7px 18px rgba(69, 191, 239, .07)";
}

export function resetNftTilt<T extends HTMLElement>(event: SyntheticEvent<T>) {
  const element = event.currentTarget;
  element.style.setProperty("--nft-rotate-x", "0deg");
  element.style.setProperty("--nft-rotate-y", "0deg");
  element.style.setProperty("--nft-glare-opacity", "0");
  element.style.removeProperty("box-shadow");
}
