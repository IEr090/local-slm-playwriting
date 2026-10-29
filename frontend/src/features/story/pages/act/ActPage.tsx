import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useParams } from "react-router";
import { useCastState } from "@/features/characters/store/cast-context";
import { ACT_STATUS_LABEL, actName, numberWord, roman, SCENE_STATUS_LABEL } from "@/features/story/model/labels";
import { actStage, allScenesApproved, isOpenAct, type ActStage } from "@/features/story/model/progress";
import { isIncomplete, openAfterCut, openAfterMove } from "@/features/story/model/scenes";
import type { Act, StoryBible } from "@/features/story/model/types";
import { paths } from "@/features/story/paths";
import { useStoryActions, useStoryState } from "@/features/story/store/story-context";
import type { StoryState } from "@/features/story/store/story-reducer";
import { cn } from "@/shared/lib/utils";
import { ChatPanel } from "@/shared/ui/chat/ChatPanel";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { ArrowDown, ArrowLeft, ArrowUp, Close, Pen } from "@/shared/ui/icons";
import { Notice } from "@/shared/ui/Notice";
import { RoundIconButton } from "@/shared/ui/RoundIconButton";
import { StoryHeader } from "../StoryHeader";
import { sceneAnchor } from "./anchors";
import { Manuscript } from "./Manuscript";
import { AddingSceneCard, SceneCard } from "./SceneCard";
import { ScenePlanCard, type CastChip } from "./ScenePlanCard";

type Actions = ReturnType<typeof useStoryActions>;

/** Page "/play/acts/:n": the scenes of one act, their plans, then its text. */
export function ActPage() {
  const n = Number(useParams().n);
  const state = useStoryState();
  const actions = useStoryActions();
  const { cast } = useCastState();
  const { loaded, story, jobs, chatOpen, chats, typing, draft, pending, highlight, editingScenes } = state;
  // structure scenes whose editor is open; a scene added by hand opens with it
  const [open, setOpen] = useState<Set<number>>(new Set());

  const { actOpened } = actions;
  const hasStory = !!story;
  useEffect(() => {
    if (loaded && hasStory) actOpened(n);
  }, [n, loaded, hasStory, actOpened]);

  if (!loaded) return null; // the Story Bible is still being read after a reload
  const act = story?.acts.find((item) => item.number === n);
  if (!story || !act || !isOpenAct(story, n)) return <Navigate to={paths.play} replace />;

  const stage = actStage(
    act,
    { staging: jobs.includes(`structure:${n}`), writing: jobs.includes(`text:${n}`), recording: jobs.includes(`record:${n}`) },
    editingScenes.includes(n),
  );
  const inText = stage === "writing" || stage === "text" || stage === "recording" || stage === "done";
  const name = actName(n);
  const playTitle = story.outline?.title || "Untitled play";
  const header = actHeader(state, story, act, stage, actions);
  const chatKind = stage === "structure" || stage === "staging" ? "structure" : inText ? "text" : "scenes";

  const names = new Map(cast.map((c) => [c.id, c.name || c.surname]));
  const castChips: CastChip[] = cast.map((c) => ({ id: c.id, label: (c.name || c.surname).toUpperCase() }));
  const placeName = (id: string) => story.places.find((p) => p.id === id)?.name ?? "";
  const who = (ids: string[]) => ids.map((id) => names.get(id)).filter((x): x is string => !!x);
  const isPending = (target: string) => typing === `act:${n}` && pending.includes(target);

  // ---------- structure tools ----------

  const tools = (i: number, count: number) => (
    <>
      <ToolButton label={`Edit scene ${i + 1}`} title="Edit scene" active={open.has(i)} onClick={() => setOpen(toggle(open, i))}>
        <Pen />
      </ToolButton>
      <ToolButton
        label={`Move scene ${i + 1} up`}
        title="Move up"
        disabled={i === 0}
        onClick={() => {
          setOpen(openAfterMove(open, i, -1, count));
          actions.moveScene(n, i, -1);
        }}
      >
        <ArrowUp />
      </ToolButton>
      <ToolButton
        label={`Move scene ${i + 1} down`}
        title="Move down"
        disabled={i === count - 1}
        onClick={() => {
          setOpen(openAfterMove(open, i, 1, count));
          actions.moveScene(n, i, 1);
        }}
      >
        <ArrowDown />
      </ToolButton>
      <ToolButton
        label={`Cut scene ${i + 1}`}
        title="Cut scene"
        onClick={() => {
          setOpen(openAfterCut(open, i));
          actions.cutScene(n, i);
        }}
      >
        <Close size={11} />
      </ToolButton>
    </>
  );

  const sceneCards = act.scenes.map((scene, i) => {
    const no = scene.number;
    const target = `scene:${n}:${no}`;
    if (stage === "structure") {
      if (open.has(i) || isIncomplete(scene)) {
        return (
          <ScenePlanCard
            key={i}
            number={no}
            plan={scene}
            places={story.places}
            cast={castChips}
            onChange={(patch) => actions.editStructureScene(n, i, patch)}
            onCreatePlace={actions.createPlace}
            tools={tools(i, act.scenes.length)}
            updating={isPending(target)}
            highlighted={highlight.includes(target)}
          />
        );
      }
      return (
        <SceneCard
          key={i}
          number={no}
          place={placeName(scene.place_id)}
          placeNotes={scene.place_notes}
          who={who(scene.character_ids)}
          whatHappens={scene.what_happens}
          tools={tools(i, act.scenes.length)}
          updating={isPending(target)}
          highlighted={highlight.includes(target)}
        />
      );
    }
    const outdated = act.outdated_plans.includes(no)
      ? "A scene before this one changed after this plan was written. Check that it still follows on."
      : undefined;
    if (!scene.planned) {
      const planning = jobs.includes(`plan:${n}:${no}`);
      const waiting = i > 0 && act.scenes[i - 1].status !== "approved";
      return (
        <SceneCard
          key={i}
          number={no}
          place={placeName(scene.place_id)}
          placeNotes={scene.place_notes}
          who={who(scene.character_ids)}
          whatHappens={scene.what_happens}
          planning={planning}
          dimmed={!planning}
          updating={isPending(target)}
          tools={
            !planning && (
              <span className="pt-1 font-sans text-[10px] tracking-[1.5px] whitespace-nowrap text-muted-2">
                {waiting ? `PLANNED AFTER SCENE ${no - 1}` : "NOT PLANNED"}
              </span>
            )
          }
        />
      );
    }
    const busy = jobs.includes(`scene:${n}:${no}`) || jobs.includes(`plan:${n}:${no}`);
    return (
      <ScenePlanCard
        key={i}
        number={no}
        plan={scene}
        places={story.places}
        cast={castChips}
        onChange={(patch) => actions.editScenePlan(n, no, patch)}
        onCreatePlace={actions.createPlace}
        status={{
          label: SCENE_STATUS_LABEL[scene.status],
          approved: scene.status === "approved",
          busy,
          onApprove: () => actions.approveScene(n, no),
          onReopen: () => actions.reopenScene(n, no),
        }}
        readOnly={stage !== "plans"}
        updating={isPending(target)}
        highlighted={highlight.includes(target)}
        notice={outdated}
      />
    );
  });

  const textVeil =
    stage === "writing"
      ? { label: `WRITING ACT ${numberWord(n).toUpperCase()}`, line: "Turning the scenes into dialogue…" }
      : stage === "recording"
        ? { label: "RECORDING THE CHANGES", line: `Writing down what ${name} changed for each character…` }
        : null;

  return (
    <div className="absolute inset-0 flex">
      <div className="relative flex min-w-0 flex-1 flex-col bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]">
        <StoryHeader
          eyebrow={playTitle}
          tag={header.tag}
          title={name}
          sub={header.sub}
          status={header.status}
          chatOpen={chatOpen}
          onToggleChat={actions.toggleChat}
        >
          <HeaderPill ghost onClick={actions.goToPlay}>
            <ArrowLeft />
            <span>ALL ACTS</span>
          </HeaderPill>
          {header.button && (
            <HeaderPill disabled={header.button.disabled} onClick={header.button.onClick}>
              {header.button.label}
            </HeaderPill>
          )}
        </StoryHeader>

        <div className={cn("split [--split-width:320px]", inText && "split-on")}>
          <aside className="split-side" aria-label={`Scenes of ${name}`}>
            <div className="split-full scroll-thin box-border px-12 pt-6 pb-14">
              <div className="flex max-w-[1040px] min-w-[720px] flex-col gap-[14px]">
                <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-x-4 pt-1 pb-[10px]">
                  <div aria-hidden className="text-center font-serif text-4xl leading-none text-gold italic">
                    {roman(n)}
                  </div>
                  <div className="font-serif text-xl leading-[1.4] text-ink-3 italic">{act.summary}</div>
                </div>

                <div className="mt-[6px] flex items-center gap-[14px]">
                  <span className="font-sans text-[11px] tracking-[3px] text-ink-2">SCENES</span>
                  <span className="dotted-rule flex-1" />
                  <span className="font-sans text-[11px] tracking-[2px] text-muted-2">
                    {act.scenes.length} {act.scenes.length === 1 ? "SCENE" : "SCENES"}
                  </span>
                </div>

                {act.summary_changed && (
                  <Notice>The scenes were built from an earlier version of the act summary. Check that they still fit.</Notice>
                )}
                {act.scenes_changed && stage === "plans" && (
                  <Notice>The text of {name} was written from these scenes. If you change them, write the act again.</Notice>
                )}

                {stage === "staging" && (
                  <article className="relative min-h-[190px] rounded-[10px] border border-line bg-card">
                    <GenerationVeil
                      show={!state.failed.includes(`structure:${n}`)}
                      label={`STAGING ACT ${numberWord(n).toUpperCase()}`}
                      line="Choosing places and who is on stage…"
                    />
                  </article>
                )}

                {sceneCards}

                {stage === "structure" && isPending(`add:${n}`) && <AddingSceneCard number={act.scenes.length + 1} />}
                {stage === "structure" && (
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(new Set([...open, act.scenes.length]));
                      actions.addScene(n);
                    }}
                    className="h-14 w-full rounded-[10px] border border-dashed border-line-strong bg-transparent font-sans text-[11px] tracking-[2px] text-muted transition-colors duration-200 hover:border-gold hover:text-gold"
                  >
                    + ADD SCENE
                  </button>
                )}
              </div>
            </div>

            <div className="split-mini scroll-thin box-border px-6 pt-[26px] pb-10">
              <div className="flex items-center justify-between gap-[10px]">
                <span className="font-sans text-[11px] tracking-[2px] text-muted-2">SCENES</span>
                <HeaderPill
                  ghost
                  small
                  disabled={stage === "writing" || stage === "recording"}
                  onClick={() => actions.setEditingScenes(n, true)}
                >
                  EDIT SCENES
                </HeaderPill>
              </div>
              <div className="mt-[14px] font-serif text-[17px] leading-[1.35] text-gold-soft italic">{act.summary}</div>
              <div className="dotted-rule mt-[18px] mb-[10px]" />
              {act.scenes.map((scene) => (
                <button
                  key={scene.number}
                  type="button"
                  onClick={() => document.getElementById(sceneAnchor(n, scene.number))?.scrollIntoView({ behavior: "smooth" })}
                  className="grid w-full grid-cols-[26px_minmax(0,1fr)] gap-[10px] rounded-lg border-none bg-transparent px-2 py-[10px] text-left text-ink transition-colors duration-150 hover:bg-card"
                >
                  <span className="text-center font-serif text-[22px] leading-none text-gold italic">{scene.number}</span>
                  <span>
                    <span className="block font-serif text-lg leading-[1.15]">{placeName(scene.place_id) || "No place yet"}</span>
                    <span className="mt-[3px] block font-sans text-[11px] text-muted-2">{who(scene.character_ids).join(", ")}</span>
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="split-main scroll-thin" aria-label={`Text of ${name}`}>
            <div className="px-12 pt-8 pb-[72px]">
              <Manuscript
                act={n}
                playTitle={playTitle}
                sceneTexts={act.scene_texts}
                placeOf={(scene) => placeName(act.scenes.find((s) => s.number === scene)?.place_id ?? "")}
                veil={textVeil}
                approved={stage === "done"}
                editable={stage === "text"}
                onEdit={(scene, block, value) => actions.editSceneText(n, scene, block, value)}
                rewriting={act.scene_texts.map((t) => t.scene_number).filter((s) => isPending(`scene:${n}:${s}`))}
                highlighted={highlight.filter((h) => h.startsWith(`block:${n}:`)).map((h) => h.split(":").slice(2).join(":"))}
              />
            </div>
          </section>
        </div>
      </div>

      <ChatPanel
        open={chatOpen}
        intro={chatIntro(stage)}
        placeholder={chatKind === "structure" ? "Add, cut or change a scene…" : "Scene 3: what should change…"}
        messages={chats[`act:${n}`] ?? []}
        typing={typing === `act:${n}`}
        draft={draft}
        onDraftChange={actions.setDraft}
        onSend={() => void actions.sendMessage({ kind: chatKind, act: n })}
      />
    </div>
  );
}

function toggle(set: Set<number>, i: number): Set<number> {
  const next = new Set(set);
  if (next.has(i)) next.delete(i);
  else next.add(i);
  return next;
}

function ToolButton({ label, title, disabled, active, onClick, children }: { label: string; title: string; disabled?: boolean; active?: boolean; onClick(): void; children: ReactNode }) {
  return (
    <RoundIconButton
      aria-label={label}
      title={title}
      disabled={disabled}
      active={active}
      onClick={onClick}
      className="size-8 disabled:cursor-default disabled:opacity-30 disabled:hover:border-line-strong disabled:hover:text-ink-2"
    >
      {children}
    </RoundIconButton>
  );
}

function chatIntro(stage: ActStage): string {
  switch (stage) {
    case "staging":
    case "structure":
      return "Ask for changes to the structure, for example “add a scene at dawn on the landing” or “Scene 2: let the rival arrive earlier”.";
    case "plans":
      return "Name the scene and what should change, for example “Scene 3: she should already know”.";
    case "writing":
      return "The act is being written. You can ask for changes once the text is ready.";
    default:
      return "Ask for changes to the text, for example “Scene 3: give her a sharper line”.";
  }
}

interface ActHeader {
  tag: string;
  sub: string;
  status: boolean;
  button: { label: string; disabled: boolean; onClick(): void } | null;
}

function actHeader(state: StoryState, story: StoryBible, act: Act, stage: ActStage, actions: Actions): ActHeader {
  const { jobs, failed, typing } = state;
  const n = act.number;
  const name = actName(n);
  const word = numberWord(n).toUpperCase();
  const chatBusy = typing === `act:${n}`;
  const count = act.scenes.length;

  switch (stage) {
    case "staging":
      return failed.includes(`structure:${n}`)
        ? { tag: "STRUCTURE DRAFT", sub: `The scenes of ${name} could not be staged.`, status: false, button: { label: `STAGE ACT ${word}`, disabled: false, onClick: () => actions.stageAct(n) } }
        : { tag: "STRUCTURE DRAFT", sub: `The scenes of ${name} are being staged…`, status: true, button: { label: "APPROVE STRUCTURE", disabled: true, onClick: () => {} } };
    case "structure":
      return {
        tag: "STRUCTURE DRAFT",
        sub: `${count} ${count === 1 ? "scene" : "scenes"} proposed. Reorder, cut or add before approving the structure.`,
        status: false,
        button: {
          label: "APPROVE STRUCTURE",
          disabled: count === 0 || chatBusy || jobs.includes(`approveStructure:${n}`),
          onClick: () => actions.approveStructure(n),
        },
      };
    case "plans": {
      const approved = act.scenes.filter((s) => s.status === "approved").length;
      const planning = act.scenes.find((s) => jobs.includes(`plan:${n}:${s.number}`));
      const sub = planning ? `The plan of Scene ${planning.number} is being written…` : `${approved} of ${count} scenes approved`;
      const hasText = act.scene_texts.length > 0;
      const ready = act.status === "scenes_approved" && allScenesApproved(act);
      let button: ActHeader["button"];
      if (hasText && !act.scenes_changed && act.status !== "structure_approved") {
        button = { label: "BACK TO TEXT", disabled: false, onClick: () => actions.setEditingScenes(n, false) };
      } else {
        button = { label: `${hasText ? "REWRITE" : "WRITE"} ACT ${word}`, disabled: !ready || chatBusy, onClick: () => actions.writeText(n) };
      }
      return { tag: ACT_STATUS_LABEL[act.status], sub, status: !!planning, button };
    }
    case "writing":
      return { tag: "SCENES APPROVED", sub: `${name} is being written…`, status: true, button: { label: "APPROVE TEXT", disabled: true, onClick: () => {} } };
    case "text":
      return {
        tag: "SCENES APPROVED",
        sub: "Read the act. Ask the chat for any changes, then approve the text.",
        status: false,
        button: { label: "APPROVE TEXT", disabled: chatBusy, onClick: () => actions.approveText(n) },
      };
    case "recording":
      return { tag: "SCENES APPROVED", sub: `Recording what ${name} changed for each character…`, status: true, button: { label: "APPROVE TEXT", disabled: true, onClick: () => {} } };
    case "done": {
      const next = story.acts.find((item) => item.number === n + 1);
      return {
        tag: "TEXT APPROVED",
        sub: `The text is approved. The characters’ histories now include ${name}.`,
        status: true,
        button: { label: next ? `ON TO ACT ${numberWord(next.number).toUpperCase()}` : "BACK TO THE PLAY", disabled: false, onClick: actions.goToPlay },
      };
    }
  }
}
