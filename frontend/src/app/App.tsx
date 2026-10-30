import { AnimatePresence, motion } from "motion/react";
import { Navigate, useLocation, useRoutes } from "react-router";
import { characterRoutes } from "@/features/characters/routes";
import { storyRoutes } from "@/features/story/routes";
import { useErrors } from "@/shared/errors/errors-context";
import { ErrorBanner } from "@/shared/ui/ErrorBanner";

/** All pages of the app; a new feature adds its routes here. Unknown URLs go to the start page. */
const routes = [...characterRoutes, ...storyRoutes, { path: "*", element: <Navigate to="/" replace /> }];

export default function App() {
  const location = useLocation();
  // `location` is passed in, so a page that is fading out keeps rendering its own URL
  const page = useRoutes(routes, location);
  const { error, dismissError } = useErrors();

  return (
    <div className="relative h-screen min-h-[800px] w-screen min-w-[1280px] overflow-hidden bg-bg text-ink">
      <AnimatePresence initial={false}>
        {/* page transition: opacity + small y */}
        <motion.div
          key={location.pathname}
          className="absolute inset-0"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }}
          exit={{ opacity: 0, transition: { duration: 0.2 } }}
        >
          {page}
        </motion.div>
      </AnimatePresence>

      <ErrorBanner error={error} onDismiss={dismissError} />
    </div>
  );
}
