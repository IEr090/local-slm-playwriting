// Story Bible store provider: one reducer + async actions. It sits above the routes, so a generation keeps
// running while the user moves between the play page and an act page; requests are aborted only when a new
// cast replaces the play. Data only ever comes from `api`; errors go to the shared error banner.

import { useCallback, useEffect, useLayoutEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import { useCastState } from "@/features/characters/store/cast-context";
import { api } from "@/features/story/api";
import { currentAct, nextSceneToPlan } from "@/features/story/model/progress";
import { addBlankScene, cutScene, moveScene } from "@/features/story/model/scenes";
import type { HistoryMessage, Outline, PlaceDraft, Scene, ScenePlan, StoryBible } from "@/features/story/model/types";
import { paths } from "@/features/story/paths";
import { useErrors } from "@/shared/errors/errors-context";
import type { ChatBubble } from "@/shared/ui/chat/ChatMessage";
import { forgetAllJobs, forgetJob, rememberJob, resumableJobs } from "./resumable";
import { chatKey, revisers } from "./revisions";
import { ActionsContext, StateContext, type ChatContext, type StoryActions } from "./story-context";
import { initialState, reducer, type Action, type ChatKey, type JobKey } from "./story-reducer";
import { useAutosave } from "./use-autosave";
import { useJobs } from "./use-jobs";

/** How long changed fields glow after an AI revision. */
const HIGHLIGHT_MS = 2600;

const toBubbles = (history: HistoryMessage[]): ChatBubble[] =>
  history
    .filter((m) => m.content.trim())
    .map((m) => (m.role === "user" ? { role: "user", text: m.content } : { role: "ai", text: m.content, updated: [] }));

export function StoryProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useErrors();
  const { generation: castGeneration } = useCastState();

  const stateRef = useRef(state);
  useLayoutEffect(() => {
    stateRef.current = state;
  }, [state]);

  /** Grows when a new cast replaces the play; answers to requests of an older play are dropped. */
  const epoch = useRef(0);

  const { receive, edited, flush, flushAll, reset: resetSaves } = useAutosave({ epoch, stateRef, dispatch, showError });
  const { runJob, isRunning, abortAll, isUnloading } = useJobs({ epoch, dispatch, showError });

  /** Runs a request that answers with the Story Bible and takes the answer. */
  const runStoryJob = useCallback(
    async (key: JobKey, work: (signal: AbortSignal) => Promise<StoryBible>): Promise<boolean> => {
      const from = epoch.current;
      const story = await runJob(key, work);
      if (story) receive(story, from);
      return story !== undefined;
    },
    [runJob, receive],
  );

  // ---------- loading, and a new cast replacing the play ----------

  const loading = useRef(false);
  const historyRequested = useRef(new Set<ChatKey>());

  /** A new cast starts a new play on the backend: everything of the old play is dropped. */
  const resetPlay = useCallback(() => {
    epoch.current += 1;
    abortAll();
    resetSaves();
    historyRequested.current.clear();
    loading.current = false;
    forgetAllJobs();
    dispatch({ type: "reset" });
  }, [abortAll, resetSaves]);

  const previousCastGeneration = useRef(castGeneration);
  useEffect(() => {
    const previous = previousCastGeneration.current;
    previousCastGeneration.current = castGeneration;
    if (castGeneration === "running" && previous !== "running") resetPlay();
    // the backend started the new play only once the cast was generated
    if (castGeneration !== "running" && previous === "running") resetPlay();
  }, [castGeneration, resetPlay]);

  // On page load and after a new cast: read the Story Bible, so every page restores its state from the backend.
  useEffect(() => {
    if (state.loaded || loading.current || castGeneration === "running") return;
    loading.current = true;
    const from = epoch.current;
    api
      .getStory()
      .then((story) => {
        if (from === epoch.current) dispatch({ type: "storyLoaded", story });
      })
      .catch((error: unknown) => {
        if (from === epoch.current) showError(error);
      })
      .finally(() => {
        if (from === epoch.current) loading.current = false;
      });
  }, [state.loaded, castGeneration, showError]);

  // ---------- generations ----------

  const generateOutline = useCallback(() => {
    void runStoryJob("outline", (signal) => api.generateOutline({ signal }));
  }, [runStoryJob]);

  const stageAct = useCallback(
    (n: number) => {
      void runStoryJob(`structure:${n}`, (signal) => api.generateStructure(n, { signal }));
    },
    [runStoryJob],
  );

  const planScene = useCallback(
    (n: number, scene: number) => {
      void runStoryJob(`plan:${n}:${scene}`, (signal) => api.planScene(n, scene, { signal }));
    },
    [runStoryJob],
  );

  // The steps that follow on their own while the play is open: the outline is written, the act that can be
  // built next is staged, and the next scene is planned once the one before it is approved. A step that
  // failed is not repeated on its own; the user starts it again.
  const onPlay = location.pathname.startsWith(paths.play);
  useEffect(() => {
    const { loaded, story, jobs, failed } = state;
    if (!onPlay || !loaded || !story) return;
    const idle = (key: JobKey) => !jobs.includes(key) && !failed.includes(key) && !isRunning(key);
    if (!story.outline) {
      if (idle("outline")) generateOutline();
      return;
    }
    const act = currentAct(story);
    if (!act) return;
    if (act.status === "draft" && act.scenes.length === 0) {
      if (idle(`structure:${act.number}`)) stageAct(act.number);
      return;
    }
    const scene = nextSceneToPlan(act);
    const busy = jobs.some((key) => key.startsWith(`plan:${act.number}:`) || key.startsWith(`scene:${act.number}:`));
    if (scene !== null && !busy && idle(`plan:${act.number}:${scene}`)) planScene(act.number, scene);
  }, [state, onPlay, isRunning, generateOutline, stageAct, planScene]);

  // ---------- chat ----------

  // Every page opens with the chat closed; the user opens it with the button in the header.
  useEffect(() => {
    dispatch({ type: "chatClosed" });
  }, [location.pathname]);

  const chatOpened = useCallback(
    (key: ChatKey) => {
      if (stateRef.current.chats[key] || historyRequested.current.has(key)) return;
      historyRequested.current.add(key);
      const from = epoch.current;
      const request =
        key === "outline" ? api.getOutlineChat() : key === "acts" ? api.getActsChat() : api.getActChat(Number(key.slice(4)));
      request
        .then((history) => {
          if (from === epoch.current) dispatch({ type: "chatLoaded", key, messages: toBubbles(history) });
        })
        .catch((error: unknown) => {
          historyRequested.current.delete(key);
          if (from === epoch.current) showError(error);
        });
    },
    [showError],
  );

  const highlightTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(highlightTimer.current), []);

  /** Puts an edit into the fields at once, so a save started right after it sends it. */
  const apply = useCallback((action: Action) => {
    dispatch(action);
    stateRef.current = reducer(stateRef.current, action);
  }, []);

  /**
   * Sends the draft to the agent of the page with the data as it is in the fields. When the agent applies
   * changes, its answer carries the changed data: the changed parts are put into the fields, saved and glow.
   */
  const sendMessage = useCallback(
    async ({ kind, act: n }: ChatContext) => {
      const { draft, story, typing } = stateRef.current;
      const text = draft.trim();
      if (!text || typing || !story) return;
      const key = chatKey(kind, n);
      dispatch({ type: "messageSent", key, text });

      const from = epoch.current;
      try {
        const revision = await revisers[kind](story, text, story.acts.find((item) => item.number === n));
        if (from !== epoch.current) return;
        if (!revision) {
          dispatch({ type: "replyFailed", key });
          return;
        }
        if (revision.places) dispatch({ type: "placesReceived", places: revision.places });
        for (const edit of revision.edits) {
          apply(edit.action);
          edited(edit.key, 0);
        }
        dispatch({ type: "replyReceived", key, text: revision.reply, updated: revision.updated, highlight: revision.highlight });
        if (revision.highlight.length) {
          clearTimeout(highlightTimer.current);
          highlightTimer.current = setTimeout(() => dispatch({ type: "clearHighlight" }), HIGHLIGHT_MS);
        }
      } catch (error) {
        if (from !== epoch.current) return;
        dispatch({ type: "replyFailed", key });
        showError(error);
      }
    },
    [apply, edited, showError],
  );

  // ---------- outline and acts ----------

  const story = () => stateRef.current.story;
  const findAct = (n: number) => story()?.acts.find((act) => act.number === n);

  const editOutline = useCallback(
    (patch: Partial<Outline>) => {
      dispatch({ type: "outlineEdited", patch });
      edited("outline");
    },
    [edited],
  );

  const approveOutline = useCallback(async () => {
    await flush("outline");
    void runStoryJob("acts", (signal) => api.generateActs({ signal }));
  }, [flush, runStoryJob]);

  const editActSummary = useCallback(
    (n: number, summary: string) => {
      dispatch({ type: "actEdited", number: n, summary });
      edited(`act:${n}`);
    },
    [edited],
  );

  /** Drafts the acts again, before they are approved. */
  const redraftActs = useCallback(async () => {
    await flushAll("act:");
    void runStoryJob("acts", (signal) => api.generateActs({ signal }));
  }, [flushAll, runStoryJob]);

  const approveActs = useCallback(async () => {
    await flushAll("act:");
    void runStoryJob("approveActs", () => api.approveActs());
  }, [flushAll, runStoryJob]);

  // ---------- one act: structure ----------

  const restructure = useCallback(
    (n: number, change: (scenes: Scene[]) => Scene[], delay?: number) => {
      const act = findAct(n);
      if (!act) return;
      dispatch({ type: "scenesEdited", number: n, scenes: change(act.scenes) });
      edited(`scenes:${n}`, delay);
    },
    [edited],
  );

  const approveStructure = useCallback(
    async (n: number) => {
      await flush(`scenes:${n}`);
      void runStoryJob(`approveStructure:${n}`, () => api.approveStructure(n));
    },
    [flush, runStoryJob],
  );

  // ---------- one act: scene plans ----------

  const editScenePlan = useCallback(
    (n: number, scene: number, patch: Partial<ScenePlan>) => {
      dispatch({ type: "sceneEdited", number: n, scene, patch });
      edited(`scene:${n}:${scene}`);
    },
    [edited],
  );

  const approveScene = useCallback(
    async (n: number, scene: number) => {
      await flush(`scene:${n}:${scene}`);
      void runStoryJob(`scene:${n}:${scene}`, () => api.approveScene(n, scene));
    },
    [flush, runStoryJob],
  );

  const reopenScene = useCallback(
    async (n: number, scene: number) => {
      await flush(`scene:${n}:${scene}`);
      void runStoryJob(`scene:${n}:${scene}`, () => api.reopenScene(n, scene));
    },
    [flush, runStoryJob],
  );

  const createPlace = useCallback(
    async (draft: PlaceDraft) => {
      const place = await runJob("place", () => api.createPlace(draft));
      if (!place) return null;
      dispatch({ type: "placesReceived", places: [...(story()?.places ?? []), place] });
      return place;
    },
    [runJob],
  );

  const actOpened = useCallback(
    (n: number) => {
      chatOpened(`act:${n}`);
      const from = epoch.current;
      api
        .getPlaces()
        .then((places) => {
          if (from === epoch.current) dispatch({ type: "placesReceived", places });
        })
        .catch(showError);
    },
    [chatOpened, showError],
  );

  // ---------- one act: text ----------

  /** Writes the text; remembered in the tab, so a reload in between starts it again. */
  const startWriting = useCallback(
    async (n: number) => {
      rememberJob(`text:${n}`);
      const done = await runStoryJob(`text:${n}`, (signal) => api.generateText(n, { signal }));
      // a reload cancelled it: it stays remembered and starts again on the next load
      if (isUnloading()) return;
      forgetJob(`text:${n}`);
      if (done) {
        // the backend starts the act page's chat anew with the new text
        historyRequested.current.delete(`act:${n}`);
        dispatch({ type: "chatCleared", key: `act:${n}` });
      }
    },
    [runStoryJob, isUnloading],
  );

  const writeText = useCallback(
    async (n: number) => {
      await flushAll(`scene:${n}:`, `scenes:${n}`);
      dispatch({ type: "setEditingScenes", number: n, editing: false });
      navigate(paths.play);
      void startWriting(n);
    },
    [flushAll, navigate, startWriting],
  );

  const editSceneText = useCallback(
    (n: number, scene: number, text: string) => {
      const act = findAct(n);
      if (!act) return;
      const sceneTexts = act.scene_texts.map((item) => (item.scene_number === scene ? { ...item, text } : item));
      dispatch({ type: "sceneTextsEdited", number: n, sceneTexts });
      edited(`text:${n}`, 800);
    },
    [edited],
  );

  /** Approves the text and records the histories; remembered in the tab like writing. */
  const startRecording = useCallback(
    async (n: number) => {
      rememberJob(`record:${n}`);
      await runStoryJob(`record:${n}`, (signal) => api.approveText(n, { signal }));
      if (!isUnloading()) forgetJob(`record:${n}`);
    },
    [runStoryJob, isUnloading],
  );

  const approveText = useCallback(
    async (n: number) => {
      await flush(`text:${n}`);
      void startRecording(n);
    },
    [flush, startRecording],
  );

  // After a reload: start again what the reload cancelled, if the act still needs it.
  const resumed = useRef(false);
  useEffect(() => {
    if (!state.loaded || !state.story || resumed.current) return;
    resumed.current = true;
    for (const job of resumableJobs()) {
      const [kind, value] = job.split(":");
      const act = state.story.acts.find((item) => item.number === Number(value));
      if (act?.status !== "scenes_approved") forgetJob(job);
      else if (kind === "text") void startWriting(act.number);
      else if (act.scene_texts.length > 0) void startRecording(act.number);
      else forgetJob(job);
    }
  }, [state.loaded, state.story, startWriting, startRecording]);

  // ---------- public actions ----------

  const actions = useMemo<StoryActions>(
    () => ({
      chatOpened,
      actOpened,
      toggleChat: () => dispatch({ type: "toggleChat" }),
      setDraft: (draft) => dispatch({ type: "setDraft", draft }),
      sendMessage,
      generateOutline,
      editOutline,
      approveOutline: () => void approveOutline(),
      editActSummary,
      redraftActs: () => void redraftActs(),
      approveActs: () => void approveActs(),
      stageAct,
      openAct: (n) => navigate(paths.act(n)),
      goToPlay: () => navigate(paths.play),
      moveScene: (n, index, step) => restructure(n, (scenes) => moveScene(scenes, index, step), 300),
      cutScene: (n, index) => restructure(n, (scenes) => cutScene(scenes, index), 300),
      addScene: (n) => restructure(n, addBlankScene, 300),
      editStructureScene: (n, index, patch) =>
        restructure(n, (scenes) => scenes.map((scene, i) => (i === index ? { ...scene, ...patch } : scene))),
      approveStructure: (n) => void approveStructure(n),
      editScenePlan,
      approveScene: (n, scene) => void approveScene(n, scene),
      reopenScene: (n, scene) => void reopenScene(n, scene),
      createPlace,
      setEditingScenes: (n, editing) => dispatch({ type: "setEditingScenes", number: n, editing }),
      writeText: (n) => void writeText(n),
      editSceneText,
      approveText: (n) => void approveText(n),
    }),
    [
      chatOpened, actOpened, sendMessage, generateOutline, editOutline, approveOutline, editActSummary, redraftActs, approveActs,
      stageAct, navigate, restructure, approveStructure, editScenePlan, approveScene, reopenScene, createPlace,
      writeText, editSceneText, approveText,
    ],
  );

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}
