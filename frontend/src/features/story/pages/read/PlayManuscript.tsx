import { actName } from "@/features/story/model/labels";
import { actSection, CAST_SECTION, sceneSection, TITLE_SECTION, titleLine } from "@/features/story/model/play-reader";
import { parseSceneText, type ScriptBlock } from "@/features/story/model/script";
import type { Play, PlayScene } from "@/features/story/model/types";
import { useAutoGrow } from "@/shared/hooks/use-auto-grow";
import { cn } from "@/shared/lib/utils";

interface PlayManuscriptProps {
  play: Play;
  /** The text is unlocked: the words of every speech and stage direction can be changed. */
  editing: boolean;
  isChanged(act: number, scene: number, index: number): boolean;
  onEdit(act: number, scene: number, index: number, value: string): void;
  /** A line lost focus: its scene is saved. */
  onBlur(act: number, scene: number): void;
}

/** The whole play on one card: title page, Dramatis Personae, every act with its scenes, the end. */
export function PlayManuscript({ play, editing, isChanged, onEdit, onBlur }: PlayManuscriptProps) {
  return (
    <div
      className={cn(
        "mx-auto box-border max-w-[760px] rounded-[10px] border border-line bg-card px-[88px] pt-16 pb-[88px] transition-[border-color,box-shadow] duration-400",
        "max-[900px]:px-5 max-[900px]:py-8",
        editing && "border-gold/55 shadow-[0_0_0_1px_rgba(201,162,75,.15),0_0_40px_rgba(201,162,75,.08)]",
      )}
    >
      <section data-sec={TITLE_SECTION} className="pb-14 text-center">
        <span
          aria-hidden
          className="mx-auto mb-[26px] block size-[46px] rounded-full border border-gold/55 font-serif text-[22px] leading-[44px] text-gold-light italic"
        >
          A
        </span>
        <h2 className="m-0 font-serif text-[60px] leading-none font-medium max-[900px]:text-[42px]">{play.title}</h2>
        <div className="mt-[14px] font-serif text-[22px] text-gold-soft italic">{titleLine(play.genre, play.act_count)}</div>
        <p className="mx-auto mt-7 mb-0 max-w-[440px] font-sans text-[13px] leading-[1.6] text-muted">{play.premise}</p>
      </section>

      <section data-sec={CAST_SECTION} className="pt-14 pb-2">
        <div className="text-center font-sans text-[11px] tracking-[3px] text-gold">DRAMATIS PERSONAE</div>
        <div className="mx-auto mt-[26px] flex max-w-[520px] flex-col gap-[14px]">
          {play.cast.map((member) => (
            <div key={member.character_id} className="grid grid-cols-[150px_minmax(0,1fr)] items-baseline gap-4 max-[900px]:grid-cols-1 max-[900px]:gap-0.5">
              <span className="font-sans text-[11px] tracking-[2.5px] text-gold-soft uppercase">{member.name}</span>
              <span className="font-serif text-[18px] leading-[1.35] text-ink-3">{member.description}</span>
            </div>
          ))}
        </div>
        {play.time_and_world && (
          <p className="mx-auto mt-7 mb-0 max-w-[520px] text-center font-serif text-[18px] leading-[1.45] text-muted italic">{play.time_and_world}</p>
        )}
      </section>

      {play.acts.map((act, actIndex) => (
        <section key={act.number} data-sec={actSection(act.number)} className="pt-24">
          <h2 className="m-0 text-center font-serif text-[42px] leading-[1.1] font-medium">{actName(act.number)}</h2>
          {act.scenes.map((scene, sceneIndex) => (
            <Scene
              key={scene.number}
              act={act.number}
              scene={scene}
              first={sceneIndex === 0}
              editing={editing}
              isChanged={isChanged}
              onEdit={onEdit}
              onBlur={onBlur}
            />
          ))}
          {actIndex === play.acts.length - 1 && (
            <>
              <div className="mt-16 text-center font-serif text-[26px] text-gold italic">Curtain.</div>
              <div className="mt-[10px] text-center font-sans text-[11px] tracking-[4px] text-muted-2">THE END</div>
            </>
          )}
        </section>
      ))}
    </div>
  );
}

interface SceneProps extends Pick<PlayManuscriptProps, "editing" | "isChanged" | "onEdit" | "onBlur"> {
  act: number;
  scene: PlayScene;
  first: boolean;
}

function Scene({ act, scene, first, editing, isChanged, onEdit, onBlur }: SceneProps) {
  return (
    <div data-sec={sceneSection(act, scene.number)} className={first ? "mt-7" : "mt-16"}>
      <div className="mb-2 flex flex-col items-center gap-[6px] text-center">
        <span className="font-sans text-[11px] tracking-[3px] text-gold">SCENE {scene.number}</span>
        <span className="font-serif text-[24px] text-ink">{scene.place_name}</span>
      </div>
      {parseSceneText(scene.text).map((block, index) => (
        <Line
          key={index}
          block={block}
          editing={editing}
          changed={isChanged(act, scene.number, index)}
          onEdit={(value) => onEdit(act, scene.number, index, value)}
          onBlur={() => onBlur(act, scene.number)}
        />
      ))}
    </div>
  );
}

const DIRECTION = "font-serif text-[19px] leading-[1.6] italic text-[#b7ac94]";
const SPEECH = "font-serif text-[22px] leading-[1.6] text-[#f0ebdf]";

interface LineProps {
  block: ScriptBlock;
  editing: boolean;
  changed: boolean;
  onEdit(value: string): void;
  onBlur(): void;
}

/** One block of a scene. Unlocked, the words of a speech or a direction are a field; the rest never is. */
function Line({ block, editing, changed, onEdit, onBlur }: LineProps) {
  const editable = editing && block.kind !== "plain";
  return (
    <div className={cn("relative", changed && "line-changed")}>
      {block.kind === "speech" && (
        <div className="mt-5">
          <div className="mb-0.5 font-sans text-[11px] tracking-[2.5px] text-gold-soft">
            {block.who}
            {block.paren && <span className="ml-2 font-serif text-[16px] tracking-normal text-muted italic">({block.paren})</span>}
          </div>
          {editable ? (
            <LineField value={block.text} label={`Line of ${block.who}`} className={SPEECH} onEdit={onEdit} onBlur={onBlur} />
          ) : (
            <div className={cn("mt-[3px] whitespace-pre-wrap", SPEECH)}>{block.text}</div>
          )}
        </div>
      )}
      {block.kind === "direction" &&
        (editable ? (
          <LineField value={block.text} label="Stage direction" className={cn("mt-4", DIRECTION)} onEdit={onEdit} onBlur={onBlur} />
        ) : (
          <p className={cn("m-0 mt-5 whitespace-pre-wrap", DIRECTION)}>{block.text}</p>
        ))}
      {block.kind === "plain" && <p className="m-0 mt-5 whitespace-pre-wrap font-serif text-[19px] leading-[1.6] text-ink-3">{block.text}</p>}
    </div>
  );
}

interface LineFieldProps {
  value: string;
  label: string;
  className: string;
  onEdit(value: string): void;
  onBlur(): void;
}

/** The words of a line in place: same font and size as the text, a soft gold background, a gold ring on focus. */
function LineField({ value, label, className, onEdit, onBlur }: LineFieldProps) {
  const ref = useAutoGrow<HTMLTextAreaElement>(value);
  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      aria-label={label}
      onChange={(e) => onEdit(e.target.value)}
      onBlur={onBlur}
      className={cn(
        "m-0 mt-[3px] -ml-[6px] box-border block w-[calc(100%+12px)] resize-none overflow-hidden rounded-md border-none bg-gold/[0.04] px-[6px] pt-0.5 pb-1 outline-none",
        "transition-[background-color,box-shadow] duration-200 hover:bg-gold/[0.08] focus:bg-gold/10 focus:shadow-[0_0_0_1px_rgba(201,162,75,.5)]",
        className,
      )}
    />
  );
}
