// Block 1 placeholder: a style sheet of tokens and shared components. Replaced by the screens in block 2.
import { Orb } from "@/components/brand/Orb";
import { Chip } from "@/components/common/Chip";
import { DottedRule } from "@/components/common/DottedRule";
import { ArrowRight, ChevronLeft, ChevronRight, Spark } from "@/components/common/icons";
import { GoldPill, Pill } from "@/components/common/Pill";
import { RoundIconButton } from "@/components/common/RoundIconButton";

const SWATCHES = [
  "bg", "panel", "card", "card-focus", "line", "line-strong", "line-hover", "line-subtle",
  "gold", "gold-soft", "gold-light", "terracotta", "ink", "ink-2", "ink-3", "muted", "muted-2", "faint",
];

export default function App() {
  return (
    <main className="min-h-screen space-y-10 p-12">
      <div className="flex items-center gap-6">
        <Orb />
        <Orb variant="mini" />
        <h1 className="font-serif text-[44px] font-medium">Dramatis Personae</h1>
      </div>

      <div className="flex flex-wrap gap-3">
        {SWATCHES.map((name) => (
          <div key={name} className="w-24 text-[10px] tracking-[1.5px] text-faint uppercase">
            <div className="mb-1 h-10 rounded-[10px] border border-line-subtle" style={{ background: `var(--color-${name})` }} />
            {name}
          </div>
        ))}
      </div>

      <DottedRule className="w-[420px]" />

      <div className="flex items-center gap-4">
        <Pill>← New premise</Pill>
        <Pill>+ Add character</Pill>
        <GoldPill>GENERATE CHARACTERS <ArrowRight /></GoldPill>
        <RoundIconButton aria-label="Previous character"><ChevronLeft /></RoundIconButton>
        <RoundIconButton aria-label="Next character"><ChevronRight /></RoundIconButton>
        <RoundIconButton active aria-label="Hide AI chat"><Spark /></RoundIconButton>
      </div>

      <div className="flex gap-[6px]">
        <Chip selected>PROTAGONIST</Chip>
        <Chip>ANTAGONIST</Chip>
        <Chip>CONFIDANT</Chip>
      </div>

      <p className="shimmer-text text-[11px] tracking-[3px]">UPDATING CARD</p>
    </main>
  );
}
