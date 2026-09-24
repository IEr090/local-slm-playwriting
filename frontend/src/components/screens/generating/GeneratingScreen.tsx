import { motion } from "motion/react";
import { Pill } from "@/components/common/Pill";
import { fullName } from "@/lib/text";
import { useCastActions, useCastState } from "@/state/cast-context";
import { FlowingNames, FlowingWords } from "./FlowingText";
import { Axis, Fog, Orrery, Stars } from "./Scenery";
import { STATUS } from "./timeline";
import { useGeneration } from "./use-generation";

/** Screen 1b — the generation animation (README §4.2). A fixed 1280×800 stage, centred. */
export function GeneratingScreen() {
  const { premise, generationReady, cast } = useCastState();
  const { cancelGeneration, finishGeneration } = useCastActions();
  const { phase, words, names, status } = useGeneration({
    premise,
    ready: generationReady,
    names: generationReady ? cast.map(fullName) : [],
    onDone: finishGeneration,
  });

  return (
    <div className="absolute inset-0 overflow-hidden">
      <div className="absolute top-1/2 left-1/2 h-[800px] w-[1280px] -translate-x-1/2 -translate-y-1/2">
        <Fog />
        <Stars />
        <Axis />
        <Orrery />

        <div className="absolute top-[590px] left-0 flex w-[1280px] flex-col items-center gap-[14px]">
          <div className="font-serif text-[15px] tracking-[6px] text-gold">SUMMONING THE CAST</div>
          {/* the new status replaces the old one and fades up (as .fade-up in the prototype) */}
          <motion.div
            key={status}
            aria-live="polite"
            className="font-serif text-[30px] text-ink italic"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            {STATUS[status]}
          </motion.div>
        </div>

        {(phase === "burst" || phase === "names") && (
          <motion.div
            aria-hidden
            className="pointer-events-none absolute top-[360px] left-[640px] size-[120px] rounded-full border border-gold"
            style={{ x: "-50%", y: "-50%" }}
            initial={{ scale: 0.6, opacity: 0.9 }}
            animate={{ scale: 2.4, opacity: 0 }}
            transition={{ duration: 1.4, ease: "easeOut" }}
          />
        )}

        <FlowingWords words={words} />
        <FlowingNames names={names} />

        <div className="absolute bottom-8 left-0 flex w-[1280px] justify-center">
          <Pill onClick={cancelGeneration} className="text-[11px] tracking-[2px]">
            CANCEL
          </Pill>
        </div>
      </div>
    </div>
  );
}
