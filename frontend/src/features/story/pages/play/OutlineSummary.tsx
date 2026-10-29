import { genreLabel } from "@/features/story/model/labels";
import type { Outline } from "@/features/story/model/types";
import { HeaderPill } from "@/shared/ui/HeaderPill";

/** The approved outline, collapsed into the left column next to the acts. */
export function OutlineSummary({ outline: o, onEdit }: { outline: Outline; onEdit(): void }) {
  const rows: [string, string, string][] = [
    ["TONE", o.tone, "line-clamp-4"],
    ["TIME & WORLD", o.time_and_world, "line-clamp-4"],
    ["CONFLICT", o.central_conflict, "line-clamp-4"],
    ["SYNOPSIS", o.synopsis, "line-clamp-7"],
  ];
  return (
    <>
      <div className="flex items-center justify-between gap-[10px]">
        <span className="font-sans text-[11px] tracking-[2px] text-muted-2">THE PLAY</span>
        <HeaderPill ghost small onClick={onEdit}>
          EDIT OUTLINE
        </HeaderPill>
      </div>
      <h2 className="mt-[14px] mb-0 font-serif text-[32px] leading-[1.05] font-medium">{o.title || "Untitled play"}</h2>
      <div className="mt-[10px] font-serif text-[19px] leading-[1.3] text-gold-soft italic">{o.premise}</div>
      <div className="dotted-rule mt-5 mb-4" />
      <SummaryRow label="GENRE">{genreLabel(o.genre)}</SummaryRow>
      {rows.map(([label, value, clamp]) => (
        <SummaryRow key={label} label={label} className={clamp}>
          {value}
        </SummaryRow>
      ))}
    </>
  );
}

function SummaryRow({ label, className, children }: { label: string; className?: string; children: string }) {
  return (
    <div className="mb-[14px] flex flex-col gap-1">
      <span className="font-sans text-[10px] tracking-[1.5px] text-muted-2">{label}</span>
      <span className={`font-sans text-[13px] leading-[1.5] text-ink-3 ${className ?? ""}`}>{children}</span>
    </div>
  );
}
