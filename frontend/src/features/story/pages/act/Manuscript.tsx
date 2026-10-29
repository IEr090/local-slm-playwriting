import { actName } from "@/features/story/model/labels";
import { parseSceneText, type ScriptBlock } from "@/features/story/model/script";
import type { SceneText } from "@/features/story/model/types";
import { cn } from "@/shared/lib/utils";
import { TextField } from "@/shared/ui/fields/TextField";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { UpdatingOverlay } from "@/shared/ui/UpdatingOverlay";
import { sceneAnchor } from "./anchors";

interface ManuscriptProps {
  act: number;
  playTitle: string;
  sceneTexts: SceneText[];
  /** Place name of every scene by its number. */
  placeOf(scene: number): string;
  veil: { label: string; line: string } | null;
  approved: boolean;
  /** Lines can be edited by hand (the text is written and not approved yet). */
  editable: boolean;
  onEdit(scene: number, block: number, value: string): void;
  /** Scenes the agent is rewriting right now. */
  rewriting: number[];
  /** "S:I" of the lines the agent has just changed. */
  highlighted: string[];
}

/** The text of the act as a manuscript page: act and title, then every scene with its directions and speeches. */
export function Manuscript({ act, playTitle, sceneTexts, placeOf, veil, approved, editable, onEdit, rewriting, highlighted }: ManuscriptProps) {
  const empty = sceneTexts.length === 0;
  return (
    <div
      className={cn(
        "relative mx-auto box-border max-w-[780px] rounded-[10px] border border-line bg-card px-[72px] pt-14 pb-16 transition-[border-color] duration-400",
        approved && "border-gold/50",
        veil && "min-h-[420px]",
      )}
    >
      {approved && (
        <span className="absolute top-[22px] right-6 rounded-full border border-gold/40 px-[10px] py-[3px] font-sans text-[10px] tracking-[2.5px] text-gold">
          TEXT APPROVED
        </span>
      )}
      <div className="text-center">
        <div className="font-serif text-[22px] text-gold italic">{actName(act)}</div>
        <h2 className="mt-[6px] mb-0 font-serif text-[40px] leading-none font-medium">{playTitle}</h2>
      </div>

      {empty && veil && (
        <div aria-hidden className="mt-10">
          {["30%", "92%", "78%", "18%", "64%", "22%", "84%", "40%"].map((width, i) => (
            <div key={i} className={cn("my-3 h-[10px] rounded-[5px] bg-line-subtle", (i === 3 || i === 5) && "mt-6")} style={{ width }} />
          ))}
        </div>
      )}

      {sceneTexts.map(({ scene_number: scene, text }) => (
        <section key={scene} id={sceneAnchor(act, scene)} className="relative mt-11 animate-fade-up scroll-mt-6 rounded-md">
          <div className="flex items-center gap-[14px]">
            <span className="font-sans text-[10px] tracking-[2.5px] text-gold">SCENE {scene}</span>
            <span className="font-serif text-xl">{placeOf(scene)}</span>
            <span className="dotted-rule flex-1" />
          </div>
          {parseSceneText(text).map((block, i) => (
            <Block
              key={i}
              block={block}
              editable={editable}
              glow={highlighted.includes(`${scene}:${i}`)}
              onEdit={(value) => onEdit(scene, i, value)}
            />
          ))}
          <UpdatingOverlay show={rewriting.includes(scene)} label="REWRITING" className="-inset-2 rounded-md" />
        </section>
      ))}
      {!empty && <div className="mt-[52px] text-center font-serif text-2xl text-gold italic">Curtain.</div>}

      <GenerationVeil show={!!veil} label={veil?.label ?? ""} line={veil?.line ?? ""} className="justify-start pt-[140px]" />
    </div>
  );
}

function Block({ block, editable, glow, onEdit }: { block: ScriptBlock; editable: boolean; glow: boolean; onEdit(value: string): void }) {
  if (block.kind === "direction") {
    return (
      <div className={cn("-mx-2 mt-4 rounded-md px-2 transition-[background-color,box-shadow] duration-600", glow && "bg-gold/10 shadow-[0_0_0_1px_#c9a24b80]")}>
        <TextField
          rows={1}
          label="Stage direction"
          value={block.text}
          readOnly={!editable}
          onChange={onEdit}
          className="font-serif text-lg leading-[1.45] text-muted italic"
        />
      </div>
    );
  }
  return (
    <div className={cn("-mx-2 mt-4 rounded-md px-2 py-[2px] transition-[background-color,box-shadow] duration-600", glow && "bg-gold/10 shadow-[0_0_0_1px_#c9a24b80]")}>
      {block.kind === "speech" && (
        <div className="font-sans text-[11px] tracking-[2.5px] text-gold-soft">
          {block.who}
          {block.paren && <span className="ml-2 font-serif text-base tracking-normal text-muted italic">({block.paren})</span>}
        </div>
      )}
      <TextField
        rows={1}
        label={block.kind === "speech" ? `Line of ${block.who}` : "Text"}
        value={block.text}
        readOnly={!editable}
        onChange={onEdit}
        className="mt-[3px] font-serif text-xl leading-[1.45] text-ink"
      />
    </div>
  );
}
