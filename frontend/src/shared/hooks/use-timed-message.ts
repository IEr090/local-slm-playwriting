import { useCallback, useEffect, useRef, useState } from "react";

export interface TimedMessage {
  open: boolean;
  /** The last message; kept while the toast fades out. */
  message: string;
  /** Shows a message; showing one again replaces it and restarts the timer. */
  show(message: string): void;
}

/** A message for the bottom toast that hides itself after `ms`. */
export function useTimedMessage(ms: number): TimedMessage {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const show = useCallback(
    (next: string) => {
      clearTimeout(timer.current);
      setMessage(next);
      setOpen(true);
      timer.current = setTimeout(() => setOpen(false), ms);
    },
    [ms],
  );
  return { open, message, show };
}
