import { Pill } from "@/components/common/Pill";
import { useCastActions, useCastState } from "@/state/cast-context";

/** Placeholder until block 4 (character detail). */
export function DetailScreen() {
  const { cast, selectedIndex } = useCastState();
  const { goTo } = useCastActions();
  const character = cast[selectedIndex];
  return (
    <div className="absolute inset-0 px-12 pt-9">
      <div className="flex items-end justify-between">
        <h1 className="m-0 font-serif text-[46px] font-medium">
          {character ? `${character.name} ${character.surname}` : "Unnamed character"}
        </h1>
        <Pill onClick={() => goTo("grid")}>ALL CHARACTERS</Pill>
      </div>
    </div>
  );
}
