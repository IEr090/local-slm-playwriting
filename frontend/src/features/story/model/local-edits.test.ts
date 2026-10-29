import { describe, expect, it } from "vitest";
import { act, outline, scene, story } from "./fixtures";
import { withLocalEdits } from "./local-edits";

describe("withLocalEdits", () => {
  const server = story({ outline_changed: true, acts: [act(1, { summary: "server", summary_changed: true }), act(2)] });

  it("takes the backend's story when nothing is edited", () => {
    expect(withLocalEdits(server, story(), [])).toBe(server);
    expect(withLocalEdits(server, null, ["outline"])).toBe(server);
  });

  it("keeps the edited parts from the local copy and the flags from the backend", () => {
    const local = story({
      outline: { ...outline, title: "Typed" },
      acts: [
        act(1, { summary: "typed", scenes: [scene(1)], scene_texts: [{ scene_number: 1, text: "X: y" }] }),
        act(2),
      ],
    });
    const merged = withLocalEdits(server, local, ["outline", "act:1", "scenes:1", "text:1", "act:7"]);
    expect(merged.outline?.title).toBe("Typed");
    expect(merged.outline_changed).toBe(true);
    expect(merged.acts[0]).toMatchObject({ summary: "typed", summary_changed: true, scenes: [scene(1)] });
    expect(merged.acts[0].scene_texts).toEqual([{ scene_number: 1, text: "X: y" }]);
    expect(merged.acts[1]).toBe(server.acts[1]);
  });

  it("keeps one edited scene plan and takes the other scenes from the backend", () => {
    const fromServer = story({
      acts: [act(1, { status: "structure_approved", scenes: [scene(1, { status: "approved" }), scene(2, { planned: true, what_happens: "planned" })] })],
    });
    const local = story({ acts: [act(1, { scenes: [scene(1, { what_happens: "typed" }), scene(2)] })] });
    const merged = withLocalEdits(fromServer, local, ["scene:1:1"]);
    expect(merged.acts[0].scenes[0]).toMatchObject({ what_happens: "typed", status: "approved" });
    expect(merged.acts[0].scenes[1]).toMatchObject({ what_happens: "planned", planned: true });
  });
});
