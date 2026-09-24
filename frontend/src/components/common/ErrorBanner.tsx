import { AnimatePresence, motion } from "motion/react";
import type { ApiErrorInfo } from "@/types/character";
import { Alert, Close } from "./icons";

interface ErrorBannerProps {
  error: ApiErrorInfo | null;
  onDismiss(): void;
}

/**
 * One reusable error banner for generation, card update and chat (README §4.6, Error.dc.html):
 * top centre, 640px, terracotta left border, message + faint technical detail, close ×.
 */
export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  return (
    <AnimatePresence>
      {error && (
        <motion.div
          key={`${error.message}|${error.detail}`}
          role="alert"
          className="absolute top-6 left-1/2 z-10 box-border flex w-[640px] items-center gap-[14px] rounded-[10px] border border-l-[3px] border-line-strong border-l-terracotta bg-card-focus py-3 pr-3 pl-[18px] shadow-[0_12px_40px_#000000b3]"
          style={{ x: "-50%" }}
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
        >
          <Alert className="shrink-0 text-terracotta" />
          <div className="min-w-0 flex-1">
            <div className="font-sans text-[13px] leading-[1.4] text-ink">{error.message}</div>
            <div className="mt-[2px] font-sans text-[11px] tracking-[0.3px] text-faint">{error.detail}</div>
          </div>
          <button
            type="button"
            aria-label="Dismiss"
            onClick={onDismiss}
            className="flex size-7 shrink-0 items-center justify-center rounded-full border-none bg-transparent p-0 text-faint transition-colors hover:bg-white/[0.04] hover:text-ink-2"
          >
            <Close />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
