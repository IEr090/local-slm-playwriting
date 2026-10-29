import type { ReactNode } from "react";
import { BrowserRouter } from "react-router";
import { CastProvider } from "@/features/characters/store/CastProvider";
import { StoryProvider } from "@/features/story/store/StoryProvider";
import { ErrorsProvider } from "@/shared/errors/ErrorsProvider";

/** Router → shared errors → feature stores. The story store reads the cast store, so it sits inside it. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <ErrorsProvider>
        <CastProvider>
          <StoryProvider>{children}</StoryProvider>
        </CastProvider>
      </ErrorsProvider>
    </BrowserRouter>
  );
}
