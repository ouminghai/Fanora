"use client";

import { useEffect } from "react";

export default function ModeChanger() {
  useEffect(() => {
    const htmlElm = document.getElementsByTagName("html")[0];
    const currentState = localStorage.getItem("idDarkMode");
    const isDarkMode = currentState === null || currentState === "true";

    if (isDarkMode) {
      htmlElm.classList.add("dark");
    } else {
      htmlElm.classList.remove("dark");
    }

    if (currentState === null) {
      localStorage.setItem("idDarkMode", "true");
    }
  }, []);
  return <></>;
}
