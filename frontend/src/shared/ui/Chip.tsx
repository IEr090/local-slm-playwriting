import type { ComponentProps } from "react";
import { cn } from "@/shared/lib/utils";

interface ChipProps extends ComponentProps<"button"> {
  selected?: boolean;
}

/** Selectable chip for gender and dramatic role (`.chip` / `.chip-on`). */
export function Chip({ selected = false, className, ...props }: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "rounded-full border px-3 py-[6px] font-sans text-[11px] tracking-[1px] transition-all duration-150",
        selected
          ? "border-gold bg-gold/[0.12] text-gold-light"
          : "border-line bg-transparent text-muted hover:border-gold hover:text-gold-soft",
        className,
      )}
      {...props}
    />
  );
}
