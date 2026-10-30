import { describe, expect, it } from "vitest";
import { act, scene, story } from "./fixtures";
import { actStage, allScenesApproved, canOpenAct, currentAct, isOpenAct, nextSceneToPlan } from "./progress";

const idle = { staging: false, writing: false, recording: false };

describe("currentAct", () => {
  it("is none before the acts are approved", () => {
    expect(currentAct(story())).toBeNull();
  });

  it("is the first act whose text is not approved", () => {
    const s = story({ acts_approved: true, acts: [act(1, { status: "text_approved" }), act(2), act(3)] });
    expect(currentAct(s)?.number).toBe(2);
    expect(currentAct(story({ acts_approved: true, acts: [act(1, { status: "text_approved" })] }))).toBeNull();
  });
});

describe("opening an act", () => {
  const s = story({ acts_approved: true, acts: [act(1, { status: "text_approved", scenes: [scene(1)] }), act(2), act(3)] });

  it("needs the text of the act before to be approved", () => {
    expect(isOpenAct(s, 1)).toBe(true);
    expect(isOpenAct(s, 2)).toBe(true);
    expect(isOpenAct(s, 3)).toBe(false);
    expect(isOpenAct(story(), 1)).toBe(false);
  });

  it("needs the structure to be staged", () => {
    expect(canOpenAct(s, s.acts[0])).toBe(true);
    expect(canOpenAct(s, s.acts[1])).toBe(false);
  });
});

describe("actStage", () => {
  it("stages a draft act without scenes, then shows its structure", () => {
    expect(actStage(act(1), idle, false)).toBe("staging");
    expect(actStage(act(1, { scenes: [scene(1)] }), idle, false)).toBe("structure");
    expect(actStage(act(1, { scenes: [scene(1)] }), { ...idle, staging: true }, false)).toBe("staging");
  });

  it("shows the plans until the text is written", () => {
    expect(actStage(act(1, { status: "structure_approved", scenes: [scene(1)] }), idle, false)).toBe("plans");
    expect(actStage(act(1, { status: "scenes_approved", scenes: [scene(1)] }), idle, false)).toBe("plans");
  });

  it("shows the text once written, the plans again on EDIT SCENES", () => {
    const written = act(1, { status: "scenes_approved", scenes: [scene(1)], scene_texts: [{ scene_number: 1, text: "(Night.)" }] });
    expect(actStage(written, idle, false)).toBe("text");
    expect(actStage(written, idle, true)).toBe("plans");
    expect(actStage({ ...written, status: "text_approved" }, idle, false)).toBe("done");
    // a reopened scene: the text can no longer be approved
    expect(actStage({ ...written, status: "structure_approved" }, idle, false)).toBe("plans");
  });

  it("puts writing and recording above everything else", () => {
    expect(actStage(act(1), { ...idle, writing: true }, false)).toBe("writing");
    expect(actStage(act(1), { ...idle, writing: true, recording: true }, false)).toBe("recording");
  });
});

describe("nextSceneToPlan", () => {
  it("plans nothing while the structure is a draft", () => {
    expect(nextSceneToPlan(act(1, { scenes: [scene(1)] }))).toBeNull();
  });

  it("plans the first scene, then the next one once the one before is approved", () => {
    const approved = { status: "structure_approved" as const };
    expect(nextSceneToPlan(act(1, { ...approved, scenes: [scene(1), scene(2)] }))).toBe(1);
    expect(nextSceneToPlan(act(1, { ...approved, scenes: [scene(1, { planned: true }), scene(2)] }))).toBeNull();
    expect(
      nextSceneToPlan(act(1, { ...approved, scenes: [scene(1, { planned: true, status: "approved" }), scene(2)] })),
    ).toBe(2);
    expect(nextSceneToPlan(act(1, { ...approved, scenes: [scene(1, { planned: true, status: "approved" })] }))).toBeNull();
  });
});

it("knows when every scene is approved", () => {
  expect(allScenesApproved(act(1))).toBe(false);
  expect(allScenesApproved(act(1, { scenes: [scene(1, { status: "approved" }), scene(2)] }))).toBe(false);
  expect(allScenesApproved(act(1, { scenes: [scene(1, { status: "approved" })] }))).toBe(true);
});
