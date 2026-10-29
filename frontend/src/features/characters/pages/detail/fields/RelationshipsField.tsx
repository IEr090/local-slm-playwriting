import { useState } from "react";
import { relationOptions } from "@/features/characters/model/relationships";
import { fullName } from "@/features/characters/model/text";
import type { Character, CharacterCard, Relationship } from "@/features/characters/model/types";
import { CharacterCombobox } from "./CharacterCombobox";
import { TextField } from "@/shared/ui/fields/TextField";

interface RelationshipsFieldProps {
  selfId: string;
  relationships: Relationship[];
  cast: Character[];
  cards: Record<string, CharacterCard>;
  onChange(relationships: Relationship[]): void;
}

/** Rows "character + description". Characters are stored by id; the name is looked up for display. */
export function RelationshipsField({ selfId, relationships, cast, cards, onChange }: RelationshipsFieldProps) {
  const [picking, setPicking] = useState<number | null>(null);
  const [query, setQuery] = useState("");

  const nameOf = (id: string) => {
    const target = cast.find((c) => c.id === id);
    return target ? fullName(target) : "";
  };
  const setRow = (i: number, patch: Partial<Relationship>) =>
    onChange(relationships.map((r, ri) => (ri === i ? { ...r, ...patch } : r)));
  const openPicker = (i: number | null) => {
    setPicking(i);
    setQuery("");
  };

  return (
    <>
      <div className="flex flex-col">
        {relationships.map((rel, i) => (
          <div key={i} className="flex items-start gap-[14px] border-t border-dotted border-line-subtle py-2 first:border-t-0">
            <CharacterCombobox
              label={nameOf(rel.character_id)}
              open={picking === i}
              onOpenChange={(open) => openPicker(open ? i : null)}
              options={picking === i ? relationOptions(cast, selfId, relationships, i, query) : []}
              cards={cards}
              query={query}
              onQueryChange={setQuery}
              onPick={(characterId) => {
                setRow(i, { character_id: characterId });
                openPicker(null);
              }}
            />
            <TextField
              rows={1}
              label="Relationship"
              placeholder="Describe the relationship"
              lined
              value={rel.description}
              onChange={(description) => setRow(i, { description })}
              className="flex-1 pt-[3px]"
            />
            <button
              type="button"
              aria-label="Remove relationship"
              onClick={() => {
                onChange(relationships.filter((_, ri) => ri !== i));
                openPicker(null);
              }}
              className="border-none bg-transparent px-1 py-[2px] text-sm text-placeholder hover:text-ink-2"
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={() => {
          onChange([...relationships, { character_id: "", description: "" }]);
          openPicker(relationships.length);
        }}
        className="self-start rounded-full border border-dashed border-line-strong bg-transparent px-[14px] py-[6px] font-sans text-[11px] tracking-[1px] text-muted-2 hover:border-gold hover:text-gold-soft"
      >
        + Add relationship
      </button>
    </>
  );
}
