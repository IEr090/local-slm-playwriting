import { genreLabel } from "@/features/story/model/labels";
import type { Outline } from "@/features/story/model/types";

/** The approved outline, collapsed into the left column next to the acts; it is final and read-only.
 * Every field is shown in full; the column scrolls. */
export function OutlineSummary({ outline: o }: { outline: Outline }) {
  const rows: [string, string][] = [
    ["TONE", o.tone],
    ["TIME & WORLD", o.time_and_world],
    ["CONFLICT", o.central_conflict],
    ["SYNOPSIS", o.synopsis],
  ];
  return (
    <>
      <span className="font-sans text-[11px] tracking-[2px] text-muted-2">THE PLAY</span>
      <h2 className="mt-[14px] mb-0 font-serif text-[32px] leading-[1.05] font-medium">{o.title || "Untitled play"}</h2>
      <div className="mt-[10px] font-serif text-[19px] leading-[1.3] text-gold-soft italic">{o.premise}</div>
      <div className="dotted-rule mt-5 mb-4" />
      <SummaryRow label="GENRE">{genreLabel(o.genre)}</SummaryRow>
      {rows.map(([label, value]) => (
        <SummaryRow key={label} label={label}>
          {value}
        </SummaryRow>
      ))}
    </>
  );
}

function SummaryRow({ label, children }: { label: string; children: string }) {
  return (
    <div className="mb-[14px] flex flex-col gap-1">
      <span className="font-sans text-[10px] tracking-[1.5px] text-muted-2">{label}</span>
      <span className="font-sans text-[13px] leading-[1.5] text-ink-3">{children}</span>
    </div>
  );
}
