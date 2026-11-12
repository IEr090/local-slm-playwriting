// Long requests (generations and approvals): one at a time per key, shown as running (veils, disabled buttons)
// until they end. A failure goes to the error banner; an abort, a reload or a newer play is not a failure.

import { useCallback, useRef, type Dispatch, type RefObject } from "react";
import { isAbort } from "@/shared/api/errors";
import { useUnloading } from "@/shared/hooks/use-unloading";
import type { Action, JobKey } from "./story-reducer";

interface JobsOptions {
  /** Grows when a new cast replaces the play; answers for an older play are dropped. */
  epoch: RefObject<number>;
  dispatch: Dispatch<Action>;
  showError(error: unknown): void;
}

export function useJobs({ epoch, dispatch, showError }: JobsOptions) {
  const controllers = useRef(new Map<JobKey, AbortController>());
  const unloading = useUnloading();

  const isRunning = useCallback((key: JobKey) => controllers.current.has(key), []);

  /** Runs the work unless the key is running; resolves to the answer, or undefined if it failed or was aborted. */
  const runJob = useCallback(
    async <T,>(key: JobKey, work: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> => {
      if (controllers.current.has(key)) return undefined;
      const from = epoch.current;
      const controller = new AbortController();
      controllers.current.set(key, controller);
      dispatch({ type: "jobStarted", key });
      try {
        const result = await work(controller.signal);
        if (controller.signal.aborted || from !== epoch.current) return undefined;
        dispatch({ type: "jobEnded", key });
        return result;
      } catch (error) {
        if (isAbort(error) || controller.signal.aborted || from !== epoch.current || unloading.current) return undefined;
        dispatch({ type: "jobEnded", key, failed: true });
        showError(error);
        return undefined;
      } finally {
        if (controllers.current.get(key) === controller) controllers.current.delete(key);
      }
    },
    [epoch, dispatch, showError, unloading],
  );

  /** A new play: every running request of the old one is aborted. */
  const abortAll = useCallback(() => {
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
  }, []);

  /** The page is being reloaded or closed: the requests it cancels are not failures. */
  const isUnloading = useCallback(() => unloading.current, [unloading]);

  return { runJob, isRunning, abortAll, isUnloading };
}
