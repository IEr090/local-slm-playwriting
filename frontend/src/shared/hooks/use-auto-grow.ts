import { useLayoutEffect, useRef } from "react";

/**
 * Textarea grows downwards with its content, no inner scrolling.
 * `rows` on the textarea stays the minimum height. Re-measures on value change and on width change
 * (e.g. when the chat panel opens or closes).
 */
export function useAutoGrow<T extends HTMLTextAreaElement>(value: string) {
  const ref = useRef<T>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    let width = el.clientWidth;
    const observer = new ResizeObserver(() => {
      if (el.clientWidth === width) return;
      width = el.clientWidth;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}
