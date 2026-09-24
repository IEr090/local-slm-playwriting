import { motion } from "motion/react";
import type { Flowing } from "./timeline";
import { NAME_DURATION_S, NAME_TRAVEL_PX, WORD_DURATION_S, WORD_TRAVEL_PX } from "./timeline";

const glow = "font-serif italic text-ink [text-shadow:0_0_18px_#c9a24b88]";

/** Premise words: appear at the left edge and float right above the axis into the core. */
export function FlowingWords({ words }: { words: Flowing[] }) {
  return (
    <>
      {words.map((w, i) => (
        // outer: right edge anchored at x=0 (translate -100%), vertically centred on y=336
        <span key={i} className="pointer-events-none absolute top-[336px] left-0 z-[6] -translate-x-full -translate-y-1/2 whitespace-nowrap">
          <motion.span
            className={`inline-block text-2xl ${glow}`}
            initial={{ x: 0, opacity: 0 }}
            animate={{ x: [0, WORD_TRAVEL_PX], opacity: [0, 1, 1, 0] }}
            transition={{
              x: { duration: WORD_DURATION_S, ease: "linear", delay: w.delay },
              opacity: { duration: WORD_DURATION_S, ease: "linear", delay: w.delay, times: [0, 0.08, 0.88, 1] },
            }}
          >
            {w.text}
          </motion.span>
        </span>
      ))}
    </>
  );
}

/** Full names: float out of the core to the right, same style and speed as the words. */
export function FlowingNames({ names }: { names: Flowing[] }) {
  return (
    <>
      {names.map((n) => (
        <span key={n.text} className="pointer-events-none absolute top-[336px] left-[676px] z-[5] -translate-y-1/2 whitespace-nowrap">
          <motion.span
            className={`inline-block text-[26px] ${glow}`}
            initial={{ x: 0, opacity: 0 }}
            animate={{ x: [0, NAME_TRAVEL_PX], opacity: [0, 1, 1, 0] }}
            transition={{
              x: { duration: NAME_DURATION_S, ease: "linear", delay: n.delay },
              opacity: { duration: NAME_DURATION_S, ease: "linear", delay: n.delay, times: [0, 0.08, 0.85, 1] },
            }}
          >
            {n.text}
          </motion.span>
        </span>
      ))}
    </>
  );
}
