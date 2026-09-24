import { Orb } from "@/shared/ui/Orb";
import { ArrowRight } from "@/shared/ui/icons";
import { GoldPill } from "@/shared/ui/Pill";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";

/** Screen 1 — "Describe your idea — we will summon the cast" (README §4.1). */
export function PromptScreen() {
  const { premise } = useCastState();
  const { setPremise, startGeneration, addBlank } = useCastActions();

  return (
    <div className="absolute inset-0 bg-[radial-gradient(ellipse_900px_700px_at_50%_38%,#17130d_0%,#0b0a08_70%)]">
      {/* vignette */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_1400px_900px_at_50%_0%,transparent_40%,#000000_100%)] opacity-55" />

      {/* logo, only on this screen */}
      <div className="absolute top-7 left-12">
        <Orb />
      </div>

      {/* decorative rings, top right */}
      <svg
        aria-hidden
        width="360"
        height="360"
        viewBox="0 0 360 360"
        fill="none"
        className="absolute -top-[90px] -right-[90px] opacity-50"
      >
        <circle cx="180" cy="180" r="179" stroke="#4a4229" strokeWidth="1" />
        <circle cx="180" cy="180" r="130" stroke="#4a4229" strokeWidth="1" strokeDasharray="2 6" />
        <circle cx="180" cy="180" r="80" stroke="#c9a24b" strokeWidth="1" opacity="0.5" />
      </svg>

      <div className="absolute top-[170px] left-1/2 flex w-[760px] -translate-x-1/2 flex-col items-center gap-7">
        <div className="flex flex-col items-center gap-[10px]">
          <div className="font-serif text-[15px] tracking-[6px] text-gold">A NEW STORY BEGINS</div>
          <h1 className="m-0 text-center font-serif text-[52px] leading-[1.15] font-medium">
            Describe your idea — we will summon the cast
          </h1>
          <p className="m-0 max-w-[520px] text-center font-sans text-sm leading-[1.6] text-muted-2">
            Tell us about your play: its premise, place and mood. Anton will propose a cast of characters, ready for you
            to shape.
          </p>
        </div>

        <form
          className="w-full rounded-[14px] border border-line-strong bg-card/80 p-1"
          onSubmit={(e) => {
            e.preventDefault();
            void startGeneration();
          }}
        >
          <label htmlFor="premise" className="sr-only">
            Premise
          </label>
          <textarea
            id="premise"
            rows={4}
            value={premise}
            onChange={(e) => setPremise(e.target.value)}
            placeholder="An independent theatre in Vienna. Three former classmates meet again after twenty years…"
            className="block w-full resize-none rounded-[10px] border-none bg-transparent px-[22px] py-5 font-sans text-base leading-[1.6] text-ink placeholder:text-faint focus:outline-none"
          />
          <div className="flex items-center justify-between pt-[6px] pr-[14px] pb-[10px] pl-[18px]">
            <div className="font-sans text-xs text-faint">Add genre, tone or number of characters if you like</div>
            <GoldPill type="submit">
              GENERATE CHARACTERS
              <ArrowRight />
            </GoldPill>
          </div>
        </form>

        <div className="w-[420px] border-t border-dotted border-line-hover" />
        <button
          type="button"
          onClick={() => void addBlank()}
          className="border-none bg-transparent px-3 py-2 font-sans text-[11px] tracking-[2px] text-muted-2"
        >
          OR START WITH A BLANK CHARACTER
        </button>
      </div>
    </div>
  );
}
