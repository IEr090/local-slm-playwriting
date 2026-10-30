import type { ComponentProps } from "react";
import { cn } from "@/shared/lib/utils";

interface HeaderPillProps extends ComponentProps<"button"> {
  /** Outlined grey pill (back links, "EDIT OUTLINE") instead of the gold one. */
  ghost?: boolean;
  /** 30px high, for pills inside a column. */
  small?: boolean;
}

/** 40px pill of the page headers ("ALL CHARACTERS", "SAVE", "APPROVE OUTLINE"). */
export function HeaderPill({ ghost = false, small = false, className, ...props }: HeaderPillProps) {
  return (
    <button
      type="button"
      className={cn(
        "box-border inline-flex items-center justify-center gap-[10px] rounded-full border bg-transparent font-sans leading-none whitespace-nowrap",
        "transition-[background-color,opacity,border-color,color] duration-150 disabled:cursor-default disabled:opacity-35",
        small ? "h-[30px] px-[14px] text-[10px] tracking-[2px]" : "h-10 px-5 text-[11px] tracking-[2px]",
        ghost
          ? "border-line-strong text-ink-2 hover:border-gold hover:text-gold disabled:hover:border-line-strong disabled:hover:text-ink-2"
          : "border-gold text-gold hover:bg-gold/[0.133] disabled:hover:bg-transparent",
        className,
      )}
      {...props}
    />
  );
}
