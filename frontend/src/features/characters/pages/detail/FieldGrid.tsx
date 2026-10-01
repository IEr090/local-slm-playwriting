import { Chip } from "@/shared/ui/Chip";
import { GENDER_LABEL, roleLabel } from "@/features/characters/model/labels";
import { DRAMATIC_ROLES, GENDERS, type Character, type CharacterCard } from "@/features/characters/model/types";
import { FieldCard } from "./FieldCard";
import { RelationshipsField } from "./fields/RelationshipsField";
import { SerifInput } from "./fields/SerifInput";
import { TextField } from "./fields/TextField";

type Patch = Partial<Omit<Character, "id">>;

interface FieldGridProps {
  character: Character;
  cast: Character[];
  cards: Record<string, CharacterCard>;
  onChange(patch: Patch): void;
  /** Fields to glow after an AI revision. */
  highlighted?: readonly (keyof Character)[];
}

type TextKey = {
  [K in keyof Character]: Character[K] extends string ? K : never;
}[keyof Character];

/** The 16 always-editable field cards in two sections. */
export function FieldGrid({ character: c, cast, cards, onChange, highlighted = [] }: FieldGridProps) {
  const text = (key: TextKey, num: number, label: string, rows: number, span: 2 | 4, hint?: string) => (
    <FieldCard
      num={num}
      label={label}
      hint={hint}
      highlighted={highlighted.includes(key)}
      className={span === 4 ? "col-span-4" : "col-span-2"}
    >
      <TextField rows={rows} label={label} value={c[key]} onChange={(value) => onChange({ [key]: value })} />
    </FieldCard>
  );

  return (
    <div className="grid grid-cols-4 gap-3">
      <SectionHeading numeral="I" title="BASIC PROFILE" />

      {/* Row 1 on one line. Name · Surname fill exactly the left column (same edges as field 5);
          Age (narrow) · Gender fill the right column. */}
      <FieldCard num={1} label="Name" compact>
        <SerifInput
          aria-label="Name"
          size={8}
          placeholder="First name"
          value={c.name}
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </FieldCard>
      <FieldCard num={2} label="Surname" compact>
        <SerifInput
          aria-label="Surname"
          size={8}
          placeholder="Surname"
          value={c.surname}
          onChange={(e) => onChange({ surname: e.target.value })}
        />
      </FieldCard>
      <div className="col-span-2 grid grid-cols-[92px_minmax(0,1fr)] gap-3">
        <FieldCard num={3} label="Age" compact>
          <SerifInput
            aria-label="Age"
            size={3}
            inputMode="numeric"
            className="text-center"
            value={c.age ?? ""}
            onChange={(e) => {
              const digits = e.target.value.replace(/\D/g, "").slice(0, 3);
              onChange({ age: digits ? Number(digits) : null });
            }}
          />
        </FieldCard>
        <FieldCard num={4} label="Gender" compact className="gap-[6px]">
          <div className="flex gap-[6px]" role="group" aria-label="Gender">
            {GENDERS.map((g) => (
              <Chip key={g} selected={c.gender === g} onClick={() => onChange({ gender: g })} className="px-[10px] py-[5px]">
                {GENDER_LABEL[g]}
              </Chip>
            ))}
          </div>
        </FieldCard>
      </div>

      {text("nationality_background", 5, "Nationality / Background", 2, 2)}
      {text("occupation_social_role", 6, "Occupation / Social role", 2, 2)}
      {text("appearance", 7, "Appearance", 4, 2)}
      {text("personality", 8, "Personality", 4, 2)}
      {text("biography", 9, "Biography", 3, 4, "KEY EVENTS ONLY")}

      <SectionHeading numeral="II" title="DRAMATIC PROFILE" className="mt-[14px]" />

      <FieldCard
        num={10}
        label="Dramatic role"
        className="col-span-4"
        highlighted={highlighted.includes("dramatic_role") || highlighted.includes("dramatic_role_description")}
      >
        <div className="flex flex-wrap gap-[6px]" role="group" aria-label="Dramatic role">
          {DRAMATIC_ROLES.map((role) => (
            <Chip key={role} selected={c.dramatic_role === role} onClick={() => onChange({ dramatic_role: role })}>
              {roleLabel(role).toUpperCase()}
            </Chip>
          ))}
        </div>
        <TextField
          rows={2}
          label="Dramatic role description"
          value={c.dramatic_role_description}
          onChange={(value) => onChange({ dramatic_role_description: value })}
          className="text-ink-2"
        />
      </FieldCard>

      {text("goal", 11, "Goal", 4, 2, "WHAT")}
      {text("motivation", 12, "Motivation", 4, 2, "WHY")}
      {text("fear_weakness", 13, "Fear / Weakness", 5, 2)}
      {text("internal_conflict", 14, "Internal conflict", 5, 2)}

      <FieldCard
        num={15}
        label="Relationships"
        hint={`${c.relationships.length} ${c.relationships.length === 1 ? "LINK" : "LINKS"}`}
        className="col-span-4"
      >
        <RelationshipsField
          selfId={c.id}
          relationships={c.relationships}
          cast={cast}
          cards={cards}
          onChange={(relationships) => onChange({ relationships })}
        />
      </FieldCard>

      {text("character_arc", 16, "Character arc", 3, 4)}
    </div>
  );
}

function SectionHeading({ numeral, title, className = "" }: { numeral: string; title: string; className?: string }) {
  return (
    <div className={`col-span-4 mt-[6px] mb-[2px] flex items-center gap-[14px] ${className}`}>
      <span className="font-serif text-xl text-gold italic">{numeral}</span>
      <span className="font-sans text-[11px] tracking-[3px] text-ink-2">{title}</span>
      <span className="dotted-rule flex-1" />
    </div>
  );
}
