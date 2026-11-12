import { useEffect, useRef, type RefObject } from "react";

/** True while the page is being reloaded or closed, which cancels the running requests. */
export function useUnloading(): RefObject<boolean> {
  const unloading = useRef(false);
  useEffect(() => {
    const leave = () => {
      unloading.current = true;
    };
    // back from the back-forward cache: the page lives on
    const back = () => {
      unloading.current = false;
    };
    window.addEventListener("pagehide", leave);
    window.addEventListener("beforeunload", leave);
    window.addEventListener("pageshow", back);
    return () => {
      window.removeEventListener("pagehide", leave);
      window.removeEventListener("beforeunload", leave);
      window.removeEventListener("pageshow", back);
    };
  }, []);
  return unloading;
}
