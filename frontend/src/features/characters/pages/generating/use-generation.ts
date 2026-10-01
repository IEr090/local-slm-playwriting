import { useEffect, useRef, useState } from "react";
import { measureText } from "./measure";
import {
  planNames,
  planWords,
  premiseWords,
  resultSchedule,
  STATUS_CYCLE_MS,
  STATUS_RISES,
  statusAt,
  type Flowing,
} from "./timeline";

export const WORD_FONT = 'italic 400 24px "Cormorant Garamond"';
export const NAME_FONT = 'italic 400 26px "Cormorant Garamond"';

export type Phase = "loading" | "words" | "burst" | "names";

interface Options {
  premise: string;
  /** The api has answered. */
  ready: boolean;
  /** Full names of the generated cast (used once `ready`). */
  names: string[];
  /** The last name has flowed out: open the grid. */
  onDone(): void;
}

/**
 * Drives the generating screen: phase 1 premise words, phase 2 waiting statuses,
 * phase 3 burst + names. All timers are cleared on unmount (e.g. CANCEL).
 */
export function useGeneration({ premise, ready, names, onDone }: Options) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [words, setWords] = useState<Flowing[]>([]);
  const [flyingNames, setFlyingNames] = useState<Flowing[]>([]);
  const [status, setStatus] = useState(0);

  const startedAt = useRef(0);
  const absorbedMs = useRef(0);
  const readyAt = useRef<number | null>(null);
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  });

  // Phase 1: measure the words once the italic face is loaded, then let them flow.
  const [initialPremise] = useState(premise);
  useEffect(() => {
    let alive = true;
    const fonts = Promise.all([document.fonts.load(WORD_FONT), document.fonts.load(NAME_FONT)]).catch(() => []);
    void fonts.then(() => {
      if (!alive) return;
      const list = premiseWords(initialPremise);
      const plan = planWords(list, list.map((w) => measureText(w, WORD_FONT)));
      startedAt.current = performance.now();
      absorbedMs.current = plan.absorbedMs;
      setWords(plan.words);
      setPhase("words");
    });
    return () => {
      alive = false;
    };
  }, [initialPremise]);

  // Phase 2: status lines while the words flow and while we wait for the model.
  useEffect(() => {
    if (phase !== "words") return;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      const elapsed = performance.now() - startedAt.current;
      setStatus(statusAt(elapsed, absorbedMs.current));
      const step = absorbedMs.current / 4;
      const next = elapsed < 3 * step ? step - (elapsed % step) : STATUS_CYCLE_MS - ((elapsed - 3 * step) % STATUS_CYCLE_MS);
      timer = setTimeout(tick, next + 5);
    };
    tick();
    return () => clearTimeout(timer);
  }, [phase]);

  // Phase 3: once the api has answered (and the words are done), burst → names → grid.
  const namesKey = names.join("|");
  const started = phase !== "loading";
  useEffect(() => {
    if (!ready || !started) return;
    readyAt.current ??= performance.now() - startedAt.current;
    const list = namesKey ? namesKey.split("|") : [];
    const planned = planNames(list, list.map((n) => measureText(n, NAME_FONT)));
    const { burstAt, namesAt, gridAt } = resultSchedule(absorbedMs.current, readyAt.current, planned);
    const now = performance.now() - startedAt.current;
    const timers = [
      setTimeout(() => setPhase("burst"), Math.max(0, burstAt - now)),
      setTimeout(() => {
        setFlyingNames(planned);
        setStatus(STATUS_RISES);
        setPhase("names");
      }, Math.max(0, namesAt - now)),
      setTimeout(() => onDoneRef.current(), Math.max(0, gridAt - now)),
    ];
    return () => timers.forEach(clearTimeout);
  }, [ready, started, namesKey]);

  return { phase, words, names: flyingNames, status };
}
