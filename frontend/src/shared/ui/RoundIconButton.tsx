import type { ComponentProps } from "react";
import { cn } from "@/shared/lib/utils";

interface RoundIconButtonProps extends ComponentProps<"button"> {
  /** Gold state, e.g. the chat toggle while the chat is open. */
  active?: boolean;
}

/** 40px round icon button (previous / next / chat toggle). */
export function RoundIconButton({ active = false, className, ...props }: RoundIconButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        "flex size-10 items-center justify-center rounded-full border p-0 transition-all duration-200",
        "hover:border-gold hover:text-gold",
        active ? "border-gold bg-gold/[0.12] text-gold" : "border-line-strong bg-transparent text-ink-2",
        className,
      )}
      {...props}
    />
  );
}
