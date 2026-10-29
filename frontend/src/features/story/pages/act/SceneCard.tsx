import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { Notice } from "@/shared/ui/Notice";
import { UpdatingOverlay } from "@/shared/ui/UpdatingOverlay";

interface SceneCardProps {
  number: number;
  place: string;
  placeNotes: string;
  who: string[];
  whatHappens: string;
  /** Move / cut / edit buttons, or a small note on the right. */
  tools?: ReactNode;
  updating?: boolean;
  highlighted?: boolean;
  /** Veil while the plan of this scene is being written. */
  planning?: boolean;
  dimmed?: boolean;
  notice?: string;
  /** The scene cannot be edited yet: a click explains why. */
  onLockedClick?(): void;
}

/** A scene in short: italic number, place in serif with its note, who is on stage, what happens. */
export function SceneCard({
  number,
  place,
  placeNotes,
  who,
  whatHappens,
  tools,
  updating,
  highlighted,
  planning,
  dimmed,
  notice,
  onLockedClick,
}: SceneCardProps) {
  return (
    <article
      onClick={onLockedClick}
      className={cn(
        "relative grid animate-fade-up grid-cols-[44px_minmax(0,1fr)_auto] gap-x-4 rounded-[10px] border border-line bg-card py-[18px] pr-5 pl-4",
        "transition-[border-color,background-color,box-shadow] duration-200 hover:border-line-hover",
        highlighted && "border-gold shadow-[0_0_0_1px_#c9a24b,0_0_24px_#c9a24b44] hover:border-gold",
        planning && "min-h-[150px]",
      )}
    >
      <div aria-hidden className="pt-[2px] text-center font-serif text-[32px] leading-none text-gold italic">
        {number}
      </div>
      <div className={cn("min-w-0 transition-opacity duration-500", dimmed && "opacity-55")}>
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-serif text-[22px] leading-[1.1] font-medium">{place || "No place yet"}</span>
          {placeNotes && <span className="font-sans text-xs text-muted italic">{placeNotes}</span>}
        </div>
        {who.length > 0 && (
          <div className="mt-[9px] mb-2 flex flex-wrap gap-[5px]">
            {who.map((name) => (
              <span key={name} className="rounded-full border border-gold/40 bg-gold/[0.078] px-[9px] py-[2px] font-sans text-[11px] text-gold-soft">
                {name}
              </span>
            ))}
          </div>
        )}
        <div className={cn("font-sans text-[13px] leading-[1.55] text-ink-3", who.length === 0 && "mt-2")}>
          {whatHappens || <span className="text-placeholder">What happens is not written yet.</span>}
        </div>
        {notice && <Notice className="mt-3">{notice}</Notice>}
      </div>
      <div className="flex items-start gap-[6px]">{tools}</div>
      <UpdatingOverlay show={!!updating && !planning} className="rounded-[10px]" />
      <GenerationVeil show={!!planning} label={`PLANNING SCENE ${number}`} line="Setting the place, who is on stage and what happens…" />
    </article>
  );
}

/** Placeholder card while the agent adds a scene. */
export function AddingSceneCard({ number }: { number: number }) {
  return (
    <article aria-label="Adding a scene" className="relative grid min-h-[120px] grid-cols-[44px_minmax(0,1fr)] gap-x-4 rounded-[10px] border border-line bg-card py-[18px] pr-5 pl-4">
      <div aria-hidden className="text-center font-serif text-[32px] leading-none text-gold italic">
        {number}
      </div>
      <div>
        {["40%", "85%", "65%"].map((width) => (
          <div key={width} className="my-[5px] h-[9px] rounded-[5px] bg-line-subtle" style={{ width }} />
        ))}
      </div>
      <UpdatingOverlay show label="ADDING A SCENE" className="rounded-[10px]" />
    </article>
  );
}
