import { motion } from "motion/react";
import { useState } from "react";
import { Navigate } from "react-router";
import { paths } from "@/features/characters/paths";
import { Pill } from "@/shared/ui/Pill";
import { fullName } from "@/features/characters/model/text";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";
import { FlowingNames, FlowingWords } from "./FlowingText";
import { Axis, Fog, Orrery, SideNodes, Stars } from "./Scenery";
import { STATUS } from "./timeline";
import { useGeneration } from "./use-generation";

/** Page "/generating": the generation animation. */
export function GeneratingPage() {
  const { generation } = useCastState();
  // /generating without a running generation (e.g. after a reload) → prompt
  const [orphan] = useState(generation === "idle");
  if (orphan) return <Navigate to={paths.prompt} replace />;
  return <GenerationStage />;
}

/** Background layers over the whole window; the animation on a fixed 1280×800 stage, centred. */
function GenerationStage() {
  const { premise, generation, cast } = useCastState();
  const { cancelGeneration, finishGeneration } = useCastActions();
  const ready = generation === "ready";
  const { phase, words, names, status } = useGeneration({
    premise,
    ready,
    names: ready ? cast.map(fullName) : [],
    onDone: finishGeneration,
  });

  return (
    <div className="absolute inset-0 overflow-hidden">
      <Fog />
      <Stars />
      <Axis />
      <div className="absolute top-1/2 left-1/2 h-[800px] w-[1280px] -translate-x-1/2 -translate-y-1/2">
        <SideNodes />
        <Orrery />

        <div className="absolute top-[590px] left-0 flex w-[1280px] flex-col items-center gap-[14px]">
          <div className="font-serif text-[15px] tracking-[6px] text-gold">SUMMONING THE CAST</div>
          {/* the new status replaces the old one and fades up */}
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
