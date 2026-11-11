import { motion } from "motion/react";
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { ACT_STATUS_LABEL, actName, firstClause, genreLabel, numberWord, roman } from "@/features/story/model/labels";
import { canOpenAct, currentAct, isOpenAct } from "@/features/story/model/progress";
import type { Act, OutlineField, StoryBible } from "@/features/story/model/types";
import { paths } from "@/features/story/paths";
import { useStoryActions, useStoryState } from "@/features/story/store/story-context";
import type { StoryState } from "@/features/story/store/story-reducer";
import { useTimedMessage } from "@/shared/hooks/use-timed-message";
import { cn } from "@/shared/lib/utils";
import { ChatPanel } from "@/shared/ui/chat/ChatPanel";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { ArrowLeft } from "@/shared/ui/icons";
import { Notice } from "@/shared/ui/Notice";
import { Toast } from "@/shared/ui/Toast";
import { StoryHeader } from "../StoryHeader";
import { ActCard, type ActCardProps } from "./ActCard";
import { FinaleCard } from "./FinaleCard";
import { OutlineEditor } from "./OutlineEditor";
import { OutlineSummary } from "./OutlineSummary";

/** How many act cards stand under the veil while the acts are drafted (the backend writes three to five). */
const DRAFT_PLACEHOLDERS = 4;
/** How long the notice about an act that cannot be opened yet stays. */
const NOTICE_MS = 3500;

/** Page "/play": the outline, then the acts with their progress. */
export function PlayPage() {
  const state = useStoryState();
  const actions = useStoryActions();
  const navigate = useNavigate();
  const { loaded, story, jobs, chatOpen, chats, typing, draft } = state;
  const notice = useTimedMessage(NOTICE_MS);

  // once approved, the outline is final: the acts are shown and the outline stays a read-only summary
  const showActs = !!story?.outline && (story.acts.length > 0 || jobs.includes("acts"));
  const chatKey = showActs ? "acts" : "outline";
  // the chat is for the outline and the acts; once the acts are approved, the work goes on act by act
  const hasChat = !!story?.outline && !story.acts_approved;
  const { chatOpened } = actions;
  useEffect(() => {
    if (hasChat) chatOpened(chatKey);
  }, [chatKey, chatOpened, hasChat]);

  if (!loaded) return null; // the Story Bible is still being read after a reload

  const chat = hasChat && (
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
          <StoryHeader eyebrow="THE PLAY" tag="OUTLINE" title="A new play" sub="">
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

  const header = playHeader(state, story, showActs, actions);
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
          chat={hasChat ? { open: chatOpen, onToggle: actions.toggleChat } : undefined}
        >
          {header.secondary && (
            <HeaderPill ghost disabled={header.secondary.disabled} onClick={header.secondary.onClick}>
              {header.secondary.label}
            </HeaderPill>
          )}
          {header.button && (
            <HeaderPill disabled={header.button.disabled} onClick={header.button.onClick}>
              {header.button.label}
            </HeaderPill>
          )}
        </StoryHeader>

        <div className={cn("split", showActs && "split-on")}>
          <aside className="split-side" aria-label="Play outline">
            <div className="split-full scroll-thin box-border px-12 pt-5 pb-12">
              {/* while the outline is written: nothing under the veil, the fields fade in once it is there */}
              {story.outline && !jobs.includes("outline") && (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut" }}>
                  <OutlineEditor
                    outline={story.outline}
                    readOnly={showActs}
                    onChange={actions.editOutline}
                    highlighted={outlineHighlight}
                  />
                </motion.div>
              )}
            </div>
            <GenerationVeil
              flat
              show={!showActs && jobs.includes("outline")}
              label="WRITING THE OUTLINE"
              line="Reading your idea and the cast…"
            />
            <div className="split-mini scroll-thin box-border px-7 pt-[26px] pb-10">
              {story.outline && <OutlineSummary outline={story.outline} />}
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
                        <ActCard {...actCardProps(state, story, act, actions, notice.show)} />
                      </div>
                    ))}
                {story.play_complete && (
                  <FinaleCard
                    title={story.outline?.title || "Untitled play"}
                    acts={story.acts.length}
                    scenes={story.acts.reduce((sum, act) => sum + act.scenes.length, 0)}
                    onRead={() => navigate(paths.read)}
                  />
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
      {chat}
      <Toast open={notice.open}>{notice.message}</Toast>
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
  /** A ghost pill before the main one: write the outline or draft the acts again. */
  secondary?: { label: string; disabled: boolean; onClick(): void };
}

/** The header follows the play: outline, acts being drafted, acts to approve, then the act being built. */
function playHeader(state: StoryState, story: StoryBible, showActs: boolean, actions: Actions): PlayHeader {
  const { jobs, failed, typing } = state;
  const outline = story.outline;

  if (!showActs) {
    if (!outline || jobs.includes("outline")) {
      const writing = jobs.includes("outline") || !failed.includes("outline");
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
    return {
      tag: "OUTLINE",
      title: outline.title || "Untitled play",
      sub: [genreLabel(outline.genre), firstClause(outline.tone)].filter(Boolean).join(" · "),
      status: false,
      secondary: { label: "REWRITE OUTLINE", disabled: typing === "outline", onClick: actions.generateOutline },
      button: {
        label: "APPROVE OUTLINE",
        disabled: !outline.title.trim() || !outline.synopsis.trim() || typing === "outline" || jobs.includes("acts"),
        onClick: actions.approveOutline,
      },
    };
  }

  const count = story.acts.length;
  const title = count ? `${numberWord(count)} acts` : "The acts";
  if (count === 0 || jobs.includes("acts")) {
    return { tag: "ACTS", title, sub: "The acts are being drafted from the synopsis…", status: true, button: { label: "APPROVE ACTS", disabled: true, onClick: () => {} } };
  }
  if (!story.acts_approved) {
    return {
      tag: "ACTS",
      title,
      sub: outline?.premise ?? "",
      status: false,
      secondary: { label: "REDRAFT ACTS", disabled: jobs.includes("approveActs") || typing === "acts", onClick: actions.redraftActs },
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
function actCardProps(state: StoryState, story: StoryBible, act: Act, actions: Actions, showNotice: (message: string) => void): ActCardProps {
  const { jobs, failed, highlight } = state;
  const n = act.number;
  const name = actName(n);
  const word = numberWord(n).toUpperCase();
  const current = currentAct(story);
  const isCurrent = current?.number === n;
  const waitingToStage = isCurrent && act.status === "draft" && act.scenes.length === 0;

  let veil: ActCardProps["veil"] = null;
  if (jobs.includes("acts")) veil = { label: `DRAFTING ACT ${word}`, line: "Shaping the act from the synopsis…" };
  else if (jobs.includes(`record:${n}`)) veil = { label: "RECORDING THE CHANGES", line: `Writing down what ${name} changed for each character…` };
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
    // the summaries are final once the acts are approved
    onSummaryChange: veil || story.acts_approved ? undefined : (summary) => actions.editActSummary(n, summary),
    veil,
    highlighted: highlight.includes(`act:${n}`),
    dimmed: story.acts_approved && !!current && n > current.number,
    open: openable ? { label: read ? "READ" : "OPEN", aria: `${read ? "Read" : "Open"} ${name}`, onOpen: () => actions.openAct(n) } : null,
    retry: waitingToStage && failed.includes(`structure:${n}`) ? { label: `STAGE ACT ${word}`, onRetry: () => actions.stageAct(n) } : null,
    onLockedClick:
      story.acts_approved && !isOpenAct(story, n)
        ? () => showNotice(`${name} can be opened only after the text of ${actName(n - 1)} is approved.`)
        : undefined,
  };
}
