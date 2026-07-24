"use client";

import { useEffect, useRef } from "react";

const activeLocks = new Set<symbol>();
let originalOverflow = "";

export function useBodyScrollLock(active: boolean) {
  const lockId = useRef(Symbol("fanora-modal-scroll-lock"));

  useEffect(() => {
    if (!active) return;
    const id = lockId.current;
    if (activeLocks.size === 0) originalOverflow = document.body.style.overflow;
    activeLocks.add(id);
    document.body.style.overflow = "hidden";

    return () => {
      activeLocks.delete(id);
      if (activeLocks.size === 0) {
        document.body.style.overflow = originalOverflow;
        originalOverflow = "";
      }
    };
  }, [active]);
}
