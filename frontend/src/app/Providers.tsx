import type { ReactNode } from "react";
import { BrowserRouter } from "react-router";
import { CastProvider } from "@/features/characters/store/CastProvider";
import { ErrorsProvider } from "@/shared/errors/ErrorsProvider";

/** Router → shared errors → feature stores. A new feature adds its provider here. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <ErrorsProvider>
        <CastProvider>{children}</CastProvider>
      </ErrorsProvider>
    </BrowserRouter>
  );
}
