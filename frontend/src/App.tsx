import { AnimatePresence, motion } from "motion/react";
import { DetailScreen } from "@/components/screens/detail/DetailScreen";
import { GeneratingScreen } from "@/components/screens/generating/GeneratingScreen";
import { GridScreen } from "@/components/screens/grid/GridScreen";
import { PromptScreen } from "@/components/screens/prompt/PromptScreen";
import { ErrorBanner } from "@/components/common/ErrorBanner";
import { useCastActions, useCastState } from "@/state/cast-context";
import type { Screen } from "@/state/cast-reducer";

const SCREENS: Record<Screen, () => React.JSX.Element | null> = {
  prompt: PromptScreen,
  generating: GeneratingScreen,
  grid: GridScreen,
  detail: DetailScreen,
};

export default function App() {
  const { screen, error } = useCastState();
  const { dismissError } = useCastActions();
  const Current = SCREENS[screen];

  return (
    <div className="relative h-screen min-h-[800px] w-screen min-w-[1280px] overflow-hidden bg-bg text-ink">
      <AnimatePresence initial={false}>
        {/* screen transition: opacity + small y, as .screen in the prototype */}
        <motion.div
          key={screen}
          className="absolute inset-0"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }}
          exit={{ opacity: 0, transition: { duration: 0.2 } }}
        >
          <Current />
        </motion.div>
      </AnimatePresence>

      <ErrorBanner error={error} onDismiss={dismissError} />
    </div>
  );
}
