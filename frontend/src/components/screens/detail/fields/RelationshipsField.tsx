import { ChevronDown } from "@/components/common/icons";
import { fullName } from "@/lib/text";
import type { Character, Relationship } from "@/types/character";
import { TextField } from "./TextField";

interface RelationshipsFieldProps {
  relationships: Relationship[];
  cast: Character[];
  onChange(relationships: Relationship[]): void;
}

/** Rows "character + description". Characters are stored by id; the name is looked up for display. */
export function RelationshipsField({ relationships, cast, onChange }: RelationshipsFieldProps) {
  const nameOf = (id: string) => {
    const target = cast.find((c) => c.id === id);
    return target ? fullName(target) : "";
  };
  const setRow = (i: number, patch: Partial<Relationship>) =>
    onChange(relationships.map((r, ri) => (ri === i ? { ...r, ...patch } : r)));

  return (
    <>
      <div className="flex flex-col">
        {relationships.map((rel, i) => {
          const who = nameOf(rel.character_id);
          return (
            <div key={i} className="flex items-start gap-[14px] border-t border-dotted border-line-subtle py-2 first:border-t-0">
              <div className="relative w-[180px] shrink-0">
                {/* the character picker (combobox) arrives in block 5 */}
                <button
                  type="button"
                  aria-label="Change character"
                  className={`inline-flex max-w-full items-center gap-[6px] border-0 border-b border-dotted border-line-strong bg-transparent p-0 pb-[2px] text-left font-serif text-lg hover:border-gold ${who ? "text-gold-light" : "text-faint"}`}
                >
                  <span>{who || "Choose character"}</span>
                  <ChevronDown className="text-muted-2" />
                </button>
              </div>
              <TextField
                rows={1}
                label="Relationship"
                value={rel.description}
                onChange={(description) => setRow(i, { description })}
                className="flex-1 pt-[3px]"
              />
              <button
                type="button"
                aria-label="Remove relationship"
                onClick={() => onChange(relationships.filter((_, ri) => ri !== i))}
                className="border-none bg-transparent px-1 py-[2px] text-sm text-placeholder hover:text-ink-2"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        onClick={() => onChange([...relationships, { character_id: "", description: "" }])}
        className="self-start rounded-full border border-dashed border-line-strong bg-transparent px-[14px] py-[6px] font-sans text-[11px] tracking-[1px] text-muted-2 hover:border-gold hover:text-gold-soft"
      >
        + Add relationship
      </button>
    </>
  );
}
