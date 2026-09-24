import { Pill, GoldPill } from "@/components/common/Pill";
import { Toast } from "@/components/common/Toast";
import { useCastActions, useCastState } from "@/state/cast-context";
import { CharacterCardView } from "./CharacterCardView";

/** Screen 2 — the cast grid "Dramatis Personae" (README §4.3). */
export function GridScreen() {
  const { cast, cards, toast } = useCastState();
  const { goTo, addBlank, openCharacter, showToast } = useCastActions();

  return (
    <div className="absolute inset-0">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_1300px_800px_at_50%_-10%,#17130d_0%,#0b0a08_65%)]" />

      <div className="relative flex items-end justify-between px-16 pt-11">
        <h1 className="m-0 font-serif text-[44px] font-medium">Dramatis Personae</h1>
        <div className="flex items-center gap-[14px]">
          <Pill onClick={() => goTo("prompt")}>← New premise</Pill>
          <Pill onClick={() => void addBlank()}>+ Add character</Pill>
          <GoldPill onClick={showToast} className="px-5 py-[10px] text-xs tracking-[1px]">
            Continue →
          </GoldPill>
        </div>
      </div>

      <div className="relative mt-[14px] px-16">
        <div className="dotted-rule" />
      </div>

      <div className="scroll-thin relative box-border grid h-[calc(100%-200px)] grid-cols-3 content-start gap-x-8 gap-y-5 overflow-y-auto px-16 pt-7">
        {cast.map((character, i) => (
          <CharacterCardView
            key={character.id}
            character={character}
            card={cards[character.id]}
            number={i + 1}
            onOpen={() => openCharacter(i)}
          />
        ))}
      </div>

      <Toast open={toast}>Cast approved. Next stage — Plot — arrives in Milestone 3.</Toast>
    </div>
  );
}
