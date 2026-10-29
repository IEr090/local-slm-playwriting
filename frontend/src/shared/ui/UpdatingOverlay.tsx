import { AnimatePresence, motion } from "motion/react";
import { cn } from "@/shared/lib/utils";
import { Orb } from "./Orb";

interface UpdatingOverlayProps {
  show: boolean;
  /** Shimmering label, e.g. "UPDATING CARD", "UPDATING", "REVISING". */
  label?: string;
  /** The small "A" above the label (cast cards); field cards show the label only. */
  orb?: boolean;
  className?: string;
}

/** Blurred overlay with a shimmering label while the AI rewrites what is under it. The parent needs `relative`. */
export function UpdatingOverlay({ show, label = "UPDATING", orb = false, className }: UpdatingOverlayProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.span
          role="status"
          aria-label={label.charAt(0) + label.slice(1).toLowerCase()}
          className={cn(
            "absolute inset-0 z-[2] flex flex-col items-center justify-center gap-[14px] rounded-[inherit] bg-bg/65 backdrop-blur-[5px]",
            className,
          )}
          initial={{ opacity: 0, y: orb ? 8 : 0 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: orb ? 0.4 : 0.3, ease: "easeOut" }}
        >
          {orb && <Orb variant="mini" />}
          <span className="shimmer-text block font-sans text-[11px] tracking-[3px]">{label}</span>
        </motion.span>
      )}
    </AnimatePresence>
  );
}
