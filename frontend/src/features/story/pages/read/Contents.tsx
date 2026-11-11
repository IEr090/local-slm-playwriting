import { useEffect, useRef, type ReactNode } from "react";
import { actName } from "@/features/story/model/labels";
import {
  actOfSection,
  actSection,
  CAST_SECTION,
  contentsTotals,
  sceneSection,
  TITLE_SECTION,
} from "@/features/story/model/play-reader";
import type { Play } from "@/features/story/model/types";
import { cn } from "@/shared/lib/utils";

interface ContentsProps {
  play: Play;
  /** The section at the top of the reading area. */
  active: string;
  onGo(section: string): void;
}

/** The contents on the left: title page, cast, every act with its scenes. The highlighted entry stays in view. */
export function Contents({ play, active, onGo }: ContentsProps) {
  const ref = useRef<HTMLElement>(null);
  const activeAct = actOfSection(active);

  // with many acts the column scrolls: keep the highlighted entry in view
  useEffect(() => {
    const nav = ref.current;
    const entry = nav?.querySelector<HTMLElement>(`[data-toc="${active}"]`);
    if (!nav || !entry) return;
    const box = nav.getBoundingClientRect();
    const rect = entry.getBoundingClientRect();
    const top = rect.top - box.top;
    const bottom = rect.bottom - box.top;
    const margin = 24;
    const sticky = 60;
    if (top < sticky) nav.scrollTo({ top: nav.scrollTop + top - sticky, behavior: "smooth" });
    else if (bottom > nav.clientHeight - margin) nav.scrollTo({ top: nav.scrollTop + bottom - nav.clientHeight + margin, behavior: "smooth" });
  }, [active]);

  const entry = (id: string, className: string, children: ReactNode, idle = "text-ink-2") => (
    <button
      key={id}
      type="button"
      data-toc={id}
      aria-current={active === id ? "location" : undefined}
      onClick={() => onGo(id)}
      className={cn(
        "flex w-full items-baseline gap-[10px] rounded-lg border-none bg-transparent px-[10px] text-left transition-[background-color,color] duration-150",
        "hover:bg-card hover:text-ink",
        active === id ? "bg-gold/10 text-gold-light hover:bg-gold/10 hover:text-gold-light" : idle,
        className,
      )}
    >
      {children}
    </button>
  );

  return (
    <nav
      ref={ref}
      aria-label="Contents"
      className="scroll-thin box-border h-full min-h-0 flex-[0_0_300px] overflow-y-auto overscroll-contain border-r border-dotted border-line-strong pr-5 pb-10 pl-7 max-[900px]:h-auto max-[900px]:max-h-[220px] max-[900px]:flex-none max-[900px]:border-r-0 max-[900px]:border-b max-[900px]:p-4"
    >
      <div className="sticky top-0 z-[1] -mr-1 bg-gradient-to-b from-[#0d0b08] from-75% to-transparent pt-[26px] pb-3">
        <div className="font-sans text-[11px] tracking-[2px] text-muted-2">CONTENTS</div>
      </div>

      <div className="mt-[18px]">
        {entry(TITLE_SECTION, "py-[7px] font-serif text-[18px]", "Title page")}
        {entry(CAST_SECTION, "py-[7px] font-serif text-[18px]", "Dramatis Personae")}
      </div>

      {play.acts.map((act) => (
        <div key={act.number} className="mt-[18px]">
          {entry(
            actSection(act.number),
            cn("py-[7px] font-serif text-[21px] font-medium", activeAct === act.number && active !== actSection(act.number) && "text-gold-light"),
            actName(act.number),
          )}
          <div className="mt-[2px] mb-2 ml-3">
            {act.scenes.map((scene) =>
              entry(
                sceneSection(act.number, scene.number),
                "py-[5px] font-sans text-[13px] leading-[1.35]",
                <>
                  <span className="w-[14px] shrink-0 text-[11px] text-gold">{scene.number}</span>
                  <span>{scene.place_name}</span>
                </>,
                "text-muted",
              ),
            )}
          </div>
        </div>
      ))}

      <div className="mt-8 pl-[10px] font-sans text-[11px] leading-[1.9] tracking-[1.5px] text-muted-2">{contentsTotals(play)}</div>
    </nav>
  );
}
