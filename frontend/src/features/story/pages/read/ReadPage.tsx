import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { activeSection, readerSub, TITLE_SECTION } from "@/features/story/model/play-reader";
import { paths } from "@/features/story/paths";
import { isChanged } from "@/features/story/store/play-reader-reducer";
import { usePlayReader } from "@/features/story/store/use-play-reader";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { ArrowLeft, Lock, Unlock } from "@/shared/ui/icons";
import { RoundIconButton } from "@/shared/ui/RoundIconButton";
import { StoryHeader } from "../StoryHeader";
import { Contents } from "./Contents";
import { PlayManuscript } from "./PlayManuscript";

/** How far below the top edge of the reading area a section counts as "the one being read". */
const SPY_MARGIN = 140;
/** Space left above a section the contents scroll to. */
const SCROLL_GAP = 24;

/** Page "/play/read": the finished play to read from the title page to the curtain, and to edit line by line. */
export function ReadPage() {
  const navigate = useNavigate();
  const { state, editLine, flushScene, flushAll } = usePlayReader();
  const { play } = state;
  const [unlocked, setUnlocked] = useState(false);
  const [active, setActive] = useState(TITLE_SECTION);
  const readRef = useRef<HTMLElement>(null);
  const frame = useRef(0);

  /** Finds the section at the top of the reading area (the positions are measured, so they follow the layout). */
  const spy = useCallback(() => {
    const read = readRef.current;
    if (!read) return;
    const origin = read.getBoundingClientRect().top - read.scrollTop;
    const sections = [...read.querySelectorAll<HTMLElement>("[data-sec]")].map((el) => ({
      id: el.dataset.sec ?? "",
      top: el.getBoundingClientRect().top - origin,
    }));
    setActive(activeSection(sections, read.scrollTop, SPY_MARGIN));
  }, []);

  const onScroll = () => {
    if (frame.current) return;
    frame.current = requestAnimationFrame(() => {
      frame.current = 0;
      spy();
    });
  };
  useEffect(() => () => cancelAnimationFrame(frame.current), []);
  // the text is there (or has grown): measure again
  useEffect(() => {
    if (play) spy();
  }, [play, spy]);

  const goTo = (section: string) => {
    const read = readRef.current;
    const target = read?.querySelector<HTMLElement>(`[data-sec="${section}"]`);
    if (!read || !target) return;
    const top = target.getBoundingClientRect().top - read.getBoundingClientRect().top + read.scrollTop - SCROLL_GAP;
    read.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  };

  const toggleLock = () => {
    // locking the text again saves what is still waiting
    if (unlocked) void flushAll();
    setUnlocked(!unlocked);
  };
  const lockLabel = unlocked ? "Lock the text" : "Unlock the text to edit it";

  return (
    <div className="absolute inset-0 flex">
      <div className="relative flex min-w-0 flex-1 flex-col bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]">
        <StoryHeader eyebrow="THE PLAY" tag={unlocked ? "EDITING" : undefined} title={play?.title ?? ""} sub={play ? readerSub(unlocked) : ""} status={unlocked}>
          <HeaderPill ghost onClick={() => navigate(paths.play)}>
            <ArrowLeft />
            <span>ALL ACTS</span>
          </HeaderPill>
          <HeaderPill ghost disabled title="PDF export comes later">
            EXPORT PDF
          </HeaderPill>
          <RoundIconButton
            active={unlocked}
            onClick={toggleLock}
            aria-pressed={unlocked}
            aria-label={lockLabel}
            title={lockLabel}
            className={unlocked ? "shadow-[0_0_18px_rgba(201,162,75,.25)]" : undefined}
          >
            {unlocked ? <Unlock /> : <Lock />}
          </RoundIconButton>
        </StoryHeader>

        {play && (
          <div className="flex min-h-0 flex-1 max-[900px]:flex-col">
            <Contents play={play} active={active} onGo={goTo} />
            <main
              ref={readRef}
              aria-label="The text of the play"
              onScroll={onScroll}
              className="scroll-thin relative min-w-0 flex-1 overflow-y-auto px-12 pt-9 pb-24 max-[900px]:p-4"
            >
              <PlayManuscript
                play={play}
                editing={unlocked}
                isChanged={(act, scene, index) => isChanged(state, act, scene, index)}
                onEdit={editLine}
                onBlur={flushScene}
              />
            </main>
          </div>
        )}
      </div>
    </div>
  );
}
