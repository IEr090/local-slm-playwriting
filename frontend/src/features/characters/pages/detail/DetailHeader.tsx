import { ArrowLeft, Spark } from "@/shared/ui/icons";
import { RoundIconButton } from "@/shared/ui/RoundIconButton";
import { fullName, headLine } from "@/features/characters/model/text";
import { roleLabel } from "@/features/characters/model/labels";
import type { Character } from "@/features/characters/model/types";

interface DetailHeaderProps {
  character: Character;
  index: number;
  total: number;
  chatOpen: boolean;
  /** "CREATE" for a new character, "SAVE" for an existing one. */
  saveLabel: string;
  saveDisabled: boolean;
  onAll(): void;
  onSave(): void;
  onToggleChat(): void;
}

/** Fixed header; name and line update live while typing. */
export function DetailHeader({
  character,
  index,
  total,
  chatOpen,
  saveLabel,
  saveDisabled,
  onAll,
  onSave,
  onToggleChat,
}: DetailHeaderProps) {
  const chatLabel = chatOpen ? "Hide AI chat" : "Show AI chat";
  return (
    <div className="relative flex items-end justify-between border-b border-dotted border-line-strong px-12 pt-[34px] pb-[18px]">
      <div className="min-w-0">
        <div className="flex items-center gap-[14px]">
          <span className="font-sans text-[11px] tracking-[2px] text-muted-2">
            CHARACTER {index + 1} OF {total}
          </span>
          <span className="rounded-full border border-gold/40 px-[10px] py-[3px] font-sans text-[10px] tracking-[2.5px] text-gold">
            {roleLabel(character.dramatic_role).toUpperCase()}
          </span>
        </div>
        <h1 className="mt-2 mb-0 font-serif text-[46px] leading-none font-medium">
          {fullName(character) || "Unnamed character"}
        </h1>
        <div className="mt-2 min-h-[1lh] font-sans text-[13px] text-muted">{headLine(character)}</div>
      </div>

      <div className="mb-1 flex shrink-0 items-center gap-[10px]">
        <button
          type="button"
          onClick={onAll}
          className="box-border inline-flex h-10 items-center justify-center gap-[10px] rounded-full border border-line-strong bg-transparent px-5 font-sans text-[11px] leading-none tracking-[2px] whitespace-nowrap text-ink-2 transition-colors duration-150 hover:border-gold hover:text-gold"
        >
          <ArrowLeft className="block shrink-0" />
          <span>ALL CHARACTERS</span>
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saveDisabled}
          className="box-border inline-flex h-10 items-center justify-center rounded-full border border-gold bg-transparent px-5 font-sans text-[11px] leading-none tracking-[2px] whitespace-nowrap text-gold transition-[background-color,opacity] duration-150 hover:bg-gold/[0.133] disabled:cursor-default disabled:opacity-35 disabled:hover:bg-transparent"
        >
          {saveLabel}
        </button>
        <RoundIconButton active={chatOpen} onClick={onToggleChat} aria-label={chatLabel} title={chatLabel}>
          <Spark />
        </RoundIconButton>
      </div>
    </div>
  );
}
