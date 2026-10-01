import { useCallback, useMemo, useState, type ReactNode } from "react";
import { toErrorInfo, type ApiErrorInfo } from "@/shared/api/errors";
import { ErrorsContext, type Errors } from "./errors-context";

/** Holds the one error shown by the ErrorBanner. */
export function ErrorsProvider({ children }: { children: ReactNode }) {
  const [error, setError] = useState<ApiErrorInfo | null>(null);
  const showError = useCallback((e: unknown) => setError(toErrorInfo(e)), []);
  const dismissError = useCallback(() => setError(null), []);
  const value = useMemo<Errors>(() => ({ error, showError, dismissError }), [error, showError, dismissError]);
  return <ErrorsContext.Provider value={value}>{children}</ErrorsContext.Provider>;
}
