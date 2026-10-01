import { describe, expect, it } from "vitest";
import {
  planNames,
  planWords,
  premiseWords,
  resultSchedule,
  statusAt,
  WORD_FIRST_DELAY_S,
  WORD_SPEED,
} from "./timeline";

describe("premiseWords", () => {
  it("takes the first 18 words", () => {
    const text = Array.from({ length: 30 }, (_, i) => `w${i}`).join("  ");
    expect(premiseWords(text)).toHaveLength(18);
    expect(premiseWords("  An   independent theatre ")).toEqual(["An", "independent", "theatre"]);
  });
});

describe("planWords", () => {
  it("delays each word by the previous width + gap at constant speed", () => {
    const { words, absorbedMs } = planWords(["An", "independent"], [20, 100]);
    expect(words[0].delay).toBe(WORD_FIRST_DELAY_S);
    expect(words[1].delay).toBeCloseTo(WORD_FIRST_DELAY_S + (20 + 22) / WORD_SPEED);
    expect(absorbedMs).toBeCloseTo((words[1].delay + 2.9) * 1000);
  });

  it("never lets two words overlap on the axis", () => {
    const widths = [30, 120, 45, 80];
    const { words } = planWords(["a", "b", "c", "d"], widths);
    for (let i = 1; i < words.length; i++) {
      // distance travelled by the previous word when this one starts ≥ previous width + gap
      expect((words[i].delay - words[i - 1].delay) * WORD_SPEED).toBeGreaterThanOrEqual(widths[i - 1] + 22 - 1e-9);
    }
  });
});

describe("planNames", () => {
  it("starts at 0 and spaces names by width + 80px at 200px/s", () => {
    const names = planNames(["Elena Hofbauer", "Mark Seidl"], [160, 120]);
    expect(names.map((n) => n.delay)).toEqual([0, (160 + 80) / 200]);
  });
});

describe("resultSchedule", () => {
  const names = [{ text: "A", delay: 0 }, { text: "B", delay: 1.2 }];

  it("waits for the words when the api answers early", () => {
    expect(resultSchedule(5000, 1000, names)).toEqual({ burstAt: 4800, namesAt: 6200, gridAt: 6200 + 4400 });
  });

  it("starts right away when the api answers after the words", () => {
    expect(resultSchedule(5000, 9000, names).burstAt).toBe(9000);
  });
});

describe("statusAt", () => {
  it("steps through the four waiting lines, then cycles 1–3", () => {
    const absorbed = 8000; // step = 2000
    expect([0, 1999, 2000, 4000, 6000].map((t) => statusAt(t, absorbed))).toEqual([0, 0, 1, 2, 3]);
    expect([9000, 12000, 15000, 18000].map((t) => statusAt(t, absorbed))).toEqual([1, 2, 3, 1]);
  });
});
