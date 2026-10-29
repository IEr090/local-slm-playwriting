import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { cn } from "@/shared/lib/utils";
import { VeilOrb } from "./Orb";

interface GenerationVeilProps {
  show: boolean;
  /** Shimmering uppercase label, e.g. "WRITING THE OUTLINE". */
  label: string;
  /** Italic line under the label. */
  line: string;
  /** No rounded corners: the veil covers a whole column, not a card. */
  flat?: boolean;
  className?: string;
}

/** Blurred veil with the turning "A" over whatever the model is writing right now. The parent needs `relative`. */
export function GenerationVeil({ show, label, line, flat = false, className }: GenerationVeilProps) {
  // while it fades out, the veil keeps the words it had
  const [shown, setShown] = useState({ label, line });
  if (show && (shown.label !== label || shown.line !== line)) setShown({ label, line });
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          role="status"
          aria-label={shown.label.charAt(0) + shown.label.slice(1).toLowerCase()}
          className={cn(
            "absolute inset-0 z-[3] flex flex-col items-center justify-center bg-bg/65 backdrop-blur-[5px]",
            flat ? "rounded-none" : "rounded-[10px]",
            className,
          )}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        >
          <div className="flex animate-fade-up flex-col items-center gap-[14px]">
            <VeilOrb />
            <span className="shimmer-text block font-sans text-[11px] tracking-[3px]">{shown.label}</span>
            <span className="font-sans text-xs text-muted italic">{shown.line}</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
