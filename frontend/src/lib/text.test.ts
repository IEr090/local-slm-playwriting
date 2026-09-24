import { describe, expect, it } from "vitest";
import { fullName } from "./text";

describe("fullName", () => {
  it("joins name and surname and trims empty parts", () => {
    expect(fullName({ name: "Elena", surname: "Hofbauer" })).toBe("Elena Hofbauer");
    expect(fullName({ name: "Elena", surname: "" })).toBe("Elena");
    expect(fullName({ name: "", surname: "" })).toBe("");
  });
});
