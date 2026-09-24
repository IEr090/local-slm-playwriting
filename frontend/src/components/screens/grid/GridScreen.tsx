import { Pill } from "@/components/common/Pill";
import { useCastActions, useCastState } from "@/state/cast-context";

/** Placeholder until block 3 (cast grid). */
export function GridScreen() {
  const { cast } = useCastState();
  const { goTo, openCharacter } = useCastActions();
  return (
    <div className="absolute inset-0 px-16 pt-11">
      <div className="flex items-end justify-between">
        <h1 className="m-0 font-serif text-[44px] font-medium">Dramatis Personae</h1>
        <Pill onClick={() => goTo("prompt")}>← New premise</Pill>
      </div>
      <ul className="mt-8 space-y-2 font-serif text-2xl">
        {cast.map((c, i) => (
          <li key={c.id}>
            <button type="button" onClick={() => openCharacter(i)} className="hover:text-gold">
              {c.name} {c.surname}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
