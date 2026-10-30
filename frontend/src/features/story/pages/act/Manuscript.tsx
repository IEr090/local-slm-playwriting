import { actName } from "@/features/story/model/labels";
import { insertBlock, parseSceneText, removeBlock, updateBlock, type ScriptBlock } from "@/features/story/model/script";
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
  /** Lines can be edited, added and cut by hand (the text is written and not approved yet). */
  editable: boolean;
  /** The whole new text of a scene after a hand edit. */
  onEdit(scene: number, text: string): void;
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

      {sceneTexts.map(({ scene_number: scene, text }) => {
        const blocks = parseSceneText(text);
        const lastSpeaker = [...blocks].reverse().find((b) => b.kind === "speech");
        return (
          <section key={scene} id={sceneAnchor(act, scene)} className="relative mt-11 animate-fade-up scroll-mt-6 rounded-md">
            <div className="flex items-center gap-[14px]">
              <span className="font-sans text-[10px] tracking-[2.5px] text-gold">SCENE {scene}</span>
              <span className="font-serif text-xl">{placeOf(scene)}</span>
              <span className="dotted-rule flex-1" />
            </div>
            {blocks.map((block, i) => (
              <Block
                key={i}
                block={block}
                editable={editable}
                glow={highlighted.includes(`${scene}:${i}`)}
                onChange={(patch) => onEdit(scene, updateBlock(text, i, patch))}
                onAddSpeech={() =>
                  onEdit(scene, insertBlock(text, i, { kind: "speech", who: block.kind === "speech" ? block.who : speakerOf(lastSpeaker), paren: "", text: "" }))
                }
                onAddDirection={() => onEdit(scene, insertBlock(text, i, { kind: "direction", text: "" }))}
                onCut={() => onEdit(scene, removeBlock(text, i))}
              />
            ))}
            <UpdatingOverlay show={rewriting.includes(scene)} label="REWRITING" className="-inset-2 rounded-md" />
          </section>
        );
      })}
      {!empty && <div className="mt-[52px] text-center font-serif text-2xl text-gold italic">Curtain.</div>}

      <GenerationVeil show={!!veil} label={veil?.label ?? ""} line={veil?.line ?? ""} className="justify-start pt-[140px]" />
    </div>
  );
}

const speakerOf = (block: ScriptBlock | undefined) => (block?.kind === "speech" ? block.who : "NAME");

interface BlockProps {
  block: ScriptBlock;
  editable: boolean;
  glow: boolean;
  onChange(patch: Partial<{ text: string; who: string; paren: string }>): void;
  onAddSpeech(): void;
  onAddDirection(): void;
  onCut(): void;
}

function Block({ block, editable, glow, onChange, onAddSpeech, onAddDirection, onCut }: BlockProps) {
  return (
    <div
      className={cn(
        "group relative -mx-2 mt-4 rounded-md px-2 py-[2px] transition-[background-color,box-shadow] duration-600",
        glow && "bg-gold/10 shadow-[0_0_0_1px_#c9a24b80]",
      )}
    >
      {block.kind === "speech" &&
        (editable ? (
          <div className="flex items-baseline gap-2">
            <input
              aria-label="Speaker"
              value={block.who}
              // letter-spaced capitals are wider than `size` counts
              style={{ width: `calc(${Math.max(block.who.length, 4) + 1}ch + ${Math.max(block.who.length, 4) * 2.5}px)` }}
              onChange={(e) => onChange({ who: e.target.value.toUpperCase() })}
              className="border-none bg-transparent p-0 font-sans text-[11px] tracking-[2.5px] text-gold-soft focus:outline-none"
            />
            {/* the note in parentheses; an empty one shows only while the line is hovered or edited */}
            <span
              className={cn(
                "flex items-baseline font-serif text-base text-muted italic transition-opacity duration-150",
                !block.paren && "opacity-0 group-focus-within:opacity-100 group-hover:opacity-100",
              )}
            >
              (
              <input
                aria-label="Acting note"
                value={block.paren}
                placeholder="note"
                style={{ width: `${Math.max(block.paren.length, 4) + 1}ch` }}
                onChange={(e) => onChange({ paren: e.target.value })}
                className="border-none bg-transparent p-0 font-serif text-base text-muted italic placeholder:text-placeholder focus:outline-none"
              />
              )
            </span>
          </div>
        ) : (
          <div className="font-sans text-[11px] tracking-[2.5px] text-gold-soft">
            {block.who}
            {block.paren && <span className="ml-2 font-serif text-base tracking-normal text-muted italic">({block.paren})</span>}
          </div>
        ))}
      <TextField
        rows={1}
        label={block.kind === "speech" ? `Line of ${block.who}` : block.kind === "direction" ? "Stage direction" : "Text"}
        placeholder={block.kind === "direction" ? "Stage direction" : "Line"}
        value={block.text}
        readOnly={!editable}
        onChange={(text) => onChange({ text })}
        className={
          block.kind === "direction"
            ? "font-serif text-lg leading-[1.45] text-muted italic"
            : "mt-[3px] font-serif text-xl leading-[1.45] text-ink"
        }
      />
      {editable && (
        <div className="absolute top-0 -right-[60px] flex flex-col items-start gap-1 opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100">
          <LineTool label="Add a line after this one" onClick={onAddSpeech}>+ LINE</LineTool>
          <LineTool label="Add a stage direction after this one" onClick={onAddDirection}>+ DIR.</LineTool>
          <LineTool label="Cut this line" onClick={onCut}>CUT</LineTool>
        </div>
      )}
    </div>
  );
}

function LineTool({ label, onClick, children }: { label: string; onClick(): void; children: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="border-none bg-transparent p-0 font-sans text-[9px] tracking-[1.5px] whitespace-nowrap text-faint transition-colors duration-150 hover:text-gold"
    >
      {children}
    </button>
  );
}
