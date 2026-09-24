import { Pill } from "@/components/common/Pill";
import { useCastActions } from "@/state/cast-context";

/** Placeholder until block 7 (generation animation): waits for the api, CANCEL returns to the prompt. */
export function GeneratingScreen() {
  const { cancelGeneration } = useCastActions();
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-[14px]">
      <div className="font-serif text-[15px] tracking-[6px] text-gold">SUMMONING THE CAST</div>
      <div className="font-serif text-[30px] italic">Reading your premise…</div>
      <div className="absolute bottom-8 flex w-full justify-center">
        <Pill onClick={cancelGeneration} className="text-[11px] tracking-[2px]">
          CANCEL
        </Pill>
      </div>
    </div>
  );
}
