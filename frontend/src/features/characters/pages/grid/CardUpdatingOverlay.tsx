import { AnimatePresence, motion } from "motion/react";
import { Orb } from "@/shared/ui/Orb";

/** Blurred overlay with the small "A" and shimmering "UPDATING CARD" while a card is regenerated. */
export function CardUpdatingOverlay({ show }: { show: boolean }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.span
          role="status"
          aria-label="Updating card"
          className="absolute inset-0 z-[2] flex flex-col items-center justify-center gap-[14px] rounded-[10px] bg-bg/65 backdrop-blur-[5px]"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <Orb variant="mini" />
          <span className="shimmer-text block font-sans text-[11px] tracking-[3px]">UPDATING CARD</span>
        </motion.span>
      )}
    </AnimatePresence>
  );
}
