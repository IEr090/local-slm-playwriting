import { useEffect } from "react";
import { useNavigate } from "react-router";
import { ACT_STATUS_LABEL, actName, firstClause, genreLabel, numberWord, roman } from "@/features/story/model/labels";
import { canOpenAct, currentAct } from "@/features/story/model/progress";
import type { Act, Outline, OutlineField, StoryBible } from "@/features/story/model/types";
import { useStoryActions, useStoryState } from "@/features/story/store/story-context";
import type { StoryState } from "@/features/story/store/story-reducer";
import { cn } from "@/shared/lib/utils";
import { ChatPanel } from "@/shared/ui/chat/ChatPanel";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { ArrowLeft } from "@/shared/ui/icons";
import { Notice } from "@/shared/ui/Notice";
import { StoryHeader } from "../StoryHeader";
import { ActCard, type ActCardProps } from "./ActCard";
import { OutlineEditor } from "./OutlineEditor";
import { OutlineSummary } from "./OutlineSummary";

const BLANK_OUTLINE: Outline = {
  title: "", premise: "", genre: "drama", tone: "", time_and_world: "", central_conflict: "", synopsis: "",
};

/** How many act cards stand under the veil while the acts are drafted (the backend writes three to five). */
const DRAFT_PLACEHOLDERS = 4;

/** Page "/play": the outline, then the acts with their progress. */
export function PlayPage() {
  const state = useStoryState();
  const actions = useStoryActions();
  const navigate = useNavigate();
  const { loaded, story, jobs, editingOutline, chatOpen, chats, typing, draft } = state;

  const showActs = !!story?.outline && !editingOutline && (story.acts.length > 0 || jobs.includes("acts"));
  const chatKey = showActs ? "acts" : "outline";
  const { chatOpened } = actions;
  useEffect(() => {
    if (story?.outline) chatOpened(chatKey);
  }, [chatKey, chatOpened, story?.outline]);

  if (!loaded) return null; // the Story Bible is still being read after a reload

  const chat = (
    <ChatPanel
      open={chatOpen}
      intro={
        showActs
          ? "Name the act and what should change, for example “Act Two: the rival should be crueller here” or “end Act One on a question”. The Story Agent keeps every act in line with the synopsis."
          : "Describe what should change in the outline, for example “make the ending darker” or “move it to the present day”. The Story Agent will rewrite the relevant fields."
      }
      placeholder={showActs ? "Act Two: what should change…" : "Describe what to change…"}
      messages={chats[chatKey] ?? []}
      typing={typing === chatKey}
      draft={draft}
      onDraftChange={actions.setDraft}
      onSend={() => void actions.sendMessage({ kind: chatKey })}
    />
  );

  if (!story) {
    return (
      <div className="absolute inset-0 flex">
        <div className="relative flex min-w-0 flex-1 flex-col bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]">
          <StoryHeader eyebrow="THE PLAY" tag="OUTLINE" title="A new play" sub="" chatOpen={false} onToggleChat={() => {}}>
            <HeaderPill ghost onClick={() => navigate("/")}>
              <ArrowLeft />
              <span>NEW PREMISE</span>
            </HeaderPill>
          </StoryHeader>
          <div className="px-12 pt-6">
            <Notice className="max-w-[720px]">No play yet. Generate the characters first: the play is built from your idea and the cast.</Notice>
          </div>
        </div>
      </div>
    );
  }

  const outline = story.outline ?? BLANK_OUTLINE;
  const header = playHeader(state, story, showActs, actions);
  const outlinePending = fieldsOf(state.pending, "outline:");
  const outlineHighlight = fieldsOf(state.highlight, "outline:");

  return (
    <div className="absolute inset-0 flex">
      <div className="relative flex min-w-0 flex-1 flex-col bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]">
        <StoryHeader
          eyebrow="THE PLAY"
          tag={header.tag}
          title={header.title}
          sub={header.sub}
          status={header.status}
          chatOpen={chatOpen}
          onToggleChat={actions.toggleChat}
        >
          {header.button && (
            <HeaderPill disabled={header.button.disabled} onClick={header.button.onClick}>
              {header.button.label}
            </HeaderPill>
          )}
        </StoryHeader>

        <div className={cn("split", showActs && "split-on")}>
          <aside className="split-side" aria-label="Play outline">
            <div className="split-full scroll-thin box-border px-12 pt-5 pb-12">
              {story.outline_changed && story.acts.length > 0 && (
                <Notice className="mb-[14px] max-w-[1180px] min-w-[720px]">
                  The acts were built from this outline. If you change it, check that the acts still fit: they are not
                  rewritten on their own.
                </Notice>
              )}
              <OutlineEditor
                outline={outline}
                readOnly={!story.outline}
                onChange={actions.editOutline}
                updating={typing === "outline" ? outlinePending : []}
                highlighted={outlineHighlight}
              />
            </div>
            <GenerationVeil
              flat
              show={!showActs && jobs.includes("outline")}
              label="WRITING THE OUTLINE"
              line="Reading your idea and the cast…"
            />
            <div className="split-mini scroll-thin box-border px-7 pt-[26px] pb-10">
              {story.outline && <OutlineSummary outline={story.outline} onEdit={() => actions.setEditingOutline(true)} />}
            </div>
          </aside>

          <section className="split-main scroll-thin" aria-label="Acts">
            <div className="box-border max-w-[1040px] px-12 pt-6 pb-14">
              <div className="flex flex-col gap-[14px]">
                {story.acts.length === 0 && jobs.includes("acts")
                  ? Array.from({ length: DRAFT_PLACEHOLDERS }, (_, i) => (
                      <div key={i} className="slide-in">
                        <ActCard
                          roman={roman(i + 1)}
                          name={actName(i + 1)}
                          status=""
                          summary=""
                          veil={{ label: `DRAFTING ACT ${numberWord(i + 1).toUpperCase()}`, line: "Shaping the act from the synopsis…" }}
                        />
                      </div>
                    ))
                  : story.acts.map((act) => (
                      <div key={act.number} className="slide-in">
                        <ActCard {...actCardProps(state, story, act, actions)} />
                      </div>
                    ))}
              </div>
            </div>
          </section>
        </div>
      </div>
      {chat}
    </div>
  );
}

const fieldsOf = (targets: string[], prefix: string) =>
  targets.filter((t) => t.startsWith(prefix)).map((t) => t.slice(prefix.length) as OutlineField);

type Actions = ReturnType<typeof useStoryActions>;

interface PlayHeader {
  tag: string;
  title: string;
  sub: string;
  status: boolean;
  button: { label: string; disabled: boolean; onClick(): void } | null;
}

/** The header follows the play: outline, acts being drafted, acts to approve, then the act being built. */
function playHeader(state: StoryState, story: StoryBible, showActs: boolean, actions: Actions): PlayHeader {
  const { jobs, failed, typing } = state;
  const outline = story.outline;

  if (!showActs) {
    if (!outline) {
      const writing = !failed.includes("outline");
      return {
        tag: "OUTLINE",
        title: "A new play",
        sub: writing ? "The outline is being written from your idea and the cast…" : "The outline could not be written.",
        status: writing,
        button: writing
          ? { label: "APPROVE OUTLINE", disabled: true, onClick: () => {} }
          : { label: "WRITE THE OUTLINE", disabled: false, onClick: actions.generateOutline },
      };
    }
    const hasActs = story.acts.length > 0;
    return {
      tag: "OUTLINE",
      title: outline.title || "Untitled play",
      sub: [genreLabel(outline.genre), firstClause(outline.tone)].filter(Boolean).join(" · "),
      status: false,
      button: hasActs
        ? { label: "BACK TO ACTS", disabled: false, onClick: () => actions.setEditingOutline(false) }
        : {
            label: "APPROVE OUTLINE",
            disabled: !outline.title.trim() || !outline.synopsis.trim() || typing === "outline" || jobs.includes("acts"),
            onClick: actions.approveOutline,
          },
    };
  }

  const count = story.acts.length;
  const title = count ? `${numberWord(count)} acts` : "The acts";
  if (count === 0) {
    return { tag: "ACTS", title, sub: "The acts are being drafted from the synopsis…", status: true, button: { label: "APPROVE ACTS", disabled: true, onClick: () => {} } };
  }
  if (!story.acts_approved) {
    return {
      tag: "ACTS",
      title,
      sub: outline?.premise ?? "",
      status: false,
      button: { label: "APPROVE ACTS", disabled: jobs.includes("approveActs") || typing === "acts", onClick: actions.approveActs },
    };
  }

  // once the acts are approved, each act opens from its own card: no button in the header
  const act = currentAct(story);
  if (!act) return { tag: "TEXT APPROVED", title, sub: "Every act is approved. The play is written.", status: false, button: null };
  const name = actName(act.number);
  const before = act.number > 1 ? `${actName(act.number - 1)} is approved. ` : "";
  const tag = `ACT ${numberWord(act.number).toUpperCase()}`;
  const line = (sub: string, status: boolean) => ({ tag, title, sub, status, button: null });
  if (jobs.includes(`record:${act.number}`)) return line(`Recording what ${name} changed for each character…`, true);
  if (jobs.includes(`text:${act.number}`)) return line(`${name} is being written…`, true);
  if (act.scene_texts.length > 0) return line(`${name} is written. Read it and approve the text.`, false);
  if (act.scenes.length === 0) {
    return failed.includes(`structure:${act.number}`)
      ? line(`${before}The scenes of ${name} could not be staged.`, false)
      : line(`${before}The scenes of ${name} are being staged…`, true);
  }
  if (jobs.some((key) => key.startsWith(`plan:${act.number}:`))) return line(`The scenes of ${name} are being planned…`, true);
  return line(`${before}${name} is staged. Open it to review its scenes.`, false);
}

/** What one act card shows, from the Story Bible and the running requests. */
function actCardProps(state: StoryState, story: StoryBible, act: Act, actions: Actions): ActCardProps {
  const { jobs, failed, pending, highlight, typing } = state;
  const n = act.number;
  const name = actName(n);
  const word = numberWord(n).toUpperCase();
  const current = currentAct(story);
  const isCurrent = current?.number === n;
  const waitingToStage = isCurrent && act.status === "draft" && act.scenes.length === 0;

  let veil: ActCardProps["veil"] = null;
  if (jobs.includes(`record:${n}`)) veil = { label: "RECORDING THE CHANGES", line: `Writing down what ${name} changed for each character…` };
  else if (jobs.includes(`text:${n}`)) veil = { label: `WRITING ACT ${word}`, line: "Turning the scenes into dialogue…" };
  else if (jobs.includes(`structure:${n}`) || (waitingToStage && !failed.includes(`structure:${n}`)))
    veil = { label: `STAGING ACT ${word}`, line: "Choosing places and who is on stage…" };

  const openable = !veil && canOpenAct(story, act);
  const read = act.scene_texts.length > 0;
  return {
    roman: roman(n),
    name,
    status: ACT_STATUS_LABEL[act.status],
    summary: act.summary,
    onSummaryChange: veil ? undefined : (summary) => actions.editActSummary(n, summary),
    veil,
    revising: typing === "acts" && pending.includes(`act:${n}`),
    highlighted: highlight.includes(`act:${n}`),
    dimmed: story.acts_approved && !!current && n > current.number,
    open: openable ? { label: read ? "READ" : "OPEN", aria: `${read ? "Read" : "Open"} ${name}`, onOpen: () => actions.openAct(n) } : null,
    retry: waitingToStage && failed.includes(`structure:${n}`) ? { label: `STAGE ACT ${word}`, onRetry: () => actions.stageAct(n) } : null,
    notice: act.summary_changed
      ? `The scenes of ${name} were built from the earlier version of this summary. If you keep this change, check that they still fit.`
      : undefined,
  };
}
