import type { ComponentProps } from "react";
import { cn } from "@/shared/lib/utils";

/** Outlined pill button (`.pill` in the prototype). */
export function Pill({ className, ...props }: ComponentProps<"button">) {
  return (
    <button
      type="button"
      className={cn(
        "rounded-full border border-line-strong bg-transparent px-[18px] py-[10px] font-sans text-xs tracking-[1px] text-ink-2",
        "transition-colors duration-150 hover:border-gold hover:text-gold",
        className,
      )}
      {...props}
    />
  );
}

/** Gold outlined pill — the main call to action (`.pill-gold`). */
export function GoldPill({ className, ...props }: ComponentProps<"button">) {
  return (
    <button
      type="button"
      className={cn(
        "flex items-center gap-[10px] rounded-full border border-gold bg-transparent px-[22px] py-[11px] font-sans text-[13px] tracking-[1.5px] text-gold",
        "transition-[background-color] duration-150 hover:bg-gold/[0.133]",
        className,
      )}
      {...props}
    />
  );
}
