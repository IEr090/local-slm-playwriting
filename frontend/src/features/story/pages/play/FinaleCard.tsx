import { playSummary } from "@/features/story/model/play-reader";
import { ArrowRight } from "@/shared/ui/icons";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { Orb } from "@/shared/ui/Orb";

interface FinaleCardProps {
  title: string;
  acts: number;
  scenes: number;
  onRead(): void;
}

/** Under the act cards once every act is approved: the way to the whole play. */
export function FinaleCard({ title, acts, scenes, onRead }: FinaleCardProps) {
  return (
    <section
      aria-label="The play is written"
      className="relative mt-[14px] animate-fade-up rounded-[10px] border border-gold/60 bg-[radial-gradient(ellipse_600px_260px_at_50%_0%,#211a0f_0%,#141109_70%)] px-10 pt-12 pb-11 text-center shadow-[0_0_40px_rgba(201,162,75,.12)]"
    >
      <Orb className="mx-auto mb-5" />
      <div className="font-sans text-[11px] tracking-[2px] text-muted-2">THE PLAY IS WRITTEN</div>
      <h2 className="mt-3 mb-0 font-serif text-[46px] leading-none font-medium">{title}</h2>
      <p className="mx-auto mt-[14px] mb-7 max-w-[560px] font-sans text-[14px] leading-[1.6] text-ink-2">
        {playSummary(acts, scenes)}
        <br />
        Read it from the first line to the curtain, or edit any line.
      </p>
      <HeaderPill onClick={onRead} className="h-[54px] px-8 text-[12px] tracking-[3px] hover:shadow-[0_0_24px_rgba(201,162,75,.3)]">
        <span>READ THE WHOLE PLAY</span>
        <ArrowRight size={16} />
      </HeaderPill>
    </section>
  );
}
