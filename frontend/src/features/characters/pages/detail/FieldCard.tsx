import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";

interface FieldCardProps {
  num: number;
  label: string;
  /** Small uppercase hint on the right ("WHAT", "KEY EVENTS ONLY", "4 LINKS"). */
  hint?: string;
  /** Row 1 cards (name, surname, age, gender): tighter padding, smaller label. */
  compact?: boolean;
  /** Gold glow after an AI revision changed this field. */
  highlighted?: boolean;
  /** Red border: a required field left empty after CREATE / SAVE was pressed. */
  invalid?: boolean;
  className?: string;
  children: ReactNode;
}

/** A field card (`.fcard`): gold border while focused, stretches with its grid row. */
export function FieldCard({ num, label, hint, compact, highlighted, invalid, className, children }: FieldCardProps) {
  return (
    <motion.div
      layout="position"
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn(
        "box-border flex min-w-0 flex-col rounded-[10px] border border-line bg-card transition-[border-color,background-color,box-shadow] duration-200",
        "hover:border-line-hover focus-within:border-gold focus-within:bg-card-focus",
        compact ? "gap-1 px-[14px] py-[10px]" : "gap-[10px] px-[18px] pt-[14px] pb-4",
        highlighted && "shadow-[0_0_0_1px_#c9a24b,0_0_24px_#c9a24b44]",
        invalid && "border-terracotta hover:border-terracotta focus-within:border-terracotta",
        className,
      )}
    >
      <div className="flex items-center gap-[10px]">
        <span className="font-sans text-[10px] tracking-[2px] text-gold">{num}</span>
        <span className={cn("font-serif font-medium text-ink", compact ? "text-[15px]" : "text-lg")}>{label}</span>
        {hint && <span className="ml-auto font-sans text-[10px] tracking-[1.5px] text-faint">{hint}</span>}
      </div>
      {children}
    </motion.div>
  );
}
