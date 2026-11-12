import { cn } from "@/shared/lib/utils";
import { TextField } from "@/shared/ui/fields/TextField";
import { GenerationVeil } from "@/shared/ui/GenerationVeil";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { ArrowRight } from "@/shared/ui/icons";

export interface ActCardProps {
  roman: string;
  name: string;
  /** Status from the Story Bible, e.g. "STRUCTURE APPROVED"; empty for a placeholder. */
  status: string;
  summary: string;
  /** Hand edits of the summary, only before the acts are approved; without it the summary is plain text. */
  onSummaryChange?(summary: string): void;
  /** Veil while the act is drafted, staged, written or recorded. */
  veil?: { label: string; line: string } | null;
  highlighted?: boolean;
  /** Acts after the one being built. */
  dimmed?: boolean;
  /** The act's page can be opened: gold border and the OPEN / READ pill. */
  open?: { label: string; aria: string; onOpen(): void } | null;
  /** The structure could not be generated: a pill to try again. */
  retry?: { label: string; onRetry(): void } | null;
  /** The act cannot be worked on yet: a click explains why. */
  onLockedClick?(): void;
}

/** One act of the play: italic roman numeral, name and status, the summary. */
export function ActCard({
  roman,
  name,
  status,
  summary,
  onSummaryChange,
  veil = null,
  highlighted = false,
  dimmed = false,
  open = null,
  retry = null,
  onLockedClick,
}: ActCardProps) {
  return (
    <article
      onClick={onLockedClick}
      className={cn(
        "relative grid grid-cols-[52px_minmax(0,1fr)] gap-x-4 rounded-[10px] border border-line bg-card py-5 pr-[22px] pl-[18px]",
        "transition-[border-color,background-color,box-shadow] duration-200 hover:border-line-hover",
        onSummaryChange && "focus-within:border-gold focus-within:bg-card-focus",
        open && "border-gold/60",
        highlighted && "border-gold shadow-[0_0_0_1px_#c9a24b,0_0_24px_#c9a24b44] hover:border-gold",
        veil && "min-h-[190px]",
      )}
    >
      <div aria-hidden className="pt-[2px] text-center font-serif text-4xl leading-none text-gold italic">
        {roman}
      </div>
      <div className={cn("flex min-w-0 flex-col gap-3 transition-opacity duration-500", dimmed && "opacity-55")}>
        <div className="flex flex-wrap items-center gap-[14px]">
          <span className="font-serif text-2xl leading-none font-medium">{name}</span>
          <span className={cn("ml-auto font-sans text-[10px] tracking-[1.5px]", status === "DRAFT" ? "text-muted-2" : "text-gold")}>
            {status}
          </span>
        </div>
        {onSummaryChange ? (
          <TextField rows={2} label={`Summary of ${name}`} value={summary} onChange={onSummaryChange} />
        ) : (
          <p className="m-0 font-sans text-[13px] leading-[1.55] whitespace-pre-line text-ink">{summary}</p>
        )}
        {(open || retry) && (
          <div className="flex animate-fade-up justify-end">
            {open && (
              <HeaderPill aria-label={open.aria} onClick={open.onOpen}>
                {open.label}
                <ArrowRight />
              </HeaderPill>
            )}
            {retry && <HeaderPill onClick={retry.onRetry}>{retry.label}</HeaderPill>}
          </div>
        )}
      </div>
      <GenerationVeil show={!!veil} label={veil?.label ?? ""} line={veil?.line ?? ""} />
    </article>
  );
}
