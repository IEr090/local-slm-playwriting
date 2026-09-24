import { Command as CommandPrimitive } from "cmdk";
import { useRef, useState } from "react";
import { ChevronDown } from "@/components/common/icons";
import { Command, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { fullName } from "@/lib/text";
import { cn } from "@/lib/utils";
import type { Character, CharacterCard } from "@/types/character";

interface CharacterComboboxProps {
  /** Name shown on the button; "" → "Choose character". */
  label: string;
  open: boolean;
  onOpenChange(open: boolean): void;
  /** Characters allowed for this row (see lib/relationships.ts); filtered by `query`. */
  options: Character[];
  cards: Record<string, CharacterCard>;
  query: string;
  onQueryChange(query: string): void;
  onPick(characterId: string): void;
}

/**
 * Relationship target picker: click the name → search field + list of the other characters.
 * Only list items can be chosen (no free text). Enter picks the first match (or the one moved to with
 * the arrow keys), Escape closes.
 */
export function CharacterCombobox({
  label,
  open,
  onOpenChange,
  options,
  cards,
  query,
  onQueryChange,
  onPick,
}: CharacterComboboxProps) {
  // Highlighted item; falls back to the first match whenever it is not in the list.
  const [active, setActive] = useState("");
  const anchor = useRef<HTMLDivElement>(null);
  const highlighted = options.some((o) => o.id === active) ? active : (options[0]?.id ?? "");

  return (
    <Command
      shouldFilter={false}
      loop
      value={highlighted}
      onValueChange={setActive}
      className="h-auto w-[180px] shrink-0 overflow-visible rounded-none! bg-transparent p-0 text-ink"
    >
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverAnchor asChild>
          <div ref={anchor} className="relative w-full">
            {open ? (
              <CommandPrimitive.Input
                autoFocus
                value={query}
                onValueChange={onQueryChange}
                placeholder="Type a name…"
                aria-label="Choose character"
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    e.preventDefault();
                    onOpenChange(false);
                  }
                }}
                className="box-border w-full rounded-md border border-gold bg-well px-2 py-1 font-serif text-[17px] text-ink placeholder:text-faint focus:outline-none"
              />
            ) : (
              <button
                type="button"
                aria-label="Change character"
                onClick={() => onOpenChange(true)}
                className={cn(
                  "inline-flex max-w-full items-center gap-[6px] border-0 border-b border-dotted border-line-strong bg-transparent p-0 pb-[2px] text-left font-serif text-lg hover:border-gold",
                  label ? "text-gold-light" : "text-faint",
                )}
              >
                <span>{label || "Choose character"}</span>
                <ChevronDown className="text-muted-2" />
              </button>
            )}
          </div>
        </PopoverAnchor>

        <PopoverContent
          align="start"
          sideOffset={4}
          // keep focus in the search field
          onOpenAutoFocus={(e) => e.preventDefault()}
          onCloseAutoFocus={(e) => e.preventDefault()}
          // clicks in the search field are not "outside"
          onInteractOutside={(e) => {
            if (anchor.current?.contains(e.target as Node)) e.preventDefault();
          }}
          className="w-[260px] gap-0 rounded-lg border border-line-strong bg-card-focus p-1 shadow-[0_10px_30px_#000000aa] ring-0"
        >
          <CommandList className="max-h-72">
            {options.map((c) => (
              <CommandItem
                key={c.id}
                value={c.id}
                onMouseDown={(e) => e.preventDefault()}
                onSelect={() => onPick(c.id)}
                className="flex cursor-pointer flex-col items-start gap-px rounded-md px-[10px] py-[7px] data-selected:bg-gold/10 [&>svg:last-child]:hidden"
              >
                <span className="font-serif text-[17px] text-ink">{fullName(c)}</span>
                <span className="font-sans text-[10px] tracking-[1px] text-muted-2">
                  {(cards[c.id]?.tagline ?? "").toUpperCase()}
                </span>
              </CommandItem>
            ))}
            {options.length === 0 && (
              <div className="px-[10px] py-2 font-sans text-xs text-faint">No character with this name</div>
            )}
          </CommandList>
        </PopoverContent>
      </Popover>
    </Command>
  );
}
