import { describe, expect, it } from "vitest";
import { actName, firstClause, genreLabel, numberWord, roman } from "./labels";

describe("story labels", () => {
  it("names acts in words and roman numerals", () => {
    expect(numberWord(1)).toBe("One");
    expect(numberWord(5)).toBe("Five");
    expect(numberWord(12)).toBe("12");
    expect(roman(4)).toBe("IV");
    expect(actName(2)).toBe("Act Two");
  });

  it("capitalises a genre", () => {
    expect(genreLabel("tragicomedy")).toBe("Tragicomedy");
  });

  it("keeps the first clause of a text", () => {
    expect(firstClause("Chamber and cold, with irony; the storm")).toBe("Chamber and cold");
    expect(firstClause("")).toBe("");
  });
});
