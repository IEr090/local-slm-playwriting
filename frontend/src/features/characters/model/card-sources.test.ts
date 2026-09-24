import { describe, expect, it } from "vitest";
import type { Character } from "@/features/characters/model/types";
import { cardSources, cardSourcesChanged } from "./card-sources";

const elena = {
  id: "elena",
  name: "Elena",
  surname: "Hofbauer",
  appearance: "Tall",
  dramatic_role: "protagonist",
  occupation_social_role: "Director",
  personality: "Composed",
  goal: "Save the theatre",
  motivation: "Proof",
  fear_weakness: "Cowardice",
} as Character;

describe("cardSourcesChanged", () => {
  const snapshot = cardSources(elena);

  it("is false when nothing on the card sources changed", () => {
    expect(cardSourcesChanged({ ...elena }, snapshot)).toBe(false);
  });

  it("ignores fields that are not on the card (name, appearance…)", () => {
    expect(cardSourcesChanged({ ...elena, name: "Lena", appearance: "Short" }, snapshot)).toBe(false);
  });

  it.each(["dramatic_role", "occupation_social_role", "personality", "goal", "motivation", "fear_weakness"] as const)(
    "is true when %s changed",
    (field) => {
      const value = field === "dramatic_role" ? "mentor" : "changed";
      expect(cardSourcesChanged({ ...elena, [field]: value }, snapshot)).toBe(true);
    },
  );

  it("is false when a change was reverted", () => {
    expect(cardSourcesChanged({ ...elena, goal: "Save the theatre" }, snapshot)).toBe(false);
  });
});
