import { AnimatePresence, motion } from "motion/react";

/** Small pill message at the bottom centre that fades up; a calm notice, not an error. */
export function Toast({ open, children }: { open: boolean; children: React.ReactNode }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="status"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }}
          exit={{ opacity: 0, transition: { duration: 0.3 } }}
          className="pointer-events-none absolute inset-x-0 bottom-7 flex justify-center"
        >
          <div className="rounded-full border border-gold/[0.533] bg-bubble px-[22px] py-3 font-sans text-xs tracking-[1px] text-ink-3">
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
