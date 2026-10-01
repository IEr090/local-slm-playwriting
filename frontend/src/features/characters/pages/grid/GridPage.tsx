import { useEffect, useRef, useState } from "react";
import { Pill, GoldPill } from "@/shared/ui/Pill";
import { Toast } from "@/shared/ui/Toast";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";
import { CharacterCardView } from "./CharacterCardView";

/** "Continue" toast: shown for 3 s. */
const TOAST_MS = 3000;

/** Page "/cast": the cast grid "Dramatis Personae". */
export function GridPage() {
  const { cast, cards, updating } = useCastState();
  const { newPremise, addBlank, openCharacter } = useCastActions();
  const [toast, showToast] = useTimedFlag(TOAST_MS);

  return (
    <div className="absolute inset-0">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_1300px_800px_at_50%_-10%,#17130d_0%,#0b0a08_65%)]" />

      <div className="relative flex items-end justify-between px-16 pt-11">
        <h1 className="m-0 font-serif text-[44px] font-medium">Dramatis Personae</h1>
        <div className="flex items-center gap-[14px]">
          <Pill onClick={newPremise}>← New premise</Pill>
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
            updating={updating.includes(character.id)}
            onOpen={() => openCharacter(character.id)}
          />
        ))}
      </div>

      <Toast open={toast}>Cast approved. Next stage, Plot, arrives in Milestone 3.</Toast>
    </div>
  );
}

/** A flag that turns itself off after `ms`; calling `show` again restarts the timer. */
function useTimedFlag(ms: number): [boolean, () => void] {
  const [on, setOn] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const show = () => {
    clearTimeout(timer.current);
    setOn(true);
    timer.current = setTimeout(() => setOn(false), ms);
  };
  return [on, show];
}
