import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";
import { Alert } from "./icons";

/** Calm warning in a bordered box: gold alert icon, italic text. Not an error, nothing to dismiss. */
export function Notice({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      role="note"
      className={cn(
        "flex animate-fade-up items-center gap-3 rounded-[10px] border border-line-strong px-4 py-3 font-sans text-[13px] leading-[1.5] text-ink-2 italic",
        className,
      )}
    >
      <Alert className="shrink-0 text-gold" />
      <span>{children}</span>
    </div>
  );
}
