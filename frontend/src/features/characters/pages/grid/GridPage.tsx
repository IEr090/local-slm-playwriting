import { useNavigate } from "react-router";
import { Pill, GoldPill } from "@/shared/ui/Pill";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";
import { paths as storyPaths } from "@/features/story/paths";
import { CharacterCardView } from "./CharacterCardView";

/** Page "/cast": the cast grid "Dramatis Personae". */
export function GridPage() {
  const { cast, cards, saving, updating } = useCastState();
  const { newPremise, addBlank, openCharacter } = useCastActions();
  const navigate = useNavigate();

  return (
    <div className="absolute inset-0">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_1300px_800px_at_50%_-10%,#17130d_0%,#0b0a08_65%)]" />

      <div className="relative flex items-end justify-between px-16 pt-11">
        <h1 className="m-0 font-serif text-[44px] font-medium">Dramatis Personae</h1>
        <div className="flex items-center gap-[14px]">
          <Pill onClick={newPremise}>← New premise</Pill>
          <Pill onClick={() => void addBlank()}>+ Add character</Pill>
          {cast.length > 0 && (
            <GoldPill onClick={() => navigate(storyPaths.play)} className="px-5 py-[10px] text-xs tracking-[1.5px]">
              WRITE THE PLAY →
            </GoldPill>
          )}
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
            saving={saving.includes(character.id)}
            updating={updating.includes(character.id)}
            onOpen={() => openCharacter(character.id)}
          />
        ))}
      </div>
    </div>
  );
}
