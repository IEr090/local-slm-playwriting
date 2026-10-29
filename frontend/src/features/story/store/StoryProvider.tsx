// Story Bible store provider: one reducer + async actions. It sits above the routes, so a generation keeps
// running while the user moves between the play page and an act page; requests are aborted only when a new
// cast replaces the play. Data only ever comes from `api`; errors go to the shared error banner.

import { useCallback, useEffect, useLayoutEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import { useCastState } from "@/features/characters/store/cast-context";
import { api } from "@/features/story/api";
import { changedActNumbers, changedBlocks, changedOutlineFields, changedSceneIndexes, changedSceneTextNumbers } from "@/features/story/model/diff";
import { actName, OUTLINE_FIELD_LABEL } from "@/features/story/model/labels";
import { withLocalEdits, type EditKey } from "@/features/story/model/local-edits";
import { currentAct, nextSceneToPlan } from "@/features/story/model/progress";
import { addBlankScene, cutScene, moveScene, toPlan, toScenes } from "@/features/story/model/scenes";
import { aboutLabel, predictTargets } from "@/features/story/model/targets";
import type { HistoryMessage, Outline, PlaceDraft, Scene, ScenePlan, StoryBible } from "@/features/story/model/types";
import { paths } from "@/features/story/paths";
import { isAbort } from "@/shared/api/errors";
import { useErrors } from "@/shared/errors/errors-context";
import type { ChatBubble } from "@/shared/ui/chat/ChatMessage";
import { forgetAllJobs, forgetJob, rememberJob, resumableJobs } from "./resumable";
import { ActionsContext, StateContext, type ChatContext, type StoryActions } from "./story-context";
import { initialState, reducer, type ChatKey, type JobKey } from "./story-reducer";

/** How long changed fields glow after an AI revision. */
const HIGHLIGHT_MS = 2600;
/** Typing pause before a hand edit is saved. */
const SAVE_DELAY_MS = 600;

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

  // ---------- local edits and saving ----------

  const editVersion = useRef(new Map<EditKey, number>());
  const savedVersion = useRef(new Map<EditKey, number>());
  const saveTimers = useRef(new Map<EditKey, ReturnType<typeof setTimeout>>());
  const saveChains = useRef(new Map<EditKey, Promise<void>>());

  const dirtyKeys = useCallback(
    () => [...editVersion.current].filter(([key, v]) => v > (savedVersion.current.get(key) ?? 0)).map(([key]) => key),
    [],
  );

  /** Takes the Story Bible the backend answered with, keeping what the user has typed since. */
  const receive = useCallback(
    (server: StoryBible, from: number) => {
      if (from !== epoch.current) return;
      const story = withLocalEdits(server, stateRef.current.story, dirtyKeys());
      stateRef.current = { ...stateRef.current, story };
      dispatch({ type: "storyReceived", story });
    },
    [dirtyKeys],
  );

  /** Sends the local version of one edited part to the backend. */
  const performSave = useCallback(async (key: EditKey): Promise<StoryBible | null> => {
    const story = stateRef.current.story;
    if (!story) return null;
    if (key === "outline") return story.outline ? api.saveOutline(story.outline) : null;
    const [kind, value, sceneValue] = key.split(":");
    const act = story.acts.find((item) => item.number === Number(value));
    if (!act) return null;
    switch (kind) {
      case "act":
        return api.saveAct(act.number, act.summary, act.dramatic_function);
      case "scenes":
        return api.saveStructure(act.number, act.scenes.map(toPlan));
      case "scene": {
        const scene = act.scenes.find((item) => item.number === Number(sceneValue));
        return scene ? api.saveScene(act.number, scene.number, toPlan(scene)) : null;
      }
      default:
        return api.saveText(act.number, act.scene_texts);
    }
  }, []);

  /** Saves one part now (one save per part at a time, in order). Resolves when it is saved or failed. */
  const flush = useCallback(
    (key: EditKey): Promise<void> => {
      clearTimeout(saveTimers.current.get(key));
      saveTimers.current.delete(key);
      const from = epoch.current;
      const previous = saveChains.current.get(key) ?? Promise.resolve();
      const next = previous.then(async () => {
        const version = editVersion.current.get(key) ?? 0;
        if (from !== epoch.current || version <= (savedVersion.current.get(key) ?? 0)) return;
        try {
          const server = await performSave(key);
          savedVersion.current.set(key, Math.max(version, savedVersion.current.get(key) ?? 0));
          if (server) receive(server, from);
        } catch (error) {
          // the edit stays local; the next edit or step saves it again
          if (from === epoch.current) showError(error);
        }
      });
      saveChains.current.set(key, next);
      return next;
    },
    [performSave, receive, showError],
  );

  /** Saves every edited part whose key starts with one of the prefixes ("" = all). */
  const flushAll = useCallback(
    (...prefixes: string[]) =>
      Promise.all(dirtyKeys().filter((key) => prefixes.some((p) => key.startsWith(p))).map(flush)).then(() => undefined),
    [dirtyKeys, flush],
  );

  /** A part was edited locally: save it after a pause (or at once). */
  const edited = useCallback(
    (key: EditKey, delay = SAVE_DELAY_MS) => {
      editVersion.current.set(key, (editVersion.current.get(key) ?? 0) + 1);
      clearTimeout(saveTimers.current.get(key));
      saveTimers.current.set(key, setTimeout(() => void flush(key), delay));
    },
    [flush],
  );

  // ---------- long requests ----------

  const running = useRef(new Set<JobKey>());
  const controllers = useRef(new Map<JobKey, AbortController>());

  // A reload or a closed tab cancels the running requests: that is not a failure to report or to forget.
  const unloading = useRef(false);
  useEffect(() => {
    const leave = () => {
      unloading.current = true;
    };
    // back from the back-forward cache: the page lives on
    const back = () => {
      unloading.current = false;
    };
    window.addEventListener("pagehide", leave);
    window.addEventListener("beforeunload", leave);
    window.addEventListener("pageshow", back);
    return () => {
      window.removeEventListener("pagehide", leave);
      window.removeEventListener("beforeunload", leave);
      window.removeEventListener("pageshow", back);
    };
  }, []);

  /**
   * Runs one request at a time per key; the key is shown as running (veils, disabled buttons) until it ends.
   * Resolves to the answer, or undefined if it failed (banner) or was aborted.
   */
  const runJob = useCallback(
    async <T,>(key: JobKey, work: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> => {
      if (running.current.has(key)) return undefined;
      const from = epoch.current;
      const controller = new AbortController();
      running.current.add(key);
      controllers.current.set(key, controller);
      dispatch({ type: "jobStarted", key });
      try {
        const result = await work(controller.signal);
        if (controller.signal.aborted || from !== epoch.current) return undefined;
        dispatch({ type: "jobEnded", key });
        return result;
      } catch (error) {
        if (isAbort(error) || controller.signal.aborted || from !== epoch.current || unloading.current) return undefined;
        dispatch({ type: "jobEnded", key, failed: true });
        showError(error);
        return undefined;
      } finally {
        if (controllers.current.get(key) === controller) {
          running.current.delete(key);
          controllers.current.delete(key);
        }
      }
    },
    [showError],
  );

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
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
    running.current.clear();
    saveTimers.current.forEach((timer) => clearTimeout(timer));
    saveTimers.current.clear();
    saveChains.current.clear();
    editVersion.current.clear();
    savedVersion.current.clear();
    historyRequested.current.clear();
    loading.current = false;
    forgetAllJobs();
    dispatch({ type: "reset" });
  }, []);

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
    const idle = (key: JobKey) => !jobs.includes(key) && !failed.includes(key) && !running.current.has(key);
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
  }, [state, onPlay, generateOutline, stageAct, planScene]);

  // ---------- chat ----------

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

  /**
   * Sends the draft to the agent of the page with the data as it is in the fields. When the agent applies
   * changes, its answer carries the changed data: the changed parts are put into the fields, saved and glow.
   */
  const sendMessage = useCallback(
    async ({ kind, act: n }: ChatContext) => {
      const { draft, story, typing, chats } = stateRef.current;
      const text = draft.trim();
      if (!text || typing || !story) return;
      const key: ChatKey = kind === "outline" ? "outline" : kind === "acts" ? "acts" : `act:${n ?? 0}`;
      const act = story.acts.find((item) => item.number === n);
      const counts = { acts: story.acts.length, scenes: act?.scenes.length ?? 0 };
      const history = [...(chats[key] ?? [])].reverse();
      const lastReply = history.find((m) => m.role === "ai")?.text ?? "";
      const previousMessage = history.find((m) => m.role === "user")?.text ?? "";
      const pending = predictTargets(kind, text, lastReply, counts, previousMessage).map((target) => {
        if (kind === "outline") return `outline:${target}`;
        if (kind === "acts") return target;
        return target === "add" ? `add:${n}` : `scene:${n}:${target.slice(6)}`;
      });
      dispatch({ type: "messageSent", key, text, about: aboutLabel(kind, text, counts), pending });

      const from = epoch.current;
      const updated: string[] = [];
      const highlight: string[] = [];
      try {
        if (kind === "outline" && story.outline) {
          const sent = story.outline;
          const result = await api.reviseOutline(sent, text);
          if (from !== epoch.current) return;
          const fields = changedOutlineFields(sent, result.outline);
          if (fields.length) {
            const patch = Object.fromEntries(fields.map((f) => [f, result.outline[f]])) as Partial<Outline>;
            dispatch({ type: "outlineEdited", patch });
            stateRef.current = reducer(stateRef.current, { type: "outlineEdited", patch });
            edited("outline", 0);
          }
          updated.push(...fields.map((f) => OUTLINE_FIELD_LABEL[f]));
          highlight.push(...fields.map((f) => `outline:${f}`));
          dispatch({ type: "replyReceived", key, text: result.reply, updated, highlight });
        } else if (kind === "acts") {
          const sent = story.acts.map(({ number, summary, dramatic_function }) => ({ number, summary, dramatic_function }));
          const result = await api.reviseActs(sent, text);
          if (from !== epoch.current) return;
          for (const number of changedActNumbers(sent, result.acts)) {
            const revised = result.acts.find((item) => item.number === number)!;
            const action = { type: "actEdited" as const, number, summary: revised.summary, dramatic_function: revised.dramatic_function };
            dispatch(action);
            stateRef.current = reducer(stateRef.current, action);
            edited(`act:${number}`, 0);
            const before = sent.find((item) => item.number === number)!;
            updated.push(before.dramatic_function !== revised.dramatic_function ? `${actName(number)} · dramatic function` : actName(number));
            highlight.push(`act:${number}`);
          }
          dispatch({ type: "replyReceived", key, text: result.reply, updated, highlight });
        } else if ((kind === "structure" || kind === "scenes") && act && n !== undefined) {
          const sent = act.scenes.map(toPlan);
          const result =
            kind === "structure" ? await api.reviseStructure(n, sent, text) : await api.reviseScenes(n, sent, text);
          if (from !== epoch.current) return;
          dispatch({ type: "placesReceived", places: result.places });
          const changed = changedSceneIndexes(sent, result.scenes);
          if (kind === "structure" && (changed.length || result.scenes.length !== sent.length)) {
            const action = { type: "scenesEdited" as const, number: n, scenes: toScenes(result.scenes) };
            dispatch(action);
            stateRef.current = reducer(stateRef.current, action);
            edited(`scenes:${n}`, 0);
            if (result.scenes.length < sent.length) updated.push(`${sent.length - result.scenes.length} scene(s) cut`);
          }
          if (kind === "scenes") {
            for (const i of changed) {
              const plan = result.scenes[i];
              if (!act.scenes[i]) continue;
              const action = { type: "sceneEdited" as const, number: n, scene: i + 1, patch: toPlan(plan) };
              dispatch(action);
              stateRef.current = reducer(stateRef.current, action);
              edited(`scene:${n}:${i + 1}`, 0);
            }
          }
          updated.unshift(...changed.map((i) => `Scene ${i + 1}`));
          highlight.push(...changed.map((i) => `scene:${n}:${i + 1}`));
          dispatch({ type: "replyReceived", key, text: result.reply, updated, highlight });
        } else if (kind === "text" && act && n !== undefined) {
          const sent = act.scene_texts;
          const result = await api.reviseText(n, sent, text);
          if (from !== epoch.current) return;
          const numbers = changedSceneTextNumbers(sent, result.scene_texts);
          if (numbers.length) {
            const sceneTexts = sent.map((item) =>
              numbers.includes(item.scene_number) ? result.scene_texts.find((r) => r.scene_number === item.scene_number)! : item,
            );
            const action = { type: "sceneTextsEdited" as const, number: n, sceneTexts };
            dispatch(action);
            stateRef.current = reducer(stateRef.current, action);
            edited(`text:${n}`, 0);
          }
          for (const number of numbers) {
            const before = sent.find((item) => item.scene_number === number)!.text;
            const after = result.scene_texts.find((item) => item.scene_number === number)!.text;
            updated.push(`Scene ${number} · text`);
            highlight.push(...changedBlocks(before, after).map((i) => `block:${n}:${number}:${i}`));
          }
          dispatch({ type: "replyReceived", key, text: result.reply, updated, highlight });
        } else {
          dispatch({ type: "replyFailed", key });
          return;
        }
        if (highlight.length) {
          clearTimeout(highlightTimer.current);
          highlightTimer.current = setTimeout(() => dispatch({ type: "clearHighlight" }), HIGHLIGHT_MS);
        }
      } catch (error) {
        if (from !== epoch.current) return;
        dispatch({ type: "replyFailed", key });
        showError(error);
      }
    },
    [edited, showError],
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
      if (unloading.current) return;
      forgetJob(`text:${n}`);
      if (done) {
        // the backend starts the act page's chat anew with the new text
        historyRequested.current.delete(`act:${n}`);
        dispatch({ type: "chatCleared", key: `act:${n}` });
      }
    },
    [runStoryJob],
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
      if (!unloading.current) forgetJob(`record:${n}`);
    },
    [runStoryJob],
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
